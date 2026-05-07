# Implementation Plan: Fix Remaining B1scad Gaps

Complete the remaining unimplemented or broken features in the b1scad SCAD-to-Python converter: fix broken codegen for intersection/intersection_for, wire ChildrenRef, fix let-binding semantics, fix variable scoping, add use-directive symbol merging, and add test coverage for models 17–28.

The b1scad module has a working AST/parser/codegen pipeline that already handles most OpenSCAD features (primitives, transforms, booleans, expressions, control flow, functions, modules, advanced operations). However, several features are either broken or unimplemented: intersection codegen produces syntactically invalid Python, intersection_for codegen produces wrong semantics, ChildrenRef has no support, let-bindings silently drop their assignments, variable inlining ignores scope boundaries, use-directive has incomplete symbol merging, and test coverage stops at model16. This plan addresses all remaining gaps in dependency order.

## [Types]

No new AST nodes are needed. All required node types already exist in `src/b1scad/ast_nodes.py`.

The existing `ChildrenRef` node at line 324 will be:
- Given a parser grammar rule (for `children()` calls with optional index)
- Given a `_replace_identifiers` handler in `_replace_identifiers()`
- Given a `visit_ChildrenRef` visitor in `SymbolTableVisitor`
- Given a `visit_ChildrenRef` visitor in `AstToPython`

## [Files]

One new file, modifications to two existing files.

**New files:**
- `src/b1scad/scad/model29.scad` — test for intersection
- `src/b1scad/scad/model30.scad` — test for intersection_for
- `src/b1scad/scad/model31.scad` — test for children() in modules
- `src/b1scad/scad/model32.scad` — test for let-binding with expressions
- `src/b1scad/scad/model33.scad` — test for nested scopes and variable shadowing

**Modified files:**
- `src/b1scad/scad2py.py` — fix 5 bugs/gaps, add 2 missing visitors
- `src/b1scad/scad2ast.py` — add `children` keyword token
- `src/b1scad/symbol_table.py` — add use-directive symbol merging

## [Functions]

### Fixes in `src/b1scad/scad2py.py`:

**1. `AstToPython.visit_BooleanOp` (line 1410–1421)**
- Current: `intersection` branch at line 1417 uses `.intersection(.join(...))` — invalid Python
- Fix: Generate chained `.intersection()` calls: `op0.intersection(op1).intersection(op2)`
- Token estimate: 300 tokens (2-line change)

**2. `AstToPython.visit_IntersectionFor` (line 1482–1486)**
- Current: Generates a list comprehension `[body for var in values]`
- Fix: Generate `functools.reduce(lambda a,b: a.intersection(b), [body for var in values])` or chained calls
- Token estimate: 300 tokens (1-function rewrite)

**3. Add `children` keyword grammar in parser (around line 127–133)**
- Current: No parser rule for `children()` calls in module bodies
- Fix: Add `CHILDREN` token recognition and grammar rule returning `ChildrenRef` node
- Token estimate: 500 tokens

**4. `AstToPython.visit_ChildrenRef` (new method)**
- Current: Missing, would raise `NotImplementedError`
- Add: Generate `self.api.children(...)` or similar API call reflecting the children index
- Token estimate: 300 tokens

**5. `_replace_identifiers` handler for ChildrenRef** (add after line 1132)
- Current: Missing, would fall through to return node unchanged
- Add: Handle `ChildrenRef` — pass through (no substitution needed)
- Token estimate: 100 tokens

**6. `SymbolTableVisitor.visit_ChildrenRef` (add after line 960)**
- Current: Missing
- Add: Leaf node, no children to visit
- Token estimate: 50 tokens

**7. `AstToPython.visit_LetBinding` (line 1470–1472)**
- Current: Returns just `body`, silently dropping all assignments
- Fix: Generate a Python context that preserves the bindings, e.g. using an immediately-executed lambda or inline expressions with substitution
- Token estimate: 800 tokens

**8. `_inline_vars` scope handling (line 1256–1284)**
- Current: Collects ALL assignments into a single `var_map` regardless of scope nesting
- Fix: Process statements recursively per-scope-block rather than flat. For each Block, collect only its own-level assignments, inline them into subsequent sibling statements, and recurse into child blocks with a fresh scope
- Token estimate: 3K tokens (moderate refactor)

**9. Add `children` keyword to scad2ast.py lexer** (around line 29)
- Current: `children` is not a keyword token
- Fix: Add `CHILDREN = r'children'` token and include in tokens tuple
- Token estimate: 100 tokens

### Fixes in `src/b1scad/symbol_table.py`:

**10. `SymbolTable.merge_from_use` (new method)**
- Current: No method to merge symbols from a `use`-d file
- Add: Method that takes another SymbolTable's root scope symbols and imports them into current scope (module/function definitions only, not variables)
- Token estimate: 500 tokens

## [Classes]

No class modifications. All changes are function-level within existing classes (`OpenSCADParser`, `AstToPython`, `SymbolTableVisitor`, `SymbolTable`, `OpenSCADLexer`).

## [Dependencies]

No new dependencies. The existing `functools` module (already referenced in codegen for ForLoop) is sufficient for intersection_for reduction.

## [Testing]

**Test infrastructure:**
- Modify `src/b1scad/test.py` to add per-model unit tests with explicit assertions rather than just bulk volume comparison
- Each new model (29–33) gets a dedicated test method

**New SCAD test models:**
- `model29.scad`: `intersection() { cube(10); sphere(8); }` — tests intersection operation
- `model30.scad`: `intersection_for(i = [0:2]) { translate([i*10,0,0]) sphere(5); }` — tests intersection_for
- `model31.scad`: Module using `children()` to apply transforms to child geometry
- `model32.scad`: `let (a = 5, b = 10) cube(a + b);` — tests let-binding
- `model33.scad`: Nested scopes with variable shadowing across for/if/module boundaries

**Validation strategy:**
- Existing model00–model28: Verify all still pass after each change (regression guard)
- New models 29–33: Generate reference STL via OpenSCAD CLI, compare volume
- Manual inspection of generated Python for correctness

## [Implementation Order]

Implement in dependency order: fix broken codegen first, then wire missing features, then fix scoping, then add tests.

1. Fix `visit_BooleanOp` intersection codegen (broken → working)
2. Fix `visit_IntersectionFor` codegen (broken → working)
3. Register model29 and model30 tests, generate reference STLs, verify fixes
4. Add `children` token to lexer (scad2ast.py)
5. Add `children()` grammar rule to parser (scad2py.py)
6. Add `visit_ChildrenRef` to AstToPython, _replace_identifiers, SymbolTableVisitor
7. Add model31 test, generate reference STL, verify children() support
8. Fix `visit_LetBinding` to preserve bindings
9. Add model32 test, generate reference STL, verify let-binding
10. Refactor `_inline_vars` for proper scope handling
11. Add `merge_from_use` to SymbolTable
12. Add model33 test, generate reference STL, verify scoping
13. Run full test suite (model00–model33), fix any regressions
