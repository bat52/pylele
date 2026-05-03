# Implementation Plan: Integrated 3D Visualization for b13d

## 1. Overview

Add an interactive 3D visualization capability to the b13d library, working at both the **Shape** level (low-level `Shape.show()`) and the **Solid** level (high-level assembly `Solid.show()`). The viewer should support:

- Interactive inspection (rotate, zoom, pan)
- Colored multi-part assemblies
- Integration into the existing CLI workflow
- Desktop viewer mode (trimesh/pyglet window)
- Jupyter notebook inline viewer
- Optional web-based GLB viewer

## 2. Types

### New Types

| Type | File | Description |
|------|------|-------------|
| `ViewerMode(StringEnum)` | `b13d/api/viewer.py` | Enum: `DESKTOP` (native window), `JUPYTER` (inline), `WEB` (GLB file + serve) |
| `NoOpShape` | `b13d/api/viewer.py` | Null shape for backends without show support, returns no-op |

### Modified Types

| Type | File | Change |
|------|------|-------------|
| `Shape.show()` | `b13d/api/core.py` | Add default implementation using GLB export + trimesh Scene.show() |
| `Solid.show()` | `b13d/api/solid.py` | New method to show the generated solid assembly |
| `Solid.configure()` | `b13d/api/solid.py` | Add `--show` viewer flag to CLI |
| `TMShape.show()` | `b13d/api/tm.py` | Override with direct trimesh Scene.show() |
| `main_maker()` | `b13d/api/solid.py` | Add `--show` flag support to skip export and show instead |

## 3. Files

### New Files

| File | Purpose |
|------|---------|
| `src/b13d/api/viewer.py` | Viewer module: ViewerMode enum, viewer functions (desktop, jupyter, web), NoOpShape |
| `src/b13d/api/viewer_html.py` | HTML template for Jupyter inline viewer and web viewer |

### Modified Files

| File | Changes |
|------|---------|
| `src/b13d/api/core.py` | Add import of render_to_scene; update `Shape.show()` to use trimesh Scene for all backends |
| `src/b13d/api/solid.py` | Add `--show` CLI flag; add `Solid.show()` method; update `main_maker()` to support view mode |
| `src/b13d/api/tm.py` | Override `TMShape.show()` with direct `tm.Scene([mesh]).show()` call |
| `src/b13d/api/mock.py` | Update `MockShape.show()` to be a no-op |
| `src/b13d/api/bpy.py` | Keep existing Blender show() — no change needed |
| `setup.py` | Add `b13d-show` console_scripts entry point |
| `requirements.txt` | Add `pyglet<2` if not already present (already exists), add `ipython` for Jupyter |
| `COLLECTION.md` | Add visualization tools section |

## 4. Functions

### New Functions in `viewer.py`

| Function | Signature | Description |
|----------|-----------|-------------|
| `view_shape_desktop(shape, title, parts)` | `(Shape, str, list[Shape]) -> None` | Open interactive 3D desktop window using trimesh Scene + pyglet |
| `view_shape_jupyter(shape, title, parts)` | `(Shape, str, list[Shape]) -> None` | Display inline 3D viewer in Jupyter notebook via GLB + trimesh-ipyvolume or custom HTML |
| `view_shape_web(shape, title, parts, out_dir)` | `(Shape, str, list[Shape], str) -> str` | Export GLB and generate standalone HTML viewer; returns URL/path |
| `export_to_scene(shape, parts)` | `(Shape, list[Shape]) -> trimesh.Scene` | Convert a Shape (with optional colored parts) into a trimesh Scene. Handles color assignment. If shape is TMShape, use directly; otherwise convert via STL reimport |
| `convert_shape_to_trimesh(shape)` | `(Shape) -> trimesh.Trimesh` | Export shape to STL in temp dir, reimport with trimesh. Used for backends that don't have native trimesh (CQ, SP2, MF) |
| `clip_alpha(rgb)` | `(tuple[int,int,int]) -> str` | Convert b13d color enum to CSS hex string for web viewer |

### Modified Functions in `core.py`

| Function | Change |
|----------|--------|
| `Shape.show()` | Retain as entry point. Default: export shape as GLB/STL → convert to trimesh → call `view_shape_desktop()`. Print warning for backends without native show |

### Modified Functions in `solid.py`

| Function | Change |
|----------|--------|
| `lele_solid_parser()` | Add `--show` / `-sh` flag (store_true), add `--viewer_mode` / `-vm` option (choices: desktop/jupyter/web) |
| `Solid.show()` | New method: generate full shape → collect parts → call `view_shape_desktop()` with full assembly |
| `Solid.gen_full()` | Return `self` for chaining (already returns shape, but also return self for show chaining) |
| `main_maker()` | After STL export, check `--show` flag: if set, call `solid.show()` instead of (or after) export. Add support for `--view` flag |

## 5. Classes

### New Class: `NoOpShape` (in `viewer.py`)

```python
class NoOpShape:
    """A null shape that does nothing. Used as fallback for backends without show()."""
    def __init__(self, msg="show() not supported"):
        self.msg = msg
    def __getattr__(self, name):
        return lambda *a, **kw: self
    def __repr__(self):
        return f"<NoOpShape: {self.msg}>"
```

### Modified Class: `Shape` (in `core.py`)

```python
# Updated show() method:
def show(self, viewer_mode: str = "desktop", title: str = None):
    """
    Display the shape in an interactive 3D viewer.
    
    Args:
        viewer_mode: "desktop" (native window), "jupyter" (inline), or "web" (HTML file)
        title: Window/title name (defaults to self.name)
    """
    if title is None:
        title = self.name or f"b13d Shape ({self.api.implementation.value})"
    
    from b13d.api.viewer import view_shape_desktop, view_shape_jupyter, view_shape_web
    
    parts = [self]
    
    if viewer_mode == "desktop":
        view_shape_desktop(self, title, parts)
    elif viewer_mode == "jupyter":
        view_shape_jupyter(self, title, parts)
    elif viewer_mode == "web":
        return view_shape_web(self, title, parts)
    else:
        print(f"Warning! Unknown viewer_mode '{viewer_mode}' for {self.api.implementation} api!")
```

### Modified Class: `TMShape` (in `tm.py`)

```python
# Override show() with direct trimesh scene viewer
def show(self, viewer_mode: str = "desktop", title: str = None):
    """Show using trimesh's built-in Scene.show() (pyglet window)"""
    if title is None:
        title = self.name or "Trimesh Shape"
    
    if viewer_mode == "desktop":
        scene = tm.Scene()
        scene.add_geometry(self.solid, node_name=title)
        scene.show()
    else:
        # Fallback to default implementation for other modes
        super().show(viewer_mode=viewer_mode, title=title)
```

### Modified Class: `Solid` (in `solid.py`)

```python
def show(self, viewer_mode: str = "desktop"):
    """Display the solid assembly in an interactive 3D viewer."""
    self.gen_full()
    
    # Collect parts with their shapes
    parts_shapes = [self.shape]
    if self.has_parts():
        for part in self.parts:
            if isinstance(part, Solid):
                part.gen_full()
                if part.has_shape():
                    parts_shapes.append(part.shape)
    
    from b13d.api.viewer import view_shape_desktop, view_shape_jupyter, view_shape_web
    
    title = self.fileNameBase
    
    if viewer_mode == "desktop":
        view_shape_desktop(self.shape, title, parts_shapes)
    elif viewer_mode == "jupyter":
        view_shape_jupyter(self.shape, title, parts_shapes)
    elif viewer_mode == "web":
        return view_shape_web(self.shape, title, parts_shapes)
```

## 6. Dependencies

### New Dependencies

| Package | Version | Purpose | Install |
|---------|---------|---------|---------|
| `ipython` | latest (already available) | Jupyter integration for `display()` of GLB | Already installed in typical dev env |
| `ipywidgets` | optional | Interactive widgets in Jupyter | Optional |
| `ipyvolume` | optional | 3D volume rendering in Jupyter | Optional |

Already satisfied dependencies:
- `pyglet<2`: Already in `requirements.txt` (used by trimesh for Scene.show())
- `trimesh==4.4.8`: Already in `requirements.txt`
- `manifold3d`: Already in `requirements.txt`

### No New Hard Dependencies

The core viewer implementation uses **trimesh** which is already a hard dependency of b13d. The Jupyter/web modes are optional and gracefully degrade.

## 7. Testing

### New Test File

`src/b13d/test_viewer.py`

### Test Cases

| Test | Description | Expected Result |
|------|-------------|-----------------|
| `test_viewer_imports` | Verify viewer module imports cleanly | No import errors |
| `test_export_to_scene_tm` | Export TMShape to trimesh Scene | Valid trimesh Scene with geometry |
| `test_export_to_scene_mf` | Convert MFShape → STL → trimesh → Scene | Valid trimesh Scene with geometry |
| `test_export_to_scene_colors` | Scene preserves assigned colors | Colors present in scene geometry |
| `test_export_to_scene_multipart` | Scene includes all assembly parts | Scene has multiple geometries |
| `test_shape_show_desktop` | Call Shape.show() with desktop mode (headless) | No crash, returns None |
| `test_solid_show` | Call Solid.show() for a simple solid | No crash, returns None |
| `test_shape_show_noop` | Backends without native show use fallback | Warning printed, no crash |
| `test_viewer_no_display` | Viewer handles missing display (headless/server) | Graceful fallback, no crash |
| `test_cli_show_flag` | CLI `--show` flag triggers viewer | Viewer invoked, export skipped if flagged |
| `test_web_viewer_export` | Web mode generates HTML file | HTML file exists in output dir |

### Testing Strategy

1. **Unit tests**: Run in headless mode with `pyglet` window creation disabled (use `DISPLAY=` or mock)
2. **Headless CI**: Verify viewer code paths without opening actual windows
3. **Manual visual tests**: Documented procedure for developers to verify visual output
4. **Volume integrity**: Ensure Shape.show() does not modify the shape (volume preserved)

### Test Framework Integration

- Add tests to `src/b13d/test.py` or create `src/b13d/test_viewer.py`
- Tests should work with `python -m pytest src/b13d/test_viewer.py`
- Integration with existing `test_loop()` pattern

## 8. Implementation Order

### Phase 1: Core Viewer Module (`viewer.py`)

**Step 1**: Create `src/b13d/api/viewer.py`
- Define `ViewerMode` enum
- Implement `convert_shape_to_trimesh()` — export to temp STL, reimport with trimesh
- Implement `export_to_scene()` — build trimesh Scene with colored parts
- Implement `view_shape_desktop()` — use `trimesh.Scene.show()` (pyglet)
- Implement `view_shape_jupyter()` — export GLB → display in notebook
- Implement `view_shape_web()` — export GLB + generate standalone HTML

**Step 2**: Create `src/b13d/api/viewer_html.py`
- Minimal HTML template with embedded GLB viewer (using `<model-viewer>` or three.js)
- For Jupyter: use `IPython.display.HTML` and trimesh's `scene.show()` detection

### Phase 2: Shape-Level Integration

**Step 3**: Update `Shape.show()` in `core.py`
- Import viewer module
- Add default implementation that converts to trimesh and calls viewer
- Keep backward compatibility

**Step 4**: Update `TMShape.show()` in `tm.py`
- Override with direct `tm.Scene.show()` for best performance
- Handle multi-geometry scenes

**Step 5**: Update `MockShape.show()` in `mock.py`
- Simple no-op with info message

### Phase 3: Solid-Level Integration

**Step 6**: Update `Solid` class in `solid.py`
- Add `--show`/`-sh` and `--viewer_mode`/`-vm` flags to `lele_solid_parser()`
- Implement `Solid.show()` method that generates full assembly and calls viewer
- Update `main_maker()` to support `--show` flag (skip export, show instead)

**Step 7**: Update `setup.py`
- Add `b13d-show` console_scripts entry point for standalone viewer command

### Phase 4: Testing & Polish

**Step 8**: Create tests in `src/b13d/test_viewer.py`
- Unit tests for viewer module functions
- Headless mode testing
- Integration test for CLI `--show` flag

**Step 9**: Documentation
- Update `COLLECTION.md` with visualization tools section
- Add docstrings to all new functions
- Document usage patterns

### Phase 5: Advanced Features (Future)

**Step 10** (Future): Web-based viewer with live reload
- Watch file changes and auto-refresh viewer
- Integration with VSCode extension

**Step 11** (Future): Jupyter widget with controls
- Support for toggling parts visibility
- Section/slice controls
- Measurement tools

## 9. Key Design Decisions

### 9.1 Trimesh as Primary Visualization Backend

**Decision**: Use trimesh as the core visualization engine for all backends.

**Rationale**:
- Trimesh is already a hard dependency
- `trimesh.Scene.show()` provides a pyglet-based interactive 3D window
- All backends can export to trimesh via STL (universal format)
- CadQuery, SolidPython2, Manifold can all be converted to trimesh meshes

### 9.2 Conversion Pipeline for Non-Trimesh Backends

```
[CQ Shape] → STL export → trimesh.load_mesh() → trimesh.Trimesh → trimesh.Scene → show()
[SP2 Shape] → backup_api (Manifold) → STL → trimesh
[MF Shape] → .to_mesh() → numpy arrays → trimesh.Trimesh
[BPY Shape] → bpy export → STL → trimesh  (or use native Blender viewport)
[TM Shape] → direct trimesh.Scene.show()
```

### 9.3 Color Handling

- Colors are stored per-Shape as `self.color` (ColorEnum tuple)
- When building a trimesh Scene, each mesh gets its face_colors set
- For backends supporting set_color (TM, SP2), use existing colors
- For backends without set_color (CQ, BPY, MF), assign colors when building the Scene

### 9.4 Viewer Modes

| Mode | Implementation | Use Case |
|------|---------------|----------|
| `desktop` | `tm.Scene.show()` with pyglet window | Interactive design iteration |
| `jupyter` | GLB + `IPython.display()` + `ipyvolume` or HTML | Notebook-based workflows |
| `web` | GLB file + standalone HTML with `<model-viewer>` tag | Sharing designs, documentation |

### 9.5 Headless/Server Fallback

When running in headless mode (no display server), the viewer should:
1. Detect missing display (check `os.environ.get('DISPLAY')` or catch pyglet errors)
2. Fall back to web mode (generate HTML file)
3. Print a helpful message with the file path

## 10. Usage Examples

### CLI Usage (After Implementation)

```bash
# Show generated model in desktop viewer (skip STL export)
pylele2 -i manifold -sh

# Show with specific viewer mode
pylele2 -i trimesh --viewer_mode desktop

# Show then also export STL
pylele2 -i trimesh -sh -o ./build

# Web viewer mode (generates HTML file)
pylele2 -i manifold --viewer_mode web

# Standalone viewer command
b13d-show ./output/file.glb
```

### Python API Usage

```python
from b13d.api.core import Implementation, Fidelity

api = Implementation.TRIMESH.get_api(Fidelity.MEDIUM)

# Create shape
shape = api.sphere(10).set_color(ColorEnum.ORANGE)

# Show in desktop viewer
shape.show()

# Show in Jupyter
shape.show(viewer_mode="jupyter")

# Show as web page
shape.show(viewer_mode="web")

# Solid-level usage
from pylele.pylele2.all_assembly import LeleAllAssembly

solid = LeleAllAssembly(args=["-i", "trimesh"])
solid.show()  # Opens interactive viewer with all parts
```

## 11. Future Work (Not in Scope)

- **VSCode Extension**: Live preview panel inside VSCode
- **Section Viewer**: Interactive slicing along X/Y/Z axes
- **Measurement Tools**: Click to measure distances in viewer
- **Animation**: Orbit animation for demo/turntable rendering
- **Remote Viewing**: WebSocket-based streaming to browser
