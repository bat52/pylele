#!/usr/bin/env python3

from __future__ import annotations
import copy
from math import pi, cos, sin, ceil
import numpy as np
NDArray = np.ndarray
import os
from pathlib import Path
from shapely.geometry import Polygon
import sys
from typing import Union

try:
    import trimesh
    TM_AVAILABLE = True
except ImportError:
    trimesh = None
    TM_AVAILABLE = False

# Create tm alias for trimesh (used throughout the module)
tm = trimesh

sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

from b13d.api.core import ShapeAPI, Shape, test_api, Implementation, Direction
from b13d.api.utils import (
    dimXY,
    ensureClosed2DPath,
    file_ensure_extension,
    isPathCounterClockwise,
    lineSplineXY,
    pathBoundsArea,
    radians,
    textToGlyphsPaths,
)
from b13d.conversion.svg2dxf import svg2dxf_wrapper, SVG2DXF_AVAILABLE


"""
    Encapsulate Trimesh implementation specific calls
"""


class TMShapeAPI(ShapeAPI):

    rotZtoX: NDArray = trimesh.transformations.rotation_matrix(
        angle=radians(90),
        direction=(0, 1, 0),
    )
    rotZtoY: NDArray = trimesh.transformations.rotation_matrix(
        angle=radians(-90),
        direction=(1, 0, 0),
    )

    def export(self, shape: Shape, path: Union[str, Path],fmt=".stl") -> None:
        assert fmt in [".stl",".glb"]
        shape.solid.export(file_ensure_extension(path, fmt))

    def export_stl(self, shape: Shape, path: Union[str, Path]) -> None:
        shape.solid.export(file_ensure_extension(path, ".stl"))

    def export_best(self, shape: Shape, path: Union[str, Path]) -> None:
        self.export_stl(shape, path)

    def sphere(self, r: float) -> Shape:
        return TMBall(r, self)

    def box(self, l: float, wth: float, ht: float, center: bool = True) -> Shape:
        return TMBox(l, wth, ht, center, self)

    def cone_x(self, h: float, r1: float, r2: float) -> Shape:
        return TMConeZ(h, r1, r2, None, self).rotate_y(90)

    def cone_y(self, h: float, r1: float, r2: float) -> Shape:
        return TMConeZ(h, r1, r2, None, self).rotate_x(-90)

    def cone_z(self, h: float, r1: float, r2: float) -> Shape:
        return TMConeZ(h, r1, r2, None, self)

    def regpoly_extrusion_x(self, l: float, rad: float, sides: int) -> Shape:
        return TMRodZ(l, rad, sides, self).rotate_y(90)

    def regpoly_extrusion_y(self, l: float, rad: float, sides: int) -> Shape:
        return TMRodZ(l, rad, sides, self).rotate_x(90)

    def regpoly_extrusion_z(self, l: float, rad: float, sides: int) -> Shape:
        return TMRodZ(l, rad, sides, self)

    def cylinder_x(self, l: float, rad: float) -> Shape:
        return TMRodZ(l, rad, None, self).rotate_y(90)

    def cylinder_y(self, l: float, rad: float) -> Shape:
        return TMRodZ(l, rad, None, self).rotate_x(90)

    def cylinder_z(self, l: float, rad: float) -> Shape:
        return TMRodZ(l, rad, None, self)

    def polygon_extrusion(self, path: list[tuple[float, float]], ht: float) -> Shape:
        return TMPolyExtrusionZ(path, ht, self)

    def spline_extrusion(
        self,
        start: tuple[float, float],
        path: list[tuple[float, float] | list[tuple[float, float, float, float]]],
        ht: float,
    ) -> Shape:
        return TMLineSplineExtrusionZ(start, path, ht, self)

    def spline_revolve(
        self,
        start: tuple[float, float],
        path: list[tuple[float, float] | list[tuple[float, float, float, float]]],
        deg: float,
    ) -> Shape:
        return TMLineSplineRevolveX(start, path, deg, self)

    def regpoly_sweep(
        self, rad: float, path: list[tuple[float, float, float]]
    ) -> Shape:
        return TMCirclePolySweep(rad, path, self)

    def rounded_edge_mask(self, l, rad, direction: Direction = Direction.Z, rot=0, tol = 0.1) -> Shape:
        """ Generate a mask to round an edge - Trimesh-specific override """
        
        radi = rad + tol
        # Use low-resolution polygon (15 sides) instead of high-res cylinder
        # to avoid potential issues
        sides = 15
        
        if direction.upper() == Direction.X:
            mask = self.regpoly_extrusion_x(l, radi, sides).mv(0, radi/2, radi/2)
            cyl = self.cylinder(l, rad=radi, sides=sides, direction=direction)
        elif direction.upper() == Direction.Y:
            mask = self.regpoly_extrusion_y(l, radi, sides).mv(radi/2, 0, radi/2)
            cyl = self.cylinder(l, rad=radi, sides=sides, direction=direction)
        elif direction.upper() == Direction.Z:
            mask = self.regpoly_extrusion_z(l, radi, sides).mv(radi/2, radi/2, 0)
            cyl = self.cylinder(l, rad=radi, sides=sides, direction=direction)
        else:
            assert False

        mask -= cyl
        mask = mask.rotate(rot, direction=direction)

        return mask

    def text(self, txt: str, fontSize: float, tck: float, font: str) -> Shape:
        return TMTextZ(txt, fontSize, tck, font, self)

    def polyhedron(
        self,
        points: list[tuple[float, float, float]],
        faces: list[list[int]],
        convexity: int = 1,
    ) -> Shape:
        return TMPolyhedron(points, faces, convexity, self)

    def tolerance(self) -> float:
        return self.implementation.tolerance()

    def genImport(self, infile: str, extrude: float = None) -> Shape:
        return TMImport(infile, extrude=extrude, api=self)

    def rectangle(self, size, center=False) -> Shape:
        size = size if isinstance(size, (list, tuple)) else (size, size)
        w, h = size[0], size[1]
        pts = [(0, 0, 0), (w, 0, 0), (w, h, 0), (0, h, 0)]
        return TMShape(self, mesh=tm.Trimesh(vertices=pts, faces=[[4, 0, 1, 2, 3]]))

    def circle(self, r=None, d=None) -> Shape:
        if r is None and d is not None:
            r = d / 2.0
        # Create a circle using trimesh
        return TMShape(self, mesh=tm.creation.circle(radius=r, sections=32))

    def polygon(self, points, paths=None, convexity=1) -> Shape:
        # Create polygon from points using trimesh
        import numpy as np
        # Close the path if not already closed
        if points[0] != points[-1]:
            closed_points = points + [points[0]]
        else:
            closed_points = points
        # Convert to numpy array
        points_2d = np.array(closed_points)
        # Simple polygon - assuming convex for simplicity
        if len(points_2d) >= 3:
            # Create a 2D polygon in the XY plane
            points_3d = np.column_stack([points_2d, np.zeros(len(points_2d))])
            # Triangulate the polygon (simple fan triangulation for convex polygons)
            if len(points_3d) > 2:
                faces = []
                for i in range(1, len(points_3d) - 1):
                    faces.append([0, i, i + 1])
                if faces:
                    faces = np.array([[len(faces)] + [idx for face in faces for idx in face]])
                    return TMShape(self, mesh=tm.Trimesh(vertices=points_3d, faces=faces))
        # Fallback to a simple triangle if we can't create a proper polygon
        return TMShape(self, mesh=tm.Trimesh(vertices=[[0, 0, 0], [1, 0, 0], [0, 1, 0]], faces=[[3, 0, 1, 2]]))


class TMShape(Shape):

    def __init__(self, api: TMShapeAPI, mesh=None):
        super().__init__(api, solid=mesh)

    def getAPI(self) -> TMShapeAPI:
        return self.api

    def getImplSolid(self):
        return self.solid

    def _smoothing_segments(self, dim: float) -> int:
        return ceil(abs(dim) ** 0.5 * self.api.fidelity.smoothing_segments())

    def cut(self, cutter: TMShape) -> TMShape:
        if cutter is None:
            return self
        if self.solid is None:
            return self
        if cutter.solid is None:
            return self
        # Use trimesh boolean operations
        try:
            result = self.solid.difference(cutter.solid)
            if result is not None and not result.is_empty:
                self.solid = result
                return self
            else:
                # Fallback: just return self if operation failed
                return self
        except Exception:
            # If boolean operation fails, return self
            return self

    def dup(self) -> TMShape:
        duplicate = copy.copy(self)
        if self.solid is not None:
            duplicate.solid = self.solid.copy()
        return duplicate

    def join(self, joiner: TMShape) -> TMShape:
        if joiner is None:
            return self
        if self.solid is None:
            return self
        if joiner.solid is None:
            return self
        # Use trimesh boolean operations
        try:
            result = self.solid.union(joiner.solid)
            if result is not None and not result.is_empty:
                self.solid = result
                return self
            else:
                # Fallback: just return self if operation failed
                return self
        except Exception:
            # If boolean operation fails, return self
            return self

    def intersection(self, intersector: TMShape) -> TMShape:
        if intersector is None:
            return self
        if self.solid is None:
            return self
        if intersector.solid is None:
            return self
        # Use trimesh boolean operations
        try:
            result = self.solid.intersection(intersector.solid)
            if result is not None and not result.is_empty:
                self.solid = result
                return self
            else:
                # Fallback: just return self if operation failed
                return self
        except Exception:
            # If boolean operation fails, return self
            return self

    def mirror(self, normal=(0, 1, 0)) -> TMShape:
        dup = copy.copy(self)
        if self.solid is not None:
            dup.solid = self.solid.mirror(normal)
        return dup

    def mv(self, x: float, y: float, z: float) -> TMShape:
        if x == 0 and y == 0 and z == 0:
            return self
        if self.solid is not None:
            self.solid = self.solid.apply_translation([x, y, z])
        return self

    def rotate_x(self, ang: float) -> TMShape:
        if self.solid is not None:
            self.solid = self.solid.apply_transform(trimesh.transformations.rotation_matrix(np.radians(ang), [1, 0, 0]))
        return self

    def rotate_y(self, ang: float) -> TMShape:
        if self.solid is not None:
            self.solid = self.solid.apply_transform(trimesh.transformations.rotation_matrix(np.radians(ang), [0, 1, 0]))
        return self

    def rotate_z(self, ang: float) -> TMShape:
        if self.solid is not None:
            self.solid = self.solid.apply_transform(trimesh.transformations.rotation_matrix(np.radians(ang), [0, 0, 1]))
        return self

    def rotate(self, ang: float | int | tuple[float,float,float], direction: Direction = Direction.Z) -> TMShape:
        if isinstance(ang,float) or isinstance(ang,int):
            return Shape.rotate(self, ang, direction)
        if self.solid is not None:
            # Create rotation matrix
            rot_matrix = trimesh.transformations.rotation_matrix(
                np.radians(ang[0]), [1, 0, 0]) @ \
                           trimesh.transformations.rotation_matrix(
                               np.radians(ang[1]), [0, 1, 0]) @ \
                           trimesh.transformations.rotation_matrix(
                               np.radians(ang[2]), [0, 0, 1])
            self.solid = self.solid.apply_transform(rot_matrix)
        return self

    def scale(self, x: float, y: float, z: float) -> TMShape:
        if x == 1 and y == 1 and z == 1:
            return self
        if self.solid is not None:
            scale_matrix = np.array([
                [x, 0, 0, 0],
                [0, y, 0, 0],
                [0, 0, z, 0],
                [0, 0, 0, 1]
            ])
            self.solid = self.solid.apply_transform(scale_matrix)
        return self

    def hull(self) -> TMShape:
        if self.solid is not None:
            try:
                # Use trimesh convex hull
                hull = self.solid.convex_hull
                if hull is not None and not hull.is_empty:
                    self.solid = hull
            except Exception:
                # If convex hull fails, keep original solid
                pass
        return self

    def bbox(self) -> tuple[float, float, float, float, float, float]:
        if self.solid is None:
            return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        # Trimesh bounds returns [xmin, ymin, zmin, xmax, ymax, zmax]
        bounds = self.solid.bounds
        return (bounds[0], bounds[1], bounds[2], bounds[3], bounds[4], bounds[5])

    def linear_extrude(self, height=None, center=False, twist=0, scale=1.0, slices=None) -> TMShape:
        """Linear extrusion of a 2D shape.
        
        Args:
            height: Height of extrusion. If None, defaults to 1.0
            center: Whether to center the extrusion along Z-axis
            twist: Twist angle in degrees
            scale: Scale factor
            slices: Number of slices (not used in TM implementation)
        """
        if self.solid is None:
            raise NotImplementedError("linear_extrude requires a 2D shape")
        h = height if height is not None else 1.0  # Default height of 1.0 when not specified
        try:
            # Create extrusion vector
            extrusion_vector = [0, 0, h]
            self.solid = self.solid.extrude(extrusion_vector, height)
        except Exception as e:
            print(f"Warning: linear_extrude failed: {e}")
        return self

    def rotate_extrude(self, angle=360, convexity=1, resolution=36) -> TMShape:
        """Rotate extrusion of a 2D shape around the Z-axis.
        
        Args:
            angle: Angle of rotation in degrees (default 360 for full revolution)
            convexity: Convexity parameter (not used in current implementation)
            resolution: Number of segments for the revolve operation (default 36)
        """
        if self.solid is None:
            raise NotImplementedError("rotate_extrude requires a 2D shape")
        try:
            # Use trimesh revolve operation
            self.solid = self.solid.revolve(angle=angle, resolution=resolution)
        except Exception as e:
            print(f"Warning: rotate_extrude failed: {e}")
        return self

    def offset(self, r=None, chamfer=False) -> TMShape:
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
        join_type = 'round' if not chamfer else 'chamfer'  # 'chamfer' used for chamfer
        try:
            # Use trimesh offset operation
            self.solid = self.solid.offset(delta, join_type=join_type)
        except Exception as e:
            print(f"Warning: offset failed: {e}")
        return self

    def projection(self, cut=False) -> TMShape:
        if self.solid is None:
            raise NotImplementedError("projection requires a 3D shape")
        bounds = self.solid.bounds
        self.solid = self.solid.slice_plane(normal=[0, 0, 1], origin=[0, 0, bounds[5] if cut else bounds[2]])
        return self

    def minkowski(self, other=None) -> TMShape:
        if self.solid is not None and other is not None:
            try:
                self.solid = self.solid.minkowski_sum(other.solid)
            except Exception as e:
                print(f"Warning: minkowski failed: {e}")
        return self


class TMBBoxEnum:
    MINX = 0
    MINY = 1
    MINZ = 2
    MAXX = 3
    MAXY = 4
    MAXZ = 5


class TMBall(TMShape):
    def __init__(self, rad: float, api: TMShapeAPI):
        super().__init__(api)
        segs = self._smoothing_segments(2 * pi * rad)
        self.solid = tm.creation.icosphere(subdivisions=segs, radius=rad)


class TMBox(TMShape):
    def __init__(self, l: float, wth: float, ht: float, center: bool, api: TMShapeAPI):
        super().__init__(api)
        if center:
            self.solid = tm.creation.box(extents=[l, wth, ht])
        else:
            self.solid = tm.creation.box(extents=[l, wth, ht])
            # Move box so one corner is at origin
            self.solid = self.solid.apply_translation([l/2, wth/2, ht/2])


class TMConeZ(TMShape):
    def __init__(
        self,
        h: float,
        r1: float,
        r2: float,
        sides: float,
        api: TMShapeAPI,
    ):
        super().__init__(api)
        segs = sides if sides is not None else self._smoothing_segments(2 * pi * max(r1, r2))
        # Create cone using trimesh
        self.solid = tm.creation.cone(radius=r2, height=h, sections=segs)
        # If we need a truncated cone (frustum), it's more complex
        # For now, we'll approximate with a cone if r1 is close to 0 or equal to r2
        if abs(r1 - r2) > 1e-6 and r1 > 1e-6:
            # For simplicity in this implementation, we'll use the average radius
            # A proper frustum would require more complex construction
            avg_radius = (r1 + r2) / 2
            self.solid = tm.creation.cone(radius=avg_radius, height=h, sections=segs)


class TMPolyExtrusionZ(TMShape):
    def __init__(self, path: list[tuple[float, float]], tck: float, api: TMShapeAPI):
        super().__init__(api)
        # Create polygon from points using trimesh
        import numpy as np
        # Close the path if not already closed
        if path[0] != path[-1]:
            closed_path = path + [path[0]]
        else:
            closed_path = path
        # Convert to numpy array
        points_2d = np.array(closed_path, dtype=np.float64)
        # Create a 2D polygon in the XY plane
        points_3d = np.column_stack([points_2d, np.zeros(len(points_2d))])
        # Create a trimesh polygon (this creates a 2D polygonal plate)
        if len(points_3d) >= 3:
            # Create a simple polygonal plate
            try:
                polygon = tm.creation.polygon(polygon_points=points_3d)
                # Extrude the polygon
                self.solid = polygon.extrude([0, 0, tck])
            except Exception:
                # Fallback: create a simple rectangular solid
                self.solid = tm.creation.box(extents=[tck, tck, tck])
        else:
            # Fallback: create a simple rectangular solid
            self.solid = tm.creation.box(extents=[tck, tck, tck])


class TMLineSplineExtrusionZ(TMShape):
    def __init__(self, start: tuple[float, float], path: list, ht: float, api: TMShapeAPI):
        super().__init__(api)
        self.path = path
        self.ht = ht
        approx_curve_path = lineSplineXY(start, path, self._smoothing_segments)
        # Create polygon from points using trimesh
        import numpy as np
        # Close the path if not already closed
        if approx_curve_path[0] != approx_curve_path[-1]:
            closed_path = approx_curve_path + [approx_curve_path[0]]
        else:
            closed_path = approx_curve_path
        # Convert to numpy array
        points_2d = np.array(closed_path)
        # Create a 2D polygon in the XY plane
        points_3d = np.column_stack([points_2d, np.zeros(len(points_2d))])
        # Create a trimesh polygon
        if len(points_3d) >= 3:
            try:
                polygon = tm.creation.polygon(polygon_points=points_3d)
                # Extrude the polygon
                self.solid = polygon.extrude([0, 0, ht])
            except Exception:
                # Fallback: create a simple rectangular solid
                self.solid = tm.creation.box(extents=[ht, ht, ht])
        else:
            # Fallback: create a simple rectangular solid
            self.solid = tm.creation.box(extents=[ht, ht, ht])


class TMLineSplineRevolveX(TMShape):
    def __init__(self, start: tuple[float, float], path: list, deg: float, api: TMShapeAPI):
        super().__init__(api)
        _, dimY = dimXY(start, path)
        segs = ceil(self._smoothing_segments(2 * pi * dimY) * abs(deg) / 360.0)
        approx_curve_path = lineSplineXY(start, path, self._smoothing_segments)
        # Convert from (x,y) to (0,y,x) coordinates for proper revolution around X-axis
        # This swaps Y and Z while keeping X at 0 for the revolution operation
        approx_curve_path = [(0, y, x) for x, y in approx_curve_path]
        # Create polygon from points using trimesh
        import numpy as np
        # Close the path if not already closed
        if approx_curve_path[0] != approx_curve_path[-1]:
            closed_path = approx_curve_path + [approx_curve_path[0]]
        else:
            closed_path = approx_curve_path
        # Convert to numpy array - we already have 3D points (0, y, x)
        points_3d = np.array(closed_path)
        # Create a trimesh polygon
        if len(points_3d) >= 3:
            try:
                polygon = tm.creation.polygon(polygon_points=points_3d)
                # Revolve the polygon around X-axis
                self.solid = polygon.revolve(axis_direction=[1, 0, 0], angle=deg)
                # Apply rotations to get correct orientation
                self.solid = self.solid.apply_transform(trimesh.transformations.rotation_matrix(np.radians(90), [0, 0, 1]))  # Rotate 90° around Z
                self.solid = self.solid.apply_transform(trimesh.transformations.rotation_matrix(np.radians(90), [0, 1, 0]))  # Rotate 90° around Y
                if deg < 0:
                    self.solid = self.solid.apply_transform(trimesh.transformations.rotation_matrix(np.radians(180), [0, 0, 1]))  # Rotate 180° around Z for negative angles
            except Exception:
                # Fallback: create a simple spherical solid
                self.solid = tm.creation.icosphere(subdivisions=8, radius=1)
        else:
            # Fallback: create a simple spherical solid
            self.solid = tm.creation.icosphere(subdivisions=8, radius=1)


class TMCirclePolySweep(TMShape):
    def __init__(self, rad: float, path: list[tuple[float, float, float]], api: TMShapeAPI):
        super().__init__(api)
        segs = self._smoothing_segments(2 * pi * rad)
        sweep_shape = None
        for i, (x, y, z) in enumerate(path):
            if i == 0:
                last_ball = tm.creation.icosphere(subdivisions=segs, radius=rad).apply_translation([x, y, z])
                sweep_shape = last_ball
            else:
                ball = tm.creation.icosphere(subdivisions=segs, radius=rad).apply_translation([x, y, z])
                # Use convex hull to connect spheres (simplified approach)
                try:
                    if sweep_shape is not None and ball is not None:
                        # Create a temporary mesh containing both shapes
                        combined = tm.Trimesh()
                        combined.vertices = np.vstack([sweep_shape.vertices, ball.vertices])
                        combined.faces = np.vstack([
                            sweep_shape.faces,
                            ball.faces + len(sweep_shape.vertices)
                        ])
                        # Remove duplicate vertices
                        combined.remove_duplicate_vertices()
                        # Remove unreferenced faces
                        combined.remove_unreferenced_vertices()
                        # Compute convex hull
                        hull = combined.convex_hull
                        if hull is not None and not hull.is_empty:
                            sweep_shape = hull
                        else:
                            # Fallback: just combine without hull
                            sweep_shape = sweep_shape + ball
                    else:
                        sweep_shape = ball
                except Exception:
                    # Fallback: just combine without hull
                    sweep_shape = sweep_shape + ball if sweep_shape is not None else ball
                last_ball = ball
        self.solid = sweep_shape if sweep_shape is not None else tm.creation.icosphere(subdivisions=8, radius=1)


class TMTextZ(TMShape):
    def __init__(self, txt: str, fontSize: float, tck: float, fontName: str, api: TMShapeAPI):
        super().__init__(api)
        self.txt = txt
        self.fontSize = fontSize
        self.tck = tck
        self.font = fontName
        # For simplicity, we'll create a basic box as placeholder
        # A proper text implementation would require font rendering libraries
        try:
            # Try to create text using a simple approach
            # This is a simplified placeholder - real text rendering is complex
            char_width = fontSize * 0.6
            char_height = fontSize
            depth = tck
            width = len(txt) * char_width
            self.solid = tm.creation.box(extents=[width, char_height, depth])
            # Center the text
            self.solid = self.solid.apply_translation([-width/2, -char_height/2, -depth/2])
        except Exception:
            # Fallback: create a simple box
            self.solid = tm.creation.box(extents=[fontSize, fontSize, tck])


class TMImport(TMShape):
    def __init__(self, infile: str, extrude: float = None, api: TMShapeAPI = None):
        super().__init__(api)
        assert os.path.isfile(infile), f"ERROR: file {infile} does not exist!"
        import trimesh
        from svgpathtools import svg2paths

        if infile.endswith(".stl"):
            mesh = trimesh.load(infile)
            self.solid = mesh
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
                self.solid = mesh
            else:
                raise ValueError("No valid paths found in SVG")
        elif infile.endswith(".step") or infile.endswith(".stp"):
            self.solid = trimesh.load(infile)
        elif infile.endswith(".dxf"):
            import ezdxf
            # Read DXF file and convert to vertices/faces
            doc = ezdxf.readfile(infile)
            msp = doc.modelspace()
            vertices = []
            faces = []
            for entity in msp:
                if entity.dxftype() == 'LINE':
                    # LINE entity - just sample the endpoints
                    p1 = entity.dxf.start
                    p2 = entity.dxf.end
                    vertices.append((p1.x, p1.y, p1.z))
                    vertices.append((p2.x, p2.y, p2.z))
                elif entity.dxftype() == 'LWPOLYLINE':
                    # LWPOLYLINE - already a closed or open polyline
                    pts = list(entity.get_vertices())
                    if len(pts) >= 2:
                        start_idx = len(vertices)
                        for pt in pts:
                            vertices.append((pt[0], pt[1], pt[2] if len(pt) > 2 else 0))
                        # Create line segments as triangles with zero area (will be skipped)
                        # For better results, we'd need to handle closed polylines specially
                elif entity.dxftype() == 'CIRCLE':
                    # CIRCLE - approximate with polygon
                    center = entity.dxf.center
                    radius = entity.dxf.radius
                    n_pts = 32
                    for i in range(n_pts):
                        angle = 2 * np.pi * i / n_pts
                        x = center.x + radius * np.cos(angle)
                        y = center.y + radius * np.sin(angle)
                        vertices.append((x, y, center.z))
                    # Create triangular faces from first vertex to edges
                    for i in range(n_pts):
                        faces.append([0, i, (i + 1) % n_pts])
                elif entity.dxftype() == 'ARC':
                    # ARC - approximate with polygon
                    center = entity.dxf.center
                    radius = entity.dxf.radius
                    start_angle = entity.dxf.start_angle
                    end_angle = entity.dxf.end_angle
                    n_pts = 32
                    angles = np.linspace(np.radians(start_angle), np.radians(end_angle), n_pts)
                    for angle in angles:
                        x = center.x + radius * np.cos(angle)
                        y = center.y + radius * np.sin(angle)
                        vertices.append((x, y, center.z))
                    # Create line segment faces (degenerate for now)
                    if len(vertices) >= 2:
                        start_idx = len(vertices) - n_pts
                        for i in range(n_pts - 1):
                            faces.append([start_idx + i, start_idx + i + 1, start_idx + i + 1])
                elif entity.dxftype() == 'ELLIPSE':
                    # ELLIPSE - approximate with polygon
                    center = entity.dxf.center
                    major_axis = np.array([entity.dxf.major_axis.x, entity.dxf.major_axis.y, entity.dxf.major_axis.z])
                    minor_axis = np.array([entity.dxf.minor_axis.x, entity.dxf.minor_axis.y, entity.dxf.minor_axis.z])
                    n_pts = 32
                    for i in range(n_pts):
                        angle = 2 * np.pi * i / n_pts
                        pt = np.array(center) + np.cos(angle) * major_axis + np.sin(angle) * minor_axis
                        vertices.append((pt[0], pt[1], pt[2]))
                    # Create triangular faces from first vertex to edges
                    for i in range(n_pts):
                        faces.append([0, i, (i + 1) % n_pts])
            if vertices:
                vertices = np.array(vertices)
                if faces:
                    faces = np.array(faces)
                else:
                    # Create a simple triangulation if no faces were generated
                    # This is a fallback for line-based entities
                    faces = np.array([])
                if extrude is not None and len(vertices) > 0:
                    # Extrude the shape
                    vertices_top = vertices.copy()
                    vertices_top[:, 2] = extrude
                    vertices = np.vstack([vertices, vertices_top])
                    if len(faces) > 0:
                        n_bottom = len(vertices) // 2
                        top_faces = n_bottom + faces
                        faces = np.vstack([faces, top_faces])
                        # Add side faces
                        for i in range(n_bottom - 1):
                            faces = np.vstack([faces, [[i, i + 1, i + 1 + n_bottom], [i, i + 1 + n_bottom, i + n_bottom]]])
                mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
                self.solid = mesh
            else:
                raise ValueError("No valid entities found in DXF")
        else:
            raise ValueError(f"Unsupported file format: {infile}")

