# -*- coding: utf-8 -*-
# TODO:
# better error reporting
# report inconsequential undefined atoms?
# more operators?

import re
import readline
import sys

ATOM_RE = re.compile(r"\w+", re.UNICODE) 
WHITESPACE_RE = re.compile(r"\s+", re.UNICODE)
NEGATION = u"¬"
CONJUNCTION = u"∧"
DISJUNCTION = u"∨"
GROUP_OPEN = u"("
GROUP_CLOSE = u")"

TRUE = u"1"
FALSE = u"0"

# Some helpers

def constructor_repr(obj, *params):
    return type(obj).__name__ + "(" + ", ".join(map(repr, params)) + ")"

def recognize_literal(symbol, constructor, text):
    if text.startswith(symbol):
        return (constructor(), text[len(symbol):])
    else:
        return None

# Token types

class Token(object):
    def __repr__(self):
        return constructor_repr(self)
    
    def __str__(self):
        return repr(self)

class T_Atom(Token):
    def __init__(self, name):
        self.name = name
    
    def __repr__(self):
        return constructor_repr(self, self.name)
    
    @classmethod
    def recognize(cls, text):
        match = ATOM_RE.match(text)
        if match != None:
            name = match.group()
            return (cls(name), text[len(name):])
        else:
            return None

class T_Negation(Token):
    @classmethod
    def recognize(cls, text):
        return recognize_literal(NEGATION, cls, text)

class T_Conjunction(Token):
    @classmethod
    def recognize(cls, text):
        return recognize_literal(CONJUNCTION, cls, text)

class T_Disjunction(Token):
    @classmethod
    def recognize(cls, text):
        return recognize_literal(DISJUNCTION, cls, text)

class T_GroupOpen(Token):
    @classmethod
    def recognize(cls, text):
        return recognize_literal(GROUP_OPEN, cls, text)

class T_GroupClose(Token):
    @classmethod
    def recognize(cls, text):
        return recognize_literal(GROUP_CLOSE, cls, text)

# Tokenization

class TokenizationError(Exception):
    pass

def skip_whitespace(text):
    match = WHITESPACE_RE.match(text)
    if match != None:
        return text[len(match.group()):]
    else:
        return text

def tokenize(text):
    types = (T_Atom, T_Negation, T_Conjunction, T_Disjunction, T_GroupOpen, T_GroupClose)
    remaining = skip_whitespace(text)
    while remaining:
        recognized = False
        for token_type in types:
            result = token_type.recognize(remaining)
            if result != None:
                token, remaining = result
                yield token
                remaining = skip_whitespace(remaining)
                recognized = True
                break
        if not recognized:
            raise TokenizationError(remaining)

# AST types

class Expression(object):
    def __init__(self):
        self.naked_subexpr_types = ()
        
    def unicode_subexpr(self, expr):
        if type(expr) in self.naked_subexpr_types:
            return unicode(expr)
        else:
            return GROUP_OPEN + unicode(expr) + GROUP_CLOSE
    
    def __str__(self):
        return unicode(self).encode("utf-8")

class E_Atom(Expression):
    def __init__(self, name):
        Expression.__init__(self)
        self.name = name
    
    def __repr__(self):
        return constructor_repr(self, self.name)
    
    def __unicode__(self):
        return self.name
    
    def evaluate(self, env):
        return env[self.name]

class E_Negation(Expression):
    def __init__(self, subexpr):
        Expression.__init__(self)
        self.naked_subexpr_types = (E_Atom, E_Negation)
        self.subexpr = subexpr
    
    def __repr__(self):
        return constructor_repr(self, self.subexpr)
    
    def __unicode__(self):
        return NEGATION + self.unicode_subexpr(self.subexpr)
    
    def evaluate(self, env):
        return not self.subexpr.evaluate(env)

class E_Conjunction(Expression):
    def __init__(self, lhs, rhs):
        Expression.__init__(self)
        self.naked_subexpr_types = (E_Atom, E_Negation, E_Conjunction)
        self.lhs, self.rhs = lhs, rhs
    
    def __repr__(self):
        return constructor_repr(self, self.lhs, self.rhs)

    def __unicode__(self):
        return u" ".join((
            self.unicode_subexpr(self.lhs),
            CONJUNCTION,
            self.unicode_subexpr(self.rhs)))
    
    def evaluate(self, env):
        return self.lhs.evaluate(env) and self.rhs.evaluate(env)

class E_Disjunction(Expression):
    def __init__(self, lhs, rhs):
        Expression.__init__(self)
        self.naked_subexpr_types = (E_Atom, E_Negation, E_Disjunction)
        self.lhs, self.rhs = lhs, rhs
    
    def __repr__(self):
        return constructor_repr(self, self.lhs, self, rhs)

    def __unicode__(self):
        return u" ".join((
            self.unicode_subexpr(self.lhs),
            DISJUNCTION,
            self.unicode_subexpr(self.rhs)))

    def evaluate(self, env):
        return self.lhs.evaluate(env) or self.rhs.evaluate(env)

# Generator wrapper that allows peeking at the next value

class Peekable(object):
    def __init__(self, gen):
        self._gen = gen
        self._next = None
    
    def __iter__(self):
        return self
    
    def has_next(self):
        try:
            self.peek()
            return True
        except StopIteration:
            return False
    
    def next(self):
        if self._next != None:
            value = self._next[0]
            self._next = None
            return value
        else:
            return self._gen.next()
    
    def peek(self):
        if not self._next:
            self._next = (self._gen.next(),)
        return self._next[0]

# Parsing
# See also grammar.txt

def next_token(kind, tokens):
    try:
        token = tokens.peek()
        if isinstance(token, kind):
            tokens.next()
            return token
        else:
            raise ParseError(u"expected %s, got %s" % (kind.__name__, type(token).__name__))
    except StopIteration:
        raise ParseError(u"expected %s, got EOF" % kind.__name__)

def choice(parser_dict, tokens):
    kinds = [k.__name__ for k in parser_dict.keys()]
    try:
        kind = type(tokens.peek())
        if kind in parser_dict:
            return parser_dict[kind](tokens)
        else:
            raise ParseError(u"expected %s, got %s" % (u"/".join(kinds), kind.__name__))
    except StopIteration:
        raise ParseError(u"expected %s, got EOF" % u"/".join(kinds))

class ParseError(Exception):
    pass

def parse_expr(tokens):
    lhs = choice({
        T_Atom: parse_atom,
        T_Negation: parse_negation,
        T_GroupOpen: parse_group
    }, tokens)
    return parse_expr_suf(lhs, tokens)
    
def parse_atom(tokens):
    atom = next_token(T_Atom, tokens)
    return E_Atom(atom.name)

def parse_expr_suf(lhs, tokens):
    conj = parse_conjunction_suf(lhs, tokens)
    if conj is not lhs:
        return conj
    return parse_disjunction_suf(lhs, tokens)

def parse_negation(tokens):
    next_token(T_Negation, tokens)
    return E_Negation(parse_negation_sub(tokens))

def parse_negation_sub(tokens):
    return choice({
        T_Atom: parse_atom,
        T_Negation: parse_negation,
        T_GroupOpen: parse_group
    }, tokens)

def parse_conjunction(tokens):
    lhs = choice({
        T_Atom: parse_atom,
        T_Negation: parse_negation,
        T_GroupOpen: parse_group
    }, tokens)
    return parse_conjunction_suf(lhs, tokens)

def parse_conjunction_suf(lhs, tokens):
    if tokens.has_next() and isinstance(tokens.peek(), T_Conjunction):
        tokens.next()
        rhs = parse_conjunction(tokens)
        return E_Conjunction(lhs, rhs)
    else:
        return lhs

def parse_disjunction(tokens):
    lhs = choice({
        T_Atom: parse_atom,
        T_Negation: parse_negation,
        T_GroupOpen: parse_group
    }, tokens)
    return parse_disjunction_suf(lhs, tokens)

def parse_disjunction_suf(lhs, tokens):
    if tokens.has_next() and isinstance(tokens.peek(), T_Disjunction):
        tokens.next()
        rhs = parse_disjunction(tokens)
        return E_Disjunction(lhs, rhs)
    else:
        return lhs

def parse_group(tokens):
    next_token(T_GroupOpen, tokens)
    subexpr = parse_expr(tokens)
    next_token(T_GroupClose, tokens)
    return subexpr

# Interpreter

def prompt_tty(text):
    return raw_input(text).decode("utf-8")

def prompt_no_tty(text):
    return raw_input().decode("utf-8")
    
def message_tty(*args):
    print u" ".join(args)

def message_no_tty(*args):
    pass

def run():
    prompt, message = (prompt_tty, message_tty) if sys.stdin.isatty() else (prompt_no_tty, message_no_tty)
    def_re = re.compile(r"^(%s)\s*=\s*(%s|%s)$" % (ATOM_RE.pattern, TRUE, FALSE), re.UNICODE)
    try:
        message(u"Define atoms by entering lines of the form:")
        message(u"    atomname = value")
        message(u"where value is %s or %s. Enter a blank line when done." % (TRUE, FALSE))
        env = {}
        while True:
            line = prompt(u"def> ").strip()
            if line:
                match = def_re.match(line)
                if match != None:
                    name = match.group(1)
                    value = match.group(2) == TRUE
                    env[name] = value
                else:
                    print >> sys.stderr, u"Invalid definition: %s" % line
            else:
                break
        message(u"Now enter expressions such as:")
        message(u"    %sa %s %sb %s c%s" % (NEGATION, CONJUNCTION, GROUP_OPEN, DISJUNCTION, GROUP_CLOSE))
        message(u"to evaluate their truth values.")
        while True:
            line = prompt(u"eval> ")
            if line.strip():
                try:
                    tokens = Peekable(tokenize(line))
                    ast = parse_expr(tokens)
                    truth = ast.evaluate(env)
                    print TRUE if truth else FALSE
                except TokenizationError, e:
                    print >> sys.stderr, u"Tokenization error: %s" % e
                except ParseError, e:
                    print >> sys.stderr, u"Parse error: %s" % e
                except KeyError, e:
                    print >> sys.stderr, u"Undefined atom: %s" % e.message
    except EOFError:
        message()
    except KeyboardInterrupt:
        message()

run()