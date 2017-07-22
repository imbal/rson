% swi prolog

parse(X,S) :- phrase(file(S),X),!.

lookahead(X),X --> X.

% match_any(Result, Pattern)
% match(X, `123`) matches 1 2 or 3
%
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

object(O) --> (collection(O); decorated(O); grouped(O); builtin(O); number(O); string(O)),!.
	
% collections: [], {}

collection(C) --> (set(C); list(C); dict(C); table(C)),!.

% unordered {}
set(set(C)) --> "{", ws, items(C), ws, "}".
dict(dict(C)) --> "{",ws, pairs(C), ws, "}".

% ordered []
list(list(C)) --> "[", ws, items(C), ws, "]".
table(table(C)) --> "[", ws, pairs(C), ws, "]".

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

% grouped objects: ()'s

grouped(O) --> "(", ws, string_record(O), ws, ")". 
grouped(O) --> "(", ws, object(O), ws, ")".

% records: mixed list of items and pairs

grouped(record([])) --> "(", ws, ")".
grouped(record(O)) --> "(", ws, entries(O), ws, ")".

entries([K:V|T]) --> object(K), ws, ":", ws, object(V), ws, ",", ws, entries0(T). 
entries([H|T]) --> object(H), ws, ",", ws, entries0(T).

entries0([K:V|T]) --> object(K), ws, ":", ws, object(V), entry_tail(T). 
entries0([H|T]) --> object(H),  entry_tail(T).
entries0([]) --> [].

entry_tail(T) --> ws, ",", ws, entries0(T).
entry_tail([]) --> [].

% decorators

decorated(D) --> "@",!,identifier(N), arguments(A), ws, object(O), {decorate(N,A,O,D)}.

arguments([]) --> [].
arguments(A) --> "(", ws, entries0(A), ws, ")".

% @float "NaN"
decorate(N,A, O, d(N,A,O)).

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
    "0x", 
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
    plusorminus(P),
    match(D0,`0123456789`), 
    match_any(D,`0123456789_`), 
    build_number([I,`p`,P,D0,D],O).

% +/- int [ frac ] [ eE exp ]
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
% ( " .." ws " ..." *)
string_record(_) --> {!,fail}.

string(S) --> string(S, "\"").
% escapes
% '' 
% """ / ''' with multiline

string(A,T) --> [T], chars(S,T), {string_to_list(A,S)},!.
chars([],T) --> [T].
chars([H|C],T) --> [H], chars(C,T).

% escapes: b n f r t \ / u 
% escapes: U " '

% bytestrings, also b"..." and \x...


% builtins
builtin(A) --> identifier(A), {member(A, [true, false, null])}.

identifier(A) -->  csym(C),csyms(N), {string_to_atom([C|N],A)},!. 
csyms([H|T]) --> csym_(H), csyms(T).
csyms([]) --> [].
csym(C) --> [C], {code_type(C, csymf)}.
csym_(C) --> [C], {code_type(C, csym)}.


%todo
% bytestrings
% decorators (reserved names, builtins)
% datetimes, periods
% format strings
% RSV: file is top_objects by newline
% unicode
% replace calls to build with calls to decorate 



% use ``'s not ""s for 'reasons'
% ?- parse(`(add 1 2 3 4)`,P), eval(P, X).
% P = [add, 1, 2, 3, 4],
% X = 10.

