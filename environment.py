import math
import operator as op


def standard_env():
    """An environment with some Scheme standard procedures."""
    env = Env()

    env.update(vars(math))  # gives us sin, cos, sqrt, pi

    env.update({
        '+': op.add, '-': op.sub, '*':op.mul, '/': op.truediv,
        '>': op.gt, '<': op.lt, '>=': op.ge, '<=': op.le, '=': op.eq,
        'begin':    lambda *x: x[-1],
        'or': op.or_,
        'even?':    lambda x: x % 2 == 0
    })
    return env


class Env(dict):
    """An environment: a dict of {'var':val} paris, with an outer Env."""
    def __init__(self, params=(), args=(), outer=None):
        self.update(zip(params, args))
        self.outer = outer

    def find(self, var):
        """Find the innermost Env where var appears."""
        if var in self: return self
        elif self.outer: return self.outer.find(var)
        else:
            raise Exception("Unresolved symbol: %s", var)

