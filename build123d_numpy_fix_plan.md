# Implementation Plan

[Overview]
Resolve the numpy version conflict in requirements_b123d.txt where the pinned numpy==1.26.4 is incompatible with build123d==0.10.0's requirement of numpy>=2,<3.

requirements_b123d.txt is the dependency file for the build123d backend. It pins numpy==1.26.4 (1.x series) but build123d==0.10.0 requires numpy>=2,<3 (2.x series). The other dependencies (nlopt==2.7.1 with numpy>=1.18.5, trimesh==4.4.8 with numpy>=1.20) have lower bounds satisfied by both 1.x and 2.x numpy, so they don't constrain the upper bound. The codebase already has a compatibility shim (np.bool8 = np.bool_ in resonance.py) for numpy 2.x removed APIs. requirements.txt (the non-build123d requirements file) is NOT to be modified.

[Types]
No type system changes — this is purely a dependency version constraint change.

[Files]
Single file content change: requirements_b123d.txt.

- `requirements_b123d.txt` (existing): Change line 1 from `numpy==1.26.4` to `numpy>=2,<3`
- No new files created, no files deleted.

[Functions]
No function modifications.

[Classes]
No class modifications.

[Dependencies]
One dependency version constraint change.

- numpy: `==1.26.4` → `>=2,<3` in requirements_b123d.txt
- All other dependencies remain unchanged (nlopt==2.7.1, trimesh==4.4.8, build123d==0.10.0, etc.)

[Testing]
No new tests required. After the change, pip install -r requirements_b123d.txt should resolve successfully without version conflicts.

[Implementation Order]
A single-line edit to requirements_b123d.txt.
