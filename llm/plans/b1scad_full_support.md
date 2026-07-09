---
name: b1scad-full-support
description: "Plan and implement full OpenSCAD language support in b1scad module. USE FOR: updating b1scad to handle variables, control flow, advanced operations, and modules; implementing phased approach to SCAD language features; adding regression tests for new features."
---

# B1scad Full SCAD Language Support Plan

This skill provides a detailed roadmap for upgrading the b1scad module from its current experimental state (basic primitives + transforms) to full OpenSCAD language support. The plan is structured in four phases, each building on the previous while maintaining backward compatibility.

## Current State Assessment

**What Works:**
- Basic geometric primitives: `cube()`, `sphere()`, `cylinder()`, `polyhedron()`
- Simple transforms: `translate()`, `rotate()`, `scale()`, `hull()`
- Boolean operations: `union()`, `difference()` (missing: `intersection()`)
- Named and positional parameters
- Code generation to b13d API
- 18 test models with volume-based validation

**Critical Gaps:**
- No variables or expressions
- No control flow (if/else, for loops)
- No user-defined functions
- No advanced operations (linear_extrude, rotate_extrude, offset, minkowski)
- No modules or scoping
- Limited error reporting
- Token-stream based parsing (not proper AST)

## Four-Phase Implementation Strategy

### Phase 1: Foundation (Strengthen Core Architecture)

**Goal:** Upgrade the parser infrastructure to support advanced features while maintaining all existing functionality.

**Key Changes:**
1. **Replace token stream with AST tree** - Convert from string manipulation to proper Abstract Syntax Tree with nodes for Module, FuncCall, Assignment, IfStmt, ForLoop, VarRef, etc.
2. **Add symbol table** - Implement scope management for variable/function tracking and name resolution
3. **Expression parser** - Support arithmetic (`+`, `-`, `*`, `/`, `%`) and logical operations (`==`, `!=`, `<`, `>`, `&&`, `||`)
4. **Enhanced error reporting** - Add line numbers and descriptive messages for parse failures
5. **Add intersection operation** - Complete the boolean operations set

**Files to Modify:**
- `scad2ast.py`: Upgrade lexer to produce AST nodes instead of token streams
- `scad2py.py`: Implement AST visitor pattern for code generation, add expression evaluation
- Add new file: `ast_nodes.py` for AST node definitions
- Add new file: `symbol_table.py` for scope management

**Testing:** All 18 existing models pass; add 5-10 new models testing expressions and intersection

### Phase 2: Variables & Control Flow (Unlock Parameterization)

**Goal:** Enable parameterized designs and conditional geometry.

**Key Changes:**
1. **Variable assignment and references** - Support `a = 10;`, `b = a * 2;`
2. **Boolean conditionals** - `if (condition) { ... } else { ... }`
3. **For loops** - `for (i = [0:10]) { ... }` with range iteration
4. **Function parameters** - Default values and type hints
5. **Let-bindings** - Local scope variables

**Files to Modify:**
- `scad2py.py`: Add grammar rules for assignments, conditionals, loops
- `ast_nodes.py`: Add nodes for Assignment, IfStmt, ForLoop, VarRef
- `symbol_table.py`: Extend for variable scoping and resolution

**Testing:** 15-20 new parameterized models; test nested scopes and variable shadowing

### Phase 3: Advanced Geometric Operations (Extend Modeling Capability)

**Goal:** Support common SCAD operations for 2D→3D conversion and shape manipulation.

**Key Changes:**
1. **linear_extrude** - `linear_extrude(height=10, twist=90, scale=[2,1]) { ... }`
2. **rotate_extrude** - `rotate_extrude(angle=360) { ... }`
3. **offset** - `offset(r=2) { ... }` for dilation/erosion
4. **minkowski** - `minkowski() { shape1; shape2; }`
5. **Improve hull** - Better handling of non-convex inputs

**Prerequisites:** Verify b13d API support for these operations; add wrappers if needed.

**Files to Modify:**
- `scad2py.py`: Add grammar rules and code generation for new operations
- `ast_nodes.py`: Add nodes for Extrude, Offset, Minkowski operations

**Testing:** Models using each operation; geometric comparison against OpenSCAD references

### Phase 4: Modules & Functions (Support Code Reuse)

**Goal:** Enable reusable design patterns and complex hierarchical models.

**Key Changes:**
1. **User-defined functions** - `function name(params) = expression;`
2. **Module definitions** - `module name(params) { ... }`
3. **Recursion support** - Self-referential modules/functions
4. **Children concept** - Reference geometry passed to modules
5. **Namespace management** - Avoid naming collisions

**Files to Modify:**
- `scad2py.py`: Add grammar for function/module definitions and calls
- `ast_nodes.py`: Add FunctionDef, ModuleDef, Call nodes
- `symbol_table.py`: Extend for function/module scoping

**Testing:** Multi-module designs, recursive patterns, complex hierarchies

## Implementation Guidelines

### Code Quality Standards
- Maintain backward compatibility - all existing tests must pass after each phase
- Add comprehensive error handling with clear messages
- Include line number information in error reports
- Follow existing code style and patterns

### Testing Strategy
- **Regression tests:** Existing 18 models verified after each phase
- **Unit tests:** Isolated tests for each new feature
- **Integration tests:** End-to-end SCAD→Python→STL validation
- **Error tests:** Verify unsupported features produce clear diagnostics

### Dependencies
- Check b13d API for required operations (extrude, offset, minkowski)
- May need b13d extensions for advanced geometric operations
- Consider performance implications of AST vs. token-stream approach

### Risk Mitigation
- Phase-by-phase approach minimizes risk of breaking changes
- Each phase includes verification against existing test suite
- Clear rollback points if issues arise

## Usage

This skill provides the strategic plan. To implement:

1. Start with Phase 1 to establish solid foundations
2. Implement incrementally, testing at each step
3. Use the existing test framework (`test.py`) as validation
4. Add new SCAD fixtures in `src/b1scad/scad/` for each phase

For implementation details on any phase, reference the session memory at `/memories/session/b1scad_strategy.md`.