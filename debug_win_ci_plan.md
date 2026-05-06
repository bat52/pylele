# Implementation Plan — Debug Windows CI Workflow Failure

Fix the `test_win.yml` GitHub Actions pipeline that fails on Python 3.11 and 3.12 on `windows-latest` runners.

## Root Cause Summary

| Factor | Detail |
|--------|--------|
| **Failing step** | `pip install -r requirements.txt` (not `all_assembly.py`) |
| **Python versions** | 3.11 and 3.12 fail; 3.10 succeeds |
| **Conflict** | `nlopt==2.7.1` (pinned) ↔ `cadquery>=2.5.x → nlopt>=2.9.0` |
| **Why 3.10 works** | pip resolves older `cadquery-ocp` without strict `nlopt>=2.9.0` |
| **Why Ubuntu works** | Uses default (Manifold) backend, not cadquery |

**Note:** The Windows workflow runs `all_assembly.py` with `-i cq` (cadquery backend), while the Ubuntu workflow uses the default (Manifold) backend. This means the Windows pipeline must install and import cadquery+OCP dependencies, which is where the conflict surfaces.

### Why capping cadquery (not bumping nlopt) is the correct fix

- `nlopt>=2.9.0` requires `numpy>=2.0`, but `numpy` is pinned to `1.26.4` (required by other dependencies)
- `cadquery 2.4.x` requires just `nlopt` (no version constraint), so it works with `nlopt==2.7.1`
- `cadquery-ocp 7.7.2` has Windows wheels for cp310, cp311, cp312 and no numpy dependency
- Therefore: **cap cadquery at 2.4.0** to avoid the nlopt≥2.9→numpy≥2 conflict entirely

---

## [Changes]

### 1. `requirements.txt` — Cap `cadquery` at 2.4.0, keep `nlopt==2.7.1`

**Problem:** `cadquery<=2.5.2` allows cadquery 2.5.x, which requires `nlopt>=2.9.0`. But `nlopt>=2.9.0` requires `numpy>=2.0`, conflicting with pinned `numpy==1.26.4`.

**Fix:** Cap cadquery at 2.4.0 (which only requires unversioned `nlopt`) and keep `nlopt==2.7.1`.

- Old: `nlopt>=2.9.0,<3.0` + `cadquery<=2.5.2`
- New: `nlopt==2.7.1` + `cadquery<=2.4.0`

This avoids the nlopt≥2.9→numpy≥2 conflict entirely while keeping all other dependencies unchanged.

---

## [Files]

| File | Action | Description |
|------|--------|-------------|
| `requirements.txt` | MODIFY | Cap `cadquery<=2.4.0`, revert `nlopt==2.7.1` |

---

## [Functions]

No functions to modify. Only dependency version changes in `requirements.txt`.

---

## [Testing]

### Verification Steps

1. **Merge the fix** (the requirements.txt change) into the main branch.
2. **Verify CI passes** for all three Python versions (3.10, 3.11, 3.12) on `windows-latest`:
   - https://github.com/bat52/pylele/actions
3. **Confirm Ubuntu workflow** is unaffected (should still pass).
4. **Optional:** Locally test `pip install -r requirements.txt` succeeds with Python 3.11 and 3.12 on Windows to validate the fix.

### Expected Outcome

- Python 3.10: ✅ Already passes, should continue to pass.
- Python 3.11: ✅ Should now pass (was failing due to nlopt conflict).
- Python 3.12: ✅ Should now pass (was failing due to nlopt conflict).

---

## [Implementation Order]

1. **Edit `requirements.txt`** — Change `nlopt>=2.9.0,<3.0` to `nlopt==2.7.1` and `cadquery<=2.5.2` to `cadquery<=2.4.0`.
2. **Commit and push** to trigger CI.
3. **Monitor** the GitHub Actions run to verify all jobs pass.
