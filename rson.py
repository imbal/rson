from collections import namedtuple, OrderedDict, defaultdict
from datetime import datetime, timedelta, timezone

import re
import io
import base64


whitespace = re.compile(r"(?:\ |\t|\r?\n|#[^\r\n]*(?:\r?\n|$))+")
int_b2 = re.compile(r"[-+]?0b[01_]+")
int_b8 = re.compile(r"[-+]?0o[0-7_]+")
int_b16 = re.compile(r"[-+]?0x[0-9a-fA-F_]+")
flt_b16 = re.compile(r"\.[0-9a-fA-F_]+[pP](?:\+|-)?[\d_]+")
int_b10 = re.compile(r"[-+]?(?!0[box])\d[\d_]*")
flt_b10 = re.compile(r"\.[\d_]+(?:[eE](?:\+|-)?[\d+_])?")
string_dq = re.compile(r'"(?:[^"\\\n]|\\(?:[\'"\\/bfnrt\n]|x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}))*"')
string_sq = re.compile(r"'(?:[^'\\\n]|\\(?:[\"'\\/bfnrt\n]|x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}))*'")
decorator_name = re.compile(r"@(?!\d)\w+[ ]+")
identifier = re.compile(r"(?!\d)\w+")
builtin_names = {'null':None,'true':True,'false':False}

builtin_decorators = set("""
        bool
        int
        float
        complex

        string
        bytestring
        base64

        duration
        datetime

        set
        dict
        list
        table

        object
    """.split())

class SyntaxErr(Exception):
    def __init__(self, buf, pos):
        self.buf = buf
        self.pos = pos
        Exception.__init__(self)

class SemanticErr(Exception):
    def __init__(self, name, item):
        self.name = name
        self.item = item
        Exception.__init__(self)

class Decorated:
    def __init__(self, name, value):
        self.name = name
        self.value = value

def decorate_object(name, item):
    if name == 'table':
        return item
    elif name == 'hash':
        return dict(item)
    elif name in builtin_decorators:
        raise SemanticErr(name, item)
    else:
        return Decorated(name, item)

def decorate_list(name, item):
    if name == 'list':
        return item
    elif name == 'set':
        out = set()
        for x in item:
            if x in out:
                raise SemanticErr('duplicate', x)
            out.add(x)
        return out
    elif name == 'complex':
        return complex(item[0], item[1])
    elif name in builtin_decorators:
        raise SemanticErr(name, item)
    else:
        return Decorated(name, item)

def decorate_string(name, item):
    if name == 'string':
        return item
    elif name == 'bytestring':
        return item.encode('latin-1')
    elif name == 'base64':
        return base64.standard_b64decode(item)
    elif name == 'datetime':
        if item[-1].lower() == 'z':
            if '.' in item:
                date, sec = item[:-1].split('.')
                date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
                sec = float("0."+sec)
                return date + timedelta(seconds=sec)
            else:
                return datetime.strptime(item, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        else:
            raise SemanticErr(name, item)

    elif name == 'float':
        if item.lower() in ('nan','-inf','+inf','inf'):
            return float(item)
        else:
            raise SemanticErr(name, item)
    elif name in builtin_decorators:
        raise SemanticErr(name, item)
    else:
        return Decorated(name, item)

def decorate_number(name, item):
    if name == 'int':
        return int(item)
    elif name == 'float':
        return float(item)
    elif name == 'duration':
        return timedelta(seconds=item)
    elif name in builtin_decorators:
        raise SemanticErr(name, item)
    else:
        return Decorated(name, item)

def decorate_builtin(name, item):
    if name == 'bool' and item in (True,False):
        return item
    elif name == 'object' and item is None:
        return item
    elif name in builtin_decorators:
        raise SemanticErr(name, item)
    else:
        return Decorated(name, item)

def parse_rson(buf, pos):
    m = whitespace.match(buf,pos)
    if m:
        pos = m.end()

    chr = buf[pos]
    name = None
    if chr == '@':
        m = decorator_name.match(buf, pos)
        if m:
            pos = m.end()
            name = buf[m.start()+1:pos].rstrip()
        else:
            raise SyntaxErr(buf, pos)

    chr = buf[pos]

    if chr == '{':
        out = OrderedDict()
        pos+=1
        m = whitespace.match(buf,pos)
        if m:
            pos = m.end()

        while buf[pos] != '}':
            key, pos = parse_rson(buf, pos)

            m = whitespace.match(buf,pos)
            if m:
                pos = m.end()

            chr = buf[pos]
            if chr == ':':
                pos +=1
                m = whitespace.match(buf,pos)
                if m:
                    pos = m.end()
            else:
                raise SyntaxErr(buf, pos)

            item, pos = parse_rson(buf, pos)
            if key in out:
                raise SemanticErr('duplicate',key)

            out[key]=item

            chr = buf[pos]
            if chr == ',':
                pos +=1
                m = whitespace.match(buf,pos)
                if m:
                    pos = m.end()
            elif chr != '}':
                raise SyntaxErr(buf, pos)
        if name:
            out = decorate_object(name,  out)
        return out, pos+1

    elif chr == '[':
        out = []
        pos+=1
        m = whitespace.match(buf,pos)
        if m:
            pos = m.end()
        while buf[pos] != ']':
            item, pos = parse_rson(buf, pos)
            out.append(item)

            m = whitespace.match(buf,pos)
            if m:
                pos = m.end()

            chr = buf[pos]
            if chr == ',':
                pos +=1
                m = whitespace.match(buf,pos)
                if m:
                    pos = m.end()
            elif chr != ']':
                raise SyntaxErr(buf, pos)
        if name:
            out = decorate_list(name,  out)
        return out, pos+1

    elif chr == "'":
        m = string_sq.match(buf, pos)
        if m:
            end = m.end()
            out = parse_rson_string(name, buf[pos:end])
            if name:
                out = decorate_string(name,  out)
            return out, end

    elif chr == '"':
        m = string_dq.match(buf, pos)
        if m:
            end = m.end()
            out = parse_rson_string(name, buf[pos:end])
            if name:
                out = decorate_string(name,  out)
            return out, end

    elif chr in "-+0123456789":
        m = int_b16.match(buf, pos)
        if m:
            t = flt_b16.match(buf, m.end())
            if t:
                end = t.end()
                out = parse_rson_float(buf[pos:end])
                if name:
                    out = decorate_float(name,  out)
                return out, end

            else:
                end = m.end()
                out = parse_rson_int(buf[pos:end])
                if name:
                    out = decorate_number(name,  out)
                return out, end

        m = int_b8.match(buf, pos)
        if m:
            end = m.end()
            out = parse_rson_int(buf[pos:end])
            if name:
                out = decorate_number(name,  out)
            return out, end

        m = int_b2.match(buf, pos)
        if m:
            end = m.end()
            out = parse_rson_int(buf[pos:end])
            if name:
                out = decorate_number(name,  out)
            return out, end

        m = int_b10.match(buf, pos)
        if m:
            t = flt_b10.match(buf, m.end())
            if t:
                end = t.end()
                out = parse_rson_float(buf[pos:end])
                if name:
                    out = decorate_number(name,  out)
                return out, end

            else:
                end = m.end()
                out = parse_rson_int(buf[pos:end])
                if name:
                    out = decorate_number(name,  out)
                return out, end

    else:
        m = identifier.match(buf, pos)
        if m:
            end = m.end()
            item = buf[pos:end]
            if item in builtin_names:
                out = builtin_names[item]
                if name:
                    out = decorate_builtin(name,  out)
                return out, end

    raise SyntaxErr(buf, pos)


def parse_rson_string(name, buf):
    # XXX: replace escapes properly.
    return eval(buf.replace(r'\x',r'\u00'))

def parse_rson_int(buf):
    if buf.startswith('0x'):
        return int(buf[2:].replace('_',''), 16)
    elif buf.startswith('0o'):
        return int(buf[2:].replace('_',''), 8)
    elif buf.startswith('0b'):
        return int(buf[2:].replace('_',''), 2)
    else:
        return int(buf.replace('_',''))

def parse_rson_float(buf):
    if buf.startswith(('0x','+0x','-0x')):
        return float.fromhex(buf.replace('_',''))
    else:
        return float(buf.replace('_',''))

def parse(buf):
    obj, pos = parse_rson(buf, 0)

    m = whitespace.match(buf,pos)
    if m:
        pos = m.end()
        m = whitespace.match(buf,pos)

    if pos != len(buf):
        print(buf[pos:])
        raise SyntaxErr(buf, pos)

    return obj


def dump(obj):
    pass

def dump_rson(obj,buf):
    pass

def test_parse(buf, obj):
    print(repr(buf), '->', obj)
    out = parse(buf)

    if (obj != obj and out == out) or (obj == obj and obj != out):
        raise AssertionError('{} != {}'.format(parse(buf),obj))

def main():
    test_parse("0",0)
    test_parse("0x0_1_2_3",0x123)
    test_parse("0o0_1_2_3",0o123)
    test_parse("0b0_1_0_1",5)
    test_parse("0 #comment",0)
    test_parse("0.0",0.0)
    test_parse("-0.0",-0.0)
    test_parse("'foo'","foo")
    test_parse("''","")
    test_parse("[1]",[1])
    test_parse("[1,]",[1])
    test_parse("[]",[])
    test_parse("[1,2,3,4,4]",[1,2,3,4,4])
    test_parse("{'a':1,'b':2}",dict(a=1,b=2))
    test_parse("@set [1,2,3,4]",set([1,2,3,4]))
    test_parse("{'a':1,'b':2}",dict(a=1,b=2))
    test_parse("@complex [1,2]",1+2j)
    test_parse("@bytestring 'foo'",b"foo")
    test_parse("@base64 '{}'".format(base64.standard_b64encode(b'foo').decode('ascii')),b"foo")
    test_parse("@float 'NaN'",float('NaN'))
    test_parse("@float '-inf'",float('-Inf'))
    obj = datetime.now().astimezone(timezone.utc)
    test_parse('@datetime "{}"'.format(obj.strftime("%Y-%m-%dT%H:%M:%S.%fZ")), obj)
    obj = timedelta(seconds=666)
    test_parse('@duration {}'.format(obj.total_seconds()), obj)



if __name__ == '__main__':
    main()
