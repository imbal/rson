# RSON: Restructured Object Notation

RSON is JSON with a little bit of sugar. 

- Trailing Commas
- Comments
- ... and a few other pieces

RSON supports encoding types outside of JSON through tagging, like timestamps.

## JSON in a nutshell:

 - whitespace is `\t \r \n \x20`
 - json document is either list, or object
 - lists `[ obj, obj ]`
 - objects `{ "key": value}`, only string keys
 - `true`, `false`, `null`
 - unicode `"strings"` with escapes `\" \\ \/ \b \f \n \r \t \uFFFF`, and no control codes unecaped.
 - int/float numbers (unary minus, no leading 0's (0900), except 0.xxx)
 - no trailing commas

## RSON:

 - file MUST be utf-8, not cesu-8/utf-16/utf-32
 - byte order mark is also treated as whitespace (along with \x09, \x0a, \x0d, \x20)
 - rson document is any rson object
 - use `#....` as comments
 - tags: names on existing values: `@duration 20`, `@a.name [1,2,3]` 
   (they do not nest)
 - optional types through tags: datetime, period, set, dict, complex

```
{ 
    "name": "Sam",
    "pets": ["Fee","Ret",],
    "birthday": @datetime "1970-01-01T00:00:00.0Z",
}
```

### RSON objects:

 - `null`
 - `true`, `false`
 - integers (decimal, binary, octal, hex)
 - floating point
 - strings (single or double quotes)
 - lists
 - records
 - tagged objects

### RSON strings: 

 - use ''s or ""s
 - json escapes, and `\xFF` (as `\u00FF`), `\UFFFFFFFF`  `\'` too
 - `\` at end of line is continuation
 - no surrogate pairs

### RSON numbers:

 - allow unary minus, plus
 - allow leading zero
 - allow underscores (except leading digits)
 - binary ints: `0b1010`
 - octal ints `0o777`
 - hex ints: `0xFF` 

### RSON lists:

 - allow trailing commas

### RSON records (aka, JSON objects):

 - no duplicate keys
 - insertion order must be preserved (like modern python, ruby, javascript do)
 - allow trailing commas
 - implementations MUST support string keys

### RSON tagged objects:

 - `@foo.foo {"foo":1}` name is any unicode letter/digit, `_`or a `.`
 - `@int 1`, `@string "two"` are just `1` and `"two"`
 - a named tag for objects
 - do not nest
 - whitespace between tag name and object is *mandatory*
 - every type has a reserved tag name
 - parsers may reject unknown, or return a wrapped object 

### RSON C99 float strings (optional):

 - `@float "0x0p0"` C99 style, sprintf('%a') format
 - `@float "NaN"` or nan,Inf,inf,+Inf,-Inf,+inf,-inf
 -  no underscores allowed

### RSON sets (optional):

 - `@set [1,2,3]`
 - always a tagged list
 - no duplicate items

### RSON dicts (optional):

 - `@dict {"a":1}` 
 - keys must be in lexical order, must round trip in same order.
 - keys must be comparable, hashable, parser MAY reject if not

### RSON datetimes/periods (optional):

 - RFC 3339 format in UTC, (i.e 'Zulu time')
 - `@datetime "2017-11-22T23:32:07.100497Z"`
 - `@duration 60` (in seconds, float or int)
 - UTC MUST be supported, using `Z` suffix
 - implementations should support subset of RFC 3339

### RSON bytestrings (optional):

 - `@bytestring "....\xff"` 
 - `@base64 "...=="`
 - returns a bytestring if possible
 - can't have `\u` `\U` escapes > 0xFF
 - all non printable ascii characters must be escaped: `\xFF`

### RSON complex numbers: (optional)

 - `@complex [0,1]`

### Builtin RSON Tags:

Pass throughs:

 - `@object` on any 
 - `@bool` on true, or false
 - `@int` on ints
 - `@float` on ints or floats
 - `@string` on strings
 - `@list` on lists
 - `@record` on records

Reserved:

 - `unknown`

Transforms:

 - @float on strings (for C99 hex floats, including NaN, -Inf, +Inf)
 - @duration on numbers (seconds)
 - @datetime on strings (utc timestamp)
 - @base64 on strings
 - @bytestring on strings 
 - @set on lists
 - @complex on lists
 - @dict on records

Any other use of a builtin tag is an error and MUST be rejected.

# Appendix: Test Vectors

## MUST parse
```
@object null
@bool true
false
0
@float 0.0
-0.0
"test-\x32-\u0032-\U00000032"
'test \" \''
[]
[1,]
{"a":"b",}
```

## MUST not parse

```
_1
0b0123
0o999
0xGHij
@set {}
@dict []
[,]
{"a"}
{"a":1, "a":2}
@object @object {}
"\uD800\uDD01"
```




