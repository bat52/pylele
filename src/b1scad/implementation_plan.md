# Implementation Plan

## [Overview]

Extend b1scad to support the full OpenSCAD language by building a proper AST from SCAD source, then walking the AST to generate b13d API Python code with include resolution.

The current codebase has well-defined AST node types and a symbol table that are defined but unused. The existing SLY lexer and parser only cover ~11 tokens and emit Python code strings directly without going through the AST. This rewrite restructures the pipeline to: SCAD source → (resolve includes) → Lexer → Parser → AST → Symbol Table analysis → Code Generator → Python (b13d API) file. The approach preserves backward compatibility by keeping the same `scad2py()` function signature and test infrastructure. All existing SCAD test models (model00 through model16) must continue to generate identical STL output.

## [Types]

Introduce new AST node types for the missing SCAD language constructs and extend existing ones, plus create a few enum/helper types.

### New AST Node Types (add to `ast_nodes.py`)

```python
# Literals
@dataclass class StringLiteral(ASTNode):         # "hello"
    value: str

@dataclass class BooleanLiteral(ASTNode):         # true/false
    value: bool

@dataclass class UndefLiteral(ASTNode):           # undef
    pass

@dataclass class RangeLiteral(ASTNode):           # [start:end] or [start:step:end]
    start: ASTNode
    step: Optional[ASTNode]  # None for [start:end]
    end: ASTNode

# Control Flow
@dataclass class IntersectionFor(ASTNode):        # intersection_for(...) { ... }
    variable: str
    values: ASTNode
    body: ASTNode

# Include/Use - resolved during transformation, kept for reference
@dataclass class IncludeDirective(ASTNode):
    path: str
    resolved_ast: Optional[ASTNode]  # populated after resolution

@dataclass class UseDirective(ASTNode):
    path: str
    resolved_ast: Optional[ASTNode]  # populated after resolution

# Expression subtypes for call/access
@dataclass class FunctionCallExpr(ASTNode):       # function call in expression context
    callee: ASTNode  # can be Identifier or MemberAccess
    arguments: List[ASTNode]
    named_arguments: dict

@dataclass class ArrayAccess(ASTNode):            # expr[index]
    target: ASTNode
    index: ASTNode

@dataclass class MemberAccess(ASTNode):           # expr.member
    target: ASTNode
    member: str

# 2D Primitives
@dataclass class Square2D(ASTNode):               # square(size) or square([w,h])
    size: ASTNode
    center: bool = False

@dataclass class Circle2D(ASTNode):               # circle(r) or circle(d)
    radius: ASTNode
    diameter: Optional[ASTNode] = None

@dataclass class Polygon2D(ASTNode):              # polygon(points, paths, convexity)
    points: ASTNode
    paths: Optional[ASTNode] = None
    convexity: int = 1

@dataclass class Text2D(ASTNode):                 # text(text, size, font, etc.)
    text: str
    size: ASTNode
    font: Optional[ASTNode] = None
    halign: Optional[str] = None
    valign: Optional[str] = None
    spacing: Optional[ASTNode] = None
    direction: Optional[str] = None
    language: Optional[str] = None
    script: Optional[str] = None

@dataclass class Projection(ASTNode):             # projection(cut) { ... }
    cut: bool = False
    body: ASTNode

# Additional Transforms
@dataclass class Mirror(ASTNode):                 # mirror([x, y, z]) { ... }
    normal: ASTNode
    body: ASTNode

@dataclass class MultMatrix(ASTNode):             # multmatrix(m) { ... }
    matrix: ASTNode
    body: ASTNode

@dataclass class Resize(ASTNode):                 # resize([x, y, z]) { ... }
    newsize: ASTNode
    auto: Optional[ASTNode] = None
    body: ASTNode

@dataclass class Color(ASTNode):                  # color(c) { ... }
    color: ASTNode
    alpha: Optional[ASTNode] = None
    body: ASTNode

# Extended extrude nodes
@dataclass class LinearExtrude(ASTNode):           # Updated with all params
    height: ASTNode
    center: bool = False
    twist: Optional[ASTNode] = None
    scale: Optional[ASTNode] = None
    slices: Optional[ASTNode] = None
    convexity: int = 1
    body: Optional[ASTNode] = None

@dataclass class RotateExtrude(ASTNode):           # Updated with all params
    angle: Optional[ASTNode] = None
    convexity: int = 1
    body: Optional[ASTNode] = None

# Special variables
@dataclass class SpecialVar(ASTNode):              # $fn, $fa, $fs
    name: str
```

### Enum/Helper Types

```python
# In ast_nodes.py or a new types.py
class OpPrecedence(IntEnum):
    ASSIGNMENT = 1
    TERNARY = 2
    LOGICAL_OR = 3
    LOGICAL_AND = 4
    EQUALITY = 5
    COMPARISON = 6
    ADDITION = 7
    MULTIPLICATION = 8
    UNARY = 9
    EXPONENT = 10
    CALL = 11
    PRIMARY = 12
```

Clarify the existing `BinaryOp.operator` values to be a closed enum set:
- Arithmetic: `+`, `-`, `*`, `/`, `%`, `^`
- Comparison: `<`, `>`, `<=`, `>=`, `==`, `!=`
- Logical: `&&`, `||`

## [Files]

Modify 4 existing files and create 0 new files — all changes are within the existing `src/b1scad/` package.

### Modified Files

1. **`src/b1scad/ast_nodes.py`** — Add all new AST node types listed above, plus a `BinaryOp.operator` type annotation enum.

2. **`src/b1scad/scad2ast.py`** — Completely rewrite the lexer to handle:
   - All missing keywords (module, function, for, if, else, let, each, include, use)
   - All missing primitives (square, circle, polygon, text)
   - All missing transforms/ops (mirror, multmatrix, resize, color, minkowski, offset, projection)
   - String literals (double-quoted)
   - Boolean/undef literals (true, false, undef)
   - Arithmetic operators (+, -, *, /, %, ^)
   - Comparison operators (<, >, <=, >=, ==, !=)
   - Logical operators (&&, ||, !)
   - Ternary (? :)
   - Dot access (.)
   - Special variables ($fa, $fs) 
   - Line comments (//), block comments (/* */)

3. **`src/b1scad/scad2py.py`** — Major rewrite:
   - Replace `OpenSCADParser` with a full SLY parser that builds an AST using nodes from `ast_nodes.py`
   - Add expression grammar with correct precedence (14 precedence levels matching OpenSCAD)
   - Add grammar rules for: module/function definitions, if/else, for loops, let bindings, include/use
   - Add grammar rules for all missing primitives, transforms, and operations
   - Add include resolution: when encountering `include <path>` or `use <path>`, recursively parse the file and merge its AST
   - Keep existing `CodeGenerator` but refactor it into an AST visitor/walker
   - Update `scad2py()` and `b1scad()` entry points

4. **`src/b1scad/test.py`** — Add new test cases covering new SCAD constructs (at minimum: for loops, if/else, modules, functions, 2D primitives, expressions, string handling)

### Files Not Modified
- `symbol_table.py` — Will be integrated into the code generation phase for scope analysis
- `__init__.py` — No changes needed if public API signatures remain the same

## [Functions]

### New Functions

1. **`ast_nodes.py`** — No new standalone functions; only new dataclass types.

2. **`scad2ast.py`** — No new public functions; `scad2ast()` signature remains `(infname: str, view: bool = True) -> List[Token]` but returns full token stream for the parser.

3. **`scad2py.py`** — New internal functions:
   - `resolve_includes(source: str, source_dir: str) -> str` — Resolves `include <...>` and `use <...>` directives, inlines file contents with path tracking
   - `ast_to_python(node: ASTNode, symbol_table: SymbolTable) -> str` — Visitor that generates b13d API Python code from an AST node
   - `generate_expression(expr_node: ASTNode) -> str` — Generates Python expression string from SCAD expression AST
   - `generate_shape_call(call_node: ASTNode) -> str` — Maps built-in module/function calls to b13d API calls
   - `generate_block(block_node: Block, symbol_table: SymbolTable) -> str` — Generates code for a block of statements
   - `lookup_builtin(name: str) -> Optional[Callable]` — Maps SCAD built-in names to code generation callbacks

### Modified Functions

1. **`OpenSCADParser.__init__`** (`scad2py.py`) — Add AST-building state (current scope, node stack)
2. **`OpenSCADParser.parse`** — Return AST root instead of string (code generation moves to visitor)
3. **`CodeGenerator.generate`** — Rewrite to use AST visitor pattern instead of string concatenation
4. **`CodeGenerator.write_template`** — Update to handle new constructs (module→function mapping, etc.)
5. **`scad2py(infname, execute_en)`** — Keep same signature, update internals for new two-phase pipeline
6. **`b1scad()`** — Keep same signature

### Removed Functions

- None removed; the monolithic string-building grammar rules in `OpenSCADParser` will be replaced.

## [Classes]

### Modified Class: `OpenSCADLexer` (scad2ast.py)
- Add ~15 new token definitions for all missing keywords, operators, and literals
- Add string literal handling (with escape sequences)
- Add block comment support `/* ... */`
- Update `ID` token to not capture keywords

### Major Rewrite: `OpenSCADParser` (scad2py.py)
- Changes from string-generating parser to AST-building parser
- Grammar rules split into precedence levels matching OpenSCAD's Yacc grammar:
  - `expr` → `ternary` → `logical_or` → `logical_and` → `equality` → 
    `comparison` → `addition` → `multiplication` → `unary` → `exponent` → 
    `call` → `primary`
- Module instantiation rules (module_id → call with child)
- Definition rules: `module_def`, `function_def`
- Flow control: `if_else`, `for_loop`, `let_binding`
- `include`/`use` directives
- Vector/list comprehension: `for`, `let`, `each`, `if` inside `[...]`

### Modified Class: `CodeGenerator` (scad2py.py)
- Rewrite from template-string writer to full AST visitor
- Add methods: `visit_Module`, `visit_Block`, `visit_ShapeCall`, `visit_Transform`, etc.
- Add `visit_Expression` for arithmetic/logic evaluation
- Add `visit_FunctionDef` and `visit_ModuleDef` → Python function generation
- Add `visit_ForLoop` → Python for loop generation
- Add `visit_IfStatement` → Python if/else generation
- Add `visit_IncludeDirective` → inline resolved AST

## [Dependencies]

No new external dependencies. The existing `sly` package is sufficient for lexer/parser. The project uses:
- `sly` (already in requirements.txt / Pipfile) — lexer/parser framework
- `b13d.api.*` (internal) — target code generation API

## [Testing]

### Existing Tests (must pass unchanged)
All 17 existing test models (model00.scad through model16.scad) must produce identical STL volumes.

### New Test Models
- model17.scad: `for` loop with `translate` and `sphere`
- model18.scad: `if`/`else` conditional geometry
- model19.scad: `module` definition with parameters and children
- model20.scad: `function` definition with arithmetic expressions
- model21.scad: 2D primitives (`square`, `circle`, `polygon`) with `linear_extrude`
- model22.scad: `mirror` transform
- model23.scad: String literals and `text()`
- model24.scad: `include` and `use` directives
- model25.scad: Complex expression evaluation (ternary, comparison, math)
- model26.scad: `rotate_extrude` with 2D shape
- model27.scad: `minkowski` operation
- model28.scad: `offset` operation

### Testing Strategy
1. Each new model has a `.scad` file and a reference STL generated by OpenSCAD
2. The test pipeline remains the same: SCAD→Python→STL, compare volume
3. `b1scad/test.py` gets new test methods for each new model

## [Implementation Order]

This is the critical sequence to minimize regressions. Each step produces a working (though partial) translator.

1. **Extend Lexer (`scad2ast.py`)** — Add all new token types. Verify existing tokens unchanged. Test with `python scad2ast.py model00.scad` on all existing models.

2. **Rewrite Parser to Build AST (`scad2py.py`)** — Replace string-emitting grammar with AST-node-emitting grammar for the *existing* subset (cube, sphere, cylinder, polyhedron, translate, rotate, scale, union, difference, intersection, hull, vectors, numbers, named args). This is the critical refactoring: must produce identical Python output for model00–model16.

3. **Add Expression Grammar** — Add full arithmetic, comparison, logical, and ternary expression parsing with AST nodes. Test by parsing `model.scad` and verifying expression AST structure.

4. **Add Control Flow (`if`/`else`, `for`, `let`, `intersection_for`)** — Add grammar rules and AST nodes for control flow constructs.

5. **Add Definitions (`module`, `function`)** — Add grammar rules for module and function definitions. Module→Python function mapping with children (`$children`/`children()`).

6. **Add Remaining Primitives and Transforms** — `square`, `circle`, `polygon`, `text`, `mirror`, `multmatrix`, `resize`, `color`, `projection`, `minkowski`, `offset`.

7. **Add Include/Use Resolution** — Implement `resolve_includes()` to recursively parse and merge included files.

8. **Update Code Generator to Walk AST** — Rewrite `CodeGenerator.generate()` and `write_template()` as an AST visitor that walks the tree and emits b13d API Python code. This replaces the old string-concatenation approach.

9. **Integrate Symbol Table** — Use `symbol_table.py` in the code generation phase for scope analysis and name resolution.

10. **Add New Test Models** — Create model17 through model28 with corresponding reference STLs.

11. **Validate All Tests** — Run `python test.py` and verify all existing + new tests pass.

12. **Clean Up and Documentation** — Remove dead code, update docstrings, verify `README` still accurate.

---

## [Token Cost Estimates]

Estimated AI agent tokens (input + output) required for each implementation step.

| # | Step | Est. Tokens | Complexity | Risk |
|---|------|------------|------------|------|
| 1 | **Extend Lexer** | ~8K–12K | ★☆☆ Easy | Low |
| 2 | **Rewrite Parser → AST** | ~40K–80K | ★★★ Hard | **High** — must match 17 models exactly |
| 3 | **Add Expression Grammar** | ~12K–20K | ★★☆ Medium | Medium |
| 4 | **Add Control Flow** | ~10K–16K | ★★☆ Medium | Medium |
| 5 | **Add Definitions** | ~10K–16K | ★★☆ Medium | Medium |
| 6 | **More Primitives & Transforms** | ~15K–25K | ★★☆ Medium | Medium |
| 7 | **Include/Use Resolution** | ~8K–12K | ★☆☆ Easy | Low |
| 8 | **AST Code Generator Visitor** | ~20K–35K | ★★☆ Medium | Medium |
| 9 | **Integrate Symbol Table** | ~8K–14K | ★★☆ Medium | Medium |
| 10 | **New Test Models** | ~10K–18K | ★☆☆ Easy | Low |
| 11 | **Validate All Tests** | ~8K–15K | ★☆☆ Varies | **High** — regression hunt |
| 12 | **Clean Up** | ~3K–5K | ★☆☆ Easy | None |
| | **Total** | **~152K–268K** | | |

### Detailed Breakdown

#### Step 1: Extend Lexer (~8K–12K tokens)
- **4K input**: Read scad2ast.py, ast_nodes.py, parser.y (reference grammar), existing test models
- **3K–5K output**: Write ~30 new regex token patterns, string literal handler, block comment handler, operator tokens, keyword→token mapping
- **1K–3K testing**: Run lexer on all existing models, verify token stream correctness
- *Low risk*: Adding tokens rarely breaks existing ones

#### Step 2: Rewrite Parser to Build AST (~40K–80K tokens) ⚡
- **8K input**: Read scad2py.py (full parser), ast_nodes.py, all 17 existing test models, test.py infrastructure
- **8K–12K output**: Write new grammar rules that emit AST nodes instead of Python strings (~15–20 rules), plus a temporary AST→string visitor that reproduces the EXACT same Python output
- **24K–60K testing**: **3–6 iterations** of: run on all 17 models → compare generated STL volumes → fix mismatches → repeat
  - Each iteration costs ~8K–10K tokens (read generated output, compare, debug, fix)
  - This is where the bulk of tokens go because of the backward-compatibility constraint
- *High risk*: Any deviation in Python output causes STL volume mismatch

#### Step 3: Add Expression Grammar (~12K–20K tokens)
- **3K input**: Read parser.y expression precedence levels, existing BinaryOp/UnaryOp/TernaryOp in ast_nodes.py
- **5K–8K output**: Write ~30 grammar rules across 14 precedence levels (expr → ternary → logical_or → logical_and → equality → comparison → addition → multiplication → unary → exponent → call → primary)
- **4K–9K testing**: Parse test expressions, verify AST structure, generate correct Python expressions
- *Medium risk*: Precedence bugs are subtle, but isolated from shape generation

#### Step 4: Add Control Flow (~10K–16K tokens)
- **3K input**: Read parser.y if/else/for/let rules, existing test model structures
- **4K–7K output**: Grammar rules for if_statement, ifelse_statement, for_loop, let_binding, intersection_for; AST→Python code generation for conditional geometry and loops
- **3K–6K testing**: Test with simple for/sphere patterns, if/else conditional shapes
- *Medium risk*: Loop variable scoping needs careful handling

#### Step 5: Add Definitions (~10K–16K tokens)
- **3K input**: Read parser.y module/function def rules, symbol_table.py, b13d API Solid class pattern
- **4K–7K output**: Grammar rules for module_def and function_def with parameter lists; code generation that maps SCAD modules to Python functions with `gen()` method pattern, children() → scope handling
- **3K–6K testing**: Module definition test → generates correct Python class, function test → generates correct Python expression function
- *Medium risk*: Children handling and scope interaction with b13d's class structure

#### Step 6: More Primitives & Transforms (~15K–25K tokens)
- **5K input**: Read b13d/api/core.py (all ShapeAPI methods), b13d/parts/ for reference, parser.y for all module ids
- **6K–12K output**: Grammar rules + code generation for: square, circle, polygon, text, mirror, multmatrix, resize, color, projection, minkowski, offset (11 new constructs)
  - Each requires: keyword token (already in lexer by step 1) → grammar rule → param extraction → b13d API call mapping
  - text() is the most complex: font handling, alignment, string escaping
- **4K–8K testing**: Test each construct individually, then in combination
- *Medium risk*: text() and polygon() have many parameters

#### Step 7: Include/Use Resolution (~8K–12K tokens)
- **2K input**: Read parser.y TOK_USE rules, SCAD file directory structure
- **3K–5K output**: `resolve_includes()` function that finds files relative to source directory, recursively parses, merges ASTs; include=inline vs use=library distinction
- **3K–5K testing**: Create test with multi-file SCAD project
- *Low risk*: Independent from parsing logic

#### Step 8: AST Code Generator Visitor (~20K–35K tokens)
- **5K input**: Read CodeGenerator class, all existing test model Python outputs, write_template structure
- **10K–18K output**: Full visitor pattern with methods for each AST node type (visit_Module, visit_Block, visit_ShapeCall, visit_Transform, visit_BooleanOp, visit_ForLoop, visit_Assignment, etc.) — each method emits correct b13d API Python code
- **5K–12K testing**: Generate complete Python files for all models, verify structure matches expected Solid class pattern, run STL comparison
- *Medium risk*: Large surface area for bugs, but mostly mechanical

#### Step 9: Integrate Symbol Table (~8K–14K tokens)
- **3K input**: Read symbol_table.py fully, existing CodeGenerator
- **3K–6K output**: Hook symbol table into code generation pass: push_scope/pop_scope at blocks, define() for assignments/defs, lookup() for variable references, error reporting for undefined references
- **2K–5K testing**: Test variable scoping in nested blocks, module parameter shadowing
- *Medium risk*: Incorrect scope handling leads to wrong code generation

#### Step 10: New Test Models (~10K–18K tokens)
- **3K input**: Read existing model00–model16 patterns, test.py test runner
- **4K–8K output**: 12 new .scad files (model17–model28) covering: for loops, if/else, modules, functions, 2D+extrude, mirror, text, include/use, expressions, rotate_extrude, minkowski, offset
- **3K–7K setup**: Generate reference STLs via OpenSCAD (`openscad -o modelXX.stl modelXX.scad`), update test.py with new test methods
- *Low risk*: Independent additions

#### Step 11: Validate All Tests (~8K–15K tokens)
- **5K input**: Run full test suite, read all test failures
- **3K–10K fixes**: Debug and fix regressions in existing tests + new tests
- *High risk*: Could uncover subtle issues from earlier steps; number of iterations depends on bugs

#### Step 12: Clean Up (~3K–5K tokens)
- **1K input**: Identify dead code, outdated comments
- **2K–4K output**: Remove old string-emitting code/comments, update docstrings, verify README
- *No risk*
