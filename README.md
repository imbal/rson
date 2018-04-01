# RSON: Restructured Object Notation

RSON is JSON, with a little bit of sugar: Comments, Commas, and Tags.

For example:

```
{
    "numbers": +0123.0,       # Can have leading zeros
    "octal": 0o10,            # Oh, and comments too
    "hex": 0xFF,              #
    "binary": 0b1000_0001,     # Number literals can have _'s 

    "lists": [1,2,3],         # Lists can have trailing commas

    "strings": "At least \x61 \u0061 and \U00000061 work now",
    "or": 'a string',          # both "" and '' work.

    "records": {
        "a": 1,               # Must have unique keys
        "b": 2,               # and the order must be kept
    },
}
```

Along with some sugar atop JSON, RSON supports tagging literals to represent types outside of JSON:

- `@datetime "2017-11-22T23:32:07.100497Z"`, a tagged RFC 3339 datestamp
- `@duration 60` (a duration in seconds, float or int)
- `@base64 "...=="`, a base64 encoded bytestring
- `@set`, `@dict`, `@complex`, `@bytestring`


## JSON in a nutshell:

 - A unicode text file, without a Byte Order Mark
 - Whitespace is `\t`, `\r`, `\n`, `\x20`
 - JSON document is either list, or object
 - Lists are `[]`, `[obj]`, `[ obj, obj ]`, ...
 - Objects: `{ "key": value}`, only string keys
 - Built-ins: `true`, `false`, `null`
 - `"unicode strings"` with escapes `\" \\ \/ \b \f \n \r \t \uFFFF`, and no control codes unecaped.
 - int/float numbers (unary minus, no leading zeros, except for `0.xxx`)
 - No Comments, No Trailing commas

## RSON in a Nutshell

 - File MUST be utf-8, not cesu-8/utf-16/utf-32, without surrogate pairs.
 - Use `#.... <end of line>` for comments
 - Byte Order Mark is treated as whitespace (along with `\x09`, `\x0a`, `\x0d`, `\x20`)
 - RSON Document is any RSON Object, (i.e `1` is a valid RSON file).
 - Lists are `[]`, `[obj]`, `[obj,]`, `[obj, obj]` ... (trailing comma optional)
 - Records are `{ "key": value}`, keys must be unique, order must be preserved. 
 - Built-ins: `true`, `false`, `null`
 - `"unicode strings"` with escapes `\" \\ \/ \b \f \n \r \t \uFFFF`, no control codes unecaped, and `''` can be used instead of `""`.
 - int/float numbers (unary plus or minus, allowleading zeros, hex, octal, and binary integer liters)
 - Tagged literals: `@name [1,2,3]` for any other type of value.


# RSON Object Model and Syntax

RSON has the following types of literals:

 - `null`, `true`, `false`
 - Integers (decimal, binary, octal, hex)
 - Floating Point
 - Strings (using single or double quotes)
 - Lists
 - Records (a JSON object with ordering and without duplicate keys)
 - Tagged Literal

RSON has a number of built-in tags:
 - `@object`, `@bool`, `@int`, `@float`, `@string`, `@list`, `@record`

As well as optional tags for other types:
 - `@bytestring`, or `@base64` for bytestrings
 - `@float "0x0p0"`, for C99 Hex Floating Point Literals
 - `@dict` for unordered key-value maps
 - `@set` for sets, `@complex` for complex numbers
 - `@datetime`, `@duration` for time as point or measurement.

## RSON strings: 

 - use ''s or ""s
 - json escapes, and `\xFF` (as `\u00FF`), `\UFFFFFFFF`  `\'` too
 - `\` at end of line is continuation
 - no surrogate pairs

## RSON numbers:

 - allow unary minus, plus
 - allow leading zero
 - allow underscores (except leading digits)
 - binary ints: `0b1010`
 - octal ints `0o777`
 - hex ints: `0xFF` 

## RSON lists:

 - allow trailing commas

## RSON records (aka, JSON objects):

 - no duplicate keys
 - insertion order must be preserved
 - allow trailing commas
 - implementations MUST support string keys

## RSON tagged objects:

 - `@foo.foo {"foo":1}` name is any unicode letter/digit, `_`or a `.`
 - `@int 1`, `@string "two"` are just `1` and `"two"`
 - do not nest,
 - whitespace between tag name and object is *mandatory*
 - every type has a reserved tag name
 - parsers MAY reject unknown, or return a wrapped object 

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
 - no duplicate items
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

 - `@complex [0,1]` (real, imaginary)

### Builtin RSON Tags:

Pass throughs (i.e `@foo bar` is `bar`):

 - `@object` on any 
 - `@bool` on true, or false
 - `@int` on ints
 - `@float` on ints or floats
 - `@string` on strings
 - `@list` on lists
 - `@record` on records

Tags that transform the literal:

 - @float on strings (for C99 hex floats, including NaN, -Inf, +Inf)
 - @duration on numbers (seconds)
 - @datetime on strings (utc timestamp)
 - @base64 on strings (into a bytesting)
 - @bytestring on strings (into a bytestring)
 - @set on lists 
 - @complex on lists
 - @dict on records

Reserved:

 - `@unknown`

Any other use of a builtin tag is an error and MUST be rejected.

# RSON Test Vectors

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

# Alternate Encodings

## Binary RSON

Note: this is a work-in-progress

This is a simple Type-Length-Value style encoding, similar to bencoding or netstrings:

```
OBJECT :== TRUE | FALSE | NULL |
                INT | FLOAT | BYTES | STRING |
                LIST | RECORD |
                TAG 

TRUE :== 'y'
FALSE :== 'n'
NULL :== 'z'
INT :== 'i' <number encoded as ascii string> '\x7f'
FLOAT :== 'f' <number encoded as hex ascii string> '\x7f'
BYTES :== 'b' <INT as n> '\x7f' <n bytes> `\x7f`
STRING :== 'u' <INT as n> '\x7f' <n bytes of utf-8 encoded string> `\x7f`

LIST :== 'l' <INT as n> <n OBJECTs> `\x7f`
RECORD :== 'r' <INT as n> <2n OBJECTs> `\x7f`
TAG :== 't' <STRING as tag> <OBJECT as value> `\x7f`
```

If a more compact representation is needed, use compression.

Work in Progress:

- Framing (i.e encaptulating in a len-checksum header, like Gob)
- tags for unsigned int8,16,32,64, signed ints
- tags for float32, float64
- tags for ints 0..31
- tags for field/tag definitions header
- tags for [type]/fixed width types

Rough plan: 
```
Tags: 'A..J' 'K..T' 'S..Z'
    unsigned 8,16,32,64, (128,256,512,1024, 2048,4096)
    negative 8,16,32,64, (128,256,512,1024, 2048,4096)
    float 16, 32         (64, 128, 256, 512)
Tags \x00-\x31:
    ints 0-31
Tags >x127:
    Either using leading bit as unary continuation bit,
    Or, UTF-8 style '10'/'11' continuation bits.
```

## Decorated JSON (RSON inside JSON)

- `true`, `false`, `null`, numbers, strings, lists unchanged.
- `{"a":1}` becomes `{'record': ["a", 1]}`
- `@tag {'a':1}` becomes `{'tag', ["a", 1]}`

Note: In this scheme, `@tag ["a",1]` and `@tag {"a":1}` encode to the same JSON, and cannot be distinguished.


