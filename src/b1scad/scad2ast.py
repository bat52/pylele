#!/usr/bin/env python3

""" converts scad to ast """

# scad_parser.py
from __future__ import annotations
from sly import Lexer

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), "../"))
from b13d.api.utils import gen_scad_foo

class OpenSCADLexer(Lexer):
    tokens = (
        # New transforms/operations (Longer patterns first)
        LINEAR_EXTRUDE, ROTATE_EXTRUDE, INTERSECTION_FOR,
        
        # Existing shape/transform tokens
        CUBE, SPHERE, CYLINDER, POLYHEDRON,
        TRANSLATE, ROTATE, SCALE, UNION, DIFFERENCE, INTERSECTION, HULL,
        
        # New 2D primitives
        SQUARE, CIRCLE, POLYGON, TEXT,
        
        # New transforms/operations (Others)
        MIRROR, MULTMATRIX, RESIZE, COLOR, PROJECTION, MINKOWSKI, OFFSET,
        
        # New keywords
        MODULE, FUNCTION, IF, ELSE, FOR, LET, EACH, INCLUDE, USE, ASSERT, ECHO, CHILDREN,

        # Literals
        NUMBER, STRING, TRUE, FALSE, UNDEF,
        
        # Identifiers and special vars
        IDENTIFIER, SFN, SFA, SFS,
        
        # Structural
        LBRACE, RBRACE, LPAREN, RPAREN, LSQUARE, RSQUARE, COMMA, SEMICOLON,
        EQU, COLON, DOT, QUESTION, PIPE,
        
        # Arithmetic operators
        PLUS, MINUS, TIMES, DIVIDE, MOD, CARET,
        
        # Comparison operators
        LESS, GREATER, LE, GE, EQ, NEQ,
        
        # Logical operators
        AND, OR, NOT,
    )
    
    ignore = ' \t\n'

    # --- New transforms/operations (Order matters! Longest first) ---
    LINEAR_EXTRUDE = r'linear_extrude'
    ROTATE_EXTRUDE = r'rotate_extrude'
    INTERSECTION_FOR = r'intersection_for'

    # --- Existing shape/transform tokens ---
    CUBE = r'cube'
    SPHERE = r'sphere'
    CYLINDER = r'cylinder'
    POLYHEDRON = r'polyhedron'
    UNION = r'union'
    DIFFERENCE = r'difference'
    INTERSECTION = r'intersection'
    TRANSLATE = r'translate'
    ROTATE = r'rotate'
    SCALE = r'scale'
    HULL = r'hull'

    # --- New 2D primitives ---
    SQUARE = r'square'
    CIRCLE = r'circle'
    POLYGON = r'polygon'
    TEXT = r'text'

    # --- New transforms/operations (Others) ---
    MIRROR = r'mirror'
    MULTMATRIX = r'multmatrix'
    RESIZE = r'resize'
    COLOR = r'color'
    PROJECTION = r'projection'
    MINKOWSKI = r'minkowski'
    OFFSET = r'offset'

    # --- New keywords ---
    MODULE = r'module'
    FUNCTION = r'function'
    IF = r'if'
    ELSE = r'else'
    FOR = r'for'
    LET = r'let'
    EACH = r'each'
    INCLUDE = r'include'
    USE = r'use'
    ASSERT = r'assert'
    ECHO = r'echo'
    CHILDREN = r'children'


    # --- Literals ---
    TRUE = r'true'
    FALSE = r'false'
    UNDEF = r'undef'

    # --- Identifiers and special vars ---
    IDENTIFIER = r'[a-zA-Z_][a-zA-Z0-9_]*'
    SFN = r'\$fn'
    SFA = r'\$fa'
    SFS = r'\$fs'

    # --- Number ---
    NUMBER = r'[+-]?\d+(\.\d+)?([eE][+-]?\d+)?'

    # --- String literal ---
    STRING = r'"(?:[^"\\]|\\.)*"'

    # --- Structural ---
    LBRACE = r'\{'
    RBRACE = r'\}'
    LPAREN = r'\('
    RPAREN = r'\)'
    LSQUARE = r'\['
    RSQUARE = r'\]'
    COMMA = r','
    SEMICOLON = r';'
    EQU = r'='
    COLON = r':'
    DOT = r'\.'
    QUESTION = r'\?'
    PIPE = r'\|'

    # --- Arithmetic operators ---
    PLUS = r'\+'
    MINUS = r'-'
    TIMES = r'\*'
    DIVIDE = r'/'
    MOD = r'%'
    CARET = r'\^'

    # --- Comparison operators ---
    LE = r'<='
    GE = r'>='
    EQ = r'=='
    NEQ = r'!='
    LESS = r'<'
    GREATER = r'>'

    # --- Logical operators ---
    AND = r'&&'
    OR = r'\|\|'
    NOT = r'!'

    # --- Comments ---
    # Note: comments are handled in scad2ast() by preprocessing the source
    # to remove them before tokenization. This avoids conflicts with the
    # DIVIDE token (/) matching // as two separate tokens.

    def NUMBER(self, t):
        t.value = float(t.value) if '.' in t.value or 'e' in t.value.lower() else int(t.value)
        return t

    def STRING(self, t):
        # Strip quotes and unescape
        val = t.value[1:-1]
        val = val.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"').replace('\\\\', '\\')
        t.value = val
        return t

    def error(self, t):
        print("Illegal character '%s'" % t.value[0])
        self.index += 1

import re

def _strip_comments(code: str) -> str:
    """Strip // line comments and /* */ block comments from SCAD source code.
    Also transforms include/use <path> into include/use "path" to avoid
    lexer conflicts with comparison operators < and >.
    
    Handles:
    - Line comments: // ... until end of line
    - Block comments: /* ... */ (can span multiple lines)
    - Preserves string literals (doesn't strip // or /* inside strings)
    """
    # Transform include/use <path> to "path"
    code = re.sub(r'(include|use)\s*<([^>]+)>', r'\1 "\2"', code)
    
    result = []
    i = 0
    in_string = False
    while i < len(code):
        c = code[i]
        
        # Track string literals to avoid stripping inside them
        if c == '"' and (i == 0 or code[i-1] != '\\'):
            in_string = not in_string
            result.append(c)
            i += 1
            continue
        
        if not in_string:
            # Line comment: //
            if c == '/' and i + 1 < len(code) and code[i + 1] == '/':
                # Skip to end of line
                i += 2
                while i < len(code) and code[i] not in '\n\r':
                    i += 1
                continue
            
            # Block comment: /* ... */
            if c == '/' and i + 1 < len(code) and code[i + 1] == '*':
                i += 2
                while i < len(code):
                    if code[i] == '*' and i + 1 < len(code) and code[i + 1] == '/':
                        i += 2
                        break
                    i += 1
                continue
        
        result.append(c)
        i += 1
    
    return ''.join(result)


# Modify parser to output Python file
def scad2ast(infname: str, view: bool = True):

    assert os.path.exists(infname), f'File not found: {infname}'
    with open(infname, 'r', encoding='utf8') as f:
        code = f.read()

        # Strip comments before tokenization to avoid conflicts with DIVIDE token
        code = _strip_comments(code)

        lexer = OpenSCADLexer()
        ast = lexer.tokenize(code)
        
        if view:
            print('AST:')
            for tok in ast:
                print('\t type=%r, value=%r' % (tok.type, tok.value))
            print('AST END')
            ast = lexer.tokenize(code)
        
        return ast

# Example usage:
if __name__ == "__main__":
    if len(sys.argv)<2:
        infname = "model.scad"
        print(f'Unspecified input file, generate default {infname}')
        gen_scad_foo(infname, module_en=False)
    else:
        infname = sys.argv[1]
    
    ast = scad2ast(infname)
