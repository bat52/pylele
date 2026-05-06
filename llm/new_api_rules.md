# LLM Rules for New API Implementation

## 1. Always run full regression tests after backend changes

When implementing or fixing a backend (bd.py, mf.py, cq.py, sp2.py, etc.), do NOT stop after testing the API-specific test (`python3 src/b13d/api/<api>.py`). You **must** also run the full b13d regression test suite:

```bash
python3 -m pytest src/b13d/test.py -v -k test_<api>_api  # example for bd
# or run all API tests:
python3 src/b13d/test.py B13DTestMethods.test_<api>_api
```

The full test suite (`src/b13d/test.py`) covers not just `test_api()` but also parts-level tests:
- `test_tube`, `test_screw`, `test_screw_holder`, `test_import3d`
- `test_scad_example`, `test_rounded_box`, `test_rounded_rectangle`
- `test_rounded_face_rectangle`, `test_torus`
- `test_polyhedron_api`
- `test_zz_report` (generates JSON reports with volume/bbox metrics)

Parts tests exercise the `Solid` class helper methods (`join`, `cut`, `mirror`, `mv`, `rotate`, `scale`, `hull`, `fillet`) which are not all covered by the basic `test_api`. A backend bug in these operations will only be caught by the parts tests.

## 2. Optimize test order for token efficiency

When validating a backend change, run tests in this order to catch failures early and minimize iteration cost:

1. **First**: Run the single backend's API test with trimesh validation:
   ```bash
   python3 src/b13d/api/<api>.py
   ```
   This is fast and catches basic geometry issues (wrong volume, not watertight, wrong bbox).

2. **Second**: Run the parts-level tests for that backend:
   ```bash
   python3 src/b13d/test.py B13DTestMethods.test_<part>_<api>
   ```
   Parts tests exercise `Solid` helper methods (join/cut/mirror/rotate etc.) via the `MockShape` → compare approach. A failure here indicates a bug in the `Solid` helper implementation (e.g., `dup()`, `mirror()`, `cut()`).

3. **Third**: Run all API tests together (cross-backend consistency check):
   ```bash
   python3 -m pytest src/b13d/test.py -v -k "test_mock_api or test_cadquery_api or test_manifold_api or test_build123d_api"
   ```
   This confirms the fix doesn't break other backends.

4. **Finally**: Generate the full report:
   ```bash
   python3 src/b13d/test.py B13DTestMethods.test_zz_report
   ```

This ordering catches the most likely failures first, reducing token waste from running long tests that will be invalidated by earlier failures.

## 3. Use trimesh validation for STL output

All backend API tests in `core.py` (`ShapeAPI.test()`) should include trimesh-based validation after `export_stl()`:
- Check `mesh.is_watertight`
- Check `mesh.volume > 0` and within expected range
- Check bounding box spans are reasonable

This catches geometric regressions (like wrong revolve axis, flipped coordinates, missing faces) before they propagate to parts-level tests.

## 4. Cross-reference with reference backends

When a backend produces unexpected output, compare against:
- `cq.py` (CadQuery) — the most mature backend, considered reference
- `mf.py` (Manifold) — reliable, uses manifold3d library
- `sp2.py` (SolidPython2) — another mature reference

If CQ, MF, and SP2 agree on a result, the new backend is likely wrong.
If only one backend disagrees, the bug is in that backend.

## 5. Update README.md with new Api Implementation description

Mention quickly the new api.

## 6. Make sure pip dependencies do not conflict with the exising configuration

Validate the consistency of requirements.txt and setup.py.
If it is not possible to resolve the conflicts, make the new backend optional in setup.py, and create a new requirements_<api>.txt that should be free of conflict by removing other optional backends.

Compute a compatibility matrix of the existing apis based on the dependency tree, and document in README.md .

## 7. update git workflow test.yml to enable testing of the new api

If the new api is incompatible with some of the others, test in isolation by resetting the enviromment, or creating a new test_<api>.yml
