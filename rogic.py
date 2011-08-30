# -*- coding: utf-8 -*-

import re

ATOM_RE = re.compile(r"\w+", re.UNICODE) 
WHITESPACE_RE = re.compile(r"\s+", re.UNICODE)
NEGATION = u"!" #u"¬"
CONJUNCTION = u"&" #u"∧"
DISJUNCTION = u"|" #u"∨"
GROUP_OPEN = u"("
GROUP_CLOSE = u")"

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
