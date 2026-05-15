#!/usr/bin/env python3
# flake8: noqa: F821

""" converts scad to python """

# scad_parser.py
from __future__ import annotations
import textwrap
from sly import Parser

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))

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

# CSS named colors mapped to (R, G, B) tuples (0-255 range).
# Based on the CSS/SVG named color palette used by OpenSCAD.
_CSS_COLORS: dict[str, tuple[int, int, int]] = {
    'aliceblue': (240, 248, 255),
    'antiquewhite': (250, 235, 215),
    'aqua': (0, 255, 255),
    'aquamarine': (127, 255, 212),
    'azure': (240, 255, 255),
    'beige': (245, 245, 220),
    'bisque': (255, 228, 196),
    'black': (0, 0, 0),
    'blanchedalmond': (255, 235, 205),
    'blue': (0, 0, 255),
    'blueviolet': (138, 43, 226),
    'brown': (165, 42, 42),
    'burlywood': (222, 184, 135),
    'cadetblue': (95, 158, 160),
    'chartreuse': (127, 255, 0),
    'chocolate': (210, 105, 30),
    'coral': (255, 127, 80),
    'cornflowerblue': (100, 149, 237),
    'cornsilk': (255, 248, 220),
    'crimson': (220, 20, 60),
    'cyan': (0, 255, 255),
    'darkblue': (0, 0, 139),
    'darkcyan': (0, 139, 139),
    'darkgoldenrod': (184, 134, 11),
    'darkgray': (169, 169, 169),
    'darkgreen': (0, 100, 0),
    'darkkhaki': (189, 183, 107),
    'darkmagenta': (139, 0, 139),
    'darkolivegreen': (85, 107, 47),
    'darkorange': (255, 140, 0),
    'darkorchid': (153, 50, 204),
    'darkred': (139, 0, 0),
    'darksalmon': (233, 150, 122),
    'darkseagreen': (143, 188, 143),
    'darkslateblue': (72, 61, 139),
    'darkslategray': (47, 79, 79),
    'darkturquoise': (0, 206, 209),
    'darkviolet': (148, 0, 211),
    'deeppink': (255, 20, 147),
    'deepskyblue': (0, 191, 255),
    'dimgray': (105, 105, 105),
    'dodgerblue': (30, 144, 255),
    'firebrick': (178, 34, 34),
    'floralwhite': (255, 250, 240),
    'forestgreen': (34, 139, 34),
    'fuchsia': (255, 0, 255),
    'gainsboro': (220, 220, 220),
    'ghostwhite': (248, 248, 255),
    'gold': (255, 215, 0),
    'goldenrod': (218, 165, 32),
    'gray': (128, 128, 128),
    'green': (0, 128, 0),
    'greenyellow': (173, 255, 47),
    'honeydew': (240, 255, 240),
    'hotpink': (255, 105, 180),
    'indianred': (205, 92, 92),
    'indigo': (75, 0, 130),
    'ivory': (255, 255, 240),
    'khaki': (240, 230, 140),
    'lavender': (230, 230, 250),
    'lavenderblush': (255, 240, 245),
    'lawngreen': (124, 252, 0),
    'lemonchiffon': (255, 250, 205),
    'lightblue': (173, 216, 230),
    'lightcoral': (240, 128, 128),
    'lightcyan': (224, 255, 255),
    'lightgoldenrodyellow': (250, 250, 210),
    'lightgray': (211, 211, 211),
    'lightgreen': (144, 238, 144),
    'lightpink': (255, 182, 193),
    'lightsalmon': (255, 160, 122),
    'lightseagreen': (32, 178, 170),
    'lightskyblue': (135, 206, 250),
    'lightslategray': (119, 136, 153),
    'lightsteelblue': (176, 196, 222),
    'lightyellow': (255, 255, 224),
    'lime': (0, 255, 0),
    'limegreen': (50, 205, 50),
    'linen': (250, 240, 230),
    'magenta': (255, 0, 255),
    'maroon': (128, 0, 0),
    'mediumaquamarine': (102, 205, 170),
    'mediumblue': (0, 0, 205),
    'mediumorchid': (186, 85, 211),
    'mediumpurple': (147, 112, 219),
    'mediumseagreen': (60, 179, 113),
    'mediumslateblue': (123, 104, 238),
    'mediumspringgreen': (0, 250, 154),
    'mediumturquoise': (72, 209, 204),
    'mediumvioletred': (199, 21, 133),
    'midnightblue': (25, 25, 112),
    'mintcream': (245, 255, 250),
    'mistyrose': (255, 228, 225),
    'moccasin': (255, 228, 181),
    'navajowhite': (255, 222, 173),
    'navy': (0, 0, 128),
    'oldlace': (253, 245, 230),
    'olive': (128, 128, 0),
    'olivedrab': (107, 142, 35),
    'orange': (255, 165, 0),
    'orangered': (255, 69, 0),
    'orchid': (218, 112, 214),
    'palegoldenrod': (238, 232, 170),
    'palegreen': (152, 251, 152),
    'paleturquoise': (175, 238, 238),
    'palevioletred': (219, 112, 147),
    'papayawhip': (255, 239, 213),
    'peachpuff': (255, 218, 185),
    'peru': (205, 133, 63),
    'pink': (255, 192, 203),
    'plum': (221, 160, 221),
    'powderblue': (176, 224, 230),
    'purple': (128, 0, 128),
    'rebeccapurple': (102, 51, 153),
    'red': (255, 0, 0),
    'rosybrown': (188, 143, 143),
    'royalblue': (65, 105, 225),
    'saddlebrown': (139, 69, 19),
    'salmon': (250, 128, 114),
    'sandybrown': (244, 164, 96),
    'seagreen': (46, 139, 87),
    'seashell': (255, 245, 238),
    'sienna': (160, 82, 45),
    'silver': (192, 192, 192),
    'skyblue': (135, 206, 235),
    'slateblue': (106, 90, 205),
    'slategray': (112, 128, 144),
    'snow': (255, 250, 250),
    'springgreen': (0, 255, 127),
    'steelblue': (70, 130, 180),
    'tan': (210, 180, 140),
    'teal': (0, 128, 128),
    'thistle': (216, 191, 216),
    'tomato': (255, 99, 71),
    'turquoise': (64, 224, 208),
    'violet': (238, 130, 238),
    'wheat': (245, 222, 179),
    'white': (255, 255, 255),
    'whitesmoke': (245, 245, 245),
    'yellow': (255, 255, 0),
    'yellowgreen': (154, 205, 50),
}

def _resolve_color_arg(arg_node):
    """Convert an OpenSCAD color argument to a Python expression string.
    
    Handles:
      - String literals ("Blue" → (0, 0, 255))
      - Vector literals ([r,g,b] → passed through as tuple)
      - Expressions (passed through as-is)
    """
    if isinstance(arg_node, StringLiteral):
        name = arg_node.value.strip()
        rgb = _CSS_COLORS.get(name.lower())
        if rgb is not None:
            return str(rgb)
        # Unknown color name — emit repr so the user can see the problematic value
        return repr(arg_node.value)
    return None  # caller should visit normally



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
    # Block (brace-enclosed statement list)
    # ============================================================
    @_('LBRACE statements RBRACE')
    def block(self, p):
        return Block(p.statements)

    @_('LBRACE RBRACE')
    def block(self, p):
        return Block([])

    # ============================================================
    # Statements
    # ============================================================
    @_("shape_statement")
    def statement(self, t):
        return t.shape_statement

    @_('SEMICOLON')
    def statement(self, p):
        return Block([])

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

    @_('IDENTIFIER LPAREN args RPAREN block')
    def shape_statement(self, p):
        return FunctionCall(p.IDENTIFIER, [], _args_to_dict(p.args))

    @_('IDENTIFIER LPAREN args RPAREN shape_statement')
    def shape_statement(self, p):
        return FunctionCall(p.IDENTIFIER, [p.shape_statement], _args_to_dict(p.args))

    @_('CHILDREN LPAREN args RPAREN SEMICOLON')
    def shape_statement(self, p):
        return ChildrenRef(_args_to_dict(p.args))

    @_('CHILDREN LPAREN args RPAREN block')
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
        # Keep AST nodes as-is for variable inlining; convert StringLiteral to str.
        if isinstance(text_val, StringLiteral):
            text_val = text_val.value
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
    @_('TRANSLATE LPAREN named_vector RPAREN block')
    def transform_op(self, p):
        return Transform('translate', {'v': p.named_vector}, p.block)

    @_('TRANSLATE LPAREN named_vector RPAREN shape_statement')
    def shape_statement(self, p):
        return Transform('translate', {'v': p.named_vector}, p.shape_statement)

    @_('ROTATE LPAREN args RPAREN block')
    def transform_op(self, p):
        return Transform('rotate', _args_to_dict(p.args), p.block)

    @_('ROTATE LPAREN args RPAREN shape_statement')
    def shape_statement(self, p):
        return Transform('rotate', _args_to_dict(p.args), p.shape_statement)

    @_('SCALE LPAREN named_vector RPAREN block')
    def transform_op(self, p):
        return Transform('scale', {'v': p.named_vector}, p.block)

    @_('SCALE LPAREN named_vector RPAREN shape_statement')
    def shape_statement(self, p):
        return Transform('scale', {'v': p.named_vector}, p.shape_statement)

    @_('MIRROR LPAREN args RPAREN block')
    def transform_op(self, p):
        return Transform('mirror', _args_to_dict(p.args), p.block)

    @_('MIRROR LPAREN args RPAREN shape_statement')
    def shape_statement(self, p):
        return Transform('mirror', _args_to_dict(p.args), p.shape_statement)

    @_('COLOR LPAREN args RPAREN block')
    def transform_op(self, p):
        return Transform('color', _args_to_dict(p.args), p.block)

    @_('COLOR LPAREN args RPAREN shape_statement')
    def shape_statement(self, p):
        return Transform('color', _args_to_dict(p.args), p.shape_statement)

    @_('RESIZE LPAREN args RPAREN block')
    def transform_op(self, p):
        return Transform('resize', _args_to_dict(p.args), p.block)

    @_('RESIZE LPAREN args RPAREN shape_statement')
    def shape_statement(self, p):
        return Transform('resize', _args_to_dict(p.args), p.shape_statement)

    @_('MULTMATRIX LPAREN args RPAREN block')
    def transform_op(self, p):
        return Transform('multmatrix', _args_to_dict(p.args), p.block)

    @_('MULTMATRIX LPAREN args RPAREN shape_statement')
    def shape_statement(self, p):
        return Transform('multmatrix', _args_to_dict(p.args), p.shape_statement)

    # ============================================================
    # Boolean operations
    # ============================================================
    @_('UNION LPAREN RPAREN block')
    def boolean_op(self, p):
        return BooleanOp('union', p.block.statements)

    @_('UNION LPAREN RPAREN shape_statement')
    def shape_statement(self, p):
        return BooleanOp('union', [p.shape_statement])

    @_('DIFFERENCE LPAREN RPAREN block')
    def boolean_op(self, p):
        return BooleanOp('difference', p.block.statements)

    @_('DIFFERENCE LPAREN RPAREN shape_statement')
    def shape_statement(self, p):
        return BooleanOp('difference', [p.shape_statement])

    @_('INTERSECTION LPAREN RPAREN block')
    def boolean_op(self, p):
        return BooleanOp('intersection', p.block.statements)

    @_('INTERSECTION LPAREN RPAREN shape_statement')
    def shape_statement(self, p):
        return BooleanOp('intersection', [p.shape_statement])

    @_('HULL LPAREN RPAREN block')
    def boolean_op(self, p):
        return Hull(p.block.statements)

    @_('HULL LPAREN RPAREN shape_statement')
    def shape_statement(self, p):
        return Hull([p.shape_statement])

    @_('INTERSECTION_FOR LPAREN for_init RPAREN block')
    def boolean_op(self, p):
        return IntersectionFor(p.for_init[0], p.for_init[1], p.block)

    # ============================================================
    # Extrude operations
    # ============================================================
    @_('LINEAR_EXTRUDE LPAREN args RPAREN block')
    def transform_op(self, p):
        args = _args_to_dict(p.args)
        return LinearExtrude(
            height=args.get('height', args.get(0, NumberLiteral(100))),
            body=p.block,
            twist=args.get('twist'),
            scale=args.get('scale'),
            center=args.get('center', False)
        )

    @_('LINEAR_EXTRUDE LPAREN args RPAREN shape_statement')
    def shape_statement(self, p):
        args = _args_to_dict(p.args)
        return LinearExtrude(
            height=args.get('height', args.get(0, NumberLiteral(100))),
            body=p.shape_statement,
            twist=args.get('twist'),
            scale=args.get('scale'),
            center=args.get('center', False)
        )

    @_('ROTATE_EXTRUDE LPAREN args RPAREN block')
    def transform_op(self, p):
        args = _args_to_dict(p.args)
        return RotateExtrude(
            angle=args.get('angle', args.get(0)),
            body=p.block
        )

    @_('ROTATE_EXTRUDE LPAREN args RPAREN shape_statement')
    def shape_statement(self, p):
        args = _args_to_dict(p.args)
        return RotateExtrude(
            angle=args.get('angle', args.get(0)),
            body=p.shape_statement
        )

    @_('OFFSET LPAREN args RPAREN block')
    def transform_op(self, p):
        args = _args_to_dict(p.args)
        return Offset(
            radius=args.get('r', args.get('delta', args.get(0))),
            body=p.block
        )

    @_('OFFSET LPAREN args RPAREN shape_statement')
    def shape_statement(self, p):
        args = _args_to_dict(p.args)
        return Offset(
            radius=args.get('r', args.get('delta', args.get(0))),
            body=p.shape_statement
        )

    @_('PROJECTION LPAREN args RPAREN block')
    def transform_op(self, p):
        return Transform('projection', _args_to_dict(p.args), p.block)

    @_('PROJECTION LPAREN args RPAREN shape_statement')
    def shape_statement(self, p):
        return Transform('projection', _args_to_dict(p.args), p.shape_statement)

    @_('MINKOWSKI LPAREN RPAREN block')
    def transform_op(self, p):
        return Minkowski(p.block.statements)

    @_('MINKOWSKI LPAREN RPAREN shape_statement')
    def shape_statement(self, p):
        return Minkowski([p.shape_statement])

    # (Module call rules moved to shape_statement above)
    
    # ============================================================
    # Assignment statement
    # ============================================================
    @_('IDENTIFIER EQU expr SEMICOLON')
    def assignment_statement(self, p):
        return Assignment(p.IDENTIFIER, p.expr)

    @_('SFS EQU expr SEMICOLON')
    def assignment_statement(self, p):
        return Assignment('$fs', p.expr)

    @_('SFA EQU expr SEMICOLON')
    def assignment_statement(self, p):
        return Assignment('$fa', p.expr)

    @_('SFN EQU expr SEMICOLON')
    def assignment_statement(self, p):
        return Assignment('$fn', p.expr)

    # ============================================================
    # Module definition
    # ============================================================
    @_('MODULE IDENTIFIER LPAREN RPAREN block')
    def module_def_statement(self, p):
        return ModuleDef(p.IDENTIFIER, [], p.block)

    @_('MODULE IDENTIFIER LPAREN param_list RPAREN block')
    def module_def_statement(self, p):
        return ModuleDef(p.IDENTIFIER, p.param_list, p.block)

    @_('MODULE IDENTIFIER LPAREN RPAREN statement')
    def module_def_statement(self, p):
        return ModuleDef(p.IDENTIFIER, [], p.statement)

    @_('MODULE IDENTIFIER LPAREN param_list RPAREN statement')
    def module_def_statement(self, p):
        return ModuleDef(p.IDENTIFIER, p.param_list, p.statement)

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

    @_('SFN EQU expr')
    def param(self, p):
        return ('$fn', p.expr)

    @_('SFA EQU expr')
    def param(self, p):
        return ('$fa', p.expr)

    @_('SFS EQU expr')
    def param(self, p):
        return ('$fs', p.expr)

    # ============================================================
    # If/else statement
    # ============================================================
    @_('IF LPAREN expr RPAREN block')
    def if_else_statement(self, p):
        return IfStatement(p.expr, p.block, None)

    @_('IF LPAREN expr RPAREN statement')
    def if_else_statement(self, p):
        return IfStatement(p.expr, p.statement, None)

    @_('IF LPAREN expr RPAREN block ELSE block')
    def if_else_statement(self, p):
        return IfStatement(p.expr, p.block0, p.block1)

    @_('IF LPAREN expr RPAREN block ELSE if_else_statement')
    def if_else_statement(self, p):
        return IfStatement(p.expr, p.block, p.if_else_statement)

    @_('IF LPAREN expr RPAREN statement ELSE statement')
    def if_else_statement(self, p):
        return IfStatement(p.expr, p.statement0, p.statement1)

    # ============================================================
    # For loop
    # ============================================================
    @_('FOR LPAREN for_init RPAREN block')
    def for_loop_statement(self, p):
        return ForLoop(p.for_init[0], p.for_init[1], p.block)

    @_('IDENTIFIER EQU expr')
    def for_init(self, p):
        return (p.IDENTIFIER, p.expr)

    # ============================================================
    # Let binding
    # ============================================================
    @_('LET LPAREN let_bindings RPAREN block')
    def let_statement(self, p):
        return LetBinding(p.let_bindings, p.block)

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
    @_('SFN EQU expr')
    def arg(self, p):
        return ('$fn', p.expr)

    @_('SFA EQU expr')
    def arg(self, p):
        return ('$fa', p.expr)

    @_('SFS EQU expr')
    def arg(self, p):
        return ('$fs', p.expr)

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
    @_('IDENTIFIER EQU expr')
    def named_vector(self, p):
        return p.expr

    @_('expr')
    def named_vector(self, p):
        return p.expr


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
    def visit_ChildrenRef(self, node: ChildrenRef) -> str:
        if node.index:
            return f'self.api.children({self.visit(node.index)})'
        else:
            return 'self.api.children()'
    def visit_ChildrenRef(self, node: ChildrenRef): pass


# ============================================================
# Variable Inlining: replace Identifier nodes with their assigned values
# ============================================================

def _is_zero(node: ASTNode) -> bool:
    """Check if an AST node represents the numeric value zero (literal or negated)."""
    if isinstance(node, NumberLiteral):
        return node.value == 0
    if isinstance(node, UnaryOp) and node.operator == '-':
        return _is_zero(node.operand)
    return False


def _is_float_literal(node: ASTNode) -> bool:
    """Check if an AST node is a NumberLiteral with a float value."""
    return isinstance(node, NumberLiteral) and isinstance(node.value, float)


def _replace_identifiers(node: ASTNode, var_map: dict[str, ASTNode],
                         _visiting: set[str] | None = None) -> ASTNode:
    """Deep copy walk of the AST, replacing Identifier nodes with their
    inlined values from var_map.
    
    When an Identifier node is found whose name matches a key in var_map,
    returns a deep copy of the corresponding value node. Otherwise,
    recursively processes child nodes and returns a new same-type node.
    
    A ``_visiting`` set tracks identifiers currently being expanded to
    detect and break cycles (e.g. ``circular_pitch = (circular_pitch!=false
    ? circular_pitch : ...)``).  When a cycle is detected the Identifier
    node is returned as-is.
    """
    if _visiting is None:
        _visiting = set()

    # Leaf nodes that need no recursion
    if isinstance(node, (NumberLiteral, StringLiteral, BooleanLiteral, UndefLiteral, SpecialVar)):
        return node
    
    # Identifier: substitute if in map
    if isinstance(node, Identifier):
        if node.name in var_map:
            if node.name in _visiting:
                # Cycle detected — leave the identifier in place
                return node
            _visiting.add(node.name)
            try:
                return _replace_identifiers(var_map[node.name], var_map, _visiting)
            finally:
                _visiting.discard(node.name)
        return node
    
    # UnaryOp
    if isinstance(node, UnaryOp):
        return UnaryOp(node.operator, _replace_identifiers(node.operand, var_map, _visiting))
    
    # BinaryOp
    if isinstance(node, BinaryOp):
        return BinaryOp(node.operator,
                        _replace_identifiers(node.left, var_map, _visiting),
                        _replace_identifiers(node.right, var_map, _visiting))
    
    # TernaryOp
    if isinstance(node, TernaryOp):
        return TernaryOp(_replace_identifiers(node.condition, var_map, _visiting),
                         _replace_identifiers(node.true_expr, var_map, _visiting),
                         _replace_identifiers(node.false_expr, var_map, _visiting))
    
    # VectorLiteral
    if isinstance(node, VectorLiteral):
        return VectorLiteral([_replace_identifiers(e, var_map, _visiting) for e in node.elements])
    
    # RangeLiteral
    if isinstance(node, RangeLiteral):
        new_step = _replace_identifiers(node.step, var_map, _visiting) if node.step else None
        return RangeLiteral(_replace_identifiers(node.start, var_map, _visiting),
                            _replace_identifiers(node.end, var_map, _visiting),
                            new_step)
    
    # ShapeCall
    if isinstance(node, ShapeCall):
        new_args = {k: _replace_identifiers(v, var_map, _visiting) if isinstance(v, ASTNode) else v
                    for k, v in node.named_args.items()}
        return ShapeCall(node.function_name, [], new_args)
    
    # Square2D
    if isinstance(node, Square2D):
        return Square2D(_replace_identifiers(node.size, var_map, _visiting), node.center)
    
    # Circle2D
    if isinstance(node, Circle2D):
        new_r = _replace_identifiers(node.radius, var_map, _visiting) if node.radius else None
        new_d = _replace_identifiers(node.diameter, var_map, _visiting) if node.diameter else None
        return Circle2D(new_r, new_d)
    
    # Polygon2D
    if isinstance(node, Polygon2D):
        new_paths = _replace_identifiers(node.paths, var_map, _visiting) if node.paths else None
        return Polygon2D(_replace_identifiers(node.points, var_map, _visiting), new_paths, node.convexity)
    
    # Text2D
    if isinstance(node, Text2D):
        new_text = _replace_identifiers(node.text, var_map, _visiting) if isinstance(node.text, ASTNode) else node.text
        new_size = _replace_identifiers(node.size, var_map, _visiting) if node.size else None
        new_spacing = _replace_identifiers(node.spacing, var_map, _visiting) if node.spacing else None
        return Text2D(new_text, new_size, node.font, node.halign, node.valign,
                      new_spacing, node.direction, node.language, node.script)
    
    # Transform
    if isinstance(node, Transform):
        new_params = {}
        for k, v in node.params.items():
            new_params[k] = _replace_identifiers(v, var_map, _visiting) if isinstance(v, ASTNode) else v
        return Transform(node.transform_type, new_params,
                         _replace_identifiers(node.body, var_map, _visiting))
    
    # BooleanOp
    if isinstance(node, BooleanOp):
        return BooleanOp(node.operation,
                         [_replace_identifiers(op, var_map, _visiting) for op in node.operands])
    
    # Hull
    if isinstance(node, Hull):
        return Hull([_replace_identifiers(op, var_map, _visiting) for op in node.operands])
    
    # Minkowski
    if isinstance(node, Minkowski):
        return Minkowski([_replace_identifiers(op, var_map, _visiting) for op in node.operands])
    
    # LinearExtrude
    if isinstance(node, LinearExtrude):
        new_twist = _replace_identifiers(node.twist, var_map, _visiting) if node.twist else None
        new_scale = _replace_identifiers(node.scale, var_map, _visiting) if node.scale else None
        new_body = _replace_identifiers(node.body, var_map, _visiting) if node.body else None
        return LinearExtrude(_replace_identifiers(node.height, var_map, _visiting), new_body,
                             new_twist, new_scale, node.center)
    
    # RotateExtrude
    if isinstance(node, RotateExtrude):
        new_body = _replace_identifiers(node.body, var_map, _visiting) if node.body else None
        return RotateExtrude(_replace_identifiers(node.angle, var_map, _visiting), new_body)
    
    # Offset
    if isinstance(node, Offset):
        new_body = _replace_identifiers(node.body, var_map, _visiting) if node.body else None
        return Offset(_replace_identifiers(node.radius, var_map, _visiting), new_body)
    
    # Block
    if isinstance(node, Block):
        return Block([_replace_identifiers(s, var_map, _visiting) for s in node.statements])
    
    # FunctionCall
    if isinstance(node, FunctionCall):
        new_args = {k: _replace_identifiers(v, var_map, _visiting) if isinstance(v, ASTNode) else v
                    for k, v in node.named_arguments.items()}
        new_children = [_replace_identifiers(c, var_map, _visiting) for c in node.arguments]
        return FunctionCall(node.name, new_children, new_args)
    
    # FunctionCallExpr
    if isinstance(node, FunctionCallExpr):
        new_args = {k: _replace_identifiers(v, var_map, _visiting) if isinstance(v, ASTNode) else v
                    for k, v in node.named_arguments.items()}
        new_children = [_replace_identifiers(c, var_map, _visiting) for c in node.arguments]
        return FunctionCallExpr(_replace_identifiers(node.callee, var_map, _visiting), new_children, new_args)
    
    # ArrayAccess
    if isinstance(node, ArrayAccess):
        return ArrayAccess(_replace_identifiers(node.target, var_map, _visiting),
                           _replace_identifiers(node.index, var_map, _visiting))
    
    # MemberAccess
    if isinstance(node, MemberAccess):
        return MemberAccess(_replace_identifiers(node.target, var_map, _visiting), node.member)
    
    # IfStatement
    if isinstance(node, IfStatement):
        new_else = _replace_identifiers(node.else_body, var_map, _visiting) if node.else_body else None
        return IfStatement(_replace_identifiers(node.condition, var_map, _visiting),
                           _replace_identifiers(node.then_body, var_map, _visiting),
                           new_else)
    
    # ForLoop
    if isinstance(node, ForLoop):
        return ForLoop(node.variable,
                       _replace_identifiers(node.values, var_map, _visiting),
                       _replace_identifiers(node.body, var_map, _visiting))
    
    # LetBinding
    if isinstance(node, LetBinding):
        new_assigns = []
        for a in node.assignments:
            new_assigns.append(Assignment(a.name, _replace_identifiers(a.value, var_map, _visiting)))
        return LetBinding(new_assigns, _replace_identifiers(node.body, var_map, _visiting))
    
    # IntersectionFor
    if isinstance(node, IntersectionFor):
        return IntersectionFor(node.variable,
                               _replace_identifiers(node.values, var_map, _visiting),
                               _replace_identifiers(node.body, var_map, _visiting))
    
    # Projection
    if isinstance(node, Projection):
        new_body = _replace_identifiers(node.body, var_map, _visiting) if node.body else None
        return Projection(node.cut, new_body)
    
    # Mirror
    if isinstance(node, Mirror):
        new_body = _replace_identifiers(node.body, var_map, _visiting) if node.body else None
        return Mirror(_replace_identifiers(node.normal, var_map, _visiting), new_body)
    
    # MultMatrix
    if isinstance(node, MultMatrix):
        new_body = _replace_identifiers(node.body, var_map, _visiting) if node.body else None
        return MultMatrix(_replace_identifiers(node.matrix, var_map, _visiting), new_body)
    
    # Resize
    if isinstance(node, Resize):
        new_auto = _replace_identifiers(node.auto, var_map, _visiting) if node.auto else None
        new_body = _replace_identifiers(node.body, var_map, _visiting) if node.body else None
        return Resize(_replace_identifiers(node.newsize, var_map, _visiting), new_auto, new_body)
    
    # Color
    if isinstance(node, Color):
        new_alpha = _replace_identifiers(node.alpha, var_map, _visiting) if node.alpha else None
        new_body = _replace_identifiers(node.body, var_map, _visiting) if node.body else None
        return Color(_replace_identifiers(node.color, var_map, _visiting), new_alpha, new_body)
    
    # Echo
    if isinstance(node, Echo):
        return Echo([_replace_identifiers(a, var_map, _visiting) for a in node.args])
    
    # Assert
    if isinstance(node, Assert):
        new_msg = _replace_identifiers(node.message, var_map, _visiting) if node.message else None
        return Assert(_replace_identifiers(node.condition, var_map, _visiting), new_msg)
    
    # ChildrenRef
    if isinstance(node, ChildrenRef):
        new_index = _replace_identifiers(node.index, var_map, _visiting) if node.index else None
        return ChildrenRef(new_index)
    
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
        # Blocks inherit the current variable map (passed via parent_var_map)
        # but we don't have it here; _inline_vars will start fresh if no parent_var_map given.
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
            # Use numpy.arange for float steps (range() does not accept floats)
            if _is_float_literal(node.step):
                return f"list(__import__('numpy').arange({start}, ({end})+({step})/2, {step}))"
            return f"range({start}, ({end})+1, {step})"
        return f"range({start}, ({end})+1)"

    def visit_Identifier(self, node: Identifier) -> str:
        return node.name

    def visit_SpecialVar(self, node: SpecialVar) -> str:
        return node.name

    def visit_BinaryOp(self, node: BinaryOp) -> str:
        left = self.visit(node.left)
        right = self.visit(node.right)
        op = node.operator
        # Translate SCAD operators that differ from Python
        if op == '&&':
            op = 'and'
        elif op == '||':
            op = 'or'
        return f"({left} {op} {right})"

    def visit_UnaryOp(self, node: UnaryOp) -> str:
        operand = self.visit(node.operand)
        return f"({node.operator}{operand})"

    def visit_TernaryOp(self, node: TernaryOp) -> str:
        cond = self.visit(node.condition)
        true_expr = self.visit(node.true_expr)
        false_expr = self.visit(node.false_expr)
        return f"({true_expr} if {cond} else {false_expr})"

    def _inline_vars(self, statements: list[ASTNode], parent_var_map: dict[str, ASTNode] | None = None) -> str:
        """Collect assignments and inline variable references in subsequent statements.
        
        SCAD variables are constants (no mutation), so we can substitute their
        values directly wherever they are referenced. This avoids generating
        invalid Python like 'x=10 + self.api.box(x,x,x)'.
        
        Variables are only substituted in statements that appear *after* their
        assignment. Nested blocks (Block nodes) get their own scope: they start
        with a copy of the current var_map, but assignments inside the block
        do not leak out.
        """
        # Start with the parent's variable map (if any)
        var_map: dict[str, ASTNode] = {}
        if parent_var_map is not None:
            var_map.update(parent_var_map)
        
        parts: list[str] = []
        for stmt in statements:
            if isinstance(stmt, Assignment):
                # Record the assignment for later statements
                var_map[stmt.name] = stmt.value
                # Assignments contribute no geometry
                continue
            
            if isinstance(stmt, Block):
                # Nested block gets its own scope: pass a *copy* of the current var_map
                rendered = self._inline_vars(stmt.statements, dict(var_map))
                if rendered:
                    parts.append(rendered)
                continue
            
            # For any other statement, substitute using the current var_map
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
            center_val = node.named_args.get('center', BooleanLiteral(False))
            center_str = self.visit(center_val)
            if 0 in node.named_args and isinstance(node.named_args[0], VectorLiteral):
                vec = self.visit(node.named_args[0])
                return f"self.api.box(*{vec}, center={center_str})"
            elif 0 in node.named_args:
                val = self.visit(node.named_args[0])
                return f"self.api.box({val},{val},{val}, center={center_str})"
            elif 'size' in node.named_args:
                val = self.visit(node.named_args['size'])
                if isinstance(node.named_args['size'], VectorLiteral):
                    vec = self.visit(node.named_args['size'])
                    return f"self.api.box(*{vec}, center={center_str})"
                return f"self.api.box({val},{val},{val}, center={center_str})"
            else:
                raise ValueError(f"cube requires a size argument, got {list(node.named_args.keys())}")
        elif name == 'sphere':
            args = node.named_args
            if 'd' in args:
                d_val = self.visit(args['d'])
                return f"self.api.sphere(r={d_val}/2)"
            elif 'r' in args:
                r_val = self.visit(args['r'])
                return f"self.api.sphere(r={r_val})"
            else:
                args_str = self._format_named_args(args)
                return f"self.api.sphere({args_str})"
        elif name == 'cylinder':
            # Map OpenSCAD cylinder params to API: r → rad, h → l
            # cylinder_z(l, rad) and cone_z(h, r1, r2) do NOT accept center;
            # the generated code discards center for now.
            args = node.named_args
            # Detect purely positional args: keys 0, 1, 2, ...
            pos_count = sum(1 for k in args if isinstance(k, int))
            if pos_count > 0 and not any(isinstance(k, str) for k in args):
                # Purely positional: 1→h, 2→(h,r), 3→(h,r1,r2)
                if pos_count == 3:
                    h_val = self.visit(args[0])
                    r1_val = self.visit(args[1])
                    r2_val = self.visit(args[2])
                    if r1_val == r2_val:
                        return f"self.api.cylinder_z(l={h_val}, rad={r1_val})"
                    else:
                        return f"self.api.cone_z(h={h_val}, r1={r1_val}, r2={r2_val})"
                elif pos_count == 2:
                    h_val = self.visit(args[0])
                    r_val = self.visit(args[1])
                    return f"self.api.cylinder_z(l={h_val}, rad={r_val})"
                else:  # 1 positional
                    h_val = self.visit(args[0])
                    # No radius given; use default r=1 per OpenSCAD spec
                    return f"self.api.cylinder_z(l={h_val}, rad=1)"
            # Named args (or mixed) — use standard key-based lookup
            has_r = 'r' in args
            has_d = 'd' in args
            has_r1 = 'r1' in args
            has_r2 = 'r2' in args
            has_h = 'h' in args or 'height' in args
            if has_r and has_h:
                r_val = self.visit(args['r'])
                h_val = self.visit(args.get('h', args.get('height')))
                return f"self.api.cylinder_z(l={h_val}, rad={r_val})"
            elif has_d and has_h:
                d_val = self.visit(args['d'])
                h_val = self.visit(args.get('h', args.get('height')))
                return f"self.api.cylinder_z(l={h_val}, rad={d_val}/2)"
            elif has_r1 and has_r2 and has_h:
                h_val = self.visit(args.get('h', args.get('height')))
                r1_val = self.visit(args['r1'])
                r2_val = self.visit(args['r2'])
                return f"self.api.cone_z(h={h_val}, r1={r1_val}, r2={r2_val})"
            elif has_r1 and not has_r2 and has_h:
                h_val = self.visit(args.get('h', args.get('height')))
                r1_val = self.visit(args['r1'])
                return f"self.api.cone_z(h={h_val}, r1={r1_val}, r2={r1_val})"
            elif has_r and not has_h:
                return f"self.api.cylinder_z(rad={self.visit(args['r'])})"
            # Fallback
            args_str = self._format_named_args(args)
            return f"self.api.cylinder_z({args_str})"
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
        conv_str = self.visit(node.convexity) if node.convexity else None
        if conv_str and conv_str != '1':
            parts.append(f"convexity={conv_str}")
        return f"self.api.polygon({', '.join(parts)})"

    def _gen_text2d_call(self, node: Text2D, tck_val: str | None = None) -> str:
        """Generate self.api.text(...) call from a Text2D node.

        The API's text() creates a fully 3D shape (extrudes glyphs by tck).
        SCAD's text() is 2D and relies on linear_extrude to add the 3rd dimension.
        When a caller knows the extrusion height (e.g. LinearExtrude wrapping text),
        it supplies `tck_val` so the generated call produces the correct 3D shape
        without a subsequent .linear_extrude() call.
        """
        if isinstance(node.text, str):
            text_val = repr(node.text)
        else:
            text_val = self.visit(node.text)
        parts = [text_val]
        # Map SCAD 'size' → API 'fontSize'
        if node.size is not None:
            parts.append(f"fontSize={self.visit(node.size)}")
        # Use the caller-supplied tck_val (extrusion height) or a reasonable default.
        if tck_val is not None:
            parts.append(f"tck={tck_val}")
        else:
            parts.append("tck=1")
        # Map SCAD 'font' → API 'font'
        if node.font is not None:
            parts.append(f"font={self.visit(node.font)}")
        return f"self.api.text({', '.join(parts)})"

    def visit_Text2D(self, node: Text2D) -> str:
        """Standalone text() call — no extrusion context, use default tck."""
        return self._gen_text2d_call(node)

    def _visit_body_text2d_in_extrude(self, node: Text2D, height_str: str) -> str:
        """Text2D inside linear_extrude: embed height as tck, skip extrude."""
        return self._gen_text2d_call(node, tck_val=height_str)

    def visit_LinearExtrude(self, node: LinearExtrude) -> str:
        # Check if the body is a plain Text2D node (no intermediate transforms).
        # The API's text() is inherently 3D via its tck parameter, so when SCAD
        # says text(...) → linear_extrude(height=H), we generate text(..., tck=H)
        # and skip the .linear_extrude() step entirely.
        if isinstance(node.body, Text2D):
            height_str = self.visit(node.height)
            return self._visit_body_text2d_in_extrude(node.body, height_str)

        body = self.visit(node.body)
        parts = [f"height={self.visit(node.height)}"]
        if node.twist is not None:
            parts.append(f"twist={self.visit(node.twist)}")
        if node.scale is not None:
            parts.append(f"scale={self.visit(node.scale)}")
        # node.center is a bool (Python) or BooleanLiteral (AST node).
        # When it's a BooleanLiteral, evaluate its .value attribute.
        center_val = node.center
        if isinstance(center_val, BooleanLiteral):
            center_val = center_val.value
        if center_val:
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
        # Wrap body in parentheses to ensure correct operator precedence when
        # the body is a compound expression (e.g. "a + b" → "(a + b).mv(...)"
        # not "a + b.mv(...)").
        if body:
            body = f"({body})"
        tt = node.transform_type
        if tt == 'translate':
            vec = self.visit(node.params.get('v', node.params.get(0, VectorLiteral([]))))
            return f"{body}.mv(*{vec})"
        elif tt == 'rotate':
            rot_param = node.params.get('a', node.params.get(0, None))
            # Detect rotate([0,0,angle]) — common SCAD idiom for 2D rotation
            # around Z.  The API's vector-rotate calls _ensure3d(), which
            # breaks linear_extrude later, so emit a scalar rotate instead.
            if (isinstance(rot_param, VectorLiteral)
                    and len(rot_param.elements) == 3
                    and _is_zero(rot_param.elements[0])
                    and _is_zero(rot_param.elements[1])):
                # Extract the Z-angle component
                ang = self.visit(rot_param.elements[2])
                return f"self._guard({body}).rotate({ang})"
            vec = self.visit(rot_param)
            return f"self._guard({body}).rotate({vec})"
        elif tt == 'scale':
            param = node.params.get('v', node.params.get(0, NumberLiteral(1)))
            scaled = self.visit(param)
            # Scalar (NumberLiteral) → body.scale(x,x,x);  Vector → body.scale(*[x,y,z])
            if isinstance(param, NumberLiteral):
                return f"{body}.scale({scaled}, {scaled}, {scaled})"
            return f"{body}.scale(*{scaled})"
        elif tt == 'mirror':
            args = node.params
            if 0 in args:
                normal = self.visit(args[0])
                return f"{body}.mirror(normal={normal})"
            else:
                return f"{body}.mirror()"
        elif tt == 'color':
            # Convert string color names to RGB tuples; pass other args as-is
            resolved = {}
            for key, val in node.params.items():
                if isinstance(key, int) and key == 0:
                    resolved_val = _resolve_color_arg(val)
                    if resolved_val is not None:
                        resolved[key] = resolved_val
                        continue
                resolved[key] = self.visit(val)
            args_str = ", ".join(
                v if isinstance(k, int) else f"{k}={v}"
                for k, v in resolved.items()
            )
            return f"{body}.set_color({args_str})"
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
        children_str = ', '.join(self.visit(child) for child in node.arguments)
        if children_str and args_str:
            return f'self._{node.name}({children_str}, {args_str})'
        elif children_str:
            return f'self._{node.name}({children_str})'
        else:
            return f'self._{node.name}({args_str})'

    def visit_ChildrenRef(self, node: ChildrenRef) -> str:
        return 'children()'

    def visit_FunctionCallExpr(self, node: FunctionCallExpr) -> str:
        callee = self.visit(node.callee)
        args_str = self._format_named_args(node.named_arguments)
        # User-defined functions are stored as self._<name> methods
        if isinstance(node.callee, Identifier) and node.callee.name in self.helper_functions:
            return f"self._{callee}({args_str})"
        # SCAD math builtins → math.<name>
        # OpenSCAD trig functions use DEGREES; Python's math module uses RADIANS.
        # Convert accordingly.
        if isinstance(node.callee, Identifier) and node.callee.name in self.SCAD_MATH_FUNCS:
            name = node.callee.name
            # Functions whose INPUT is in degrees: wrap each arg with math.radians()
            DEG_INPUT = {'cos', 'sin', 'tan'}
            if name in DEG_INPUT:
                # Wrap each positional argument with math.radians()
                rad_args = ', '.join(
                    f"math.radians({self.visit(val)})"
                    if isinstance(key, int) else f"{key}=math.radians({self.visit(val)})"
                    for key, val in node.named_arguments.items()
                )
                return f"math.{name}({rad_args})"
            # Functions whose OUTPUT is in degrees: wrap the whole call with math.degrees()
            DEG_OUTPUT = {'acos', 'asin', 'atan'}
            if name in DEG_OUTPUT:
                return f"math.degrees(math.{name}({args_str}))"
            # atan2: both input and output differ: SCAD atan2(y,x) returns degrees,
            # Python math.atan2(y,x) takes radians input, returns radians output.
            if name == 'atan2':
                return f"math.degrees(math.atan2({args_str}))"
            # Non-trig functions: direct mapping
            return f"math.{name}({args_str})"
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
        # Skip if-statement when the body is empty (e.g. echo-only)
        if not then_body:
            return ""
        if node.else_body:
            else_body = self.visit(node.else_body)
            return f"({then_body} if {cond} else {else_body})"
        return f"({then_body} if {cond} else None)"

    def visit_ForLoop(self, node: ForLoop) -> str:
        var = node.variable
        values = self.visit(node.values)
        body = self.visit(node.body)
        # Filter out None values (from if-statements without else) so they
        # don't propagate into shape method chains like .rotate(None).
        return f"__import__('functools').reduce(lambda a,b:a+b, filter(None, [{body} for {var} in {values}]))"

    def _substitute_vars(self, node: ASTNode, var_map: dict) -> ASTNode:
        if node is None:
            return None
        if isinstance(node, Identifier) and node.name in var_map:
            return var_map[node.name]
        # Recursively substitute in child nodes
        for attr_name in dir(node):
            if attr_name.startswith('_'):
                continue
            try:
                attr = getattr(node, attr_name)
            except Exception:
                continue
            if isinstance(attr, ASTNode):
                setattr(node, attr_name, self._substitute_vars(attr, var_map))
            elif isinstance(attr, list):
                new_list = []
                for item in attr:
                    if isinstance(item, ASTNode):
                        new_list.append(self._substitute_vars(item, var_map))
                    else:
                        new_list.append(item)
                setattr(node, attr_name, new_list)
            elif isinstance(attr, dict):
                new_dict = {}
                for k, v in attr.items():
                    if isinstance(v, ASTNode):
                        new_dict[k] = self._substitute_vars(v, var_map)
                    else:
                        new_dict[k] = v
                setattr(node, attr_name, new_dict)
        return node

    def visit_LetBinding(self, node: LetBinding) -> str:
        # Build substitution map from let-bindings
        var_map = {}
        for assign in node.assignments:
            var_map[assign.name] = assign.value
        # Substitute variables in body
        body = self._substitute_vars(node.body, var_map, _visiting)
        return self.visit(body)

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

    # SCAD math builtins that map to Python's math module
    SCAD_MATH_FUNCS = frozenset({
        'cos', 'sin', 'tan', 'acos', 'asin', 'atan', 'atan2',
        'ceil', 'exp', 'floor', 'ln', 'log', 'pow',
        'round', 'sign', 'sqrt',
    })

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

    def _collect_nested_modules(self) -> None:
        """Walk bodies of all collected modules and register nested ModuleDef nodes.
        
        In SCAD, modules can be nested (e.g. module helpers() { module line() { ... } }).
        The top-level AST walk only registers the outermost module; we need a second pass
        over their bodies to discover nested module definitions.
        """
        from b1scad.ast_nodes import Block
        _todo = list(self.helper_modules.values())
        while _todo:
            node = _todo.pop()
            body = node.body
            if isinstance(body, Block):
                for stmt in body.statements:
                    if isinstance(stmt, ModuleDef):
                        if stmt.name not in self.helper_modules:
                            self.helper_modules[stmt.name] = stmt
                            _todo.append(stmt)
                    elif isinstance(stmt, Block):
                        _todo.append(stmt)

    def gen_helper_methods(self) -> str:
        """Generate Python helper method definitions from stored module/function defs.
        
        Returns a string containing method definitions with proper class-body
        indentation (4 spaces for def line, 8 spaces for body lines),
        separated by blank lines between methods.
        """
        self._collect_nested_modules()
        parts = []
        for name, node in sorted(self.helper_modules.items()):
            # Generate method signature
            params = []
            for pname, pdefault in node.parameters:
                # Skip special vars ($fn, $fa, $fs) — not valid Python identifiers
                if pname.startswith('$'):
                    continue
                if pdefault is not None:
                    default_str = self.visit(pdefault)
                    params.append(f"{pname}={default_str}")
                else:
                    params.append(pname)
            params_str = ", ".join(params)
            
            # Generate method body: Block bodies use _inline_vars (handles variable assignments),
            # direct-statement bodies (module foo() bar();) use visit directly.
            from b1scad.ast_nodes import Block
            if isinstance(node.body, Block):
                body_expr = self._inline_vars(node.body.statements)
            else:
                body_expr = self.visit(node.body)
            
            if body_expr:
                if 'children()' in body_expr:
                    body_expr = body_expr.replace(
                        'children()',
                        '(__import__("functools").reduce(lambda a,b:a+b, children) if children else self.api.box(0,0,0, center=False))'
                    )
                if params_str:
                    lines = [f"    def _{name}(self, {params_str}, *children):",
                             f"        return {body_expr}"]
                else:
                    lines = [f"    def _{name}(self, *children):",
                             f"        return {body_expr}"]
            else:
                if params_str:
                    lines = [f"    def _{name}(self, {params_str}, *children):",
                             "        return self.api.box(0,0,0, center=False)"]
                else:
                    lines = [f"    def _{name}(self, *children):",
                             "        return self.api.box(0,0,0, center=False)"]
            parts.append("\n".join(lines))
        
        for name, node in sorted(self.helper_functions.items()):
            params = []
            for pname, pdefault in node.parameters:
                # Skip special vars ($fn, $fa, $fs)
                if pname.startswith('$'):
                    continue
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
            "import math",
            "import os",
            "import sys",
            "sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))",
            "",
            "from b13d.api.solid import Solid, test_loop, main_maker",
            "from b13d.api.core import Shape",
            "",
            f"class {cls_name}(Solid):",
            f'    """ Generate a {model} """',
            "    def _guard(self, s):",
            "        '''Convert None to a no-op shape so chained method calls work.'''",
            "        if s is not None:",
            "            return s",
            "        # Zero-volume box: harmless identity for union/difference/rotate",
            "        return self.api.box(0, 0, 0)",
            "",
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

    # generate module name (replace hyphens for valid Python identifiers)
    fname = os.path.basename(output_path)
    basefname, _ = os.path.splitext(fname)
    basefname = basefname.replace('-', '_')
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
