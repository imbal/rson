% swi prolog

parse(X,S) :- phrase(file(S),X),!.

lookahead(X),X --> X.
lookahead(X,Y,Z),X,Y,Z --> X,Y,Z.

% match_any(Result, Pattern)
% match(X, `123`) matches 1 2 or 3

match(D,A) --> [D], {member(D, A)},!.
match_any([D|T],A) --> match(D,A), match_any(T,A).
match_any([],_) --> [].

% whitespace, comments, top level

bom --> [65279],!.
bom --> [].

ws --> comment, ws.
ws --> ([9];[10];[13];[32]), ws. % json compat
ws --> [].

comment --> "#", comment_tail.
comment_tail --> ([13, 10]; [13]; [10]),!.
comment_tail --> [_], comment_tail,!.
comment_tail --> [].

file(H) --> bom, ws, object(H), ws.

object(O) --> (collection(O); decorated(O); grouped(O); builtin(O); string(O); number(O)),!.

% decorators
decorated(D) --> "@",!,identifier(N), ws, object(O), {decorate(N,A,O,D)}.

%arguments([]) --> [].
%arguments(A) --> "(", ws, entries0(A), ws, ")".

% collections: [], {}

collection(C) --> (set(C); list(C); dict(C); table(C)),!.

% unordered {}
set(set(C)) --> "{", ws, items(C), ws, "}".
dict(dict(C)) --> "{",ws, pairs(C), ws, "}".

% ordered []
list(list(C)) --> "[", ws, items(C), ws, "]".
table(table(C)) --> "[", ws, pairs(C), ws, "]".


% grouped objects: ()'s

% string record: ("a" "b") ~> "ab"
grouped(O) --> "(", ws, string_record(O), ws, ")". 
% a single object
grouped(O) --> "(", ws, object(O), ws, ")".

% ugh: records don't work without barewords, dropped
% records: mixed list of items and pairs
%grouped(record([])) --> "(", ws, ")".
% grouped(record(O)) --> "(", ws, entries(O), ws, ")".



% sequences:
% a,b,c, 
items([H|T]) --> object(H), item_tail(T).
items([]) --> [].

item_tail(T) --> ws, ",", ws, items(T).
item_tail([]) --> [].

% k:v, ...
pairs([K:V|T]) --> object(K), ws, ":", ws, object(V), pair_tail(T). 
pairs([]) --> [].

pair_tail(T) --> ws, ",", ws, pairs(T).
pair_tail([]) --> [].

% a,b,c:d,e,f:g, ....
entries([K:V|T]) --> identifier(K), ws, ":", ws, object(V), ws, ",", ws, entries0(T). 
entries([H|T]) --> object(H), ws, ",", ws, entries0(T).

% same but also matches empty string
entries0([K:V|T]) --> identifier(K), ws, ":", ws, object(V), entry_tail(T). 
entries0([H|T]) --> object(H),  entry_tail(T).
entries0([]) --> [].

entry_tail(T) --> ws, ",", ws, entries0(T).
entry_tail([]) --> [].


% numbers

number(N) --> binary_integer(N); octal_integer(N); hex_number(N); decimal_number(N).

plusorminus(`+`) --> "+".
plusorminus(`-`) --> "-".
plusorminus([]) --> [].

binary_integer(N) -->
    plusorminus(P),
    "0b",!, match(D0,`01`), match_any(D,`01_`),
    build_number([P,`0b`,D0,D],N).

octal_integer(N) -->
    plusorminus(P),
    ("0c";"0o"),!,
    match(D0,`01234567`), match_any(D,`01234567_`),
    build_number([P,`0c`,D0,D],N).

hex_number(O) --> 
    plusorminus(P),
    ("0x";"0X"), 
    match(D0,`0123456789abcdefABCDEF`), 
    match_any(D,`0123456789_abcdefABCDEF`), 
    hex_fractional([P,`0x`,D0,D], O).

hex_fractional(I,O) --> ".",
    match(D0,`0123456789abcdefABCDEF`), 
    match_any(D,`0123456789_abcdefABCDEF`), 
    hex_exponent([I,`.`,D0,D], O).

hex_fractional(I,O) --> hex_exponent(I,O).
hex_fractional(I,O) --> build_number(I,O). 

hex_exponent(I,O) --> match(_,`pP`),
    plusorminus(P), % yes, the exponent of a hex floating point is in decimal.
    match(D0,`0123456789`), 
    match_any(D,`0123456789_`), 
    build_number([I,`p`,P,D0,D],O).

decimal_number(O) --> 
    plusorminus(P),
    match(D0,`0123456789`), 
    match_any(D,`0123456789_`), 
    fractional([P,D0,D], O).

fractional(I,O) --> match(X,`.`),
    match(D0,`0123456789`), 
    match_any(D,`0123456789_`), 
    exponent([I,X,D0,D], O).

fractional(I,O) --> exponent(I, O).

exponent(I,O) -->
    match(X, `eE`),
    plusorminus(P),
    match(D0,`0123456789`), 
    match_any(D,`0123456789_`), 
    build_number([I,X,P,D0,D],O).

exponent(I,O) --> build_number(I,O).

build_number(I, number(N)) --> {flatten(I,L), string_to_list(N, L)}.

% strings

string(S) --> ustring(S); bytestring(S).

ustring(string(S)) --> 
    (umulti_double(R); umulti_single(R); usingle_double(R); usingle_single(R)),
    !, {string_to_list(S,R)},!.


umulti_double(A) -->("u";"U";[]), "\"\"\"",!, multistring_inside(A,`"`,u), "\"\"\"".
umulti_single(A)-->("u";"U";[]), "'''", !, multistring_inside(A,`'`,u), "'''".

usingle_double(A)-->("u";"U";[]), "\"", !, string_inside(A,`"`,u), "\"".
usingle_single(A)-->("u";"U";[]), "'", !, string_inside(A,`'`,u), "'".

%  bytestrings

bytestring(bytes(S)) --> 
    (bmulti_double(R); bmulti_single(R); bsingle_double(R); bsingle_single(R)),
    !, {string_to_list(S,R)},!.

bmulti_double(A) -->("b";"B";[]), "\"\"\"",!, multistring_inside(A,`"`,b), "\"\"\"".
bmulti_single(A)-->("b";"B";[]), "'''", !, multistring_inside(A,`'`,b), "'''".
bsingle_double(A)-->("b";"B";[]), "\"", !, string_inside(A,`"`,b), "\"".
bsingle_single(A)-->("b";"B";[]), "'", !, string_inside(A,`'`,b), "'".

% insides
string_inside([],T,_) --> lookahead(T),!.
string_inside([],_,_) --> ([13];[10]),!, {fail}.
string_inside([H|C], T,X) --> lookahead(`\\`),!, [H], string_escape(C,T,X).
string_inside([H|C],T,X) --> [H], {H >= 32},string_inside(C,T,X).

string_escape(C,T,X) --> ([13, 10]; [13]; [10]), string_inside(C,T,X).
string_escape([H|C],T,X) --> match(H,`bnfrt/\\"'`), string_inside(C,T,X).
string_escape([120,D0,D1|C],T,b) --> "x", hexdigit2(D0,D1), string_inside(C,T,b).
string_escape([117,D0,D1,D2,D3|C],T,u) --> "u", hexdigit4(D0,D1,D2,D3), string_inside(C,T,u).
string_escape([85,D0,D1,D2,D3,D4,D5,D6,D7|C],T,u) --> "U", hexdigit4(D0,D1,D2,D3), hexdigit4(D4,D5,D6,D7), string_inside(C,T,u).

multistring_inside([H|C],T,X) --> match(H,T), \+lookahead(T),!, multistring_inside(C,T,X).
multistring_inside([H,H|C],T,X) --> match(H,T), match(H,T), \+lookahead(T),!, multistring_inside(C,T,X).
multistring_inside([H|C],T,X) --> match(H,T),lookahead(T,T,T),!, multistring_inside(C,T,X).
multistring_inside([],T,_) --> lookahead(T,T,T),!.
multistring_inside([H|C], T,X) --> lookahead(`\\`),!, [H], multistring_escape(C,T,X).
multistring_inside([H|C],T,X) --> [H], {member(H,[9,10,13]) ;H >= 32},multistring_inside(C,T,X).

multistring_escape(C,T,X) --> ([13, 10]; [13]; [10]), multistring_inside(C,T,X).
multistring_escape([H|C],T,X) --> match(H,`bnfrt/\\"'`), multistring_inside(C,T,X).
multistring_escape([120,D0,D1|C],T,b) --> "x", hexdigit2(D0,D1), multistring_inside(C,T,b).
multistring_escape([117,D0,D1,D2,D3|C],T,u) --> "u", hexdigit4(D0,D1,D2,D3), multistring_inside(C,T,u).
multistring_escape([85,D0,D1,D2,D3,D4,D5,D6,D7|C],T,u) --> "U", hexdigit4(D0,D1,D2,D3), hexdigit4(D4,D5,D6,D7), multistring_inside(C,T,u).

hexdigit2(D0,D1) -->
    match(D0,`0123456789abcdefABCDEF`), 
    match(D1,`0123456789abcdefABCDEF`).

hexdigit4(D0,D1,D2,D3) -->
    match(D0,`0123456789abcdefABCDEF`), 
    match(D1,`0123456789abcdefABCDEF`), 
    match(D2,`0123456789abcdefABCDEF`), 
    match(D3,`0123456789abcdefABCDEF`). 


% a c holdover, kept within ()'s % concat strings ( " ... " ws " ..."  ws " ...." ...)
%
string_record(S) --> ustring_record(S); bytestring_record(S).

ustring_record(bytes(S)) --> 
    (umulti_double(R); umulti_single(R); usingle_double(R); usingle_single(R)),
    ws, ustring_suffix(T), {flatten([R|T],L), string_to_list(S,L)},!.

ustring_suffix([R|T]) --> 
    (umulti_double(R); umulti_single(R); usingle_double(R); usingle_single(R)),
    ws, ustring_suffix(T).
ustring_suffix([]) --> [].


bytestring_record(string(S)) --> 
    (bmulti_double(R); bmulti_single(R); bsingle_double(R); bsingle_single(R)),
    ws, bytestring_suffix(T), {flatten([R|T],L), string_to_list(S,L)},!.

bytestring_suffix([R|T]) --> 
    (bmulti_double(R); bmulti_single(R); bsingle_double(R); bsingle_single(R)),
    ws, bytestring_suffix(T).
bytestring_suffix([]) --> [].

% todo: format strings/templates

% todo: handling for decorators
% i.e  @float "NaN", @float "+Infinity", or @float "123.4"  

decorate(N,[], O, decorate(N,O)).
decorate(N,A, O, decorate(N,A,O)).

% builtins
builtin(A) --> identifier(A), {member(A, [true, false, null])}.

identifier(A) -->  csym(C),csyms(N), {string_to_atom([C|N],A)},!. 
csyms([H|T]) --> csym_(H), csyms(T).
csyms([]) --> [].
csym(C) --> [C], {code_type(C, csymf)}.
csym_(C) --> [C], {code_type(C, csym)}.

% empty set / empty table @set {} / @table [] 


%todo
% decorators (reserved names, builtins)
% datetimes, periods
% float decorators for some numbers
% format strings
% RSV: file is top_objects by newline
% use ``'s not ""s for 'reasons'
%
%
% alt: start from json
%      add comments
%      trailing commas
%      bom
%      decorators
%      		decoratos for set, table, list, dict, float, int
%      sugar for decorated objects
