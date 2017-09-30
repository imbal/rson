# RSON: Restructured Object Notation

DRAFT

A Superset of JSON, not a subset of JavaScript.

## Basics

Yes:

- true, false, null, 
- 1233, 1.234, "string",
- [list, ...], {key:value, unordered:dictionary}

- # and not // for comments (so that // can be an operator in supersets)

- allow ''s as well as ""s
- Ignore leading Byte Order Marks
- Leading zeros / Underscores in numbers
- Hexadecimal 0x..., Binary 0b..., Octal 0c222
- Hex Floats (C99), (and support for +/-Infinity, Nan through decorators)

- Trailing commas in lists and dictionaries [1,2,3] / {"a":1,}
- Sets: {1,2,3}, Ordered Dictionaries ["a":1] (called a table in the spec)

- 'strings' "strings" and 
- \UFFFFFFFF escape too, along with json escapes

- bytestrings: b"...." with \xFF escape, along with json escapes (except \u)
- @decorate <object>:  i.e @datetime "...."
- parenthesis, and C string hack ("aaa" "aaa") is "aaaaaa", allows
  breaking things over multiple lines, 

No:

- Barewords. Just no. It never works out. cf 'No Capes' in the Incredibles. No.
- Js comments: // or /* ... */ for comments. We're using #. That's it
- JS Compat: JSON, TOML, YAML don't have it 
- Python style """ multiline strings """ / ''' multiline strings '''

### Built in decorators:

- @datetime ".... iso/rfc date time"
- @period 123 # nmber of seconds, (maybe? allow "100ms")
- @base64 "base64 encoded bytestring"
- @float "NaN" / @float "+Infinity"

### Reserved Names / No-op decorators

- int / integer / float / double / list / set / date / time / dict / table /
  bool / complex / string / bytestring

### Encoder dependent decorators

- @path "/over/here" # 
- @url "....." # 

i.e may just be mapped to strings but optionally used for processing (
    for example, relative paths)

## Decorated JSON Output

- {'type': value} construction akin to avro, using decorator names
- {"set": [...]} {'base64':'....'}
- {"dict":[[k,v], ...... }



