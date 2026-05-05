# Implementation Plan

[Overview]
Add missing semicolon to model24.scad to fix parsing/rendering in the b1scad test pipeline.

The SCAD file `src/b1scad/scad/model24.scad` contains an `include` directive missing its terminating semicolon. The parser grammar in `scad2py.py` requires a semicolon after `INCLUDE STRING` tokens, so without it the parse returns `None`, causing an `AttributeError` in `resolve_includes()` when the test in `test.py` iterates all `.scad` files. The fix is a single-character addition to the SCAD source file.

[Types]
No type system changes required.

[Files]
No new files. One existing file modified.

**Modified files:**
- `src/b1scad/scad/model24.scad` — add missing semicolon on line 2

[Functions]
No function modifications.

[Classes]
No class modifications.

[Dependencies]
No dependency changes.

[Testing]
The existing test `test_all_scad` in `src/b1scad/test.py` iterates all `.scad` files and already covers this case. Once the fix is applied, the test should pass for model24.

[Implementation Order]
Single step: add semicolon to `include <model00.scad>` on line 2 of `src/b1scad/scad/model24.scad`.
