# Implementation Plan: 2D API Support for model21

Implement proper 2D API support in b1scad SCAD-to-Python converter, replacing generic ShapeCall/Transform usage with dedicated 2D AST nodes for `square`, `circle`, `polygon`, `text`, `linear_extrude`, `rotate_extrude`, and `offset`.

The current implementation (model21.scad: `linear_extrude(height = 10) { square(10, center = true); }`) happens to work because the parser creates generic `ShapeCall` nodes and `Transform` nodes that the code generator maps to the correct API calls. However, dedicated 2D AST nodes already exist in `ast_nodes.py` (`Square2D`, `Circle2D`, `Polygon2D`, `Text2D`, `LinearExtrude`, `RotateExtrude`, `Offset`) but are **unused by the parser**. This plan restructures the parser and code generator to use these dedicated nodes, providing proper type safety and making the AST a faithful representation of the SCAD source.

## [Types]

No new types/classes needed. All required 2D AST nodes already exist in `src/b1scad/ast_nodes.py`:
- `Square2D` (line 465): `size`, `center`
- `Circle2D` (line 477): `radius`, `diameter`
- `Polygon2D` (line 489): `points`, `paths`, `convexity`
- `Text2D` (line 503): `text`, `size`, `font`, `halign`, `valign`, `spacing`, `direction`, `language`, `script`
- `LinearExtrude` (line 162): `height`, `twist`, `scale`, `center`, `body`
- `RotateExtrude` (line 182): `angle`, `body`
- `Offset` (line 194): `radius`, `body`

## [Files]

Single sentence describing file modifications.

Only one file needs modification:
- `src/b1scad/scad2py.py`: Change parser rules to use dedicated 2D AST nodes, and add corresponding visitor methods in the code generator.

## [Functions]

Single sentence describing function modifications.

Grammar methods in `OpenSCADParser` and visitor methods in `AstToPython` both in `scad2py.py` need modification.

**Modified grammar rules in `OpenSCADParser` (in `scad2py.py`):**

### A. Parser changes (lines 154-168, 227-237): Use dedicated 2D AST nodes

**Change 1: SQUARE rule** (line 154-156)
```python
# Before:
@_('SQUARE LPAREN args RPAREN')
def shape_call(self, p):
    return ShapeCall('square', [], _args_to_dict(p.args))

# After:
@_('SQUARE LPAREN args RPAREN')
def shape_call(self, p):
    args = _args_to_dict(p.args)
    # square(size) or square([w,h]) or square(size, center=true)
    return Square2D(
        size=args.get(0, args.get('size', NumberLiteral(1))),
        center=args.get('center', False)
    )
```

**Change 2: CIRCLE rule** (line 158-160)
```python
# Before:
@_('CIRCLE LPAREN args RPAREN')
def shape_call(self, p):
    return ShapeCall('circle', [], _args_to_dict(p.args))

# After:
@_('CIRCLE LPAREN args RPAREN')
def shape_call(self, p):
    args = _args_to_dict(p.args)
    # circle(r) or circle(d) or circle($fn=N)
    return Circle2D(
        radius=args.get('r'),
        diameter=args.get('d')
    )
```

**Change 3: POLYGON rule** (line 162-164)
```python
# Before:
@_('POLYGON LPAREN poly_args RPAREN')
def shape_call(self, p):
    return ShapeCall('polygon', [], _args_to_dict(p.poly_args))

# After:
@_('POLYGON LPAREN poly_args RPAREN')
def shape_call(self, p):
    args = _args_to_dict(p.poly_args)
    return Polygon2D(
        points=args.get(0, args.get('points')),
        paths=args.get('paths'),
        convexity=args.get('convexity', 1)
    )
```

**Change 4: TEXT rule** (line 166-168)
```python
# Before:
@_('TEXT LPAREN args RPAREN')
def shape_call(self, p):
    return ShapeCall('text', [], _args_to_dict(p.args))

# After:
@_('TEXT LPAREN args RPAREN')
def shape_call(self, p):
    args = _args_to_dict(p.args)
    return Text2D(
        text=str(args.get(0, args.get('text', ''))) if not isinstance(args.get(0, args.get('text', '')), str) else args.get(0, args.get('text', '')),
        size=args.get('size'),
        font=args.get('font'),
        halign=args.get('halign'),
        valign=args.get('valign'),
        spacing=args.get('spacing'),
        direction=args.get('direction'),
        language=args.get('language'),
        script=args.get('script')
    )
```

**Change 5: LINEAR_EXTRUDE rule** (line 227-229)
```python
# Before:
@_('LINEAR_EXTRUDE LPAREN args RPAREN LBRACE statements RBRACE')
def transform_op(self, p):
    return Transform('linear_extrude', _args_to_dict(p.args), Block(p.statements))

# After:
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
```

**Change 6: ROTATE_EXTRUDE rule** (line 231-233)
```python
# Before:
@_('ROTATE_EXTRUDE LPAREN args RPAREN LBRACE statements RBRACE')
def transform_op(self, p):
    return Transform('rotate_extrude', _args_to_dict(p.args), Block(p.statements))

# After:
@_('ROTATE_EXTRUDE LPAREN args RPAREN LBRACE statements RBRACE')
def transform_op(self, p):
    args = _args_to_dict(p.args)
    return RotateExtrude(
        angle=args.get('angle', args.get(0)),
        body=Block(p.statements)
    )
```

**Change 7: OFFSET rule** (line 235-237)
```python
# Before:
@_('OFFSET LPAREN args RPAREN LBRACE statements RBRACE')
def transform_op(self, p):
    return Transform('offset', _args_to_dict(p.args), Block(p.statements))

# After:
@_('OFFSET LPAREN args RPAREN LBRACE statements RBRACE')
def transform_op(self, p):
    args = _args_to_dict(p.args)
    return Offset(
        radius=args.get('r', args.get('delta', args.get(0))),
        body=Block(p.statements)
    )
```

**Change 8: `shape_statement` handling — wrap shape_call in 2D-aware dispatch** (line 112-115)

The existing `shape_statement → shape_call` rule returns a `ShapeCall`. After changes 1-4, it will return `Square2D`, `Circle2D`, `Polygon2D`, or `Text2D`. These are already valid AST nodes; the `shape_statement` rule needs no change — it simply returns whatever `shape_call` returns. The core change is that `shape_call` now returns typed 2D nodes instead of `ShapeCall`.

### B. Code generator changes in `AstToPython`:

**Add new visitor methods for 2D nodes** (insert after existing `visit_ShapeCall` or replace the relevant cases):

```python
def visit_Square2D(self, node: Square2D) -> str:
    size_val = self.visit(node.size)
    center_str = f", center={str(node.center).lower()}" if node.center else ""
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
```

**Add new visitor methods for extrusion/offset nodes** (replace corresponding cases in `visit_Transform`):

```python
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
```

### C. Clean up dead code in visitor methods

After adding the new visitors above:
1. **Remove** the `square`, `circle`, `polygon`, `text` cases from `visit_ShapeCall` (lines 1028-1039)
2. **Remove** the `linear_extrude`, `rotate_extrude`, `offset` cases from `visit_Transform` (lines 1067-1075)

## [Classes]

Single sentence describing class modifications.

No new classes needed; only method additions/replacements within `OpenSCADParser` (grammar rules) and `AstToPython` (visitor methods).

## [Dependencies]

Single sentence describing dependency modifications.

No dependency changes needed.

## [Testing]

Single sentence describing testing approach.

After changes, run the full test suite to verify all models (including model21, model26, model28) still parse, generate code, and pass volume comparison against OpenSCAD references:
```bash
cd /home/marco/programming/pylele && PYTHONPATH=src timeout 300 python3 src/b1scad/test.py B1scadTestMethods.test_all_scad 2>&1 | cat
```
Additionally, manually verify the generated code for models 21, 26, 28 shows the correct API calls.

## [Implementation Order]

Single sentence describing the implementation sequence.

1. Edit `src/b1scad/scad2py.py` to change parser rules (7 grammar rule changes in `OpenSCADParser`) and add 6 new visitor methods + cleanup in `AstToPython`
2. Run the full test suite to verify all models pass
