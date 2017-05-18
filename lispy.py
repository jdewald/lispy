# http://norvig.com/lispy.html
import sys
import re

from environment import standard_env, Env

List    = list
Number  = (int, float)


class InPort(object):
    """An input port. Retains a line of chars."""
    tokenizer = r'''\s*(,@|[('`,)]|"(?:[\\].|[^\\"])*"|;.*|[^\s('"`,;)]*)(.*)'''

    def __init__(self, file):
        self.file = file;
        self.line = ''

    def next_token(self):
        "Return the next token, reading new text into line buffer if needed."
        while True:
            if self.line == '': self.line = self.file.readline()
            if self.line == '': return eof_object
            token, self.line = re.match(InPort.tokenizer, self.line).groups()
            if token != '' and not token.startswith(';'):
                return token


class Symbol(str): pass


def Sym(s, symbol_table={}):
    """Find or create unique symbol entry for str s in symbol table."""
    if s not in symbol_table: symbol_table[s] = Symbol(s)
    return symbol_table[s]

_quote, _if, _set, _define, _lambda, _begin, _definemacro, = map(Sym,
"quote  if   set!   define  lambda    begin   define-macro".split())

_quasiquote, _unquote, _unquotesplicing = map(Sym,
"quasiquote  unquote    unquote-splicing".split())

_load = Sym("load")


global_env = standard_env()
eof_object = Symbol('#<eof-object>')  # note that it's using Symbol, not Sym, so it's unreadable


def schemestr(exp):
    """Convert a python Object back into a Scheme-readable string."""
    if isinstance(exp, List):
        return '(%s)' % (' '.join(map(schemestr, exp)))
    else:
        return str(exp)


def parse(program):
    """Read a scheme expression from a string."""
    return read(program)


def tokenize(chars):
    """Convert a string of characters into a list of tokens."""
    return chars.replace('(', ' ( ').replace(')', ' ) ').split()


def readchar(inport):
    """Read the next character from an input port."""
    if inport.line != '':
        ch, inport.line = inport.line[0], inport.line[1:]
        return ch
    else:
        return inport.file.read(1) or eof_object


def read(inport):
    """Read a Scheme expression from an input port."""
    def read_ahead(token):
        if '(' == token:
            L = []
            while True:
                token = inport.next_token()
                if token == ')': return L
                else: L.append(read_ahead(token))
        elif ')' == token: raise SyntaxError('unexpected )')
        elif token in quotes: return [quotes[token], read(inport)]
        elif token is eof_object: raise SyntaxError("unexpected EOF in list")
        else: return atom(token)
    # body of read:
    token1 = inport.next_token()
    return eof_object if token1 is eof_object else read_ahead(token1)

quotes = {"'": _quote, "`": _quasiquote, ",": _unquote, ",@": _unquotesplicing}


def read_from_tokens(tokens):
    """Read an expression from a sequence of tokens."""
    if len(tokens) == 0:
        raise SyntaxError("Unexpected EOF while reading")

    token = tokens.pop(0)

    if '(' == token:
        L = []

        while tokens[0] != ')':
            L.append(read_from_tokens(tokens))

        tokens.pop(0)  # last thing we saw was ')', pop it
        return L
    elif ')' == token:
        raise SyntaxError('unexpected )')
    else:
        return atom(token)


def atom(token):
    """Numbers become numbers; every other token is a symbol."""
    if token == '#t': return True
    if token == '#f': return False
    elif token[0] == '"': return token[1:-1].decode('string_escape')
    try:
        return int(token)
    except ValueError:
        try:
            return float(token)
        except ValueError:
            try:
                return complex(token.replace('i', 'j', 1))
            except ValueError:
                return Sym(token)


def to_string(x):
    """Convert a Python object back into a Lisp-readable string."""
    if x is True: return "#t"
    elif x is False: return "#f"
    elif isinstance(x, Symbol): return x
    elif isinstance(x, str): return '"%s"' % x.encode('string_escape').replace('"', r'\"')
    elif isinstance(x, list): return '('+' '.join(map(to_string, x))+')'
    elif isinstance(x, complex): return str(x).replace('j', 'i')
    else: return str(x)


def load(filename):
    """Eval every expression from a file."""
    repl(None, InPort(open(filename)), None)

# This will likely get moved to it's own module
def eval(x, env=global_env):
    """Evaluate an expression in an environment"""
    print "(DEBUG: %s )" % (x, )
    if isinstance(x, Symbol):
        # variable reference: http://www.schemers.org/Documents/Standards/R5RS/HTML/r5rs-Z-H-7.html#%_sec_4.1.1
        return env.find(x)[x]
    elif not isinstance(x, List):
        # constant literal: http://www.schemers.org/Documents/Standards/R5RS/HTML/r5rs-Z-H-7.html#%_sec_4.1.2
        return x
    elif x[0] is _if:
        # conditional: http://www.schemers.org/Documents/Standards/R5RS/HTML/r5rs-Z-H-7.html#%_sec_4.1.5
        # assumes (if test conseq alt)
        (_, test, conseq, alt) = x
        exp = (conseq if eval(test, env) else alt)
        return eval(exp, env)
    elif x[0] is _define:
        # definition: http://www.schemers.org/Documents/Standards/R5RS/HTML/r5rs-Z-H-8.html#%_sec_5.2
        # this is assuming it's synactically valid: (define var expr)
        # if it's of the form (define (f params) expr) then we want to treat it as:
        #   (define f (lambda (params) expr)
        _ = x[0]
        var = x[1]
        exp = x[2]
        print "(DEBUG: \tvar is %s" % (type(var), )
        if isinstance(var, List):
            print "(DEBUG: switching to lambda)"
            return eval([x[0],
                 var[0], [_lambda, var[1:], exp]], env)
        else:
            env[var] = eval(exp, env)
            return env[var]
    elif x[0] is _set:
        # assignemnt: http://www.schemers.org/Documents/Standards/R5RS/HTML/r5rs-Z-H-7.html#%_sec_4.1.6
        (_, var, expression) = x
        env.find(var)[var] = eval(expression, env)
        return
    elif x[0] is _lambda:
        # lambda procedure: http://www.schemers.org/Documents/Standards/R5RS/HTML/r5rs-Z-H-7.html#%_sec_4.1.4
        (_, params, body) = x
        return Procedure(params, body, env)
    elif x[0] is _load:
        # my own special form, though mit-scheme has it, so it probably is defined
        (_, filename) = x
        load(filename)
    else:
        # procedure call: http://www.schemers.org/Documents/Standards/R5RS/HTML/r5rs-Z-H-7.html#%_sec_4.1.3
        proc = eval(x[0], env)
        args = [eval(arg, env) for arg in x[1:]]
        return proc(*args)


def repl(prompt="lisp.py> ", inport=InPort(sys.stdin), out=sys.stdout):
    """A prompt-read-eval-print loop."""
    sys.stderr.write("Lispy version 2.0 (jdewald)\n")
    while True:
        #try:
        if prompt: sys.stderr.write(prompt)
        x = parse(inport)
        if x is eof_object: return
        val = eval(x)
        if val is not None and out: print >> out, to_string(val)
    #except Exception as e:
         #   print '%s: %s' % (type(e).__name__, e)


def main():
    repl()


class Procedure(object):
    """A user-defined Scheme procedure
    http://www.schemers.org/Documents/Standards/R5RS/HTML/r5rs-Z-H-7.html#%_sec_4.1.4
    """
    def __init__(self, params, body, env):
        self.params, self.body, self.env = params, body, env

    def __call__(self, *args):
        return eval(self.body, Env(self.params, args, self.env))

if __name__ == "__main__":
    main()