# RSON: Restructured Object Notation

DRAFT

A Superset of JSON, not a subset of JavaScript.

## Basics

- true, false, null, 
- 1233, 1.234, "string",
- [list, ...], {key:value, unordered:dictionary}

- # and not // for comments (so that // can be an operator in supersets)

- Ignore leading Byte Order Marks
- Leading zeros / Underscores in numbers
- Hexadecimal 0x..., Binary 0b..., Octal 0c222
- Hex Floats (C99), and support for +/-Infinity, Nan through decorators

- Trailing commas in lists and dictionaries [1,2,3] / {"a":1,}
- Sets: {1,2,3}, Ordered Dictionaries ["a":1] (called a table in the spec)

- 'strings' "strings" and """ multiline strings """ / ''' multiline strings '''
- \UFFFFFFFF escape too

- bytestrings: b"...." with \xFF escape
- @decorate <Literal>
- parenthesis, and C string hack (" aaa" "aaa")

Maybe:
- Last Key wins in Ordered/Unordered dictionary
- Or automatic array? key:1 Key:1 ~>key[1,1]
- nested key defs "foo"."bar":{...} is "foo":{"bar":...}
No:

- Barewords. Just no. It never works out. cf 'No Capes' in the Incredibles. No.
- // or /* ... */ for comments. We're using #. That's it
- JS Compat: JSON, TOML, YAML don't have it 

## Decorators

@typedef {'name':'resource', fields:['a','b','c']}

@resource [1,2,3]  


### Built in decorators:

- @datetime ".... iso/rfc date time"
- @period "123" # nmber of seconds, optionally allow "100ms"
- @base64 "base64 encoded bytestring"
- @float "NaN" / @float "+Infinity"

### Reserved Names / No-op decorators

- int / integer / float / double / list / set / date / time / dict / table /
  bool / complex / string / bytestring

### Encoder dependent

- @path "/over/here" # 
- @url "....." # 

i.e may just be mapped to strings but optionally used for processing (
    for example, relative paths)

## Templates

ES6 like template literals

- f'.....' / ` ....` / ``` multiline ```
- `$a` `${b}` no real nesting inside {}

considering: $foo like literals, i.e [$a, $b,$c], because might as well standardise the misuse 

## Records

- Allow ()'s 
- Allow a record of 1,2,3,4 (no newlines) 
- with optional keys: "a", "b":3
- sugar for @record [[null, "a"], ["b", 3]]

Bonus: CSV like mode, records seperated by newlines.


## Decorated JSON Output

- {'type': value} construction akin to avro, using decorator names
- {"set": [...]} {'base64':'....'}



RSON take 2

Start with DJSON

then make RSON by sugaring JSON
first 
    -decorators 
and
- # ... Comments as Whitespace
- byte order mark dropped
- trailing commas
- wide characters
- parenthesis, string concat inside too

- decorators
    - @float "NaN" @int "0x..." @string "\\U12345678"
    - @set [] @table {} / @table [. ]
    - @base64 "..." @bytestring

- sugar for sets, wetc
    bytestirngs
