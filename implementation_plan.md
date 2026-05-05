# Implementation Plan

Fix Minkowski sum parsing and rendering for model27.scad by making it a true binary Minkowski sum operation end-to-end.

The `minkowski() { cube(10); sphere(r=2); }` construct in OpenSCAD computes the Minkowski sum of two (or more) shapes — the set of all points that are sums of points from each shape. Currently, the b1scad pipeline (a) generates `.minkowski()` as a unary method call on the union of operands, and (b) the Manifold API's `.minkowski()` raises `NotImplementedError`. This fix changes both the code generation (to chain binary `.minkowski(other)` calls) and the API (implementing MFShape's method using `manifold3d.Manifold.minkowski_sum()`). Other API backends (TM, CQ, SP2, Blender) fall back to hull as a best-effort approximation.

[Types]
Change the `Shape.minkowski()` method signature from unary to optionally binary.

Detailed specifications:

1. **`Shape.minkowski(self, other: Shape = None) -> Shape`** (core.py):
   - Currently: `def minkowski(self) -> Shape` — unary, conceptually wrong.
   - New: `def minkowski(self, other: Shape = None) -> Shape` — binary by default.
   - Raises `NotImplementedError` on base class; overridden in each backend.
   - When `other is None`, return `self` unchanged (identity for degenerate single-operand case).

2. **`Minkowski` AST node** (ast_nodes.py):
   - Unchanged structure: `operands: List[ASTNode]` — already correct.
   - Usage: 2+ operands chain into `.minkowski(A).minkowski(B)...` calls.

3. **`MFShape.minkowski(self, other=None) -> MFShape`** (api/mf.py):
   - When `other is not None`: use `self.solid.minkowski_sum(other.solid)` from manifold3d.
   - When `other is None`: return self.
   - Handle cross-section (2D) case by converting to 3D first.

4. **`TMShape.minkowski(self, other=None) -> TMShape`** (api/tm.py):
   - Falls back to `self.hull()` — trimesh lacks Minkowski sum.

5. **`Sp2Shape.minkowski(self, other=None) -> Sp2Shape`** (api/sp2.py):
   - Falls back to `self.hull()` — solid2 lacks Minkowski sum.

6. **`CQShape.minkowski(self, other=None) -> CQShape`** (api/cq.py):
   - Falls back to `self.hull()` — cadquery lacks Minkowski sum.

7. **`BlenderShape.minkowski(self, other=None) -> BlenderShape`** (api/bpy.py):
   - Falls back to `self.hull()` — bpy lacks Minkowski sum.

8. **`MockShape.minkowski(self, other=None) -> MockShape`** (api/mock.py):
   - Return self (no-op, as before).

[Files]
Modify 6 files; no new files, no deletions.

Detailed breakdown:

1. **`/home/marco/programming/pylele/src/b1scad/scad2py.py`** — MODIFY
   - Rewrite `AstToPython.visit_Minkowski` (line 1427-1429):
     - Old: `body = " + ".join(self.visit(op) for op in node.operands)` then `f"({body}).minkowski()"`
     - New: chain `.minkowski(other)` for each operand after the first.

2. **`/home/marco/programming/pylele/src/b13d/api/core.py`** — MODIFY
   - Change `Shape.minkowski` signature (line 404-405):
     - Old: `def minkowski(self) -> Shape:`
     - New: `def minkowski(self, other: Shape = None) -> Shape:`

3. **`/home/marco/programming/pylele/src/b13d/api/mf.py`** — MODIFY
   - Rewrite `MFShape.minkowski` to implement actual Minkowski sum using manifold3d.

4. **`/home/marco/programming/pylele/src/b13d/api/tm.py`** — MODIFY
   - Update `TMShape.minkowski` signature and impl.

5. **`/home/marco/programming/pylele/src/b13d/api/sp2.py`** — MODIFY
   - Update `Sp2Shape.minkowski` signature.

6. **`/home/marco/programming/pylele/src/b13d/api/cq.py`** — MODIFY
   - Update `CQShape.minkowski` signature.

7. **`/home/marco/programming/pylele/src/b13d/api/bpy.py`** — MODIFY
   - Update `BlenderShape.minkowski` signature.

8. **`/home/marco/programming/pylele/src/b13d/api/mock.py`** — MODIFY
   - Update `MockShape.minkowski` signature.

[Functions]
Modify 7 functions; no new or removed functions.

Detailed breakdown:

1. **`AstToPython.visit_Minkowski`** — scad2py.py:1427
   - Old: generates `(A + B).minkowski()` — union-then-minkowski (wrong).
   - New: generates `A.minkowski(B)` for 2 operands, `A.minkowski(B).minkowski(C)` for 3+.
   - Edge case: single operand generates just `A` (no minkowski call).

2. **`Shape.minkowski`** — core.py:404
   - Old: `def minkowski(self) -> Shape:`
   - New: `def minkowski(self, other: Shape = None) -> Shape:`
   - Error message unchanged.

3. **`MFShape.minkowski`** — mf.py (around line 265)
   - Old: `raise NotImplementedError("minkowski not fully implemented for MFShape")`
   - New: Use `self.solid.minkowski_sum(other.solid)` when `other` is provided.
   - Implementation:
     ```python
     def minkowski(self, other=None) -> MFShape:
         if self.cross_section is not None:
             self._ensure3d()
         if other is not None:
             if other.cross_section is not None:
                 other = other.dup()
                 other._ensure3d()
             self.solid = self.solid.minkowski_sum(other.solid)
         return self
     ```

4. **`TMShape.minkowski`** — tm.py (around line 373)
   - Old: `def minkowski(self) -> TMShape: self.hull()`
   - New: `def minkowski(self, other=None) -> TMShape: return self.hull() if other is not None else self`

5. **`Sp2Shape.minkowski`** — sp2.py (around line 142)
   - Old: unary, falls back to hull.
   - New: binary signature, falls back to hull when `other is not None`.
   - Also propagate to backup_solid.

6. **`CQShape.minkowski`** — cq.py (around line 198)
   - Old: unary, falls back to hull.
   - New: binary signature, falls back to hull.

7. **`BlenderShape.minkowski`** — bpy.py (around line 406)
   - Old: unary, falls back to hull.
   - New: binary signature, falls back to hull.

8. **`MockShape.minkowski`** — mock.py:171
   - Old: `def minkowski(self) -> MockShape: return self`
   - New: `def minkowski(self, other=None) -> MockShape: return self`

[Classes]
No new classes. No removed classes. No class hierarchy changes.

[Dependencies]
No new dependencies. `manifold3d` package (manifold3d) is already a dependency and its `Manifold.minkowski_sum()` method will be used.

[Testing]
Run `test_all_scad` from `test.py` to verify model27.scad generates correctly.

Verification steps:
1. Run `python3 src/b1scad/test.py` and confirm model27.scad passes (volume match with OpenSCAD reference).
2. The generated `model27.py` should contain `.minkowski(` calls instead of `.minkowski()` calls.
3. The Manifold backend should produce a mesh with volume matching the OpenSCAD reference.

[Implementation Order]
Implement changes from bottom-up (API first, then code generation, then test).

1. Modify `Shape.minkowski` in `core.py` — change signature to binary.
2. Implement `MFShape.minkowski` in `mf.py` — use manifold3d `minkowski_sum`.
3. Update `MockShape.minkowski` in `mock.py` — match new signature.
4. Update `TMShape.minkowski` in `tm.py` — match new signature.
5. Update `CQShape.minkowski` in `cq.py` — match new signature.
6. Update `Sp2Shape.minkowski` in `sp2.py` — match new signature.
7. Update `BlenderShape.minkowski` in `bpy.py` — match new signature.
8. Rewrite `visit_Minkowski` in `scad2py.py` — generate binary `.minkowski(other)` calls.
9. Run test to validate.
