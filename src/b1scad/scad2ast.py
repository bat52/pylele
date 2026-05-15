#!/usr/bin/env python3

""" converts scad to ast """

# scad_parser.py
from __future__ import annotations
from sly import Lexer

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))
from b13d.api.utils import gen_scad_foo

class OpenSCADLexer(Lexer):
    tokens = (
        # New transforms/operations (Longer patterns first)
        'LINEAR_EXTRUDE', 'ROTATE_EXTRUDE', 'INTERSECTION_FOR',
        
        # Existing shape/transform tokens
        'CUBE', 'SPHERE', 'CYLINDER', 'POLYHEDRON',
        'TRANSLATE', 'ROTATE', 'SCALE', 'UNION', 'DIFFERENCE', 'INTERSECTION', 'HULL',
        
        # New 2D primitives
        'SQUARE', 'CIRCLE', 'POLYGON', 'TEXT',
        
        # New transforms/operations (Others)
        'MIRROR', 'MULTMATRIX', 'RESIZE', 'COLOR', 'PROJECTION', 'MINKOWSKI', 'OFFSET',
        
        # New keywords
        'MODULE', 'FUNCTION', 'IF', 'ELSE', 'FOR', 'LET', 'EACH', 'INCLUDE', 'USE', 'ASSERT', 'ECHO', 'CHILDREN',

        # Literals
        'NUMBER', 'STRING', 'TRUE', 'FALSE', 'UNDEF',
        
        # Identifiers and special vars
        'IDENTIFIER', 'SFN', 'SFA', 'SFS',
        
        # Structural
        'LBRACE', 'RBRACE', 'LPAREN', 'RPAREN', 'LSQUARE', 'RSQUARE', 'COMMA', 'SEMICOLON',
        'EQU', 'COLON', 'DOT', 'QUESTION',
        
        # Arithmetic operators
        'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'MOD', 'CARET',
        
        # Comparison operators
        'LESS', 'GREATER', 'LE', 'GE', 'EQ', 'NEQ',
        
        # Logical operators
        'AND', 'OR', 'NOT',
    )
    
    ignore = ' \t\n#'

    # --- Identifiers and special vars ---
    # IDENTIFIER MUST be defined before all keyword tokens in the lexer class.
    # SLY builds a single regex alternation from all token patterns in the order
    # they are defined.  Since Python's re.match returns the FIRST matching
    # alternative (not the longest), having a standalone pattern like
    # cylinder=r'cylinder' before IDENTIFIER causes 'cylinderHeight' to be
    # tokenized as CYLINDER('cylinder') + IDENTIFIER('Height').
    # Placing IDENTIFIER first ensures it always wins, and the token function
    # below remaps specific values to keyword types.
    IDENTIFIER = r'[a-zA-Z_][a-zA-Z0-9_]*'

    # All keyword-like tokens (shapes, transforms, control flow, literals) are
    # handled by the IDENTIFIER token function below — NO separate regex patterns
    # are defined for them.  The tokens tuple still declares them so the parser
    # can reference them.
    _keywords = {
        # Shapes
        'cube': 'CUBE',
        'sphere': 'SPHERE',
        'cylinder': 'CYLINDER',
        'polyhedron': 'POLYHEDRON',
        'square': 'SQUARE',
        'circle': 'CIRCLE',
        'polygon': 'POLYGON',
        'text': 'TEXT',
        # Transforms / operations
        'translate': 'TRANSLATE',
        'rotate': 'ROTATE',
        'scale': 'SCALE',
        'union': 'UNION',
        'difference': 'DIFFERENCE',
        'intersection': 'INTERSECTION',
        'hull': 'HULL',
        'mirror': 'MIRROR',
        'multmatrix': 'MULTMATRIX',
        'resize': 'RESIZE',
        'color': 'COLOR',
        'projection': 'PROJECTION',
        'minkowski': 'MINKOWSKI',
        'offset': 'OFFSET',
        'linear_extrude': 'LINEAR_EXTRUDE',
        'rotate_extrude': 'ROTATE_EXTRUDE',
        'intersection_for': 'INTERSECTION_FOR',
        # Control flow / module keywords
        'module': 'MODULE',
        'function': 'FUNCTION',
        'if': 'IF',
        'else': 'ELSE',
        'for': 'FOR',
        'let': 'LET',
        'each': 'EACH',
        'include': 'INCLUDE',
        'use': 'USE',
        'assert': 'ASSERT',
        'echo': 'ECHO',
        'children': 'CHILDREN',
        # Literals
        'true': 'TRUE',
        'false': 'FALSE',
        'undef': 'UNDEF',
    }

    def IDENTIFIER(self, t):
        t.type = self._keywords.get(t.value, 'IDENTIFIER')
        return t

    SFN = r'\$fn'
    SFA = r'\$fa'
    SFS = r'\$fs'

    # --- Number ---
    NUMBER = r'(?:\d+\.?\d*|\.\d+)([eE][+-]?\d+)?'

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
    EQ = r'=='
    NEQ = r'!='
    LE = r'<='
    GE = r'>='
    EQU = r'='
    LESS = r'<'
    GREATER = r'>'
    COLON = r':'
    DOT = r'\.'
    QUESTION = r'\?'
    AND = r'&&'
    OR = r'\|\|'
    NOT = r'!'

    # --- Arithmetic operators ---
    PLUS = r'\+'
    MINUS = r'-'
    TIMES = r'\*'
    DIVIDE = r'/'
    MOD = r'%'
    CARET = r'\^'

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
    Also strips SCAD debug modifier characters (# % !) that appear before
    shape calls (these are visual-only modifiers in OpenSCAD and would
    otherwise cause lexer errors).
    
    Handles:
    - Line comments: // ... until end of line
    - Block comments: /* ... */ (can span multiple lines)
    - Preserves string literals (doesn't strip //, /*, or modifiers inside strings)
    - Does NOT strip * (multiplication operator, also a SCAD modifier but
      impossible to distinguish from multiplication without a parser).
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
            
            # Strip SCAD debug modifier characters (# %).
            # These are NOT comments — they are visual-only modifiers in
            # OpenSCAD that prefix shape calls. They do not affect geometry
            # and must be removed to avoid lexer errors (# in particular
            # causes SLY's ignore mechanism to misbehave).
            # Do NOT strip '!' — it is the logical NOT operator in
            # expressions (e.g. x!=y).  The reference lexer returns '!' as
            # a character token and the parser distinguishes NOT from the
            # debug-modifier prefix by context.
            # Do NOT strip '*' here — it is both a modifier and the
            # multiplication operator, and cannot be safely distinguished
            # without a full parser.
            if c in '#%':
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


