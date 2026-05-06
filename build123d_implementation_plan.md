# build123d Backend Implementation Plan

## Overview

Create a new `b13d` backend based on the **build123d** library (`b13d.api.bd`). Build123d is a Python-native parametric 3D CAD library that provides modern, Pythonic API with native boolean operations, fillet, hull, and excellent STL/STEP export.

## Implementation Cost Estimate (LLM tokens)

| Phase | Description | Est. Tokens |
|-------|-------------|-------------|
| P1 | Create `bd.py` core implementation (~750 LOC) | 10,000 |
| P2 | Register in `core.py` (enum + APIS_INFO) | 200 |
| P3 | Register in `__init__.py` | 50 |
| P4 | Add test method to `test.py` | 200 |
| P5 | Add dependency to `requirements.txt` + `setup.py` | 100 |
| **Total** | | **~10,550 tokens** |

> **Note**: Token estimates assume a single-pass implementation. Debugging, testing, and CI issues could add 2,000-5,000 additional tokens.

## Files to Modify

| File | Change Type | Est. Lines Changed |
|------|-------------|-------------------|
| `src/b13d/api/bd.py` | **CREATE** | ~750 lines |
| `src/b13d/api/core.py` | EDIT (+enum, +APIS_INFO, +supported_apis) | ~10 lines |
| `src/b13d/api/__init__.py` | EDIT (+"bd" in __all__) | 1 line |
| `src/b13d/test.py` | EDIT (+test method) | ~6 lines |
| `requirements.txt` | EDIT (+build123d) | 1 line |
| `setup.py` | EDIT (+build123d) | 1 line |

## Step-by-Step Plan

### Step 1: Register `Implementation.BUILD123D` in `core.py`

```python
class Implementation(StringEnum):
    MOCK = "mock"
    CADQUERY = "cq"
    BLENDER = "bpy"
    TRIMESH = "tm"
    SOLID2 = "sp2"
    MANIFOLD = "mf"
    BUILD123D = "bd"  # NEW
```

Add to `APIS_INFO`:
```python
Implementation.BUILD123D: {"module": "b13d.api.bd", "class": "BDShapeAPI", "fillet": True, "hull": True},
```

Add to `supported_apis()`:
```python
apis = [..., Implementation.MANIFOLD, Implementation.BUILD123D]
```

### Step 2: Create `src/b13d/api/bd.py`

Following the pattern of `mf.py` (the reference modern backend).

#### `BDShapeAPI(ShapeAPI)` — Factory Methods

| Method | Implementation | Notes |
|--------|---------------|-------|
| `sphere(r)` | `bd.Sphere(r)` | |
| `box(l, w, h, center)` | `bd.Box(l, w, h)` | Apply center translation if needed |
| `cone_x/y/z(h, r1, r2)` | `bd.Cone(r_bottom=r1, r_top=r2, h)` + rotation | |
| `cylinder_x/y/z(l, rad)` | `bd.Cylinder(rad, l)` + rotation | |
| `regpoly_extrusion_x/y/z(l, rad, sides)` | Regular polygon `bd.Polygon` → `bd.extrude()` + rotation | |
| `polygon_extrusion(path, ht)` | `bd.extrude(bd.Polygon(path), ht)` | |
| `spline_extrusion(start, path, ht)` | `lineSplineXY()` → polygon → extrude | Reuse utility from utils.py |
| `spline_revolve(start, path, deg)` | Points → polygon → `bd.revolve()` | |
| `regpoly_sweep(rad, path)` | Sweep sphere segments via hull | Same pattern as mf.py |
| `text(txt, fontSize, tck, font)` | fonttools → `textToGlyphsPaths` → extrude | Reuse utility from utils.py |
| `polyhedron(points, faces)` | `bd.Polyhedron(points, faces)` | Build123d native support |
| `rectangle(size)` | `bd.Rectangle(w, h)` | 2D shape |
| `circle(r)` | `bd.Circle(r)` | 2D shape |
| `polygon(points)` | `bd.Polygon(points)` | 2D shape |
| `export_stl(shape, path)` | `bd.export_stl(shape.solid, path)` | |
| `export_best(shape, path)` | Reuse `export_stl` | |
| `export(shape, path, fmt)` | Reuse `export_stl` | |

#### `BDShape(Shape)` — Operations

| Method | Implementation | Notes |
|--------|---------------|-------|
| `cut(cutter)` | `self.solid = self.solid - cutter.solid` | Native `-` operator |
| `join(joiner)` | `self.solid = self.solid + joiner.solid` | Native `+` operator |
| `intersection(intersector)` | `self.solid = self.solid * intersector.solid` | Native `*` operator |
| `mirror(normal)` | Use negative scale on relevant axis | Or `bd.mirror()` on plane |
| `mv(x, y, z)` | `bd.Pos(x, y, z) * self.solid` | Native location |
| `rotate_x/y/z(ang)` | `bd.Rotation(ang, 0, 0) * self.solid` | Native rotation |
| `scale(x, y, z)` | `bd.scale(self.solid, (x, y, z))` | Or compound `bd.Location` |
| `bbox()` | `self.solid.bounding_box()` → extract 6-tuple | Map build123d bbox format |
| `fillet(nearestPts, rad)` | `self.solid.fillet(rad, edge_selector)` | Build123d has excellent fillet |
| `hull()` | `bd.Part.convex_hull(...)` or hull_points | If multiple parts, join then hull |
| `linear_extrude(...)` | `bd.extrude(cross_section, height)` | If 2D shape |
| `rotate_extrude(angle)` | `bd.revolve(cross_section, angle)` | If 2D shape |
| `offset(r)` | `bd.offset_2d(cross_section, r)` | If 2D shape |
| `projection(cut)` | Project to XY plane → 2D sketch | |
| `minkowski(other)` | `minkowski_sum()` if available | |
| `dup()` | `copy.deepcopy(self)` | |

#### Named Geometry Classes (following convention)

Following `mf.py` pattern: `BDBall`, `BDBox`, `BDRodZ`, `BDConeZ`, `BDPolyExtrusionZ`, `BDLineSplineExtrusionZ`, `BDLineSplineRevolveX`, `BDCirclePolySweep`, `BDTextZ`, `BDPolyhedron`.

#### 2D/3D Dual Representation

Following `mf.py`'s pattern: use a `cross_section` attribute for 2D shapes (`bd.Sketch` or `bd.Part` with 2D geometry). Convert to 3D automatically when a 3D operation is required.

### Step 3: Register in `src/b13d/api/__init__.py`

Add `"bd"` to `__all__` list.

### Step 4: Add Test in `src/b13d/test.py`

```python
def test_build123d_api(self):
    """Test Build123D API"""
    test_api(api=Implementation.BUILD123D)
```

### Step 5: Add Dependency

**`requirements.txt`:**
```
build123d>=0.6.0
```

**`setup.py`:**
```python
"build123d>=0.6.0",
```

## Key Design Decisions

1. **2D/3D split**: Build123d has first-class 2D support (Sketch/Plane-based). Follow mf.py's cross_section attribute pattern.
2. **fillet=True, hull=True**: Build123d supports both natively.
3. **Build123d tolerance**: Should match well with existing join tolerance (0.02 for non-CQ backends).
4. **Native operators**: Build123d uses `+`, `-`, `*` for boolean ops, mapping directly to our API.
5. **Export**: Build123d exports STL via `export_stl()`.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Build123d API differences from expected | Design implementation to isolate build123d specifics in named classes |
| 2D→3D conversion edge cases | Follow mf.py's proven `_ensure3d()` pattern |
| Fillet edge selection | Build123d supports vertex-based edge selection for fillet |
| Bounding box format mismatch | Add adapter to convert build123d bbox → 6-tuple (minX, maxX, minY, maxY, minZ, maxZ) |
