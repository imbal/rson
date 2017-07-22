% swi prolog

parse(X,S) :- phrase(file(S),X),!.

bom --> [65279],!.
bom --> [].

ws --> [X], {code_type(X, white)}, ows.
ows --> ws ; [].

%% comments
comment --> "#", comment_tail.

comment_tail --> newline,!.
comment_tail --> [_], comment_tail,!.
comment_tail --> [].

newline --> [10], linefeed. 
linefeed --> [13]; [].


%todo
% replace calls to build with calls to decorate
% comments
% records, collections
% integer types (float, hex, octal, binary, hex float)
% string types (single quotes, triple quotes, ("a" "a"))
% bytestrings
% decorators
% float literals @float "NaN"
% datetimes, periods
% format strings
% file is top_objects by newline

file(H) --> bom, ows, top_object(H), ows.

top_object(O) --> object(O) ; record(O).

object(O) --> (atom(O) ; collection(O); decorated(O); grouped(O)),!.

atom(A) --> identifier(A), builtin(A),!.
atom(A) --> (number(A); string(A)),!.
	
collection(C) --> (set(C); list(C); dict(C); table(C)),!.

decorated(D) --> "@",!,identifier(N), ws, object(O), {decorate(N,O,D)}.

set(set(C)) --> "{",!, ows, values(C), ows, "}".  % allow newlines
dict(dict(C)) --> "{",!, ows, pairs(C), ows, "}".
list(list(C)) --> "[",!, ows, values(C), ows, "]".
table(table(C)) --> "[",!, ows, pairs(C), ows, "]".

record(record(O)) --> entries(O).

grouped(record([])) --> "(", ows, ")".

grouped(O) --> "(", ows, string(O), ows, ")". % string builder
grouped(O) --> "(", ows, object(O), ows, ")".
grouped(O) --> "(", ows, record(O), ows, ")".


values([H|T]) --> object(H), value_tail(T).
values([]) --> [].

value_tail(T) --> ows, ",", ows, values(T).
value_tail([]) --> [].


pairs([K:V|T]) --> object(K), ows, ":", ows, object(V), pair_tail(T). 
pairs([]) --> [].

pair_tail(T) --> ows, ",", ows, pairs(T).
pair_tail([]) --> [].


entries([K:V|T]) --> object(K), ows, ":", ows, object(V), ows, ",", ows, entries0(T). 
entries([H|T]) --> object(H), ows, ",", ows, entries0(T).

entries0([K:V|T]) --> object(K), ows, ":", ows, object(V), entry_tail(T). 
entries0([H|T]) --> object(H),  entry_tail(T).
entries0([]) --> [].

entry_tail(T) --> ows, ",", ows, entries0(T).
entry_tail([]) --> [].



number(N) --> "-",!, number(N1),!, {N is -N1}.
number(N) --> "+",!,number(N).
number(N) --> number_raw(N).

number_raw(N) --> integer(N).
%   (hex_int(N); octal_int(N); binary_int(N); integer(N);
%    hex_float(N); float(N); float_literal(N); decorated_float(N)).

integer(N) --> digit(D0), digits(D), { number_codes(N, [D0|D]) },!.

%float(O) -->".",digit(D0),!, {append(".",[D0|T],O)}, digits(T).

digit(D) --> [D], {code_type(D, digit)},!.
digits([D|T]) --> ("_" -> !; []),digit(D), digits(T).
digits([]) --> [].

string(S) --> string(S, "\"").

string(A,T) --> [T], chars(S,T), {string_to_list(A,S)},!.
chars([],T) --> [T].
chars(O, T) --> "\\",!, escapes(O,T). 
chars([H|C],T) --> [H], chars(C,T).

escapes(O,T) --> "\"", {append("\"",T,O)},chars(T).
escapes(O,T) --> "n", {append("\n",T,O)},chars(T).

identifier(A) -->  csym(C),csyms(N), {string_to_atom([C|N],A)},!. 
csyms([H|T]) --> csym_(H), csyms(T).
csyms([]) --> [].
csym(C) --> [C], {code_type(C, csymf)}.
csym_(C) --> [C], {code_type(C, csym)}.

builtin(A) --> {member(A, [true, false, null])}.

decorate(float, _, _) :- !, fail.
decorate(N,O, decorated(N,O)).

% use ``'s not ""s for 'reasons'
% ?- parse(`(add 1 2 3 4)`,P), eval(P, X).
% P = [add, 1, 2, 3, 4],
% X = 10.

