# Implementation Plan

Fix failing test cases in `src/b1scad/test.py` by correcting the OpenSCAD-to-Python parser in `src/b1scad/scad2py.py` so that generated Python code correctly calls the Shape API methods.

The test `test_all_scad` iterates through 19 `.scad` files in `src/b1scad/scad/`, converts each to Python via the SLY-based parser, generates STL output, and compares volumes against OpenSCAD-generated reference STLs. The test currently fails at model02 because the parser generates `.mv([5, 6, 7])` (passing a list) but the Shape API's `mv()` method expects three separate positional arguments `(x, y, z)`. Additionally, the parser has no grammar rule to connect named arguments (like `r = 10`) into the `args` production chain, causing models 12-16 to fail. All fixes are confined to `src/b1scad/scad2py.py`.

[Types]
No new types are needed.

The fix involves changing how vector values are passed to method calls in the generated Python code:
- `mv([x, y, z])` → `mv(x, y, z)` (unpack list with `*`)
- `scale([x, y, z])` → `scale(x, y, z)` (unpack list with `*`)
- `rotate([x, y, z])` → `rotate(x, y, z)` (remove extra wrapping brackets)

[Files]
Only one file needs modification: `src/b1scad/scad2py.py`.

No new files, no deleted files, no configuration changes.

[Functions]
Only the `OpenSCADParser` class in `src/b1scad/scad2py.py` needs modifications.

**Modified functions (grammar rules in OpenSCADParser):**

1. **`op` rule for `TRANSLATE`** (line ~41):
   - Current: `f"{p.shape_set}.mv({p.named_vector})"`
   - Change: `f"{p.shape_set}.mv(*{p.named_vector})"`
   - Effect: Unpacks `[5, 6, 7]` into `mv(5, 6, 7)`

2. **`op` rule for `ROTATE`** (line ~65):
   - Current: `f"{p.shape_set}.rotate([{p.named_vector}])"`
   - Change: `f"{p.shape_set}.rotate({p.named_vector})"`
   - Effect: Removes extra `[]` wrapping, generates `rotate([0, 90, 0])` instead of `rotate([[0, 90, 0]])`

3. **`op` rule for `SCALE`** (line ~69):
   - Current: `f"{p.shape_set}.scale({p.named_vector})"`
   - Change: `f"{p.shape_set}.scale(*{p.named_vector})"`
   - Effect: Unpacks `[0.5, 1, 2]` into `scale(0.5, 1, 2)`

4. **`args` grammar rule** (add new production after line ~149):
   - Add: `@_('arg')` → `def args(self, p): return p.arg`
   - Effect: Allows named arguments like `r = 10` to be parsed as `args`, enabling models 12-16 to work

[Classes]
No new classes. No removed classes.

**Modified class: `OpenSCADParser`** in `src/b1scad/scad2py.py`
- Three grammar rules modified (TRANSLATE, ROTATE, SCALE)
- One new grammar rule added (args → arg)

[Dependencies]
No dependency changes.

[Testing]
The existing test in `src/b1scad/test.py` (`test_all_scad`) is the test that needs to pass. After fixes, running `python3 -m unittest src/b1scad/test.py -v` should complete without failures for all 19 `.scad` models.

[Implementation Order]
Single step: Apply the four changes to `src/b1scad/scad2py.py` as described above, then run the test to verify.
