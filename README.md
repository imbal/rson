# RSON: Restructured Object Notation

## JSON:
 - true, false, null
 - "strings" with \" \\ \/ \b \f \n \r \t \uFFFF, no control codes
 - int/float numbers (unary minus, no leading 0's (0900), except 0.xxx)
 - [ lists, no, trailing, commas ]   {"objects":"..."} with only string keys
 - list or object as root item
 - whitespace is tab, space, cr, lf

## RSON:
 - file MUST be utf-8, not cesu-8/utf-16/utf-32
 - byte order mark is treated as whitespace
 - any value as root object
 - use `#....` as comments
 - decorators: tags on existing values: `@a.name [1,2,3]` 
 - optional types through decorators: datetime, period, set, dict, complex

## RSON objects:
 - null
 - true, false
 - integers
 - floating point
 - strings
 - lists
 - records
 - decorated objects

### RSON strings: 
 - \xFF as \u00FF
 - \UFFFFFFFF  \' escapes
 - use ''s or ""s
 - \ at end of line is continuation
 - no surrogate pairs

### RSON numbers:
 - allow unary minus, plus
 - allow leading zero
 - allow underscores (except leading digits)
 - binary ints: 0b1010
 - octal ints: 0o777
 - hex ints: 0xFF 

### RSON lists:
 - allow trailing commas

### RSON records (aka, JSON objects):
 - no duplicate keys
 - insertion order must be preserved
 - allow trailing commas
 - implementations MUST support string keys

## RSON decorated objects:
 - `@foo.foo {"foo":1}` name is any unicode letter/digit, or a .
 - `@int 1`, `@string "two"` are just `1` and `"two"`

 - allow objects to be 'decorated', via a named tag
 - whitespace between decorator name and object is *mandatory*
 - do not nest

 - all built in types have names reserved, used for special values
 - parsers may reject unknown, or return a wrapped object 

### RSON C99 float strings (optional):
 - `@float "0x0p0"` C99 style, sprintf('%a') format
 - `@float "NaN"` or nan,Inf,inf,+Inf,-Inf,+inf,-inf
 -  no underscores

### RSON sets (optional):
 - `@set [1,2,3]`
 - always a decorated list
 - no duplicate items

### RSON dicts (optional):
 - `@dict {"a":1}` 
 - keys must be in lexical order, must round trip in same order.
 - keys must be comparable

### RSON datetimes/periods (optional):
 - `@datetime "2017-11-22T23:32:07.100497Z"`
 - `@duration 60` (in seconds)
 - UTC MUST be supported, using `Z` suffix
 - implementations should support subset of RFC 3339

### RSON bytestrings (optional):
 - `@bytestring "....\xff"` 
 - `@base64 "...=="`
 - returns a bytestring if possible
 - can't have \u \U escapes > 0xFF
 - all non printable ascii characters must be escaped: \xFF

### RSON complex numbers: (optional)
 - `@complex [0,1]`

### Builtin RSON Decorators:
 - `@object` on any (is a pass through)
 - `@bool` on true, or false
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
 - @dict on records
 - @record on records

 - other uses of  @bool, @int, @float, @complex, @string, @bytestring, @base64,
   @duration, @datetime, @set, @list, @dict, @record is an error
 - @object is always fine

# Appendix: Decorated JSON

RSON objects can be encoded as a wrapped JSON, where:

true, false, null, strings, numbers, lists unchanged,
objects, and all decorated types are encoded as
{'name':value}, where value can be wrapped, too

e.g. {'object':[['a',1], ['b',2],3]} 


