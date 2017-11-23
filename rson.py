r"""
RSON: Restructured Object Notation

JSON:
 - true, false, null
 - "strings" with \" \\\b \f \n \r \t \uFFFF, no control codes
 - numbers (unary minus, no leading 0's)
 - [ lists, ]   {"objects":"..."} with only string keys
 - list or object as root item

RSON:
 - byte order mark is whitespace
 - any value as root object
 - use `#....` as comments
 - decorators: tags on existing values: `@float "NaN"` 
 - new optional types through decorators: datetime, period, set, dict, complex

RSON strings:
 - \UFFFFFFFF \xFF \' escapes
 - \xFF is \u00FF
 - use ''s or ""s
 - \ at end of line is continuation

RSON numbers:
 - allow leading zero, underscores (except leading digits)
 - allow unary minus, plus
 - binary: 0b1010
 - octal: 0o777
 - hex: 0xFF and C99 style hex floats
 - decorated strings for special floats: `@float "NaN"`

RSON lists:
 - allow trailing commas

RSON objects:
 - like JSON, string only keys
 - no duplicate keys
 - insertion order must be preserved
 - allow trailing commas

RSON decorated objects:
 - allow objects to be 'decorated', via a named tag
 - whitespace between decorator name and object is *mandatory*
 - do not nest

 - all built in types have names reserved, used for special values
 - `@foo.foo {"foo":1}` name is any unicode letter/digit, or a .
 - `@int 1`, `@string "two"` are just `1` and `"two"`

 - parsers may reject unknown, or return a wrapped object 

RSON sets (optional):
 - `@set [1,2,3]`
 - always a decorated list
 - no duplicate items

RSON dicts (optional):
 - `@dict {"a":1}` or `@dict [["a",1],...]`
 - keys must be in lexical order
 - keys must be comparable, (usually means same type, all string, all number)

RSON datetimes/periods (optional):
 - `@datetime "2017-11-22T23:32:07.100497Z"`
 - `@duration 60` (in seconds)
 - UTC must be supported, using `Z` prefix
 - MAY support RFC 3339

RSON bytestrings (optional):
 - `@base64 "...=="`
 - `@bytestring "....\xff"` (cannot have codepoints >255)

RSON complex numbers: (optional)
 - `@complex [0,1]`

RSON Builtin Decorators:
 - `@bool` on true, or false
 - `@complex` on null

 - @int, @float on numbers
 - @duration on numbers

 - @string on strings
 - @float on strings, for NaN, -Inf, +Inf only
 - @datetime on strings
 - @base64 / @bytestring on strings

 - @set on lists
 - @complex on lists
 - @list on lists

 - @object on objects
 - @dict on objects

 - use of @bool, @int, @float, @complex, @string, @bytestring, @base64,
   @duration, @datetime, @set, @list, @dict, @object on other values
   is an error

"""

from collections import namedtuple, OrderedDict, defaultdict
from datetime import datetime, timedelta, timezone

import re
import io
import base64


class SyntaxErr(Exception):
    def __init__(self, buf, pos):
        self.buf = buf
        self.pos = pos
        Exception.__init__(self)

class SemanticErr(Exception):
    pass

class BadDecorator(SemanticErr):
    def __init__(self, name, reason):
        self.name = name
        SemanticErr.__init__(self,reason)

whitespace = re.compile(r"(?:\ |\t|\uFEFF|\r|\n|#[^\r\n]*(?:\r?\n|$))+")

int_b2 = re.compile(r"[-+]?0b[01][01_]*")
int_b8 = re.compile(r"[-+]?0o[0-7][0-7_]*")
int_b10 = re.compile(r"[-+]?(?!0[box])\d[\d_]*")
int_b16 = re.compile(r"[-+]?0x[0-9a-fA-F][0-9a-fA-F_]*")

flt_b10 = re.compile(r"\.[\d_]+(?:[eE](?:\+|-)?[\d+_])?")
flt_b16 = re.compile(r"\.[0-9a-fA-F_]+[pP](?:\+|-)?[\d_]+")

string_dq = re.compile(r'"(?:[^"\\\n\x00-\x1F]|\\(?:[\'"\\/bfnrt\n]|x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}))*"')
string_sq = re.compile(r"'(?:[^'\\\n\x00-\x1F]|\\(?:[\"'\\/bfnrt\n]|x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}))*'")

decorator_name = re.compile(r"@(?!\d)\w+[ ]+")
identifier = re.compile(r"(?!\d)[\w\.]+")

builtin_names = {'null':None,'true':True,'false':False}
builtin_values = {None:'null',True:'true',False: 'false'}

builtin_decorators = set("""
        bool int float complex
        string bytestring base64
        duration datetime
        set list dict object
""".split())

registered_decorators = OrderedDict() # names -> Classes (take name, value as args)
registered_classes = OrderedDict() # classes -> undecorators (get name, value)

class Decorated:
    def __init__(self, name, value):
        self.name = name
        self.value = value

registered_classes[Decorated] = lambda obj: (obj.name, obj.value)

def undecorate(obj):
   if obj.__class__ in registered_classes:
        und = registered_classes[obj.__class__]
        name, value = und(obj)
   else:
       raise SemanticErr("Can't undecorate {}: unknown class {}".format(obj, obj.__class__))

   if name not in builtin_decorators:
       return name, value
   else:
       raise BadDecorator(name,"Can't undecorate {}, as {} is reserved name".format(obj, name))
        
def decorate(name, value):
    if name in builtin_decorators:
        raise BadDecorator(name, "{} is reserved".format(name))

    if name in registered_decorators:
        dec = registered_decorators[name]
        return dec(name, value)
    else:
        return Decorated(name, value)

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

    if chr == '@':
        raise SyntaxErro(buf, pos)

    elif chr == '{':
        if name == 'object' or name not in builtin_decorators:
            out = OrderedDict()
        elif name == 'dict':
            out = dict()
        else:
            raise BadDecorator(name, "{} can't be used on objects".format(name))

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
                raise SemanticErr('duplicate key: {}'.format(key))

            out[key]=item

            chr = buf[pos]
            if chr == ',':
                pos +=1
                m = whitespace.match(buf,pos)
                if m:
                    pos = m.end()
            elif chr != '}':
                raise SyntaxErr(buf, pos)
        if name not in (None, 'object', 'dict'):
            out = decorate(name,  out)
        return out, pos+1

    elif chr == '[':
        if name in (None, 'list', 'complex') or name not in builtin_decorators:
            out = []
        elif name == 'set':
            out = set()
        else:
            raise BadDecorator(name, "{} can't be used on lists".format(name))

        pos+=1
        m = whitespace.match(buf,pos)
        if m:
            pos = m.end()
        while buf[pos] != ']':
            item, pos = parse_rson(buf, pos)
            if name == 'set':
                if item in out:
                    raise SemanticErr('duplicate item in set: {}'.format(item))
                else:
                    out.add(item)
            else:
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
        if name == 'complex':
            out = complex(*out)
        elif name not in (None, 'list', 'set'):
            out = decorate(name,  out)
        return out, pos+1

    elif chr == "'" or chr =='"':
        if name in (None, 'string', 'float', 'datetime') or name not in builtin_decorators:
            pass
        elif name in ('base64', 'bytestring'):
            pass
        else:
            raise BadDecorator(name, "{} can't be used on strings".format(name))

        if chr == "'":
            m = string_sq.match(buf, pos)
            if m:
                end = m.end()
            else:
                raise SyntaxErr(buf, pos)
        else:
            m = string_dq.match(buf, pos)
            if m:
                end = m.end()
            else:
                raise SyntaxErr(buf, pos)

        #XXX: all of this:
        out = eval(buf[pos:end].replace(r'\x',r'\u00'))

        if name == 'bytestring':
            out = out.encode('latin-1')
        elif name == 'base64':
            out= base64.standard_b64decode(out)
        elif name == 'datetime':
            if out[-1].lower() == 'z':
                if '.' in out:
                    date, sec = out[:-1].split('.')
                    date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
                    sec = float("0."+sec)
                    out = date + timedelta(seconds=sec)
                else:
                    out = datetime.strptime(out, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
            else:
                raise SemanticErr("invalid datetime: {}".format(out))
        elif name == 'float':
            if out.lower() in ('nan','-inf','+inf','inf'):
                out = float(out)
            else:
                raise SemanticErr("invalid float literal: {}".format(out))
        elif name not in (None, 'string', 'base64', 'bytestring'):
            out = decorate(name,  out)

        return out, end

    elif chr in "-+0123456789":
        if name in (None, 'int', 'float', 'duration') or name not in builtin_decorators:
            pass
        else:
            raise BadDecorator(name, "{} can't be used on numbers".format(name))

        m = int_b16.match(buf, pos)
        if m:
            t = flt_b16.match(buf, m.end())
            if t:
                end = t.end()
                out = parse_rson_float(name, buf[pos:end])
                if name not in (None, 'int', 'float', 'duration'):
                    out = decorate(out)
                return out, end

            else:
                end = m.end()
                out = parse_rson_int(name, buf[pos:end])
                if name not in (None, 'int', 'float', 'duration'):
                    out = decorate(out)
                return out, end

        m = int_b8.match(buf, pos)
        if m:
            end = m.end()
            out = parse_rson_int(name, buf[pos:end])
            if name not in (None, 'int', 'float', 'duration'):
                out = decorate(out)
            return out, end

        m = int_b2.match(buf, pos)
        if m:
            end = m.end()
            out = parse_rson_int(name, buf[pos:end])
            if name not in (None, 'int', 'float', 'duration'):
                out = decorate(out)
            return out, end

        m = int_b10.match(buf, pos)
        if m:
            t = flt_b10.match(buf, m.end())
            if t:
                end = t.end()
                out = parse_rson_float(name, buf[pos:end])
                if name not in (None, 'int', 'float', 'duration'):
                    out = decorate(out)
                return out, end

            else:
                end = m.end()
                out = parse_rson_int(name, buf[pos:end])
                if name not in (None, 'int', 'float', 'duration'):
                    out = decorate(out)
                return out, end

    else:
        m = identifier.match(buf, pos)
        if m:
            end = m.end()
            item = buf[pos:end]
        else:
            raise SyntaxErr(buf, pos)

        if item not in builtin_names:
            raise SyntaxErr(buf, pos)

        out = builtin_names[item]

        if name == 'object':
            if buf != 'null':
                raise BadDecorator('object','must be null or {}')
        elif name == 'bool':
            if buf not in ('true', 'false'): 
                raise BadDecorator('bool','must be true or false')
        elif name in builtin_decorators:
            raise BadDecorator(name, "{} can't be used on builtins".format(name))
        elif name is not None:
            out = decorate(name,  out)

        return out, end

    raise SyntaxErr(buf, pos)

def parse_rson_int(name, buf):
    if buf.startswith('0x'):
        out = int(buf[2:].replace('_',''), 16)
    elif buf.startswith('0o'):
        out = int(buf[2:].replace('_',''), 8)
    elif buf.startswith('0b'):
        out = int(buf[2:].replace('_',''), 2)
    else:
        out = int(buf.replace('_',''))

    if name == 'float':
        return float(item)
    elif name == 'duration':
        return timedelta(seconds=out)
    return out

def parse_rson_float(name, buf):
    if buf.startswith(('0x','+0x','-0x')):
        out = float.fromhex(buf.replace('_',''))
    else:
        out = float(buf.replace('_',''))

    if name == 'int':
        return int(item)
    elif name == 'duration':
        return timedelta(seconds=out)

    return out

def dump_rson(obj,buf):
    if obj is True or obj is False or obj is None:
        buf.write(builtin_values[obj])
    elif isinstance(obj, str):
        buf.write(repr(obj)) #fix escapes
    elif isinstance(obj, int):
        buf.write(str(obj))
    elif isinstance(obj, float):
        hex = obj.hex()
        if hex.startswith(('0','-')):
            buf.write(str(obj))
        else:
            buf.write('@float "{}"'.format(hex)) 
    elif isinstance(obj, complex):
        buf.write("@complex [{}, {}]".format(obj.real, obj.imag))
    elif isinstance(obj, bytes):
        buf.write('@base64 "')
        buf.write(base64.standard_b64encode(obj).decode('ascii'))
        buf.write('"')
    elif isinstance(obj,(list, tuple)):
        buf.write('[')
        first = True
        for x in obj:
            if first:
                first = False
            else:
                buf.write(", ")
            dump_rson(x, buf)
        buf.write(']')
    elif isinstance(obj, set):
        buf.write('@set [')
        first = True
        for x in obj:
            if first:
                first = False
            else:
                buf.write(", ")
            dump_rson(x, buf)
        buf.write(']')
    elif isinstance(obj, OrderedDict):
        buf.write('{')
        first = True
        for k,v in obj.items():
            if first:
                first = False
            else:
                buf.write(", ")
            dump_rson(k, buf)
            buf.write(": ")
            dump_rson(v, buf)
        buf.write('}')
    elif isinstance(obj, dict):
        buf.write('@dict {')
        first = True
        for k in sorted(obj.keys()):
            if first:
                first = False
            else:
                buf.write(", ")
            dump_rson(k, buf)
            buf.write(": ")
            dump_rson(obj[k], buf)
        buf.write('}')
    elif isinstance(obj, datetime):
        obj = obj.astimezone(timezone.utc)
        buf.write('@datetime "{}"'.format(obj.strftime("%Y-%m-%dT%H:%M:%S.%fZ")))
    elif isinstance(obj, timedelta):
        buf.write('@duration {}'.format(obj.total_seconds()))
    else:
        nv = undecorate(obj)
        name, value = nv
        buf.write('@{} '.format(name))
        dump_rson(value, buf)

def parse(buf):
    obj, pos = parse_rson(buf, 0)

    m = whitespace.match(buf,pos)
    if m:
        pos = m.end()
        m = whitespace.match(buf,pos)

    if pos != len(buf):
        raise SyntaxErr(buf, pos)

    return obj

def dump(obj):
    buf = io.StringIO('')
    dump_rson(obj, buf)
    return buf.getvalue()



# Tests

def test_parse(buf, obj):
    print(repr(buf), '->', obj)
    out = parse(buf)

    if (obj != obj and out == out) or (obj == obj and obj != out):
        raise AssertionError('{} != {}'.format(obj, out))

def test_dump(obj, buf):
    out = dump(obj)
    print(obj, 'dumps to ',repr(out))

    if buf != out:
        raise AssertionError('{} != {}'.format(buf, out))

def test_parse_err(buf, exc):
    try:
        obj = parse(buf)
    except Exception as e:
        if isinstance(e, exc):
            return
        else:
            raise AssertionError('{} did not cause {}, but '.format(buf,exc,e))
    else:
        raise AssertionError('{} did not cause {}, parsed:{}'.format(buf,exc, obj))

def test_dump_err(obj, exc):
    try:
        buf = dump(obj)
    except Exception as e:
        if isinstance(e, exc):
            return
        else:
            raise AssertionError('{} did not cause {}, but '.format(obj,exc,e))
    else:
        raise AssertionError('{} did not cause {}, dumping: {}'.format(obj,exc, buf))

def test_round(obj):
    buf0 = dump(obj)
    obj1 = parse(buf0)
    buf1 = dump(obj1)

    out = parse(buf1)
    print(obj)

    if obj != obj:
        if buf0 != buf1 or obj1 == obj1 or out == out:
            raise AssertionError('{} != {}'.format(obj, out))
    else:
        if buf0 != buf1:
            raise AssertionError('buf {} != {}'.format(buf0, buf1))
        if obj != obj1:
            raise AssertionError('buf {} != {}'.format(obj, obj1))
        if obj != out:
            raise AssertionError('buf {} != {}'.format(obj, out))
        
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
    test_parse("@bytestring 'fo\x20o'",b"fo o")
    test_parse((3000000.0).hex(), 3000000.0)
    test_parse(hex(123), 123)

    test_dump(1,"1")
    
    test_dump_err(Decorated('float', 123), BadDecorator)
    test_parse_err('@object "foo"', BadDecorator)

    for x in [
        0, -1, +1,
        -0.0, +0.0, 1.9,
        True, False, None,
        "str", b"bytes",
        [1,2,3], {"a":1}, set([1,2,3]), OrderedDict(a=1,b=2),
        1+2j,float('NaN'),
        datetime.now().astimezone(timezone.utc),
         timedelta(seconds=666),
    ]:
        test_round(x)
    
if __name__ == '__main__':
    main()
