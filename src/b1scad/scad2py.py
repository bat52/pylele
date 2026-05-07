#!/usr/bin/env python3

""" converts scad to python """

# scad_parser.py
from __future__ import annotations
import textwrap
from sly import Parser, _

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), "../"))

from b13d.api.utils import gen_scad_foo, snake2camel, file_replace_extension
from b1scad.scad2ast import scad2ast, OpenSCADLexer
from b1scad.ast_nodes import (
    ASTNode, Module, NumberLiteral, VectorLiteral, Identifier,
    BinaryOp, UnaryOp, TernaryOp, ShapeCall, Transform, BooleanOp,
    ChildrenRef,
    Hull, Assignment, Block, FunctionCall,
    StringLiteral, BooleanLiteral, UndefLiteral, RangeLiteral,
    IntersectionFor, IncludeDirective, UseDirective,
    FunctionCallExpr, ArrayAccess, MemberAccess, SpecialVar,
    Square2D, Circle2D, Polygon2D, Text2D, Projection,
    Mirror, MultMatrix, Resize, Color, Echo, Assert,
    LinearExtrude, RotateExtrude, Offset, Minkowski,
    IfStatement, ForLoop, LetBinding, FunctionDef, ModuleDef,
)
from b1scad.symbol_table import SymbolTable



class OpenSCADParser(Parser):
    tokens = OpenSCADLexer.tokens
    debugfile = 'parser.out'

    # Precedence and associativity (lowest to highest)
    precedence = (
        ('left', 'PLUS', 'MINUS'),
        ('left', 'TIMES', 'DIVIDE', 'MOD'),
        ('right', 'UMINUS', 'NOT'),
        ('left', 'CARET'),
    )

    def __init__(self):
        self.result = []

    # ============================================================
    # Top-level entry (S')
    # ============================================================
    @_("statements")
    def module_start(self, t):
        return Module(t.statements)


    # ============================================================
    # Statement list
    # ============================================================
    @_("statement")
    def statements(self, t):
        return [t.statement]

    @_("statements statement")
    def statements(self, t):
        return t.statements + [t.statement]

    # ============================================================
    # Statements
    # ============================================================
    @_("shape_statement")
    def statement(self, t):
        return t.shape_statement

    @_("assignment_statement")
    def statement(self, t):
        return t.assignment_statement

    @_("module_def_statement")
    def statement(self, t):
        return t.module_def_statement

    @_("function_def_statement")
    def statement(self, t):
        return t.function_def_statement

    @_("if_else_statement")
    def statement(self, t):
        return t.if_else_statement

    @_("for_loop_statement")
    def statement(self, t):
        return t.for_loop_statement

    @_("let_statement")
    def statement(self, t):
        return t.let_statement

    @_("include_statement")
    def statement(self, t):
        return t.include_statement

    @_("use_statement")
    def statement(self, t):
        return t.use_statement

    @_("echo_statement")
    def statement(self, t):
        return t.echo_statement

    @_("assert_statement")
    def statement(self, t):
        return t.assert_statement

    # ============================================================
    # Shape statements (module instantiation)
    # ============================================================
    @_("shape_call SEMICOLON")
    def shape_statement(self, t):
        return t.shape_call

    @_("transform_op")
    def shape_statement(self, t):
        return t.transform_op

    @_("boolean_op")
    def shape_statement(self, t):
        return t.boolean_op

    @_('IDENTIFIER LPAREN args RPAREN SEMICOLON')
    def shape_statement(self, p):
        return FunctionCall(p.IDENTIFIER, [], _args_to_dict(p.args))

    @_('IDENTIFIER LPAREN args RPAREN LBRACE statements RBRACE')
    def shape_statement(self, p):
        return FunctionCall(p.IDENTIFIER, [], _args_to_dict(p.args))

    @_('CHILDREN LPAREN args RPAREN SEMICOLON')
    def shape_statement(self, p):
        return ChildrenRef(_args_to_dict(p.args))

    @_('CHILDREN LPAREN args RPAREN LBRACE statements RBRACE')
    def shape_statement(self, p):
        return ChildrenRef(_args_to_dict(p.args))

    # ============================================================
    # Shape calls (primitives)
    # ============================================================
    @_('CUBE LPAREN args RPAREN')
    def shape_call(self, p):
        return ShapeCall('cube', [], _args_to_dict(p.args))

    @_('SPHERE LPAREN args RPAREN')
    def shape_call(self, p):
        return ShapeCall('sphere', [], _args_to_dict(p.args))

    @_('CYLINDER LPAREN args RPAREN')
    def shape_call(self, p):
        return ShapeCall('cylinder', [], _args_to_dict(p.args))

    @_('POLYHEDRON LPAREN poly_args RPAREN')
    def shape_call(self, p):
        return ShapeCall('polyhedron', [], _args_to_dict(p.poly_args))

    @_('SQUARE LPAREN args RPAREN')
    def shape_call(self, p):
        args = _args_to_dict(p.args)
        return Square2D(
            size=args.get(0, args.get('size', NumberLiteral(1))),
            center=args.get('center', False)
        )

    @_('CIRCLE LPAREN args RPAREN')
    def shape_call(self, p):
        args = _args_to_dict(p.args)
        return Circle2D(
            radius=args.get('r'),
            diameter=args.get('d')
        )

    @_('POLYGON LPAREN poly_args RPAREN')
    def shape_call(self, p):
        args = _args_to_dict(p.poly_args)
        return Polygon2D(
            points=args.get(0, args.get('points')),
            paths=args.get('paths'),
            convexity=args.get('convexity', 1)
        )

    @_('TEXT LPAREN args RPAREN')
    def shape_call(self, p):
        args = _args_to_dict(p.args)
        text_val = args.get(0, args.get('text', ''))
        if not isinstance(text_val, str):
            text_val = str(text_val)
        return Text2D(
            text=text_val,
            size=args.get('size'),
            font=args.get('font'),
            halign=args.get('halign'),
            valign=args.get('valign'),
            spacing=args.get('spacing'),
            direction=args.get('direction'),
            language=args.get('language'),
            script=args.get('script')
        )

    # ============================================================
    # Transform operations (with body)
    # ============================================================
    @_('TRANSLATE LPAREN named_vector RPAREN LBRACE statements RBRACE')
    def transform_op(self, p):
        return Transform('translate', {'v': p.named_vector}, Block(p.statements))

    @_('ROTATE LPAREN named_vector RPAREN LBRACE statements RBRACE')
    def transform_op(self, p):
        return Transform('rotate', {'a': p.named_vector}, Block(p.statements))

    @_('SCALE LPAREN named_vector RPAREN LBRACE statements RBRACE')
    def transform_op(self, p):
        return Transform('scale', {'v': p.named_vector}, Block(p.statements))

    @_('MIRROR LPAREN args RPAREN LBRACE statements RBRACE')
    def transform_op(self, p):
        return Transform('mirror', _args_to_dict(p.args), Block(p.statements))

    @_('COLOR LPAREN args RPAREN LBRACE statements RBRACE')
    def transform_op(self, p):
        return Transform('color', _args_to_dict(p.args), Block(p.statements))

    @_('RESIZE LPAREN args RPAREN LBRACE statements RBRACE')
    def transform_op(self, p):
        return Transform('resize', _args_to_dict(p.args), Block(p.statements))

    @_('MULTMATRIX LPAREN args RPAREN LBRACE statements RBRACE')
    def transform_op(self, p):
        return Transform('multmatrix', _args_to_dict(p.args), Block(p.statements))

    # ============================================================
    # Boolean operations
    # ============================================================
    @_('UNION LPAREN RPAREN LBRACE statements RBRACE')
    def boolean_op(self, p):
        return BooleanOp('union', p.statements)

    @_('DIFFERENCE LPAREN RPAREN LBRACE statements RBRACE')
    def boolean_op(self, p):
        return BooleanOp('difference', p.statements)

    @_('INTERSECTION LPAREN RPAREN LBRACE statements RBRACE')
    def boolean_op(self, p):
        return BooleanOp('intersection', p.statements)

    @_('HULL LPAREN RPAREN LBRACE statements RBRACE')
    def boolean_op(self, p):
        return Hull(p.statements)

    @_('INTERSECTION_FOR LPAREN for_init RPAREN LBRACE statements RBRACE')
    def boolean_op(self, p):
        return IntersectionFor(p.for_init[0], p.for_init[1], Block(p.statements))

    # ============================================================
    # Extrude operations
    # ============================================================
    @_('LINEAR_EXTRUDE LPAREN args RPAREN LBRACE statements RBRACE')
    def transform_op(self, p):
        args = _args_to_dict(p.args)
        return LinearExtrude(
            height=args.get('height', args.get(0, NumberLiteral(100))),
            body=Block(p.statements),
            twist=args.get('twist'),
            scale=args.get('scale'),
            center=args.get('center', False)
        )

    @_('ROTATE_EXTRUDE LPAREN args RPAREN LBRACE statements RBRACE')
    def transform_op(self, p):
        args = _args_to_dict(p.args)
        return RotateExtrude(
            angle=args.get('angle', args.get(0)),
            body=Block(p.statements)
        )

    @_('OFFSET LPAREN args RPAREN LBRACE statements RBRACE')
    def transform_op(self, p):
        args = _args_to_dict(p.args)
        return Offset(
            radius=args.get('r', args.get('delta', args.get(0))),
            body=Block(p.statements)
        )

    @_('PROJECTION LPAREN args RPAREN LBRACE statements RBRACE')
    def transform_op(self, p):
        return Transform('projection', _args_to_dict(p.args), Block(p.statements))

    @_('MINKOWSKI LPAREN RPAREN LBRACE statements RBRACE')
    def transform_op(self, p):
        return Minkowski(p.statements)

    # (Module call rules moved to shape_statement above)
    
    # ============================================================
    # Assignment statement
    # ============================================================
    @_('IDENTIFIER EQU expr SEMICOLON')
    def assignment_statement(self, p):
        return Assignment(p.IDENTIFIER, p.expr)

    # ============================================================
    # Module definition
    # ============================================================
    @_('MODULE IDENTIFIER LPAREN RPAREN LBRACE statements RBRACE')
    def module_def_statement(self, p):
        return ModuleDef(p.IDENTIFIER, [], Block(p.statements))

    @_('MODULE IDENTIFIER LPAREN param_list RPAREN LBRACE statements RBRACE')
    def module_def_statement(self, p):
        return ModuleDef(p.IDENTIFIER, p.param_list, Block(p.statements))

    # ============================================================
    # Function definition
    # ============================================================
    @_('FUNCTION IDENTIFIER LPAREN RPAREN EQU expr SEMICOLON')
    def function_def_statement(self, p):
        return FunctionDef(p.IDENTIFIER, [], p.expr)

    @_('FUNCTION IDENTIFIER LPAREN param_list RPAREN EQU expr SEMICOLON')
    def function_def_statement(self, p):
        return FunctionDef(p.IDENTIFIER, p.param_list, p.expr)

    # ============================================================
    # Parameter list
    # ============================================================
    @_('param')
    def param_list(self, p):
        return [p.param]

    @_('param_list COMMA param')
    def param_list(self, p):
        return p.param_list + [p.param]

    @_('IDENTIFIER')
    def param(self, p):
        return (p.IDENTIFIER, None)

    @_('IDENTIFIER EQU expr')
    def param(self, p):
        return (p.IDENTIFIER, p.expr)

    # ============================================================
    # If/else statement
    # ============================================================
    @_('IF LPAREN expr RPAREN LBRACE statements RBRACE')
    def if_else_statement(self, p):
        return IfStatement(p.expr, Block(p.statements), None)

    @_('IF LPAREN expr RPAREN LBRACE statements RBRACE ELSE LBRACE statements RBRACE')
    def if_else_statement(self, p):
        return IfStatement(p.expr, Block(p.statements0), Block(p.statements1))

    @_('IF LPAREN expr RPAREN LBRACE statements RBRACE ELSE if_else_statement')
    def if_else_statement(self, p):
        return IfStatement(p.expr, Block(p.statements), p.if_else_statement)

    # ============================================================
    # For loop
    # ============================================================
    @_('FOR LPAREN for_init RPAREN LBRACE statements RBRACE')
    def for_loop_statement(self, p):
        return ForLoop(p.for_init[0], p.for_init[1], Block(p.statements))

    @_('IDENTIFIER EQU expr')
    def for_init(self, p):
        return (p.IDENTIFIER, p.expr)

    # ============================================================
    # Let binding
    # ============================================================
    @_('LET LPAREN let_bindings RPAREN LBRACE statements RBRACE')
    def let_statement(self, p):
        return LetBinding(p.let_bindings, Block(p.statements))

    @_('let_binding')
    def let_bindings(self, p):
        return [p.let_binding]

    @_('let_bindings COMMA let_binding')
    def let_bindings(self, p):
        return p.let_bindings + [p.let_binding]

    @_('IDENTIFIER EQU expr')
    def let_binding(self, p):
        return Assignment(p.IDENTIFIER, p.expr)

    # ============================================================
    # Include/Use
    # ============================================================
    @_('INCLUDE STRING SEMICOLON')
    def include_statement(self, p):
        return IncludeDirective(p.STRING)

    @_('USE STRING SEMICOLON')
    def use_statement(self, p):
        return UseDirective(p.STRING)

    # ============================================================
    # Echo/Assert
    # ============================================================
    @_('ECHO LPAREN args RPAREN SEMICOLON')
    def echo_statement(self, p):
        return Echo(p.args)

    @_('ASSERT LPAREN expr RPAREN SEMICOLON')
    def assert_statement(self, p):
        return Assert(p.expr)

    @_('ASSERT LPAREN expr COMMA expr RPAREN SEMICOLON')
    def assert_statement(self, p):
        return Assert(p.expr0, p.expr1)

    # ============================================================
    # Expression grammar (full precedence)
    # ============================================================
    @_("ternary_expr")
    def expr(self, t):
        return t.ternary_expr

    @_("logical_or_expr QUESTION ternary_expr COLON ternary_expr")
    def ternary_expr(self, t):
        return TernaryOp(t.logical_or_expr, t.ternary_expr0, t.ternary_expr1)

    @_("logical_or_expr")
    def ternary_expr(self, t):
        return t.logical_or_expr

    @_("logical_and_expr")
    def logical_or_expr(self, t):
        return t.logical_and_expr

    @_("logical_or_expr OR logical_and_expr")
    def logical_or_expr(self, t):
        return BinaryOp('||', t.logical_or_expr, t.logical_and_expr)

    @_("equality_expr")
    def logical_and_expr(self, t):
        return t.equality_expr

    @_("logical_and_expr AND equality_expr")
    def logical_and_expr(self, t):
        return BinaryOp('&&', t.logical_and_expr, t.equality_expr)

    @_("comparison_expr")
    def equality_expr(self, t):
        return t.comparison_expr

    @_("equality_expr EQ comparison_expr")
    def equality_expr(self, t):
        return BinaryOp('==', t.equality_expr, t.comparison_expr)

    @_("equality_expr NEQ comparison_expr")
    def equality_expr(self, t):
        return BinaryOp('!=', t.equality_expr, t.comparison_expr)

    @_("addition_expr")
    def comparison_expr(self, t):
        return t.addition_expr

    @_("comparison_expr LESS addition_expr")
    def comparison_expr(self, t):
        return BinaryOp('<', t.comparison_expr, t.addition_expr)

    @_("comparison_expr GREATER addition_expr")
    def comparison_expr(self, t):
        return BinaryOp('>', t.comparison_expr, t.addition_expr)

    @_("comparison_expr LE addition_expr")
    def comparison_expr(self, t):
        return BinaryOp('<=', t.comparison_expr, t.addition_expr)

    @_("comparison_expr GE addition_expr")
    def comparison_expr(self, t):
        return BinaryOp('>=', t.comparison_expr, t.addition_expr)

    @_("multiplication_expr")
    def addition_expr(self, t):
        return t.multiplication_expr

    @_("addition_expr PLUS multiplication_expr")
    def addition_expr(self, t):
        return BinaryOp('+', t.addition_expr, t.multiplication_expr)

    @_("addition_expr MINUS multiplication_expr")
    def addition_expr(self, t):
        return BinaryOp('-', t.addition_expr, t.multiplication_expr)

    @_("unary_expr")
    def multiplication_expr(self, t):
        return t.unary_expr

    @_("multiplication_expr TIMES unary_expr")
    def multiplication_expr(self, t):
        return BinaryOp('*', t.multiplication_expr, t.unary_expr)

    @_("multiplication_expr DIVIDE unary_expr")
    def multiplication_expr(self, t):
        return BinaryOp('/', t.multiplication_expr, t.unary_expr)

    @_("multiplication_expr MOD unary_expr")
    def multiplication_expr(self, t):
        return BinaryOp('%', t.multiplication_expr, t.unary_expr)

    @_("power_expr")
    def unary_expr(self, t):
        return t.power_expr

    @_("MINUS power_expr %prec UMINUS")
    def unary_expr(self, t):
        return UnaryOp('-', t.power_expr)

    @_("NOT power_expr")
    def unary_expr(self, t):
        return UnaryOp('!', t.power_expr)

    @_("call_expr")
    def power_expr(self, t):
        return t.call_expr

    @_("power_expr CARET unary_expr")
    def power_expr(self, t):
        return BinaryOp('^', t.power_expr, t.unary_expr)

    @_("primary")
    def call_expr(self, t):
        return t.primary

    @_("call_expr LPAREN args RPAREN")
    def call_expr(self, t):
        return FunctionCallExpr(t.call_expr, [], _args_to_dict(t.args))

    @_("call_expr LSQUARE expr RSQUARE")
    def call_expr(self, t):
        return ArrayAccess(t.call_expr, t.expr)

    @_("call_expr DOT IDENTIFIER")
    def call_expr(self, t):
        return MemberAccess(t.call_expr, t.IDENTIFIER)

    # ============================================================
    # Primary expressions
    # ============================================================
    @_('NUMBER')
    def primary(self, t):
        return NumberLiteral(t.NUMBER)

    @_('STRING')
    def primary(self, t):
        return StringLiteral(t.STRING)

    @_('TRUE')
    def primary(self, t):
        return BooleanLiteral(True)

    @_('FALSE')
    def primary(self, t):
        return BooleanLiteral(False)

    @_('UNDEF')
    def primary(self, t):
        return UndefLiteral()

    @_('IDENTIFIER')
    def primary(self, t):
        return Identifier(t.IDENTIFIER)

    @_('SFN')
    def primary(self, t):
        return SpecialVar('$fn')

    @_('SFA')
    def primary(self, t):
        return SpecialVar('$fa')

    @_('SFS')
    def primary(self, t):
        return SpecialVar('$fs')

    @_('LPAREN expr RPAREN')
    def primary(self, t):
        return t.expr

    @_('vector')
    def primary(self, t):
        return t.vector

    @_('LSQUARE for_comprehension RSQUARE')
    def primary(self, t):
        return t.for_comprehension

    # ============================================================
    # For comprehension (inside vector)
    # ============================================================
    @_('FOR LPAREN for_init RPAREN expr')
    def for_comprehension(self, p):
        return ForLoop(p.for_init[0], p.for_init[1], p.expr)

    @_('FOR LPAREN for_init RPAREN IF LPAREN expr RPAREN expr')
    def for_comprehension(self, p):
        return ForLoop(p.for_init[0], p.for_init[1], IfStatement(p.expr0, p.expr1, None))

    @_('LET LPAREN let_bindings RPAREN expr')
    def for_comprehension(self, p):
        return LetBinding(p.let_bindings, p.expr)

    @_('EACH expr')
    def for_comprehension(self, p):
        return p.expr

    # ============================================================
    # Vector literal (also handles range)
    # ============================================================
    @_('LSQUARE list_items RSQUARE')
    def vector(self, p):
        return VectorLiteral(p.list_items)

    @_('LSQUARE expr COLON expr RSQUARE')
    def vector(self, p):
        return RangeLiteral(p.expr0, p.expr1)

    @_('LSQUARE expr COLON expr COLON expr RSQUARE')
    def vector(self, p):
        return RangeLiteral(p.expr0, p.expr2, p.expr1)

    @_('list_item COMMA list_items')
    def list_items(self, p):
        return [p.list_item] + p.list_items

    @_('list_item')
    def list_items(self, p):
        return [p.list_item]

    @_('expr')
    def list_item(self, p):
        return p.expr

    # ============================================================
    # Named arguments
    # ============================================================
    @_('SFN EQU NUMBER')
    def arg(self, p):
        return ('$fn', NumberLiteral(p.NUMBER))

    @_('IDENTIFIER EQU expr')
    def arg(self, p):
        return (p.IDENTIFIER, p.expr)

    @_('expr')
    def arg(self, p):
        return p.expr

    # ============================================================
    # Args (comma-separated)
    # ============================================================
    @_('arg COMMA args')
    def args(self, p):
        return _merge_args([p.arg], p.args)

    @_('arg')
    def args(self, p):
        return [p.arg]

    @_('')
    def args(self, p):
        return []

    # ============================================================
    # poly_args (for polyhedron/polygon)
    # ============================================================
    @_('arg COMMA poly_args')
    def poly_args(self, p):
        return _merge_args([p.arg], p.poly_args)

    @_('arg')
    def poly_args(self, p):
        return [p.arg]

    # ============================================================
    # Named vector (for translate/rotate/scale)
    # ============================================================
    @_('IDENTIFIER EQU vector')
    def named_vector(self, p):
        return p.vector

    @_('vector')
    def named_vector(self, p):
        return p.vector


def _args_to_dict(args_list):
    """Convert a list of (name, value) tuples to a dict.
    Positional args get numeric keys 0, 1, 2, ...
    """
    result = {}
    pos_idx = 0
    for item in args_list:
        if isinstance(item, tuple):
            name, val = item
            result[name] = val
        else:
            result[pos_idx] = item
            pos_idx += 1
    return result


def _merge_args(a, b):
    """Merge two arg lists."""
    if isinstance(a, list) and isinstance(b, list):
        return a + b
    if isinstance(a, list):
        return a + [b]
    if isinstance(b, list):
        return [a] + b
    return [a, b]


# ============================================================
# Include/Use Resolution
# ============================================================

def resolve_includes(ast_root: Module, scad_dir: str) -> Module:
    """Resolve include and use directives by recursively parsing referenced files.
    
    For 'include <file>': replaces the IncludeDirective node with the parsed AST
    of the included file (inline expansion).
    For 'use <file>': populates the UseDirective.resolved_ast field with the
    parsed AST of the used file (for module/function access).
    """
    resolved_statements = []
    for stmt in ast_root.statements:
        if isinstance(stmt, IncludeDirective):
            inc_path = _resolve_scad_path(stmt.path, scad_dir)
            if inc_path and os.path.exists(inc_path):
                print(f"  Including: {inc_path}")
                inc_ast = _parse_scad_file(inc_path)
                # Recursively resolve includes in the included file
                inc_ast = resolve_includes(inc_ast, os.path.dirname(inc_path))
                resolved_statements.extend(inc_ast.statements)
            else:
                print(f"  Warning: include file not found: {stmt.path}")
        elif isinstance(stmt, UseDirective):
            use_path = _resolve_scad_path(stmt.path, scad_dir)
            if use_path and os.path.exists(use_path):
                print(f"  Using: {use_path}")
                use_ast = _parse_scad_file(use_path)
                stmt.resolved_ast = use_ast
                resolved_statements.append(stmt)
            else:
                print(f"  Warning: use file not found: {stmt.path}")
                resolved_statements.append(stmt)
        else:
            resolved_statements.append(stmt)
    return Module(resolved_statements)


def _resolve_scad_path(path: str, scad_dir: str) -> str:
    """Resolve a SCAD file path relative to the source directory."""
    # Try with .scad extension
    if not path.endswith('.scad'):
        path_scad = path + '.scad'
    else:
        path_scad = path
    
    # Try relative to scad_dir
    full_path = os.path.join(scad_dir, path_scad)
    if os.path.exists(full_path):
        return full_path
    
    # Try as-is
    if os.path.exists(path_scad):
        return path_scad
    
    # Try without extension
    if path.endswith('.scad'):
        full_path_no_ext = os.path.join(scad_dir, path[:-5])
        if os.path.exists(full_path_no_ext):
            return full_path_no_ext
    
    return None


def _parse_scad_file(filepath: str) -> Module:
    """Parse a SCAD file and return its AST."""
    from b1scad.scad2ast import scad2ast
    tokens = scad2ast(filepath, view=False)
    parser = OpenSCADParser()
    ast_root = parser.parse(tokens)
    return ast_root


# ============================================================
# Symbol Table Integration
# ============================================================

class SymbolTableVisitor:
    """Walk the AST and populate a symbol table with scope tracking."""
    
    def __init__(self):
        self.symtab = SymbolTable()
    
    def visit(self, node: ASTNode):
        if node is None:
            return
        method = getattr(self, f'visit_{type(node).__name__}', None)
        if method is not None:
            method(node)
    
    def visit_Module(self, node: Module):
        for stmt in node.statements:
            self.visit(stmt)
    
    def visit_Block(self, node: Block):
        self.symtab.push_scope('block')
        for stmt in node.statements:
            self.visit(stmt)
        self.symtab.pop_scope()
    
    def visit_Assignment(self, node: Assignment):
        self.symtab.define(node.name, 'variable', line=node.line)
        self.visit(node.value)
    
    def visit_FunctionDef(self, node: FunctionDef):
        param_names = [p[0] for p in node.parameters]
        self.symtab.define(node.name, 'function', parameters=param_names, line=node.line)
        self.symtab.push_scope('function')
        for pname, pdefault in node.parameters:
            self.symtab.define(pname, 'variable', line=node.line)
            if pdefault is not None:
                self.visit(pdefault)
        self.visit(node.body)
        self.symtab.pop_scope()
    
    def visit_ModuleDef(self, node: ModuleDef):
        param_names = [p[0] for p in node.parameters]
        self.symtab.define(node.name, 'module', parameters=param_names, line=node.line)
        self.symtab.push_scope('module')
        for pname, pdefault in node.parameters:
            self.symtab.define(pname, 'variable', line=node.line)
            if pdefault is not None:
                self.visit(pdefault)
        self.visit(node.body)
        self.symtab.pop_scope()
    
    def visit_ForLoop(self, node: ForLoop):
        self.symtab.push_scope('for')
        self.symtab.define(node.variable, 'variable', line=node.line)
        self.visit(node.values)
        self.visit(node.body)
        self.symtab.pop_scope()
    
    def visit_LetBinding(self, node: LetBinding):
        self.symtab.push_scope('let')
        for assign in node.assignments:
            self.visit(assign)
        self.visit(node.body)
        self.symtab.pop_scope()
    
    def visit_IfStatement(self, node: IfStatement):
        self.visit(node.condition)
        self.visit(node.then_body)
        if node.else_body:
            self.visit(node.else_body)
    
    def visit_ShapeCall(self, node: ShapeCall):
        for arg in node.args:
            self.visit(arg)
        for val in node.named_args.values():
            self.visit(val)
    
    def visit_Transform(self, node: Transform):
        for val in node.params.values():
            self.visit(val)
        self.visit(node.body)
    
    def visit_BooleanOp(self, node: BooleanOp):
        for op in node.operands:
            self.visit(op)
    
    def visit_Hull(self, node: Hull):
        for op in node.operands:
            self.visit(op)
    
    def visit_Minkowski(self, node: Minkowski):
        for op in node.operands:
            self.visit(op)
    
    def visit_FunctionCall(self, node: FunctionCall):
        for arg in node.arguments:
            self.visit(arg)
        for val in node.named_arguments.values():
            self.visit(val)
    
    def visit_FunctionCallExpr(self, node: FunctionCallExpr):
        self.visit(node.callee)
        for arg in node.arguments:
            self.visit(arg)
        for val in node.named_arguments.values():
            self.visit(val)
    
    def visit_IntersectionFor(self, node: IntersectionFor):
        self.symtab.push_scope('for')
        self.symtab.define(node.variable, 'variable', line=node.line)
        self.visit(node.values)
        self.visit(node.body)
        self.symtab.pop_scope()
    
    def visit_IncludeDirective(self, node: IncludeDirective):
        if node.resolved_ast:
            self.visit(node.resolved_ast)
    
    def visit_UseDirective(self, node: UseDirective):
        if node.resolved_ast:
            # For 'use', only register module/function definitions
            for stmt in node.resolved_ast.statements:
                if isinstance(stmt, (ModuleDef, FunctionDef)):
                    self.visit(stmt)
    
    # Expression nodes - visit children for side effects
    def visit_BinaryOp(self, node: BinaryOp):
        self.visit(node.left)
        self.visit(node.right)
    
    def visit_UnaryOp(self, node: UnaryOp):
        self.visit(node.operand)
    
    def visit_TernaryOp(self, node: TernaryOp):
        self.visit(node.condition)
        self.visit(node.true_expr)
        self.visit(node.false_expr)
    
    def visit_VectorLiteral(self, node: VectorLiteral):
        for e in node.elements:
            self.visit(e)
    
    def visit_RangeLiteral(self, node: RangeLiteral):
        self.visit(node.start)
        self.visit(node.end)
        if node.step:
            self.visit(node.step)
    
    def visit_ArrayAccess(self, node: ArrayAccess):
        self.visit(node.target)
        self.visit(node.index)
    
    def visit_MemberAccess(self, node: MemberAccess):
        self.visit(node.target)
    
    def visit_Echo(self, node: Echo):
        for arg in node.args:
            self.visit(arg)
    
    def visit_Assert(self, node: Assert):
        self.visit(node.condition)
        if node.message:
            self.visit(node.message)
    
    # Leaf nodes - nothing to do
    def visit_NumberLiteral(self, node: NumberLiteral): pass
    def visit_StringLiteral(self, node: StringLiteral): pass
    def visit_BooleanLiteral(self, node: BooleanLiteral): pass
    def visit_UndefLiteral(self, node: UndefLiteral): pass
    def visit_Identifier(self, node: Identifier): pass
    def visit_SpecialVar(self, node: SpecialVar): pass


# ============================================================
# Variable Inlining: replace Identifier nodes with their assigned values
# ============================================================

def _replace_identifiers(node: ASTNode, var_map: dict[str, ASTNode]) -> ASTNode:
    """Deep copy walk of the AST, replacing Identifier nodes with their
    inlined values from var_map.
    
    When an Identifier node is found whose name matches a key in var_map,
    returns a deep copy of the corresponding value node. Otherwise,
    recursively processes child nodes and returns a new same-type node.
    """
    # Leaf nodes that need no recursion
    if isinstance(node, (NumberLiteral, StringLiteral, BooleanLiteral, UndefLiteral, SpecialVar)):
        return node
    
    # Identifier: substitute if in map
    if isinstance(node, Identifier):
        if node.name in var_map:
            return _replace_identifiers(var_map[node.name], var_map)
        return node
    
    # UnaryOp
    if isinstance(node, UnaryOp):
        return UnaryOp(node.operator, _replace_identifiers(node.operand, var_map))
    
    # BinaryOp
    if isinstance(node, BinaryOp):
        return BinaryOp(node.operator,
                        _replace_identifiers(node.left, var_map),
                        _replace_identifiers(node.right, var_map))
    
    # TernaryOp
    if isinstance(node, TernaryOp):
        return TernaryOp(_replace_identifiers(node.condition, var_map),
                         _replace_identifiers(node.true_expr, var_map),
                         _replace_identifiers(node.false_expr, var_map))
    
    # VectorLiteral
    if isinstance(node, VectorLiteral):
        return VectorLiteral([_replace_identifiers(e, var_map) for e in node.elements])
    
    # RangeLiteral
    if isinstance(node, RangeLiteral):
        new_step = _replace_identifiers(node.step, var_map) if node.step else None
        return RangeLiteral(_replace_identifiers(node.start, var_map),
                            _replace_identifiers(node.end, var_map),
                            new_step)
    
    # ShapeCall
    if isinstance(node, ShapeCall):
        new_args = {k: _replace_identifiers(v, var_map) if isinstance(v, ASTNode) else v
                    for k, v in node.named_args.items()}
        return ShapeCall(node.function_name, [], new_args)
    
    # Square2D
    if isinstance(node, Square2D):
        return Square2D(_replace_identifiers(node.size, var_map), node.center)
    
    # Circle2D
    if isinstance(node, Circle2D):
        new_r = _replace_identifiers(node.radius, var_map) if node.radius else None
        new_d = _replace_identifiers(node.diameter, var_map) if node.diameter else None
        return Circle2D(new_r, new_d)
    
    # Polygon2D
    if isinstance(node, Polygon2D):
        new_paths = _replace_identifiers(node.paths, var_map) if node.paths else None
        return Polygon2D(_replace_identifiers(node.points, var_map), new_paths, node.convexity)
    
    # Text2D
    if isinstance(node, Text2D):
        new_size = _replace_identifiers(node.size, var_map) if node.size else None
        new_spacing = _replace_identifiers(node.spacing, var_map) if node.spacing else None
        return Text2D(node.text, new_size, node.font, node.halign, node.valign,
                      new_spacing, node.direction, node.language, node.script)
    
    # Transform
    if isinstance(node, Transform):
        new_params = {}
        for k, v in node.params.items():
            new_params[k] = _replace_identifiers(v, var_map) if isinstance(v, ASTNode) else v
        return Transform(node.transform_type, new_params,
                         _replace_identifiers(node.body, var_map))
    
    # BooleanOp
    if isinstance(node, BooleanOp):
        return BooleanOp(node.operation,
                         [_replace_identifiers(op, var_map) for op in node.operands])
    
    # Hull
    if isinstance(node, Hull):
        return Hull([_replace_identifiers(op, var_map) for op in node.operands])
    
    # Minkowski
    if isinstance(node, Minkowski):
        return Minkowski([_replace_identifiers(op, var_map) for op in node.operands])
    
    # LinearExtrude
    if isinstance(node, LinearExtrude):
        new_twist = _replace_identifiers(node.twist, var_map) if node.twist else None
        new_scale = _replace_identifiers(node.scale, var_map) if node.scale else None
        new_body = _replace_identifiers(node.body, var_map) if node.body else None
        return LinearExtrude(_replace_identifiers(node.height, var_map), new_body,
                             new_twist, new_scale, node.center)
    
    # RotateExtrude
    if isinstance(node, RotateExtrude):
        new_body = _replace_identifiers(node.body, var_map) if node.body else None
        return RotateExtrude(_replace_identifiers(node.angle, var_map), new_body)
    
    # Offset
    if isinstance(node, Offset):
        new_body = _replace_identifiers(node.body, var_map) if node.body else None
        return Offset(_replace_identifiers(node.radius, var_map), new_body)
    
    # Block
    if isinstance(node, Block):
        return Block([_replace_identifiers(s, var_map) for s in node.statements])
    
    # FunctionCall
    if isinstance(node, FunctionCall):
        new_args = {k: _replace_identifiers(v, var_map) if isinstance(v, ASTNode) else v
                    for k, v in node.named_arguments.items()}
        return FunctionCall(node.name, [], new_args)
    
    # FunctionCallExpr
    if isinstance(node, FunctionCallExpr):
        new_args = {k: _replace_identifiers(v, var_map) if isinstance(v, ASTNode) else v
                    for k, v in node.named_arguments.items()}
        return FunctionCallExpr(_replace_identifiers(node.callee, var_map), [], new_args)
    
    # ArrayAccess
    if isinstance(node, ArrayAccess):
        return ArrayAccess(_replace_identifiers(node.target, var_map),
                           _replace_identifiers(node.index, var_map))
    
    # MemberAccess
    if isinstance(node, MemberAccess):
        return MemberAccess(_replace_identifiers(node.target, var_map), node.member)
    
    # IfStatement
    if isinstance(node, IfStatement):
        new_else = _replace_identifiers(node.else_body, var_map) if node.else_body else None
        return IfStatement(_replace_identifiers(node.condition, var_map),
                           _replace_identifiers(node.then_body, var_map),
                           new_else)
    
    # ForLoop
    if isinstance(node, ForLoop):
        return ForLoop(node.variable,
                       _replace_identifiers(node.values, var_map),
                       _replace_identifiers(node.body, var_map))
    
    # LetBinding
    if isinstance(node, LetBinding):
        new_assigns = []
        for a in node.assignments:
            new_assigns.append(Assignment(a.name, _replace_identifiers(a.value, var_map)))
        return LetBinding(new_assigns, _replace_identifiers(node.body, var_map))
    
    # IntersectionFor
    if isinstance(node, IntersectionFor):
        return IntersectionFor(node.variable,
                               _replace_identifiers(node.values, var_map),
                               _replace_identifiers(node.body, var_map))
    
    # Projection
    if isinstance(node, Projection):
        new_body = _replace_identifiers(node.body, var_map) if node.body else None
        return Projection(node.cut, new_body)
    
    # Mirror
    if isinstance(node, Mirror):
        new_body = _replace_identifiers(node.body, var_map) if node.body else None
        return Mirror(_replace_identifiers(node.normal, var_map), new_body)
    
    # MultMatrix
    if isinstance(node, MultMatrix):
        new_body = _replace_identifiers(node.body, var_map) if node.body else None
        return MultMatrix(_replace_identifiers(node.matrix, var_map), new_body)
    
    # Resize
    if isinstance(node, Resize):
        new_auto = _replace_identifiers(node.auto, var_map) if node.auto else None
        new_body = _replace_identifiers(node.body, var_map) if node.body else None
        return Resize(_replace_identifiers(node.newsize, var_map), new_auto, new_body)
    
    # Color
    if isinstance(node, Color):
        new_alpha = _replace_identifiers(node.alpha, var_map) if node.alpha else None
        new_body = _replace_identifiers(node.body, var_map) if node.body else None
        return Color(_replace_identifiers(node.color, var_map), new_alpha, new_body)
    
    # Echo
    if isinstance(node, Echo):
        return Echo([_replace_identifiers(a, var_map) for a in node.args])
    
    # Assert
    if isinstance(node, Assert):
        new_msg = _replace_identifiers(node.message, var_map) if node.message else None
        return Assert(_replace_identifiers(node.condition, var_map), new_msg)
    
    # IncludeDirective / UseDirective - pass through
    if isinstance(node, (IncludeDirective, UseDirective)):
        return node
    
    # ModuleDef / FunctionDef - pass through (handled separately)
    if isinstance(node, (ModuleDef, FunctionDef)):
        return node
    
    # Assignment - pass through (should not appear after inlining)
    if isinstance(node, Assignment):
        return node
    
    # Module - pass through (should not appear inside inlining)
    if isinstance(node, Module):
        return node
    
    # Fallback: return node unchanged
    return node


# ============================================================
# AST → Python string visitor
# ============================================================

class AstToPython:
    """Walk an AST and produce the same Python string output as the old parser."""

    def __init__(self):
        self.helper_modules: dict[str, ModuleDef] = {}
        self.helper_functions: dict[str, FunctionDef] = {}

    def visit(self, node: ASTNode) -> str:
        if node is None:
            return ""
        method = getattr(self, f'visit_{type(node).__name__}', None)
        if method is None:
            raise NotImplementedError(f"No visitor for {type(node).__name__}")
        return method(node)

    def visit_Module(self, node: Module) -> str:
        return self._inline_vars(node.statements)

    def visit_Block(self, node: Block) -> str:
        return self._inline_vars(node.statements)

    def visit_NumberLiteral(self, node: NumberLiteral) -> str:
        return str(node.value)

    def visit_StringLiteral(self, node: StringLiteral) -> str:
        return repr(node.value)

    def visit_BooleanLiteral(self, node: BooleanLiteral) -> str:
        return 'True' if node.value else 'False'

    def visit_UndefLiteral(self, node: UndefLiteral) -> str:
        return 'None'

    def visit_VectorLiteral(self, node: VectorLiteral) -> str:
        elems = ", ".join(self.visit(e) for e in node.elements)
        return f"[{elems}]"

    def visit_RangeLiteral(self, node: RangeLiteral) -> str:
        start = self.visit(node.start)
        end = self.visit(node.end)
        if node.step:
            step = self.visit(node.step)
            return f"range({start}, {end}, {step})"
        return f"range({start}, {end})"

    def visit_Identifier(self, node: Identifier) -> str:
        return node.name

    def visit_SpecialVar(self, node: SpecialVar) -> str:
        return node.name

    def visit_BinaryOp(self, node: BinaryOp) -> str:
        left = self.visit(node.left)
        right = self.visit(node.right)
        return f"({left} {node.operator} {right})"

    def visit_UnaryOp(self, node: UnaryOp) -> str:
        operand = self.visit(node.operand)
        return f"({node.operator}{operand})"

    def visit_TernaryOp(self, node: TernaryOp) -> str:
        cond = self.visit(node.condition)
        true_expr = self.visit(node.true_expr)
        false_expr = self.visit(node.false_expr)
        return f"({true_expr} if {cond} else {false_expr})"

    def _inline_vars(self, statements: list[ASTNode]) -> str:
        """Collect assignments and inline variable references in subsequent statements.
        
        SCAD variables are constants (no mutation), so we can substitute their
        values directly wherever they are referenced. This avoids generating
        invalid Python like 'x=10 + self.api.box(x,x,x)'.
        """
        # First pass: collect all assignments into a substitution map
        var_map: dict[str, ASTNode] = {}
        for stmt in statements:
            if isinstance(stmt, Assignment):
                var_map[stmt.name] = stmt.value
        
        if not var_map:
            # No assignments - just concatenate as before
            parts = [self.visit(s) for s in statements]
            return " + ".join(p for p in parts if p)
        
        # Second pass: process non-assignment statements with variable substitution
        parts = []
        for stmt in statements:
            if isinstance(stmt, Assignment):
                continue  # assignments contribute no geometry
            substituted = _replace_identifiers(stmt, var_map)
            rendered = self.visit(substituted)
            if rendered:
                parts.append(rendered)
        
        return " + ".join(parts)

    def visit_Assignment(self, node: Assignment) -> str:
        return ""


    def visit_ShapeCall(self, node: ShapeCall) -> str:
        name = node.function_name
        if name == 'cube':
            if 0 in node.named_args and isinstance(node.named_args[0], VectorLiteral):
                vec = self.visit(node.named_args[0])
                return f"self.api.box(*{vec}, center=False)"
            elif 0 in node.named_args:
                val = self.visit(node.named_args[0])
                return f"self.api.box({val},{val},{val}, center=False)"
            elif 'size' in node.named_args:
                val = self.visit(node.named_args['size'])
                if isinstance(node.named_args['size'], VectorLiteral):
                    vec = self.visit(node.named_args['size'])
                    return f"self.api.box(*{vec}, center=False)"
                return f"self.api.box({val},{val},{val}, center=False)"
            else:
                raise ValueError(f"cube requires a size argument, got {list(node.named_args.keys())}")
        elif name == 'sphere':
            args_str = self._format_named_args(node.named_args)
            return f"self.api.sphere({args_str})"
        elif name == 'cylinder':
            args_str = self._format_named_args(node.named_args)
            splitargs = args_str.split(',')
            if len(splitargs) == 3:
                return f"self.api.cone_z({args_str})"
            if len(splitargs) == 2:
                return f"self.api.cylinder_z({args_str})"
            return f"self.api.cone_z({args_str})"
        elif name == 'polyhedron':
            args_str = self._format_named_args(node.named_args)
            return f"self.api.polyhedron({args_str})"
        else:
            raise NotImplementedError(f"Unknown shape: {name}")

    def visit_Square2D(self, node: Square2D) -> str:
        size_val = self.visit(node.size)
        center_str = f", center={self.visit(node.center)}" if node.center else ""
        return f"self.api.rectangle({size_val}{center_str})"

    def visit_Circle2D(self, node: Circle2D) -> str:
        if node.radius is not None:
            return f"self.api.circle(r={self.visit(node.radius)})"
        elif node.diameter is not None:
            return f"self.api.circle(d={self.visit(node.diameter)})"
        else:
            return "self.api.circle(r=1)"

    def visit_Polygon2D(self, node: Polygon2D) -> str:
        points = self.visit(node.points)
        parts = [f"points={points}"]
        if node.paths is not None:
            parts.append(f"paths={self.visit(node.paths)}")
        if node.convexity != 1:
            parts.append(f"convexity={node.convexity}")
        return f"self.api.polygon({', '.join(parts)})"

    def visit_Text2D(self, node: Text2D) -> str:
        text_val = repr(node.text)
        parts = [text_val]
        for attr in ['size', 'font', 'halign', 'valign', 'spacing', 'direction', 'language', 'script']:
            val = getattr(node, attr, None)
            if val is not None:
                parts.append(f"{attr}={self.visit(val)}")
        return f"self.api.text({', '.join(parts)})"

    def visit_LinearExtrude(self, node: LinearExtrude) -> str:
        body = self.visit(node.body)
        parts = [f"height={self.visit(node.height)}"]
        if node.twist is not None:
            parts.append(f"twist={self.visit(node.twist)}")
        if node.scale is not None:
            parts.append(f"scale={self.visit(node.scale)}")
        if node.center:
            parts.append("center=True")
        return f"{body}.linear_extrude({', '.join(parts)})"

    def visit_RotateExtrude(self, node: RotateExtrude) -> str:
        body = self.visit(node.body)
        parts = [f"angle={self.visit(node.angle)}"]
        return f"{body}.rotate_extrude({', '.join(parts)})"

    def visit_Offset(self, node: Offset) -> str:
        body = self.visit(node.body)
        parts = [f"r={self.visit(node.radius)}"]
        return f"{body}.offset({', '.join(parts)})"

    def visit_Transform(self, node: Transform) -> str:
        body = self.visit(node.body)
        tt = node.transform_type
        if tt == 'translate':
            vec = self.visit(node.params.get('v', node.params.get(0, VectorLiteral([]))))
            return f"{body}.mv(*{vec})"
        elif tt == 'rotate':
            vec = self.visit(node.params.get('a', node.params.get(0, VectorLiteral([]))))
            return f"{body}.rotate({vec})"
        elif tt == 'scale':
            vec = self.visit(node.params.get('v', node.params.get(0, VectorLiteral([]))))
            return f"{body}.scale(*{vec})"
        elif tt == 'mirror':
            args = node.params
            if 0 in args:
                normal = self.visit(args[0])
                return f"{body}.mirror(normal={normal})"
            else:
                return f"{body}.mirror()"
        elif tt == 'color':
            args_str = self._format_named_args(node.params)
            return f"{body}.color({args_str})"
        elif tt == 'resize':
            args_str = self._format_named_args(node.params)
            return f"{body}.resize({args_str})"
        elif tt == 'multmatrix':
            args_str = self._format_named_args(node.params)
            return f"{body}.multmatrix({args_str})"
        elif tt == 'projection':
            args_str = self._format_named_args(node.params)
            return f"{body}.projection({args_str})"
        else:
            raise NotImplementedError(f"Unknown transform: {tt}")

    def visit_BooleanOp(self, node: BooleanOp) -> str:
        if node.operation == 'union':
            parts = [self.visit(op) for op in node.operands]
            return " + ".join(parts)
        elif node.operation == 'difference':
            parts = [self.visit(op) for op in node.operands]
            return f"{self.visit(node.operands[0])} - ({' + '.join(self.visit(op) for op in node.operands[1:])})"
        elif node.operation == 'intersection':
            parts = [self.visit(op) for op in node.operands]
            result = parts[0]
            for p in parts[1:]:
                result = f"{result}.intersection({p})"
            return result
        else:
            raise NotImplementedError(f"Unknown boolean op: {node.operation}")

    def visit_Hull(self, node: Hull) -> str:
        body = " + ".join(self.visit(op) for op in node.operands)
        return f"({body}).hull()"

    def visit_Minkowski(self, node: Minkowski) -> str:
        operands = [self.visit(op) for op in node.operands]
        result = operands[0]
        for operand in operands[1:]:
            result = f"{result}.minkowski({operand})"
        return result

    def visit_FunctionCall(self, node: FunctionCall) -> str:
        args_str = self._format_named_args(node.named_arguments)
        # Use underscore prefix for user-defined modules to distinguish from built-in methods
        return f"self._{node.name}({args_str})"

    def visit_FunctionCallExpr(self, node: FunctionCallExpr) -> str:
        callee = self.visit(node.callee)
        args_str = self._format_named_args(node.named_arguments)
        # User-defined functions are stored as self._<name> methods
        if isinstance(node.callee, Identifier) and node.callee.name in self.helper_functions:
            return f"self._{callee}({args_str})"
        return f"{callee}({args_str})"

    def visit_ArrayAccess(self, node: ArrayAccess) -> str:
        target = self.visit(node.target)
        index = self.visit(node.index)
        return f"{target}[{index}]"

    def visit_MemberAccess(self, node: MemberAccess) -> str:
        target = self.visit(node.target)
        return f"{target}.{node.member}"

    def visit_IfStatement(self, node: IfStatement) -> str:
        cond = self.visit(node.condition)
        then_body = self.visit(node.then_body)
        if node.else_body:
            else_body = self.visit(node.else_body)
            return f"({then_body} if {cond} else {else_body})"
        return f"({then_body} if {cond} else None)"

    def visit_ForLoop(self, node: ForLoop) -> str:
        var = node.variable
        values = self.visit(node.values)
        body = self.visit(node.body)
        return f"__import__('functools').reduce(lambda a,b:a+b, [{body} for {var} in {values}])"

    def visit_LetBinding(self, node: LetBinding) -> str:
        body = self.visit(node.body)
        return body

    def visit_FunctionDef(self, node: FunctionDef) -> str:
        self.helper_functions[node.name] = node
        return ""

    def visit_ModuleDef(self, node: ModuleDef) -> str:
        self.helper_modules[node.name] = node
        return ""

    def visit_IntersectionFor(self, node: IntersectionFor) -> str:
        var = node.variable
        values = self.visit(node.values)
        body = self.visit(node.body)
        return f"__import__('functools').reduce(lambda a,b: a.intersection(b), [{body} for {var} in {values}])"

    def visit_IncludeDirective(self, node: IncludeDirective) -> str:
        return ""

    def visit_UseDirective(self, node: UseDirective) -> str:
        return ""

    def visit_Echo(self, node: Echo) -> str:
        return ""

    def visit_Assert(self, node: Assert) -> str:
        return ""

    def _format_named_args(self, named_args: dict) -> str:
        """Format named arguments dict into a string for Python output.
        
        Filters out $fn, $fa, $fs special variables as they are handled
        internally by the API, not passed as keyword arguments.
        """
        if not named_args:
            return ""
        parts = []
        for key, val in named_args.items():
            if isinstance(key, int):
                parts.append(self.visit(val))
            elif key.startswith('$'):
                # Skip special vars ($fn, $fa, $fs) - handled by API internally
                continue
            else:
                parts.append(f"{key}={self.visit(val)}")
        return ", ".join(parts)

    def gen_helper_methods(self) -> str:
        """Generate Python helper method definitions from stored module/function defs.
        
        Returns a string containing method definitions with proper class-body
        indentation (4 spaces for def line, 8 spaces for body lines),
        separated by blank lines between methods.
        """
        parts = []
        for name, node in sorted(self.helper_modules.items()):
            # Generate method signature
            params = []
            for pname, pdefault in node.parameters:
                if pdefault is not None:
                    default_str = self.visit(pdefault)
                    params.append(f"{pname}={default_str}")
                else:
                    params.append(pname)
            params_str = ", ".join(params)
            
            # Generate method body
            body_parts = []
            for stmt in node.body.statements:
                body_str = self.visit(stmt)
                if body_str:
                    body_parts.append(body_str)
            
            if body_parts:
                body_expr = " + ".join(body_parts)
                lines = [f"    def _{name}(self, {params_str}):",
                         f"        return {body_expr}"]
            else:
                lines = [f"    def _{name}(self, {params_str}):",
                         "        return self.api.box(0,0,0, center=False)"]
            parts.append("\n".join(lines))
        
        for name, node in sorted(self.helper_functions.items()):
            params = []
            for pname, pdefault in node.parameters:
                if pdefault is not None:
                    default_str = self.visit(pdefault)
                    params.append(f"{pname}={default_str}")
                else:
                    params.append(pname)
            params_str = ", ".join(params)
            body_str = self.visit(node.body)
            lines = [f"    def _{name}(self, {params_str}):",
                     f"        return {body_str}"]
            parts.append("\n".join(lines))
        
        return "\n\n".join(parts)


# ============================================================
# Code Generator: writes full Python files
# ============================================================

class CodeGenerator:
    def __init__(self, output_file):
        self.output = output_file
        self.indent = 0

    def write_template(self, retshape="", model="model", body="", helpers=""):
        """Write the Python file template directly, without textwrap.dedent
        complications, by building each line with explicit indentation."""
        cls_name = snake2camel(model)
        lines = [
            "",
            "#!/usr/bin/env python3",
            "",
            f'"""',
            f"{model} Solid",
            f'"""',
            "",
            "import os",
            "import sys",
            "sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))",
            "",
            "from b13d.api.solid import Solid, test_loop, main_maker",
            "from b13d.api.core import Shape",
            "",
            f"class {cls_name}(Solid):",
            f'    """ Generate a {model} """',
            f"    def gen(self) -> Shape:",
        ]
        # Add the body lines (already at 8-space indentation from body='' or
        # the generate() output)
        if body.strip():
            for line in body.split('\n'):
                lines.append(f"        {line}")
        # Add the return statement
        lines.append(f"        return {retshape}")
        # Add helper methods
        if helpers:
            # helpers already have class-body indentation (4 spaces for def, 8 for body)
            for line in helpers.split('\n'):
                lines.append(line)
        lines += [
            "",
            "def main(args=None):",
            f'    """ Generate a {model} """',
            "    return main_maker(module_name=__name__,",
            f"                class_name='{cls_name}',",
            "                args=args)",
            "",
            f"def test_{model}(self,apis=None):",
            f'    """ Test {model} """',
            f"    test_loop(module=__name__,apis=apis)",
            "",
            f"def test_{model}_mock(self):",
            f'    """ Test {model} Mock """',
            f"    test_{model}(self, apis=['mock'])",
            "",
            "if __name__ == '__main__':",
            "    main()",
            "",
        ]
        self.output.write('\n'.join(lines))

    def generate(self, infname: str, view_ast: bool = True) -> tuple[str, AstToPython]:
        """Parse a SCAD file and generate Python code string.
        
        Returns (python_code_string, visitor_with_helpers).
        """
        from b1scad.scad2ast import scad2ast

        ast = scad2ast(infname, view=view_ast)
        parser = OpenSCADParser()

        # Parse tokens into AST
        print('Parsing...')
        ast_root = parser.parse(ast)
        print('Parsing End!')

        # Resolve include/use directives
        scad_dir = os.path.dirname(os.path.abspath(infname))
        ast_root = resolve_includes(ast_root, scad_dir)

        # Build symbol table
        sym_visitor = SymbolTableVisitor()
        sym_visitor.visit(ast_root)
        if sym_visitor.symtab.has_errors():
            print(sym_visitor.symtab.report_errors())

        # Walk AST to produce Python code
        visitor = AstToPython()
        python_code = visitor.visit(ast_root)

        if not python_code or 'return None' in python_code:
            # Fallback for polyhedron-only models
            with open(infname, 'r', encoding='utf8') as f:
                source = f.read()
            python_code = _parse_polyhedron_source(source)

        assert python_code != "", f"Failed to generate Python code from {infname}"
        return python_code, visitor


def _parse_polyhedron_source(source: str) -> str:
    """Fallback: extract polyhedron call from raw source."""
    import re
    pattern = re.compile(r'polyhedron\s*\(\s*(.*?)\s*\)\s*;', re.S)
    match = pattern.search(source)
    if not match:
        return ""
    args = match.group(1)
    args = re.sub(r'\s+', ' ', args).strip()
    return f"self.api.polyhedron({args})"


def scad2py(infname: str, execute_en: bool = True):
    """Convert SCAD file to Python file and optionally execute it."""

    # generate output file
    output_path = file_replace_extension(infname, ".py")

    # generate module name
    fname = os.path.basename(output_path)
    basefname, _ = os.path.splitext(fname)
    modelname = snake2camel(basefname)

    # make sure output file is erased if exists
    if os.path.exists(output_path):
        os.remove(output_path)

    with open(output_path, 'w', encoding='utf8') as f:
        generator = CodeGenerator(f)

        # Generate main python code
        pyshape, visitor = generator.generate(infname)

        # Generate helper methods from collected module/function definitions
        helpers = visitor.gen_helper_methods()

        # generate python file code
        generator.write_template(retshape=pyshape, model=modelname, helpers=helpers)
        print(f"Generated Python code saved to {output_path}")

    if execute_en:
        cmdstr = f'python3 {output_path} -odoff'
        print(cmdstr)
        os.system(cmdstr)

    return output_path, modelname


def b1scad():
    if len(sys.argv) < 2:
        infname = "model.scad"
        print(f'Unspecified input file, generate default {infname}')
        gen_scad_foo(infname, module_en=False)
    else:
        infname = sys.argv[1]

    scad2py(infname)


if __name__ == "__main__":
    b1scad()
