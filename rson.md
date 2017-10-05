# RSON: Restructured Object Notation

DRAFT

A Superset of JSON, not a subset of JavaScript.

## Basics

Yes:

- true, false, null, 
- 1233, 1.234, "string",
- [list, ...], {key:value, unordered:dictionary}

- use # and not // for comments (so that // can be an operator in supersets)

- Ignore leading Byte Order Marks

- allow ''s as well as ""s
- \xFF, \UFFFF, \UFFFFFFFF escape too, along with json escapes
- parenthesis, and C string hack ("aaa" "aaa") is "aaaaaa", allows
  breaking things over multiple lines, 

- Leading zeros / Underscores in numbers
- Hexadecimal 0x..., Binary 0b..., Octal 0c222
- Hex Floats (C99), (and support for +/-Infinity, NaN through decorators)

- Trailing commas in lists and dictionaries [1,2,3] / {"a":1,}
- Sets: {1,2,3}, Ordered Dictionaries ["a":1] (called a table in the spec)
- @decorate <object>, with some built in

- @datetime ".... iso/rfc date time"
- @period 123 # seconds
- @float "NaN" / @float "+Infinity"
- bytestrings: @bytestring "1123" or @base64 "...="

- A decorator is a \w+ unicode string, letters or underscore, no punct or space, but non eading numbers, also @foo.bar for namespacing. NFC normalizing should happen too for non ascii identifiers.

No:

- Barewords. Just no. It never works out. cf 'No Capes' in the Incredibles. No. Decorators are already pushing it
- Js comments: // or /* ... */ for comments. We're using #. That's it
- Js Compat: JSON, TOML, YAML don't have it 
- Python style """ multiline strings """ / ''' multiline strings '''
- String prefixes u".../b"...", again too python
- Milisecond: Ugh, use 123.0E-9, and trust a parser not to lose resolution

### Reserved Names, Standard rules apply

- int / integer / float / double / list / set / date / time / dict / table /
  bool / complex / string / bytestring 

### Reserved, but Encoder dependent decorators

- @path "/over/here" # 
- @url "....." # 

i.e may just be mapped to strings but optionally used for processing (
    for example, relative paths)

## Decorated JSON Output

- {'type': value} construction akin to avro, using decorator names
- {"set": [...]} {'base64':'....'}
- {"dict":[[k,v], ...... }



