r"""
RSON: Restructured Object Notation

JSON:
 - true, false, null
 - "strings" with \" \\ \/ \b \f \n \r \t \uFFFF, no control codes
 - int/float numbers (unary minus, no leading 0's (0900), except 0.xxx)
 - [ lists, no, trailing, commas ]   {"objects":"..."} with only string keys
 - list or object as root item
 - whitespace is tab, space, cr, lf

RSON:
 - file MUST be utf-8, not cesu-8/utf-16/utf-32
 - byte order mark is treated as whitespace
 - any value as root object
 - use `#....` as comments
 - decorators: tags on existing values: `@a.name [1,2,3]` 
 - optional types through decorators: datetime, period, set, dict, complex

RSON strings: 
 - \xFF as \u00FF
 - \UFFFFFFFF  \' escapes
 - use ''s or ""s
 - \ at end of line is continuation
 - no surrogate pairs

RSON numbers:
 - allow leading zero, underscores (except leading digits)
 - allow unary minus, plus
 - binary ints: 0b1010
 - octal ints: 0o777
 - hex ints: 0xFF 

RSON lists:
 - allow trailing commas

RSON objects:
 - no duplicate keys
 - insertion order must be preserved
 - allow trailing commas
 - implementations MUST support string keys
 - MAY support number keys

RSON decorated objects:
 - allow objects to be 'decorated', via a named tag
 - whitespace between decorator name and object is *mandatory*
 - do not nest

 - all built in types have names reserved, used for special values
 - `@foo.foo {"foo":1}` name is any unicode letter/digit, or a .
 - `@int 1`, `@string "two"` are just `1` and `"two"`

 - parsers may reject unknown, or return a wrapped object 

RSON C99 float strings (optional):
 - `@float "0x0p0"` C99 style, sprintf('%a') format
 - `@float "NaN"` or nan,Inf,inf,+Inf,-Inf,+inf,-inf
 -  no underscores

RSON sets (optional):
 - `@set [1,2,3]`
 - always a decorated list
 - no duplicate items

RSON dicts (optional):
 - `@dict {"a":1}`
 - keys must be in lexical order, must round trip in same order.
 - keys must be comparable, (usually means same type, all string, all number)

RSON datetimes/periods (optional):
 - `@datetime "2017-11-22T23:32:07.100497Z"`
 - `@duration 60` (in seconds)
 - UTC MUST be supported, using `Z` suffix
 - implementations MAY support RFC 3339

RSON bytestrings (optional):
 - `@bytestring "....\xff"` 
 - `@base64 "...=="`
 - returns a bytestring if possible
 - can't have \u \U escapes > 0xFF
 - all non printable ascii characters must be escaped: \xFF

RSON complex numbers: (optional)
 - `@complex [0,1]`

RSON Reserved Decorators:
 - `@bool` on true, or false
 - `@object` on null
 - @int on ints, @float on numbers
 - @string on strings
 - @list on lists
 - @object on objects

 - @float on strings (for C99 hex floats, NaN, -Inf, +Inf)
 - @duration on numbers (seconds)
 - @datetime on strings (utc timestamp)
 - @base64 / @bytestring on strings 
 - @set on lists
 - @complex on lists
 - @dict on objects

 - other uses of  @bool, @int, @float, @complex, @string, @bytestring, @base64,
   @duration, @datetime, @set, @list, @dict, @object is an error

Appendix: Decorated JSON

RSON objects can be encoded as a wrapped JSON, where:

true, false, null, strings, numbers, lists unchanged,
objects, and all decorated types are encoded as
{'name':value}, where value can be wrapped, too

e.g. {'object':[['a',1], ['b',2],3]} 

"""

from collections import namedtuple, OrderedDict, defaultdict
from datetime import datetime, timedelta, timezone

import re
import io
import base64
import json

class ParserErr(Exception):
    def __init__(self, buf, pos, reason=None):
        self.buf = buf
        self.pos = pos
        if reason is None:
            nl = buf.rfind(' ',pos-10, pos)
            if nl < 0:
                nl = pos-5  
            reason = "Unknown Character {} (context: {})".format(repr(buf[pos]),repr(buf[pos-10:pos+5]))
        Exception.__init__(self, "{} (at pos={})".format(reason, pos))

class BadDecorator(Exception):
    def __init__(self, name, reason):
        self.name = name
        Exception.__init__(self, reason)

whitespace = re.compile(r"(?:\ |\t|\uFEFF|\r|\n|#[^\r\n]*(?:\r?\n|$))+")

int_b2 = re.compile(r"0b[01][01_]*")
int_b8 = re.compile(r"0o[0-7][0-7_]*")
int_b10 = re.compile(r"\d[\d_]*")
int_b16 = re.compile(r"0x[0-9a-fA-F][0-9a-fA-F_]*")

flt_b10 = re.compile(r"\.[\d_]+")
exp_b10 = re.compile(r"[eE](?:\+|-)?[\d+_]")

string_dq = re.compile(
    r'"(?:[^"\\\n\x00-\x1F\uD800-\uDFFF]|\\(?:[\'"\\/bfnrt]|\\\r?\n|x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}))*"')
string_sq = re.compile(
    r"'(?:[^'\\\n\x00-\x1F\uD800-\uDFFF]|\\(?:[\"'\\/bfnrt]|\\\r?\n|x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}))*'")

decorator_name = re.compile(r"@(?!\d)\w+[ ]+")
identifier = re.compile(r"(?!\d)[\w\.]+")

c99_flt = re.compile(
    r"NaN|nan|[-+]?Inf|[-+]?inf|[-+]?0x[0-9a-fA-F][0-9a-fA-F]*\.[0-9a-fA-F]+[pP](?:\+|-)?[\d]+")

str_escapes = {
    'b': '\b',
    'n': '\n',
    'f': '\f',
    'r': '\r',
    't': '\t',
    '/': '/',
    '"': '"',
    "'": "'",
    '\\': '\\',
}

byte_escapes = {
    'b': b'\b',
    'n': b'\n',
    'f': b'\f',
    'r': b'\r',
    't': b'\t',
    '/': b'/',
    '"': b'"',
    "'": b"'",
    '\\': b'\\',
}

escaped = {
    '\b': '\\b',
    '\n': '\\n',
    '\f': '\\f',
    '\r': '\\r',
    '\t': '\\t',
    '"': '\\"',
    "'": "\\'",
    '\\': '\\\\',
}


builtin_names = {'null': None, 'true': True, 'false': False}
builtin_values = {None: 'null', True: 'true', False: 'false'}

builtin_decorators = set("""
        bool int float complex
        string bytestring base64
        duration datetime
        set list dict object
""".split())

# names -> Classes (take name, value as args)
registered_decorators = OrderedDict()
registered_classes = OrderedDict()  # classes -> undecorators (get name, value)


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
        raise SemanticErr(
            "Can't undecorate {}: unknown class {}".format(obj, obj.__class__))

    if name not in builtin_decorators:
        return name, value
    else:
        raise BadDecorator(
            name, "Can't undecorate {}, as {} is reserved name".format(obj, name))


def decorate(name, value):
    if name in builtin_decorators:
        raise BadDecorator(name, "{} is reserved".format(name))

    if name in registered_decorators:
        dec = registered_decorators[name]
        return dec(name, value)
    else:
        return Decorated(name, value)


def parse_datetime(v):
    if v[-1] == 'Z':
        if '.' in v:
            return datetime.strptime(v, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
        else:
            return datetime.strptime(v, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    else:
        raise NotImplementedError()


def format_datetime(obj):
    obj = obj.astimezone(timezone.utc)
    return obj.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def parse_rson(buf, pos):
    m = whitespace.match(buf, pos)
    if m:
        pos = m.end()

    peek = buf[pos]
    name = None
    if peek == '@':
        m = decorator_name.match(buf, pos)
        if m:
            pos = m.end()
            name = buf[m.start() + 1:pos].rstrip()
        else:
            raise ParserErr(buf, pos)

    peek = buf[pos]

    if peek == '@':
        raise ParserErr(buf, pos, "Cannot nest decorators")

    elif peek == '{':
        if name in builtin_decorators:
            if name not in ('object', 'dict'):
                raise ParserErr(buf, pos, "{} can't be used on objects".format(name))

        if name == 'dict':
            out = dict()
        else:
            out = OrderedDict()


        pos += 1
        m = whitespace.match(buf, pos)
        if m:
            pos = m.end()

        while buf[pos] != '}':
            key, pos = parse_rson(buf, pos)

            if key in out:
                raise SemanticErr('duplicate key: {}, {}'.format(key, out))

            m = whitespace.match(buf, pos)
            if m:
                pos = m.end()

            peek = buf[pos]
            if peek == ':':
                pos += 1
                m = whitespace.match(buf, pos)
                if m:
                    pos = m.end()
            else:
                raise ParserErr(buf, pos, "Expected key:value pair but found {}".format(repr(peek)))

            item, pos = parse_rson(buf, pos)

            out[key] = item

            peek = buf[pos]
            if peek == ',':
                pos += 1
                m = whitespace.match(buf, pos)
                if m:
                    pos = m.end()
            elif peek != '}':
                raise ParserErr(buf, pos, "Expecting a ',', or a '}' but found {}".format(repr(peek)))
        if name not in (None, 'object', 'dict'):
            out = decorate(name,  out)
        return out, pos + 1

    elif peek == '[':
        if name in (None, 'list', 'complex'):
            out = []
        elif name == 'set':
            out = set()
        elif name in builtin_decorators:
            raise ParserErr(buf, pos, "{} can't be used on lists".format(name))

        pos += 1
        m = whitespace.match(buf, pos)
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

            m = whitespace.match(buf, pos)
            if m:
                pos = m.end()

            peek = buf[pos]
            if peek == ',':
                pos += 1
                m = whitespace.match(buf, pos)
                if m:
                    pos = m.end()
            elif peek != ']':
                raise ParserErr(buf, pos, "Expecting a ',', or a ']' but found {}".format(repr(peek)))
        if name == 'complex':
            out = complex(*out)
        elif name not in (None, 'list', 'set'):
            out = decorate(name,  out)
        return out, pos + 1

    elif peek == "'" or peek == '"':
        if name in builtin_decorators:
            if name not in ('string','float','datetime','bytestring','base64'):
                raise ParserErr(buf,pos, "{} can't be used on strings".format(name))

        if name == 'bytestring':
            s = bytearray()
            ascii = True
        else:
            s = io.StringIO()
            ascii = False

        if peek == "'":
            m = string_sq.match(buf, pos)
            if m:
                end = m.end()
            else:
                raise ParserErr(buf, pos, "Invalid single quoted string")
        else:
            m = string_dq.match(buf, pos)
            if m:
                end = m.end()
            else:
                raise ParserErr(buf, pos, "Invalid double quoted string")

        lo = pos + 1  # skip quotes
        while lo < end - 1:
            hi = buf.find("\\", lo, end)
            if hi == -1:
                if ascii:
                    s.extend(buf[lo:end - 1].encode('ascii'))
                else:
                    s.write(buf[lo:end - 1])  # skip quote
                break

            if ascii:
                s.extend(buf[lo:hi].encode('ascii'))
            else:
                s.write(buf[lo:hi])

            esc = buf[hi + 1]
            if esc in str_escapes:
                if ascii:
                    s.extend(byte_escapes[esc])
                else:
                    s.write(str_escapes[esc])
                lo = hi + 2
            elif esc == 'x':
                n = int(buf[hi + 2:hi + 4], 16)
                if ascii:
                    s.append(n)
                else:
                    s.write(chr(n))
                lo = hi + 4
            elif esc == 'u':
                n = int(buf[hi + 2:hi + 6], 16)
                if ascii and n > 0xFF:
                    raise SemanticErr('bytestring cannot have unicode')
                s.write(chr(n))
                lo = hi + 6
            elif esc == 'U':
                n = int(buf[hi + 2:hi + 10], 16)
                if ascii and n > 0xFF:
                    raise SemanticErr('bytestring cannot have unicode')
                s.write(chr(n))
                lo = hi + 10
            elif esc == '\n':
                lo = hi + 2
            elif (buf[hi + 1:hi + 3] == '\r\n'):
                lo = hi + 3
            else:
                raise ParserErr(buf, hi, "Unkown escape character {}".format(repr(esc)))

        if name == 'bytestring':
            out = s
        else:
            out = s.getvalue()

            if name is None or name == 'string':
                pass
            elif name == 'base64':
                try:
                    out = base64.standard_b64decode(out)
                except Exception as e:
                    raise ParserErr(buf,pos, "Invalid base64") from e
            elif name == 'datetime':
                try:
                    out = parse_datetime(out)
                except Exception as e:
                    raise ParserErr(buf,pos, "Invalid datetime: {}".format(repr(out))) from e
            elif name == 'float':
                m = c99_flt.match(out)
                if m:
                    out = float.fromhex(out)
                else:
                    raise ParserErr(buf, pos, "invalid C99 float literal: {}".format(out))
            else:
                out = decorate(name,  out)

        return out, end

    elif peek in "-+0123456789":
        if name in builtin_decorators:
            if name not in ('int', 'float', 'duration'):
                raise ParserErr(buf, pos,"{} can't be used on numbers".format(name))

        flt_end = None
        exp_end = None

        sign = +1

        if buf[pos] in "+-":
            if buf[pos] == "-":
                sign = -1
            pos += 1
        peek = buf[pos:pos + 2]

        if peek in ('0x', '0o', '0b'):
            if peek == '0x':
                base = 16
                m = int_b16.match(buf, pos)
                if m:
                    end = m.end()
                else:
                    raise ParserErr(buf, pos, "Invalid hexadecimal number (0x...)")
            elif peek == '0o':
                base = 8
                m = int_b8.match(buf, pos)
                if m:
                    end = m.end()
                else:
                    raise ParserErr(buf, pos, "Invalid octal number (0o...)")
            elif peek == '0b':
                base = 2
                m = int_b2.match(buf, pos)
                if m:
                    end = m.end()
                else:
                    raise ParserErr(buf, pos, "Invalid hexadecimal number (0x...)")

            out = sign * int(buf[pos + 2:end].replace('_', ''), base)
        else:
            m = int_b10.match(buf, pos)
            if m:
                int_end = m.end()
                end = int_end
            else:
                raise ParserErr(buf, pos, "Invalid number")

            t = flt_b10.match(buf, end)
            if t:
                flt_end = t.end()
                end = flt_end

            e = exp_b10.match(buf, end)
            if e:
                exp_end = e.end()
                end = exp_end

            if flt_end or exp_end:
                out = sign * float(buf[pos:end].replace('_', ''))
            else:
                out = sign * int(buf[pos:end].replace('_', ''), 10)

        if name == 'duration':
            out = timedelta(seconds=out)
        elif name == 'int':
            if flt_end or exp_end:
                raise ParserErr(buf, pos, "Can't decorate floating point with @int")
        elif name == 'float':
            if not isintance(out, float):
                out = float(out)
        elif name is not None:
            out = decorate(out)

        return out, end

    else:
        m = identifier.match(buf, pos)
        if m:
            end = m.end()
            item = buf[pos:end]
        else:
            raise ParserErr(buf, pos)

        if item not in builtin_names:
            raise ParserErr(buf, pos, "{} is not a recognised built-in".format(repr(name)))

        out = builtin_names[item]

        if name == 'object':
            if item != 'null':
                raise ParserErr(buf, pos, '@object can only decorate null or {}')
        elif name == 'bool':
            if item not in ('true', 'false'):
                raise ParserErr(buf,pos, '@bool can only true or false')
        elif name in builtin_decorators:
            raise ParserErr(buf, pos, "{} has no meaning for {}".format(repr(name), item) )
        elif name is not None:
            out = decorate(name,  out)

        return out, end

    raise ParserErr(buf, pos)


def parse(buf):
    obj, pos = parse_rson(buf, 0)

    m = whitespace.match(buf, pos)
    if m:
        pos = m.end()
        m = whitespace.match(buf, pos)

    if pos != len(buf):
        raise ParserErr(buf, pos, "Trailing content: {}".format(repr(buf[pos:pos+10])))

    return obj


def dump(obj):
    buf = io.StringIO('')
    dump_rson(obj, buf)
    return buf.getvalue()


def dump_rson(obj, buf):
    if obj is True or obj is False or obj is None:
        buf.write(builtin_values[obj])
    elif isinstance(obj, str):
        buf.write('"')
        for c in obj:
            if c in escaped:
                buf.write(escaped)
            elif ord(c) < 0x20:
                buf.write('\\x{:02X}'.format(ord(c)))
            else:
                buf.write(c)
        buf.write('"')
    elif isinstance(obj, int):
        buf.write(str(obj))
    elif isinstance(obj, float):
        hex = obj.hex()
        if hex.startswith(('0', '-')):
            buf.write(str(obj))
        else:
            buf.write('@float "{}"'.format(hex))
    elif isinstance(obj, complex):
        buf.write("@complex [{}, {}]".format(obj.real, obj.imag))
    elif isinstance(obj, (bytes, bytearray)):
        buf.write('@base64 "')
        # assume no escaping needed
        buf.write(base64.standard_b64encode(obj).decode('ascii'))
        buf.write('"')
    elif isinstance(obj, (list, tuple)):
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
        for k, v in obj.items():
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
        buf.write('@datetime "{}"'.format(format_datetime(obj)))
    elif isinstance(obj, timedelta):
        buf.write('@duration {}'.format(obj.total_seconds()))
    else:
        nv = undecorate(obj)
        name, value = nv
        buf.write('@{} '.format(name))
        dump_rson(value, buf)


""" 
Decorated JSON: An RSON fallback

true, false, null ~> true, false, null
"..." / '...' ~> "...." removing escapes where possible & using codepoints
[1,2,3,] ~> [1,2,3]
{"a":'object'} ~> {'object':[['a', 'object']])
@decorated "item" ~> {'decorated': "item"}
@float "NaN" ~> {'float':'NaN'}
@bytestring "..." ~> {'base64':'....'}
"""

def djson_parse(buf):
    return json.loads(buf, object_pairs_hook=djson_object_pairs_hook)


def djson_dump(obj):
    obj = djson_wrap(obj)
    return json.dumps(obj)


def djson_parse_file(fh):
    return json.load(fh, object_pairs_hook=djson_object_pairs_hook)


def djson_dump_file(obj, fh):
    obj = djson_wrap(obj)
    return json.dump(obj, fh)



def djson_object_pairs_hook(pairs):
    ((k, v),) = pairs
    if k == 'bool':
        return v
    if k == 'int':
        return v
    if k == 'float':
        return float.fromhex(v)
    if k == 'complex':
        return complex(*v)

    if k == 'string':
        return v
    if k == 'base64':
        return base64.standard_b64decode(v)
    if k == 'bytestring':
        return v.encode('ascii')
    if k == 'set':
        return set(v)
    if k == 'list':
        return v
    if k == 'dict':
        return dict(v)
    if k == 'object':
        if v is not None:
            return OrderedDict(v)
        else:
            return None

    if k == 'datetime':
        return parse_datetime(v)
    if k == 'duration':
        return timedelta(seconds=v)

    return decorate(k, v)


def djson_wrap(obj):
    if obj is True or obj is False or obj is None:
        return obj
    elif isinstance(obj, (str, int)):
        return obj
    elif isinstance(obj, float):
        h = obj.hex()
        if h.startswith(('0', '-')):
            return obj
        else:
            return {'float': h}
    elif isinstance(obj, bytes):
        return {'base64': base64.standard_b64encode(obj).decode('ascii')}
    elif isinstance(obj, (list, tuple)):
        return [djson_wrap(x) for x in obj]
    elif isinstance(obj, set):
        return {'set': [djson_wrap(x) for x in obj]}
    elif isinstance(obj, OrderedDict):
        return {'object': [(djson_wrap(x), djson_wrap(y)) for x, y in obj.items()]}
    elif isinstance(obj, dict):
        out = []
        for x in sorted(obj.keys()):
            out.append((djson_wrap(x), djson_wrap(obj[x])))
        return {'dict': out}
    elif isinstance(obj, datetime):
        return {'datetime': format_datetime(obj)}
    elif isinstance(obj, timedelta):
        return {'duration': obj.total_seconds()}
    elif isinstance(obj, complex):
        return {'complex': [obj.real, obj.imag]}
    else:
        v = undecorate(obj)
        if not v:
            raise NotImplementedError("Don't know how to wrap {}, {}".format(obj.__class__, obj))
        name, value = obj
        return {name: djson_wrap(value)}


# rbox - framing format for rson objects
#   <record type> <length> <name> <newline> 
#   <payload> <newline> 
#   end <checksum> <newline>
#
# for a log/stream of objects
# payload shoud be rson, but can be bytes or perhaps base64
# intent that record type indicates content

class rbox:
    # type, length, name, payload, checksum
    pass


class rboxIo:
    pass


def open_rbox(filename):
    pass


def parse_rbox(buf):
    pass

# Tests


def test_parse(buf, obj):
    out = parse(buf)

    if (obj != obj and out == out) or (obj == obj and obj != out):
        raise AssertionError('{} != {}'.format(obj, out))


def test_dump(obj, buf):
    out = dump(obj)
    if buf != out:
        raise AssertionError('{} != {}'.format(buf, out))


def test_parse_err(buf, exc):
    try:
        obj = parse(buf)
    except Exception as e:
        if isinstance(e, exc):
            return
        else:
            print(e.__class__, exc)
            raise AssertionError(
                '{} did not cause {}, but {}'.format(buf, exc, e)) from e
    else:
        raise AssertionError(
            '{} did not cause {}, parsed:{}'.format(buf, exc, obj))


def test_dump_err(obj, exc):
    try:
        buf = dump(obj)
    except Exception as e:
        if isinstance(e, exc):
            return
        else:
            raise AssertionError(
                '{} did not cause {}, but '.format(obj, exc, e))
    else:
        raise AssertionError(
            '{} did not cause {}, dumping: {}'.format(obj, exc, buf))


def test_round(obj):
    buf0 = dump(obj)
    obj1 = parse(buf0)
    buf1 = dump(obj1)

    out = parse(buf1)

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
    test_parse("0", 0)
    test_parse("0x0_1_2_3", 0x123)
    test_parse("0o0_1_2_3", 0o123)
    test_parse("0b0_1_0_1", 5)
    test_parse("0 #comment", 0)
    test_parse("0.0", 0.0)
    test_parse("-0.0", -0.0)
    test_parse("'foo'", "foo")
    test_parse(r"'fo\no'", "fo\no")
    test_parse("'\\\\'", "\\")
    test_parse(r"'\b\f\r\n\t\"\'\/'", "\b\f\r\n\t\"\'/")
    test_parse("''", "")
    test_parse(r'"\x20"', " ")
    test_parse(r'"\uF0F0"', "\uF0F0")
    test_parse(r'"\U0001F0F0"', "\U0001F0F0")
    test_parse("'\\\\'", "\\")
    test_parse("[1]", [1])
    test_parse("[1,]", [1])
    test_parse("[]", [])
    test_parse("[1,2,3,4,4]", [1, 2, 3, 4, 4])
    test_parse("{'a':1,'b':2}", dict(a=1, b=2))
    test_parse("@set [1,2,3,4]", set([1, 2, 3, 4]))
    test_parse("{'a':1,'b':2}", dict(a=1, b=2))
    test_parse("@complex [1,2]", 1 + 2j)
    test_parse("@bytestring 'foo'", b"foo")
    test_parse("@base64 '{}'".format(
        base64.standard_b64encode(b'foo').decode('ascii')), b"foo")
    test_parse("@float 'NaN'", float('NaN'))
    test_parse("@float '-inf'", float('-Inf'))
    obj = datetime.now().astimezone(timezone.utc)
    test_parse('@datetime "{}"'.format(
        obj.strftime("%Y-%m-%dT%H:%M:%S.%fZ")), obj)
    obj = timedelta(seconds=666)
    test_parse('@duration {}'.format(obj.total_seconds()), obj)
    test_parse("@bytestring 'fo\x20o'", b"fo o")
    test_parse("@float '{}'".format((3000000.0).hex()), 3000000.0)
    test_parse(hex(123), 123)

    test_dump(1, "1")

    test_dump_err(Decorated('float', 123), BadDecorator)
    test_parse_err('@object "foo"', ParserErr)
    test_parse_err('"foo', ParserErr)

    tests = [
        0, -1, +1,
        -0.0, +0.0, 1.9,
        True, False, None,
        "str", b"bytes",
        [1, 2, 3], {"c": 3, "a": 1, "b": 2, }, set(
            [1, 2, 3]), OrderedDict(a=1, b=2),
        1 + 2j, float('NaN'),
        datetime.now().astimezone(timezone.utc),
        timedelta(seconds=666),
    ]

    for x in tests:
        test_round(x)

    for x in tests:
        out = parse(dump(x))
        out2 = djson_parse(djson_dump(x))
        if out != out:
            if out2 == out2:
                raise AssertionError('buf {} != {}'.format(x, out))
        elif out != out2:
            raise AssertionError('buf {} != {}'.format(x, out))
    print('tests passed')


if __name__ == '__main__':
    main()
