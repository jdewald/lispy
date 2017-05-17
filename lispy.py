# http://norvig.com/lispy.html
from environment import standard_env, Env

Symbol  = str
List    = list
Number  = (int, float)


global_env = standard_env()


def schemestr(exp):
    """Convert a python Object back into a Scheme-readable string."""
    if isinstance(exp, List):
        return '(%s)' % (' '.join(map(schemestr, exp)))
    else:
        return str(exp)


def parse(program):
    """Read a scheme expression from a string."""
    return read_from_tokens(tokenize(program))


def tokenize(chars):
    """Convert a string of characters into a list of tokens."""
    return chars.replace('(', ' ( ').replace(')', ' ) ').split()


def read_from_tokens(tokens):
    """Read an expression from a sequence of tokens."""
    if len(tokens) == 0:
        raise SyntaxError("Unexpected EOF while reading")

    token = tokens.pop(0)

    if '(' == token:
        L = []

        while tokens[0] != ')':
            L.append(read_from_tokens(tokens))

        tokens.pop(0) # last ting we saw was ')', pop it
        return L
    elif ')' == token:
        raise SyntaxError('unexpected )')
    else:
        return atom(token)


def atom(token):
    """Numbers become numbers; every other token is a symbol."""
    try: return int(token)
    except ValueError:
        try: return float(token)
        except ValueError:
            return Symbol(token)


# This will likely get moved to it's own module
def eval(x, env=global_env):
    """Evaluate an expression in an environment"""
    if isinstance(x, Symbol):
        # variable reference: http://www.schemers.org/Documents/Standards/R5RS/HTML/r5rs-Z-H-7.html#%_sec_4.1.1
        return env.find(x)[x]
    elif not isinstance(x, List):
        # constant literal: http://www.schemers.org/Documents/Standards/R5RS/HTML/r5rs-Z-H-7.html#%_sec_4.1.2
        return x
    elif x[0] == 'if':
        # conditional: http://www.schemers.org/Documents/Standards/R5RS/HTML/r5rs-Z-H-7.html#%_sec_4.1.5
        # assumes (if test conseq alt)
        (_, test, conseq, alt) = x
        exp = (conseq if eval(test, env) else alt)
        return eval(exp, env)
    elif x[0] == 'define':
        # definition: http://www.schemers.org/Documents/Standards/R5RS/HTML/r5rs-Z-H-8.html#%_sec_5.2
        # this is assuming it's synactically valid: (define var expr)
        (_, var, exp) = x
        env[var] = eval(exp, env)
    elif x[0] == 'set!':
        # assignemnt: http://www.schemers.org/Documents/Standards/R5RS/HTML/r5rs-Z-H-7.html#%_sec_4.1.6
        (_, var, expression) = x
        env.find(var)[var] = eval(expression, env)
        return
    else:
        # procedure call: http://www.schemers.org/Documents/Standards/R5RS/HTML/r5rs-Z-H-7.html#%_sec_4.1.3
        proc = eval(x[0], env)
        args = [eval(arg, env) for arg in x[1:]]
        return proc(*args)


def repl(prompt="lisp.py> "):
    """A prompt-read-eval-print loop."""
    while True:
        val = eval(parse(raw_input(prompt)))
        if val is not None:
            print(schemestr(val))


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