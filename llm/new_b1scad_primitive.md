---
name: add-scad-primitive
description: Add a new SCAD primitive and generate adequate testing coverage
---

To add a new SCAD primitive, follow this process:

## Phase 0: Validation & Research
0. **Verify OpenSCAD primitives**: Check [OpenSCAD documentation](https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/Primitive_Solids) for exact syntax and parameter handling
1. **Study similar primitives**: Examine existing implementations (e.g., `sphere`, `cylinder`) in `./src/b13d/api/*.py` to understand patterns
2. **Define method signature**: Plan the abstract method signature needed in `ShapeAPI` with type hints

## Phase 1: Core API Layer
3. **Add abstract method to ShapeAPI** in `./src/b13d/api/core.py`
   - Include docstring with parameter descriptions and return type
   - Add a basic test case in the `test_api()` method to validate all supported backends

4. **Add mock implementation** in `./src/b13d/api/mock.py`
   - Mock implementations return placeholder shapes; this allows basic testing without rendering

## Phase 2: Backend Implementations
5. **Implement for each supported backend**: `cq`, `sp2`, `tm`, `mf`, `bpy`
   - Create a `<ImplementationPrefix>Primitive` class (e.g., `CQPolyhedron`)
   - Handle edge cases (e.g., invalid inputs, degenerate geometry)
   - For complex nested structures, consider fallback source-level parsing in `scad2py.py`

6. **Validate B13D tests** — Run: `export PYTHONPATH=src && python3 src/b13d/test.py`
   - Confirm all backend API tests pass including the new primitive
   - Add a dedicated regression test method to `B13DTestMethods` in `./src/b13d/test.py`

## Phase 3: B13D Parts Integration (Optional)
7. **Create a part** (if appropriate) under `./src/b13d/parts/` that uses the primitive
8. **Add part tests** to `./src/b13d/test.py` and ensure they pass

## Phase 4: B1SCAD Parser Integration
9. **Update B1SCAD lexer** in `./src/b1scad/scad2ast.py`
   - Add `PRIMITIVE_NAME = r'primitive_name'` token to the `Lexer` class
   - Include it in the token list tuple

10. **Add parser rule** in `./src/b1scad/scad2py.py`
    - Implement `@_('PRIMITIVE_NAME LPAREN args RPAREN')` grammar rule
    - Return `self.api.primitive_name(args)` formatted call
    - **For complex arguments** (nested lists, expressions): Implement fallback source-level parsing to extract raw args

11. **Create sample SCAD model** under `./src/b1scad/scad/`
    - File pattern: `model<NN>.scad` (find next available N)
    - Test with both OpenSCAD and b1scad conversion
    - Ensure auto-generated Python model (e.g., `model<NN>.py`) is syntactically valid

12. **Validate B1SCAD tests** — Run: `export PYTHONPATH=src && python3 src/b1scad/test.py`
    - Confirm dynamic SCAD model discovery and conversion works
    - Verify generated Python models compile and execute

## Phase 5: Final Review
13. **Cross-verify all integration points**:
    - Core API method ✓
    - All backend implementations ✓
    - B13D API tests passing ✓
    - (Optional) Part tests passing ✓
    - B1SCAD lexer token + grammar rule ✓
    - Sample SCAD model and generated Python ✓
    - B1SCAD conversion tests passing ✓

## Troubleshooting
- **Parser fails on complex args**: Use fallback source-level regex extraction, not grammar rules
- **Backend-specific features**: Check existing code for conditional backend capabilities (e.g., fillet support)
- **Mesh validation**: Trimesh may need `process=True` or `.convex_hull` for invalid meshes