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
 - Numbers (Floating Point, and integer literals: decimal, binary, octal, hex)
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
 - no surrogate pairs, no unprintables

## RSON numbers:

 - allow unary minus, plus
 - allow leading zero
 - allow underscores (except leading digits)
 - binary ints: `0b1010`
 - octal ints `0o777`
 - hex ints: `0xFF` 
 - floating point: `1.123e-10` `-0.0` `+0.0` 

Special floating point values `NaN`, `+Infinity` are represented using C99 hex literals, `@float "NaN"`

## RSON lists:

 - allow trailing commas

## RSON records (aka, JSON objects):

 - no duplicate keys: parser MUST reject
 - insertion order must be preserved, but not considered in equality
 - allow trailing commas
 - implementations MUST support string keys

 two keys are the same if

 - both strings and same codepoints (unnormalized)
 - same numerical value i.e `1` and `1.0` and `1.0e0` are the same key, `+0.0`, `-0.0` are the same key,
 - lists of same size and items are same
 - records of same size and key,values are same, ignoring order
 
 except:

 - `NaN` is never the same
 - a list containing `NaN` can never match another list
 - a record with a `NaN` key or value can never match another
 - each `NaN` key in a record is unique

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

`<sign>0x<hex mantissa>p<sign><decimal exponent>` or `...1x...` for subnormals.

### RSON sets (optional):

 - `@set [1,2,3]`
 - always a tagged list
 - no duplicate items, same rules as records
 - ordering does not matter when comparing

### RSON dicts (optional):

 - `@dict {"a":1}` 
 - keys must be emitted in lexical order, must round trip in same order.
 - keys should all be the same type
 - no duplicate items, same rules as records
 - keys must be comparable, hashable, parser MAY reject if not
 - a `@dict` is equal to a record if it has same keys, ignoring order.

sort order is only defined for keys of the same type

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

