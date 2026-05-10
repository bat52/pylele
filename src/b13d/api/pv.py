#!/usr/bin/env python3

from __future__ import annotations
import copy
from math import pi, ceil
try:
    import pyvista as pv
    import numpy as np
    PV_AVAILABLE = True
except ImportError:
    pv = None
    np = None
    PV_AVAILABLE = False
import os
from pathlib import Path
import sys
from typing import Union
from enum import Enum

sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

from b13d.api.core import ShapeAPI, Shape, test_api, Direction, Implementation
from b13d.api.utils import dimXY, file_ensure_extension, lineSplineXY


class PVShapeAPI(ShapeAPI):

    def export_stl(self, shape: PVShape, path: Union[str, Path]) -> None:
        mesh = shape.getImplSolid()
        if mesh is None:
            print(f"Warning: Cannot export {path} - mesh is None")
            return
        try:
            mesh.save(file_ensure_extension(path, ".stl"))
        except Exception as e:
            print(f"Warning: Failed to export {path}: {e}")

    def export_best(self, shape: PVShape, path: Union[str, Path]) -> None:
        self.export_stl(shape, path)

    def export(self, shape: PVShape, path: Union[str, Path], fmt=".stl") -> None:
        self.export_stl(shape=shape, path=path)

    def sphere(self, r: float) -> PVShape:
        return PVBall(r, self)

    def box(self, l: float, wth: float, ht: float, center: bool = True) -> PVShape:
        return PVBox(l, wth, ht, center, self)

    def cone_x(self, h: float, r1: float, r2: float) -> PVShape:
        return PVConeZ(h, r1, r2, None, self).rotate_y(90)

    def cone_y(self, h: float, r1: float, r2: float) -> PVShape:
        return PVConeZ(h, r1, r2, None, self).rotate_x(-90)

    def cone_z(self, h: float, r1: float, r2: float) -> PVShape:
        return PVConeZ(h, r1, r2, None, self)

    def regpoly_extrusion_x(self, l: float, rad: float, sides: int) -> PVShape:
        return PVRodZ(l, rad, sides, self).rotate_y(90)

    def regpoly_extrusion_y(self, l: float, rad: float, sides: int) -> PVShape:
        return PVRodZ(l, rad, sides, self).rotate_x(90)

    def regpoly_extrusion_z(self, l: float, rad: float, sides: int) -> PVShape:
        return PVRodZ(l, rad, sides, self)

    def cylinder_x(self, l: float, rad: float) -> PVShape:
        return PVRodZ(l, rad, None, self).rotate_y(90)

    def cylinder_y(self, l: float, rad: float) -> PVShape:
        return PVRodZ(l, rad, None, self).rotate_x(90)

    def cylinder_z(self, l: float, rad: float) -> PVShape:
        return PVRodZ(l, rad, None, self)

    def polygon_extrusion(self, path: list[tuple[float, float]], ht: float) -> PVShape:
        return PVPolyExtrusionZ(path, ht, self)

    def spline_extrusion(
        self,
        start: tuple[float, float],
        path: list[tuple[float, float] | list[tuple[float, float, float, float]]],
        ht: float,
    ) -> PVShape:
        return PVLineSplineExtrusionZ(start, path, ht, self)

    def spline_revolve(
        self,
        start: tuple[float, float],
        path: list[tuple[float, float] | list[tuple[float, float, float, float]]],
        deg: float,
    ) -> PVShape:
        return PVLineSplineRevolveX(start, path, deg, self)

    def regpoly_sweep(
        self, rad: float, path: list[tuple[float, float, float]]
    ) -> PVShape:
        return PVCirclePolySweep(rad, path, self)

    def text(self, txt: str, fontSize: float, tck: float, font: str) -> PVShape:
        return PVTextZ(txt, fontSize, tck, font, self)

    def polyhedron(
        self,
        points: list[tuple[float, float, float]],
        faces: list[list[int]],
        convexity: int = 1,
    ) -> PVShape:
        return PVPolyhedron(points, faces, convexity, self)

    def tolerance(self) -> float:
        return self.implementation.tolerance()

    def genImport(self, infile: str, extrude: float = None) -> PVShape:
        return PVImport(infile, extrude=extrude, api=self)

    def rectangle(self, size, center=False) -> PVShape:
        size = size if isinstance(size, (list, tuple)) else (size, size)
        w, h = size[0], size[1]
        pts = [(0, 0, 0), (w, 0, 0), (w, h, 0), (0, h, 0)]
        return PVShape(self, mesh=pv.PolyData(pts, [4, 0, 1, 2, 3])).extrude((0, 0, 0.001))

    def circle(self, r=None, d=None) -> PVShape:
        if r is None and d is not None:
            r = d / 2.0
        return PVShape(self, mesh=pv.Disc(center=(0, 0, 0), inner=0.0, outer=r, r_res=64))

    def polygon(self, points, paths=None, convexity=1) -> PVShape:
        # Create polygon from points using PolyData
        import numpy as np
        # Close the path if not already closed
        if points[0] != points[-1]:
            closed_points = points + [points[0]]
        else:
            closed_points = points
        # Convert to numpy array
        points_2d = np.array(closed_points)
        # Add Z coordinate (0 for flat polygon)
        points_3d = np.column_stack([points_2d, np.zeros(len(points_2d))])
        # Create faces (assuming convex polygon for simplicity)
        n_points = len(points_3d)
        faces = [n_points] + list(range(n_points))  # [n_points, 0, 1, 2, ..., n_points-1]
        return PVShape(self, mesh=pv.PolyData(points_3d, faces))


class PVShape(Shape):

    def __init__(self, api: PVShapeAPI, mesh=None):
        super().__init__(api, solid=mesh)

    def getAPI(self) -> PVShapeAPI:
        return self.api

    def getImplSolid(self):
        return self.solid

    def _smoothing_segments(self, dim: float) -> int:
        return ceil(abs(dim) ** 0.5 * self.api.fidelity.smoothing_segments())

    def cut(self, cutter: PVShape) -> PVShape:
        if cutter is None:
            return self
        if self.solid is None:
            return self
        if cutter.solid is None:
            return self
        # Ensure both meshes are triangulated for boolean operations
        self_solid = self.solid.triangulate()
        cutter_solid = cutter.solid.triangulate()
        try:
            result = self_solid.boolean_difference(cutter_solid)
            if result is not None and result.n_points > 0:
                self.solid = result.triangulate()
            else:
                # Fallback: return original shape unchanged
                print(f"Warning: boolean_difference returned empty result, keeping original shape")
        except Exception as e:
            print(f"Warning: boolean_difference failed: {e}, keeping original shape")
        return self

    def join(self, joiner: PVShape) -> PVShape:
        if joiner is None:
            return self
        if self.solid is None:
            return self
        if joiner.solid is None:
            return self
        # Store original solid as fallback
        original_solid = self.solid.copy()
        # Ensure both meshes are triangulated for boolean operations
        self_solid = self.solid.triangulate()
        joiner_solid = joiner.solid.triangulate()
        try:
            result = self_solid.boolean_union(joiner_solid)
            if result is not None and result.n_points > 0:
                self.solid = result.triangulate()
            else:
                # Fallback: create a convex hull of both shapes using scipy
                print(f"Warning: boolean_union returned empty result, using convex hull fallback")
                try:
                    from scipy.spatial import ConvexHull
                    points = np.vstack([self_solid.points, joiner_solid.points])
                    hull = ConvexHull(points)
                    # Scipy hull simplices may need face reversal for correct winding
                    faces = np.column_stack([np.full(len(hull.simplices), 3), hull.simplices[:, ::-1]]).flatten()
                    self.solid = pv.PolyData(hull.points, faces)
                except Exception as hull_error:
                    print(f"Warning: hull fallback also failed: {hull_error}, keeping original shape")
                    self.solid = original_solid
        except Exception as e:
            print(f"Warning: boolean_union failed: {e}, using convex hull fallback")
            try:
                from scipy.spatial import ConvexHull
                points = np.vstack([self_solid.points, joiner_solid.points])
                hull = ConvexHull(points)
                faces = np.column_stack([np.full(len(hull.simplices), 3), hull.simplices[:, ::-1]]).flatten()
                self.solid = pv.PolyData(hull.points, faces)
            except Exception as hull_error:
                print(f"Warning: hull fallback also failed: {hull_error}, keeping original shape")
                self.solid = original_solid
        return self

    def intersection(self, intersector: PVShape) -> PVShape:
        if intersector is None:
            return self
        if self.solid is None:
            return self
        if intersector.solid is None:
            return self
        # Store original solid as fallback
        original_solid = self.solid.copy()
        # Ensure both meshes are triangulated for boolean operations
        self_solid = self.solid.triangulate()
        intersector_solid = intersector.solid.triangulate()
        try:
            result = self_solid.boolean_intersection(intersector_solid)
            if result is not None and result.n_points > 0:
                self.solid = result.triangulate()
            else:
                # Fallback: return a small box
                print(f"Warning: boolean_intersection returned empty result, keeping original shape")
                self.solid = original_solid
        except Exception as e:
            print(f"Warning: boolean_intersection failed: {e}, keeping original shape")
            self.solid = original_solid
        return self

    def dup(self) -> PVShape:
        duplicate = copy.copy(self)
        if self.solid is not None:
            duplicate.solid = self.solid.copy()
        return duplicate



    def mirror(self, normal=(0, 1, 0)) -> PVShape:
        dup = copy.copy(self)
        if self.solid is not None:
            origin = (0, 0, 0)
            dup.solid = self.solid.reflect(normal=normal, point=origin, inplace=0)
        return dup

    def mv(self, x: float, y: float, z: float) -> PVShape:
        if x == 0 and y == 0 and z == 0:
            return self
        if self.solid is not None:
            self.solid = self.solid.translate((x, y, z))
        return self

    def rotate_x(self, ang: float) -> PVShape:
        if self.solid is not None:
            self.solid = self.solid.rotate_x(ang)
        return self

    def rotate_y(self, ang: float) -> PVShape:
        if self.solid is not None:
            self.solid = self.solid.rotate_y(ang)
        return self

    def rotate_z(self, ang: float) -> PVShape:
        if self.solid is not None:
            self.solid = self.solid.rotate_z(ang)
        return self

    def rotate(self, ang: float | tuple[float, float, float], direction: Direction = Direction.Z) -> PVShape:
        if isinstance(ang, (float, int)):
            return Shape.rotate(self, ang, direction)
        if self.solid is not None:
            self.solid = self.solid.rotate(ang)
        return self

    def scale(self, x: float, y: float, z: float) -> PVShape:
        if x == 1 and y == 1 and z == 1:
            return self
        if self.solid is not None:
            self.solid = self.solid.scale((x, y, z))
        return self

    def hull(self) -> PVShape:
        if self.solid is not None:
            try:
                from scipy.spatial import ConvexHull
                points = self.solid.points
                hull = ConvexHull(points)
                faces = np.column_stack([np.full(len(hull.simplices), 3), hull.simplices[:, ::-1]]).flatten()
                self.solid = pv.PolyData(hull.points, faces)
            except Exception as e:
                print(f"Warning: hull failed: {e}")
        return self

    def bbox(self) -> tuple[float, float, float, float, float, float]:
        if self.solid is None:
            return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        bounds = self.solid.bounds
        return (bounds[0], bounds[1], bounds[2], bounds[3], bounds[4], bounds[5])

    def linear_extrude(self, height=None, center=False, twist=0, scale=1.0, slices=None) -> PVShape:
        """Linear extrusion of a 2D shape.
        
        Args:
            height: Height of extrusion. If None, defaults to 1.0
            center: Whether to center the extrusion along Z-axis
            twist: Twist angle in degrees
            scale: Scale factor
            slices: Number of slices (not used in PV implementation)
        """
        if self.solid is None:
            raise NotImplementedError("linear_extrude requires a 2D shape")
        h = height if height is not None else 1.0  # Default height of 1.0 when not specified
        try:
            self.solid = self.solid.extrude((0, 0, h), capping=True)
        except Exception as e:
            print(f"Warning: linear_extrude failed: {e}")
        return self

    def rotate_extrude(self, angle=360, convexity=1, resolution=36) -> PVShape:
        """Rotate extrusion of a 2D shape around the Z-axis.
        
        Args:
            angle: Angle of rotation in degrees (default 360 for full revolution)
            convexity: Convexity parameter (not used in current implementation)
            resolution: Number of segments for the revolve operation (default 36)
        """
        if self.solid is None:
            raise NotImplementedError("rotate_extrude requires a 2D shape")
        try:
            self.solid = self.solid.extrude_rotate(angle=angle, resolution=resolution)
        except Exception as e:
            print(f"Warning: rotate_extrude failed: {e}")
        return self

    def offset(self, r=None, chamfer=False) -> PVShape:
        """Offset a 2D shape by a specified distance.
        
        Args:
            r: Offset distance. If None, defaults to 0.0
            chamfer: If True, use chamfer join type; otherwise use round join
            
        Note:
            Uses fixed join_type='round' when chamfer=False.
        """
        if self.solid is None:
            raise NotImplementedError("offset requires a 2D shape")
        delta = r if r is not None else 0.0
        join_type = 'round' if not chamfer else 'mitre'  # 'mitre' used for chamfer
        self.solid = self.solid.offset(delta, join_type=join_type)
        return self

    def projection(self, cut=False) -> PVShape:
        if self.solid is None:
            raise NotImplementedError("projection requires a 3D shape")
        bounds = self.solid.bounds
        self.solid = self.solid.slice(normal='z', origin=(0, 0, bounds[4]))
        return self

    def minkowski(self, other=None) -> PVShape:
        if self.solid is not None and other is not None:
            self.solid = self.solid.minkowski(other.solid)
        return self


class PVBBoxEnum(Enum):
    MINX = 0
    MINY = 1
    MINZ = 2
    MAXX = 3
    MAXY = 4
    MAXZ = 5


class PVBall(PVShape):
    def __init__(self, rad: float, api: PVShapeAPI):
        super().__init__(api)
        segs = self._smoothing_segments(2 * pi * rad)
        self.solid = pv.Sphere(radius=rad, phi_resolution=segs, theta_resolution=segs)


class PVBox(PVShape):
    def __init__(self, l: float, wth: float, ht: float, center: bool, api: PVShapeAPI):
        super().__init__(api)
        if center:
            self.solid = pv.Box((-l/2, l/2, -wth/2, wth/2, -ht/2, ht/2))
        else:
            self.solid = pv.Box((0, l, 0, wth, 0, ht))


class PVConeZ(PVShape):
    def __init__(self, h: float, r1: float, r2: float, sides: float, api: PVShapeAPI):
        super().__init__(api)
        segs = sides if sides is not None else self._smoothing_segments(2 * pi * max(r1, r2))
        
        # Create frustum/cone manually since pv.Cone doesn't support radius_top/radius_bottom
        if abs(r1 - r2) < 1e-10:  # Essentially a cylinder
            # Use Cylinder with caps for proper closed volume
            self.solid = pv.Cylinder(radius=r1, height=h, resolution=int(segs), direction=(0, 0, 1))
        else:
            # Frustum - create manually with caps
            self.solid = self._create_frustum(h, r1, r2, int(segs))
    
    def _create_frustum(self, h: float, r1: float, r2: float, resolution: int):
        """Create a conical frustum with bottom and top caps"""
        import numpy as np
        
        # Points for bottom circle
        bottom_points = []
        for i in range(resolution):
            angle = 2 * np.pi * i / resolution
            bottom_points.append([r1 * np.cos(angle), r1 * np.sin(angle), 0])
        
        # Points for top circle
        top_points = []
        for i in range(resolution):
            angle = 2 * np.pi * i / resolution
            top_points.append([r2 * np.cos(angle), r2 * np.sin(angle), h])
        
        points = np.array(bottom_points + top_points, dtype=np.float64)
        
        # Create faces
        faces = []
        
        # Side faces (two triangles per quad)
        for i in range(resolution):
            next_i = (i + 1) % resolution
            faces.append([3, i, next_i, resolution + next_i])
            faces.append([3, i, resolution + next_i, resolution + i])
        
        # Bottom cap (center point + perimeter)
        bottom_center_idx = 2 * resolution
        for i in range(resolution):
            next_i = (i + 1) % resolution
            faces.append([3, bottom_center_idx, i, next_i])
        
        # Top cap (center point + perimeter, reversed for correct winding)
        top_center_idx = 2 * resolution + 1
        for i in range(resolution):
            next_i = (i + 1) % resolution
            faces.append([3, top_center_idx, next_i + resolution, i + resolution])
        
        # Add center points for caps
        points = np.vstack([points, [[0, 0, 0], [0, 0, h]]])
        
        # Flatten faces for PyVista
        faces_flat = np.array(faces, dtype=np.int64).flatten()
        
        # Create mesh
        return pv.PolyData(points, faces_flat)


class PVPolyExtrusionZ(PVShape):
    def __init__(self, path: list[tuple[float, float]], tck: float, api: PVShapeAPI):
        super().__init__(api)
        # Create polygon from points using PolyData
        import numpy as np
        # Close the path if not already closed
        if path[0] != path[-1]:
            closed_path = path + [path[0]]
        else:
            closed_path = path
        # Reverse order for correct winding (right-hand rule for positive volume)
        closed_path = closed_path[::-1]
        # Convert to numpy array
        points_2d = np.array(closed_path, dtype=np.float64)
        # Add Z coordinate (0 for flat polygon)
        points_3d = np.column_stack([points_2d, np.zeros(len(points_2d))])
        # Create faces (assuming convex polygon for simplicity)
        n_points = len(points_3d)
        faces = [n_points] + list(range(n_points))  # [n_points, 0, 1, 2, ..., n_points-1]
        polygon = pv.PolyData(points_3d, faces)
        self.solid = polygon.extrude((0, 0, tck), capping=True)


class PVRodZ(PVShape):
    def __init__(self, l: float, rad: float, sides: float, api: PVShapeAPI):
        super().__init__(api)
        segs = sides if sides is not None else self._smoothing_segments(2 * pi * rad)
        self.solid = pv.Cylinder(radius=rad, height=l, resolution=int(segs), direction=(0, 0, 1))


class PVPolyhedron(PVShape):
    def __init__(self, points: list[tuple[float, float, float]], faces: list[list[int]], convexity: int, api: PVShapeAPI):
        super().__init__(api)
        triangles = []
        for face in faces:
            if len(face) >= 3:
                for i in range(1, len(face) - 1):
                    # Reverse winding to ensure positive volume (like hull operation)
                    triangles.append([face[0], face[i + 1], face[i]])
        # PyVista expects each face prefixed with its vertex count: [n, v0, v1, v2, n, v0, v1, v2, ...]
        faces_arr = []
        for tri in triangles:
            faces_arr.extend([3, tri[0], tri[1], tri[2]])
        self.solid = pv.PolyData(np.array(points, dtype=np.float32), np.array(faces_arr, dtype=np.int64))


class PVLineSplineExtrusionZ(PVShape):
    def __init__(self, start: tuple[float, float], path: list, ht: float, api: PVShapeAPI):
        super().__init__(api)
        self.path = path
        self.ht = ht
        approx_curve_path = lineSplineXY(start, path, self._smoothing_segments)
        # Create polygon from points using PolyData
        import numpy as np
        # Close the path if not already closed
        if approx_curve_path[0] != approx_curve_path[-1]:
            closed_path = approx_curve_path + [approx_curve_path[0]]
        else:
            closed_path = approx_curve_path
        # Convert to numpy array
        points_2d = np.array(closed_path)
        # Add Z coordinate (0 for flat polygon)
        points_3d = np.column_stack([points_2d, np.zeros(len(points_2d))])
        # Create faces (assuming convex polygon for simplicity)
        n_points = len(points_3d)
        faces = [n_points] + list(range(n_points))  # [n_points, 0, 1, 2, ..., n_points-1]
        polygon = pv.PolyData(points_3d, faces)
        self.solid = polygon.extrude((0, 0, ht), capping=True)


class PVLineSplineRevolveX(PVShape):
    def __init__(self, start: tuple[float, float], path: list, deg: float, api: PVShapeAPI):
        super().__init__(api)
        _, dimY = dimXY(start, path)
        segs = ceil(self._smoothing_segments(2 * pi * dimY) * abs(deg) / 360.0)
        approx_curve_path = lineSplineXY(start, path, self._smoothing_segments)
        # Convert from (x,y) to (0,y,x) coordinates for proper revolution around X-axis
        # This swaps Y and Z while keeping X at 0 for the revolution operation
        approx_curve_path = [(0, y, x) for x, y in approx_curve_path]
        # Create polygon from points using PolyData
        import numpy as np
        # Close the path if not already closed
        if approx_curve_path[0] != approx_curve_path[-1]:
            closed_path = approx_curve_path + [approx_curve_path[0]]
        else:
            closed_path = approx_curve_path
        # Convert to numpy array - we already have 3D points (0, y, x)
        points_3d = np.array(closed_path)
        # Create faces (assuming convex polygon for simplicity)
        n_points = len(points_3d)
        faces = [n_points] + list(range(n_points))  # [n_points, 0, 1, 2, ..., n_points-1]
        polygon = pv.PolyData(points_3d, faces)
        try:
            self.solid = polygon.extrude_rotate(angle=deg, resolution=segs, capping=True)
            self.solid = self.solid.rotate_z(90).rotate_y(90)
            if deg < 0:
                self.solid = self.solid.reflect(normal=(0, 0, 1), point=(0, 0, 0), inplace=0)
        except Exception as e:
            print(f"Warning: PVLineSplineRevolveX failed: {e}")
            # Fallback: create a simple shape
            self.solid = pv.Sphere(radius=1, phi_resolution=10, theta_resolution=10)


class PVCirclePolySweep(PVShape):
    def __init__(self, rad: float, path: list[tuple[float, float, float]], api: PVShapeAPI):
        super().__init__(api)
        segs = self._smoothing_segments(2 * pi * rad)
        sweep_shape = None
        for i, (x, y, z) in enumerate(path):
            if i == 0:
                last_ball = pv.Sphere(radius=rad, phi_resolution=segs, theta_resolution=segs).translate((x, y, z))
                sweep_shape = last_ball.triangulate()
            else:
                ball = pv.Sphere(radius=rad, phi_resolution=segs, theta_resolution=segs).translate((x, y, z))
                # Use capsule to connect spheres instead of delaunay hull
                p1 = np.array(last_ball.center)
                p2 = np.array(ball.center)
                dist = np.linalg.norm(p2 - p1)
                direction = p2 - p1
                # Avoid division by zero and capsules with zero/negative cylinder length
                if dist > 1e-6:
                    direction_normalized = direction / dist
                    cylinder_length = max(0, dist - 2 * rad)
                    capsule = pv.Capsule(
                        center=(p1 + p2) / 2,
                        direction=direction_normalized,
                        radius=rad,
                        cylinder_length=cylinder_length,
                        resolution=segs,
                    ).triangulate()
                    # Wrap boolean_union in try-except to prevent segfaults
                    try:
                        result = sweep_shape.boolean_union(capsule, tolerance=0.01)
                        if result is not None:
                            sweep_shape = result.triangulate()
                        else:
                            # Union failed, just add the capsule without union
                            sweep_shape = sweep_shape + capsule
                    except Exception:
                        # Fallback: just combine without union
                        sweep_shape = sweep_shape + capsule
                last_ball = ball
        self.solid = sweep_shape


class PVTextZ(PVShape):
    def __init__(self, txt: str, fontSize: float, tck: float, fontName: str, api: PVShapeAPI):
        super().__init__(api)
        self.txt = txt
        self.fontSize = fontSize
        self.tck = tck
        self.font = fontName
        fontPath = self.api.getFontPath(fontName)
        if fontPath is None:
            fontPath = self.api.getFontPath(None)
            print(f"Can't find font {fontName}, substitute with {fontPath}")

        from b13d.api.utils import textToGlyphsPaths
        glyphs_paths = textToGlyphsPaths(
            fontPath, txt, fontSize, dimToSegs=self._smoothing_segments
        )

        text3d = None
        for glyph_paths in glyphs_paths:
            glyph_meshes = []
            for path in glyph_paths:
                if len(path) >= 3:
                    # Extract coordinates from path points
                    # path is a list of points, where each point is a list/tuple of coordinates
                    coords_2d = [point[:2] for point in path]  # Take only x,y coordinates
                    # Create polygon from points using PolyData
                    import numpy as np
                    # Close the path if not already closed
                    if coords_2d[0] != coords_2d[-1]:
                        closed_coords = coords_2d + [coords_2d[0]]
                    else:
                        closed_coords = coords_2d
                    # Convert to numpy array
                    points_2d = np.array(closed_coords)
                    # Add Z coordinate (0 for flat polygon)
                    points_3d = np.column_stack([points_2d, np.zeros(len(points_2d))])
                    # Create faces (assuming convex polygon for simplicity)
                    n_points = len(points_3d)
                    faces = [n_points] + list(range(n_points))  # [n_points, 0, 1, 2, ..., n_points-1]
                    polygon = pv.PolyData(points_3d, faces)
                    extruded = polygon.extrude((0, 0, tck), capping=True)
                    glyph_meshes.append(extruded)
            
            # Combine all paths for this glyph using + operator (more reliable than boolean_union)
            if glyph_meshes:
                glyph3d = glyph_meshes[0]
                for m in glyph_meshes[1:]:
                    glyph3d = glyph3d + m
                
                # Union glyph with text3d
                if text3d is not None:
                    text3d = text3d + glyph3d
                else:
                    text3d = glyph3d

        if text3d is not None:
            bbox = text3d.bounds
            xmax = bbox[1]
            ymax = bbox[3]
            self.solid = text3d.translate((-xmax / 2, -ymax / 2, 0))
        else:
            print('# WARNING! Text Generation failed!!! ')
            self.solid = pv.Box((-fontSize / 2, fontSize / 2, -fontSize / 2, fontSize / 2, -tck / 2, tck / 2))


class PVImport(PVShape):
    def __init__(self, infile: str, extrude: float = None, api: PVShapeAPI = None):
        super().__init__(api)
        assert os.path.isfile(infile), f"ERROR: file {infile} does not exist!"
        import trimesh
        from svgpathtools import svg2paths

        if infile.endswith(".stl"):
            mesh = trimesh.load(infile)
            self.solid = pv.wrap(mesh)
        elif infile.endswith(".svg"):
            paths, _ = svg2paths(infile)
            # Convert SVG paths to vertices and faces
            vertices = []
            faces = []
            for path in paths:
                # Sample points along the path
                pts = []
                for seg in path:
                    for t in np.linspace(0, 1, 20):
                        pt = seg.point(t)
                        pts.append((pt.real, pt.imag, 0))
                if len(pts) >= 3:
                    start_idx = len(vertices)
                    vertices.extend(pts)
                    # Create faces as triangles
                    for i in range(len(pts) - 2):
                        faces.append([start_idx, start_idx + i + 1, start_idx + i + 2])
            if vertices and faces:
                vertices = np.array(vertices)
                faces = np.array(faces)
                if extrude is not None:
                    # Create top face by offsetting z
                    vertices_top = vertices.copy()
                    vertices_top[:, 2] = extrude
                    vertices = np.vstack([vertices, vertices_top])
                    n_bottom = len(vertices) // 2
                    # Flip top faces (invert winding order)
                    top_faces = n_bottom + faces
                    faces = np.vstack([faces, top_faces])
                    # Create side faces as triangles (two per quad)
                    for i in range(len(vertices) // 2 - 1):
                        v1 = i
                        v2 = i + 1
                        v3 = i + 1 + n_bottom
                        v4 = i + n_bottom
                        # Two triangles per quad
                        faces = np.vstack([faces, [[v1, v2, v3], [v1, v3, v4]]])
                mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
                self.solid = pv.wrap(mesh)
            else:
                raise ValueError("No valid paths found in SVG")
        elif infile.endswith(".step") or infile.endswith(".stp"):
            self.solid = pv.read(infile)
        else:
            raise ValueError(f"Unsupported file format: {infile}")


if __name__ == "__main__":
    test_api(Implementation.PYVISTA)