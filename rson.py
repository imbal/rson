from collections import namedtuple, OrderedDict, defaultdict
import re

whitespace = re.compile(r"(?:\ |\t|\r?\n|\#[^\r\n]*\r?\n)+") 

int_b2 = re.compile(r"[-+]?0b[01_]+")
int_b8 = re.compile(r"[-+]?0o[0-7_]+")
int_b16 = re.compile(r"[-+]?0x[0-9a-fA-F_]+")
flt_b16 = re.compile(r"\.[0-9a-fA-F_]+[pP](?:\+|-)?[\d_]+")
int_b10 = re.compile(r"[-+]?\d[\d_]*")
flt_b10 = re.compile(r"\.[\d_]+(?:[eE](?:\+|-)?[\d+_])?")
string_dq = re.compile(r'"(?:[^"\\\n]|\\(?:[\'"\\/bfnrt\n]|x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}))*"')
string_sq = re.compile(r"'(?:[^'\\\n]|\\(?:[\"'\\/bfnrt\n]|x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}))*'")
decorator_name = re.compile(r"@(?!\d)\w+[ ]+")

class SyntaxErr(Exception):
    def __init__(self, buf, pos):
        self.buf = buf
        self.pos = pos
        Exception.__init__(self)

def parse_string(buf,start,end):
    # replace escapes properly.
    return eval(buf[start:end])

def parse_int(buf, pos, end, base):
    buf = buf[pos:end]
    if base == 10:
        return int(buf.replace('_',''), base)
    return int(buf[2:].replace('_',''), base)

def parse_float(buf, pos, end, base):
    buf = buf[pos:end]
    if base == 16:
        return float.fromhex(buf.replace('_',''))
    return float(buf.replace('_',''))

def decorate(name, item):
    #int / integer / float / double /
    # list / set / date / time / dict / table 
    # / bool / complex / string / bytestring
    # path / url

    if name == "complex":
        pass
    if name == "float":
        pass
    if name == 'int':
        pass
    if name == "duration":
        pass
    if name == "datetime":
        pass
    if name == "string":
        pass
    if name == "bytestring":
        pass
    if name == "dict":
        pass
    if name == "table":
        pass
    if name == "set":
        pass
    if name == "list":
        pass

    return item
        
def parse_rson(buf, pos, raw=False):
    m = whitespace.match(buf,pos)
    if m:
        pos = m.end()

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
            out[key]=item

            chr = buf[pos]
            if chr == ',':
                pos +=1
                m = whitespace.match(buf,pos)
                if m:
                    pos = m.end()
            elif chr != '}':
                raise SyntaxErr(buf, pos)
        # raw: [(k,), ...]
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
        # raw: [(k,), ...]
        return out, pos+1

    elif chr == '@':
        # raw: {name:raw_item}
        m = decorator_name.match(buf, pos)
        if m:
            name = buf[m.start()+1:m.end()].rstrip()
            item, end = parse_rson(buf, m.end(),raw=True)
          # if raw:
          #     item = {name: item}
            item = decorate(name, item)
            return item, end
    elif chr == "'":
        m = string_sq.match(buf, pos)
        if m:
            end = m.end()
            if raw:
                return buf[pos:end], end
            return parse_string(buf, pos, end), end

    elif chr == '"':
        m = string_dq.match(buf, pos)
        if m:
            end = m.end()
            if raw:
                return buf[pos:end], end
            return parse_string(buf, pos, end), end

    elif chr in "-+0123456789":
        m = int_b10.match(buf, pos)
        if m:
            t = flt_b10.match(buf, m.end())
            if t:
                end = t.end()
                # if inside == None
                if raw:
                    return buf[pos:end], end
                return parse_float(buf, pos, end,10), end
                # else:
                # return buf[pos:end], end

            else:
                end = m.end()
                if raw:
                    return buf[pos:end], end
                return parse_int(buf, pos, end,10), end
                
        m = int_b16.match(buf, pos)
        if m:
            t = flt_b16.match(buf, m.end())
            if t:
                end = t.end()
                if raw:
                    return buf[pos:end], end
                return parse_float(buf, pos, end,16), end

            else:
                end = m.end()
                if raw:
                    return buf[pos:end], end
                return parse_int(buf, pos, end,16), end

            
        m = int_b8.match(buf, pos)
        if m:
            end = m.end()
            if raw:
                return buf[pos:end], end
            return parse_int(buf[pos:end],8), end

        m = int_b2.match(buf, pos)
        if m:
            end = m.end()
            if raw:
                return buf[pos:end], end
            return parse_int(buf[pos:end],2), end

    raise SyntaxErr(buf, pos)


def parse(buf):
    obj, pos = parse_rson(buf, 0)

    m = whitespace.match(buf,pos)
    if m:
        pos = m.end()

    if pos != len(buf):
        raise SyntaxErr(buf, pos)

    return obj

def test_parse(buf, obj):
    print(buf, obj)

    if obj != parse(buf):
        raise AssertionError('{} != {}'.format(buf,obj))
    

def main():
    test_parse("0",0)
    test_parse("0.0",0.0)
    test_parse("-0.0",-0.0)
    test_parse("'foo'","foo")
    test_parse("''","")
    test_parse("[1]",[1])
    test_parse("[1,]",[1])
    test_parse("[]",[])
    test_parse("[1,2,3,4,4]",[1,2,3,4,4])
    test_parse("{'a':1,'b':2}",dict(a=1,b=2))
    
    

if __name__ == '__main__':
    main()
