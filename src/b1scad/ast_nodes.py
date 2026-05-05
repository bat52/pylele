#!/usr/bin/env python3
"""
Abstract Syntax Tree (AST) node definitions for OpenSCAD language.

Represents the hierarchical structure of SCAD programs with proper types
for all language constructs: shapes, transforms, operations, expressions, etc.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Union, Any
from enum import Enum


class ASTNode:
    """Base class for all AST nodes."""
    def __init__(self, line: int = 0, col: int = 0):
        self.line = line
        self.col = col
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(...)"


# Module and Structure
@dataclass
class Module(ASTNode):
    """Root node representing a complete OpenSCAD module."""
    statements: List[ASTNode]
    
    def __init__(self, statements: List[ASTNode], line: int = 0):
        super().__init__(line)
        self.statements = statements


# Expressions and Literals
@dataclass
class NumberLiteral(ASTNode):
    """Numeric literal (int or float)."""
    value: Union[int, float]
    
    def __init__(self, value: Union[int, float], line: int = 0):
        super().__init__(line)
        self.value = value


@dataclass
class VectorLiteral(ASTNode):
    """Vector literal [x, y, z, ...]."""
    elements: List[ASTNode]
    
    def __init__(self, elements: List[ASTNode], line: int = 0):
        super().__init__(line)
        self.elements = elements


@dataclass
class Identifier(ASTNode):
    """Variable or function reference."""
    name: str
    
    def __init__(self, name: str, line: int = 0):
        super().__init__(line)
        self.name = name


@dataclass
class BinaryOp(ASTNode):
    """Binary operation (a + b, a * b, etc.)."""
    operator: str
    left: ASTNode
    right: ASTNode
    
    def __init__(self, operator: str, left: ASTNode, right: ASTNode, line: int = 0):
        super().__init__(line)
        self.operator = operator
        self.left = left
        self.right = right


@dataclass
class UnaryOp(ASTNode):
    """Unary operation (-x, !x, etc.)."""
    operator: str
    operand: ASTNode
    
    def __init__(self, operator: str, operand: ASTNode, line: int = 0):
        super().__init__(line)
        self.operator = operator
        self.operand = operand


@dataclass
class TernaryOp(ASTNode):
    """Ternary conditional (condition ? true_expr : false_expr)."""
    condition: ASTNode
    true_expr: ASTNode
    false_expr: ASTNode
    
    def __init__(self, condition: ASTNode, true_expr: ASTNode, false_expr: ASTNode, line: int = 0):
        super().__init__(line)
        self.condition = condition
        self.true_expr = true_expr
        self.false_expr = false_expr


# Shape Primitives
@dataclass
class ShapeCall(ASTNode):
    """Call to a shape primitive (cube, sphere, etc.)."""
    function_name: str
    args: List[ASTNode]
    named_args: dict
    
    def __init__(self, function_name: str, args: List[ASTNode] = None, named_args: dict = None, line: int = 0):
        super().__init__(line)
        self.function_name = function_name
        self.args = args or []
        self.named_args = named_args or {}


# Transformations
@dataclass
class Transform(ASTNode):
    """Transformation operation (translate, rotate, scale, etc.)."""
    transform_type: str  # 'translate', 'rotate', 'scale', 'mirror', 'multmatrix'
    params: dict  # Named parameters
    body: ASTNode  # What to transform
    
    def __init__(self, transform_type: str, params: dict, body: ASTNode, line: int = 0):
        super().__init__(line)
        self.transform_type = transform_type
        self.params = params
        self.body = body


# Boolean Operations
@dataclass
class BooleanOp(ASTNode):
    """Boolean operation (union, difference, intersection)."""
    operation: str  # 'union', 'difference', 'intersection'
    operands: List[ASTNode]
    
    def __init__(self, operation: str, operands: List[ASTNode], line: int = 0):
        super().__init__(line)
        self.operation = operation
        self.operands = operands


# Advanced Operations
@dataclass
class Hull(ASTNode):
    """Hull operation."""
    operands: List[ASTNode]
    
    def __init__(self, operands: List[ASTNode], line: int = 0):
        super().__init__(line)
        self.operands = operands


@dataclass
class LinearExtrude(ASTNode):
    """Linear extrusion (2D to 3D)."""
    height: ASTNode
    twist: Optional[ASTNode] = None
    scale: Optional[ASTNode] = None
    center: bool = False
    body: Optional[ASTNode] = None
    
    def __init__(self, height: ASTNode, body: ASTNode = None, 
                 twist: ASTNode = None, scale: ASTNode = None, 
                 center: bool = False, line: int = 0):
        super().__init__(line)
        self.height = height
        self.twist = twist
        self.scale = scale
        self.center = center
        self.body = body


@dataclass
class RotateExtrude(ASTNode):
    """Rotational extrusion."""
    angle: ASTNode
    body: Optional[ASTNode] = None
    
    def __init__(self, angle: ASTNode, body: ASTNode = None, line: int = 0):
        super().__init__(line)
        self.angle = angle
        self.body = body


@dataclass
class Offset(ASTNode):
    """Offset operation."""
    radius: ASTNode
    body: Optional[ASTNode] = None
    
    def __init__(self, radius: ASTNode, body: ASTNode = None, line: int = 0):
        super().__init__(line)
        self.radius = radius
        self.body = body


@dataclass
class Minkowski(ASTNode):
    """Minkowski sum operation."""
    operands: List[ASTNode]
    
    def __init__(self, operands: List[ASTNode], line: int = 0):
        super().__init__(line)
        self.operands = operands


# Statements
@dataclass
class Assignment(ASTNode):
    """Variable assignment."""
    name: str
    value: ASTNode
    
    def __init__(self, name: str, value: ASTNode, line: int = 0):
        super().__init__(line)
        self.name = name
        self.value = value


@dataclass
class IfStatement(ASTNode):
    """If-else statement."""
    condition: ASTNode
    then_body: ASTNode
    else_body: Optional[ASTNode] = None
    
    def __init__(self, condition: ASTNode, then_body: ASTNode, 
                 else_body: ASTNode = None, line: int = 0):
        super().__init__(line)
        self.condition = condition
        self.then_body = then_body
        self.else_body = else_body


@dataclass
class ForLoop(ASTNode):
    """For loop statement."""
    variable: str
    values: ASTNode  # Can be range or vector
    body: ASTNode
    
    def __init__(self, variable: str, values: ASTNode, body: ASTNode, line: int = 0):
        super().__init__(line)
        self.variable = variable
        self.values = values
        self.body = body


@dataclass
class LetBinding(ASTNode):
    """Let statement for local variables."""
    assignments: List[Assignment]
    body: ASTNode
    
    def __init__(self, assignments: List[Assignment], body: ASTNode, line: int = 0):
        super().__init__(line)
        self.assignments = assignments
        self.body = body


@dataclass
class FunctionDef(ASTNode):
    """Function definition."""
    name: str
    parameters: List[tuple]  # List of (name, default_value) tuples
    body: ASTNode
    
    def __init__(self, name: str, parameters: List[tuple], body: ASTNode, line: int = 0):
        super().__init__(line)
        self.name = name
        self.parameters = parameters
        self.body = body


@dataclass
class ModuleDef(ASTNode):
    """Module definition."""
    name: str
    parameters: List[tuple]  # List of (name, default_value) tuples
    body: ASTNode
    
    def __init__(self, name: str, parameters: List[tuple], body: ASTNode, line: int = 0):
        super().__init__(line)
        self.name = name
        self.parameters = parameters
        self.body = body


@dataclass
class FunctionCall(ASTNode):
    """Function or module call."""
    name: str
    arguments: List[ASTNode]
    named_arguments: dict
    
    def __init__(self, name: str, arguments: List[ASTNode] = None, 
                 named_arguments: dict = None, line: int = 0):
        super().__init__(line)
        self.name = name
        self.arguments = arguments or []
        self.named_arguments = named_arguments or {}


@dataclass
class Block(ASTNode):
    """Code block (group of statements)."""
    statements: List[ASTNode]
    
    def __init__(self, statements: List[ASTNode], line: int = 0):
        super().__init__(line)
        self.statements = statements


# Special nodes
@dataclass
class ChildrenRef(ASTNode):
    """Reference to children in a module."""
    index: Optional[ASTNode] = None
    
    def __init__(self, index: ASTNode = None, line: int = 0):
        super().__init__(line)
        self.index = index


# --- New AST node types for full SCAD language support ---

@dataclass
class StringLiteral(ASTNode):
    """String literal."""
    value: str
    
    def __init__(self, value: str, line: int = 0):
        super().__init__(line)
        self.value = value


@dataclass
class BooleanLiteral(ASTNode):
    """Boolean literal (true/false)."""
    value: bool
    
    def __init__(self, value: bool, line: int = 0):
        super().__init__(line)
        self.value = value


@dataclass
class UndefLiteral(ASTNode):
    """undef literal."""
    def __init__(self, line: int = 0):
        super().__init__(line)


@dataclass
class RangeLiteral(ASTNode):
    """Range literal [start:end] or [start:step:end]."""
    start: ASTNode
    end: ASTNode
    step: Optional[ASTNode] = None
    
    def __init__(self, start: ASTNode, end: ASTNode, step: ASTNode = None, line: int = 0):
        super().__init__(line)
        self.start = start
        self.end = end
        self.step = step


@dataclass
class IntersectionFor(ASTNode):
    """intersection_for(...) { ... }"""
    variable: str
    values: ASTNode
    body: ASTNode
    
    def __init__(self, variable: str, values: ASTNode, body: ASTNode, line: int = 0):
        super().__init__(line)
        self.variable = variable
        self.values = values
        self.body = body


@dataclass
class IncludeDirective(ASTNode):
    """include <path>"""
    path: str
    resolved_ast: Optional[ASTNode] = None
    
    def __init__(self, path: str, resolved_ast: ASTNode = None, line: int = 0):
        super().__init__(line)
        self.path = path
        self.resolved_ast = resolved_ast


@dataclass
class UseDirective(ASTNode):
    """use <path>"""
    path: str
    resolved_ast: Optional[ASTNode] = None
    
    def __init__(self, path: str, resolved_ast: ASTNode = None, line: int = 0):
        super().__init__(line)
        self.path = path
        self.resolved_ast = resolved_ast


@dataclass
class FunctionCallExpr(ASTNode):
    """Function call in expression context."""
    callee: ASTNode
    arguments: List[ASTNode]
    named_arguments: dict
    
    def __init__(self, callee: ASTNode, arguments: List[ASTNode] = None,
                 named_arguments: dict = None, line: int = 0):
        super().__init__(line)
        self.callee = callee
        self.arguments = arguments or []
        self.named_arguments = named_arguments or {}


@dataclass
class ArrayAccess(ASTNode):
    """expr[index]"""
    target: ASTNode
    index: ASTNode
    
    def __init__(self, target: ASTNode, index: ASTNode, line: int = 0):
        super().__init__(line)
        self.target = target
        self.index = index


@dataclass
class MemberAccess(ASTNode):
    """expr.member"""
    target: ASTNode
    member: str
    
    def __init__(self, target: ASTNode, member: str, line: int = 0):
        super().__init__(line)
        self.target = target
        self.member = member


@dataclass
class SpecialVar(ASTNode):
    """Special variable ($fn, $fa, $fs)."""
    name: str
    
    def __init__(self, name: str, line: int = 0):
        super().__init__(line)
        self.name = name


# 2D Primitives
@dataclass
class Square2D(ASTNode):
    """square(size) or square([w,h])"""
    size: ASTNode
    center: bool = False
    
    def __init__(self, size: ASTNode, center: bool = False, line: int = 0):
        super().__init__(line)
        self.size = size
        self.center = center


@dataclass
class Circle2D(ASTNode):
    """circle(r) or circle(d)"""
    radius: Optional[ASTNode] = None
    diameter: Optional[ASTNode] = None
    
    def __init__(self, radius: ASTNode = None, diameter: ASTNode = None, line: int = 0):
        super().__init__(line)
        self.radius = radius
        self.diameter = diameter


@dataclass
class Polygon2D(ASTNode):
    """polygon(points, paths, convexity)"""
    points: ASTNode
    paths: Optional[ASTNode] = None
    convexity: int = 1
    
    def __init__(self, points: ASTNode, paths: ASTNode = None, convexity: int = 1, line: int = 0):
        super().__init__(line)
        self.points = points
        self.paths = paths
        self.convexity = convexity


@dataclass
class Text2D(ASTNode):
    """text(text, size, font, etc.)"""
    text: str
    size: Optional[ASTNode] = None
    font: Optional[str] = None
    halign: Optional[str] = None
    valign: Optional[str] = None
    spacing: Optional[ASTNode] = None
    direction: Optional[str] = None
    language: Optional[str] = None
    script: Optional[str] = None
    
    def __init__(self, text: str, size: ASTNode = None, font: str = None,
                 halign: str = None, valign: str = None, spacing: ASTNode = None,
                 direction: str = None, language: str = None, script: str = None,
                 line: int = 0):
        super().__init__(line)
        self.text = text
        self.size = size
        self.font = font
        self.halign = halign
        self.valign = valign
        self.spacing = spacing
        self.direction = direction
        self.language = language
        self.script = script


@dataclass
class Projection(ASTNode):
    """projection(cut) { ... }"""
    cut: bool = False
    body: Optional[ASTNode] = None
    
    def __init__(self, cut: bool = False, body: ASTNode = None, line: int = 0):
        super().__init__(line)
        self.cut = cut
        self.body = body


@dataclass
class Mirror(ASTNode):
    """mirror([x, y, z]) { ... }"""
    normal: ASTNode
    body: Optional[ASTNode] = None
    
    def __init__(self, normal: ASTNode, body: ASTNode = None, line: int = 0):
        super().__init__(line)
        self.normal = normal
        self.body = body


@dataclass
class MultMatrix(ASTNode):
    """multmatrix(m) { ... }"""
    matrix: ASTNode
    body: Optional[ASTNode] = None
    
    def __init__(self, matrix: ASTNode, body: ASTNode = None, line: int = 0):
        super().__init__(line)
        self.matrix = matrix
        self.body = body


@dataclass
class Resize(ASTNode):
    """resize([x, y, z]) { ... }"""
    newsize: ASTNode
    auto: Optional[ASTNode] = None
    body: Optional[ASTNode] = None
    
    def __init__(self, newsize: ASTNode, auto: ASTNode = None, body: ASTNode = None, line: int = 0):
        super().__init__(line)
        self.newsize = newsize
        self.auto = auto
        self.body = body


@dataclass
class Color(ASTNode):
    """color(c) { ... }"""
    color: ASTNode
    alpha: Optional[ASTNode] = None
    body: Optional[ASTNode] = None
    
    def __init__(self, color: ASTNode, alpha: ASTNode = None, body: ASTNode = None, line: int = 0):
        super().__init__(line)
        self.color = color
        self.alpha = alpha
        self.body = body


@dataclass
class Echo(ASTNode):
    """echo(...) statement."""
    args: List[ASTNode]
    
    def __init__(self, args: List[ASTNode], line: int = 0):
        super().__init__(line)
        self.args = args


@dataclass
class Assert(ASTNode):
    """assert(...) statement."""
    condition: ASTNode
    message: Optional[ASTNode] = None
    
    def __init__(self, condition: ASTNode, message: ASTNode = None, line: int = 0):
        super().__init__(line)
        self.condition = condition
        self.message = message
