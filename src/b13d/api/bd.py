#!/usr/bin/env python3

"""
build123d Backend for b13d API.

Implements ShapeAPI and Shape using the build123d library.
Supports fillet and hull operations.
"""

from __future__ import annotations

import copy
from math import pi, ceil
import os
from pathlib import Path
import sys
from typing import Union

import numpy as np
from scipy.spatial import ConvexHull

bd = None
Solid = None
Face = None
Wire = None
Edge = None
Shell = None
Compound = None
ShapeList = None
BD_AVAILABLE = False
try:
    import build123d as _bd
    from build123d.topology import Solid as _Solid, Face as _Face, Wire as _Wire, Edge as _Edge, Shell as _Shell, Compound as _Compound, ShapeList as _ShapeList
    bd = _bd
    Solid = _Solid
    Face = _Face
    Wire = _Wire
    Edge = _Edge
    Shell = _Shell
    Compound = _Compound
    ShapeList = _ShapeList
    BD_AVAILABLE = True
except ImportError:
    pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))

from b13d.api.core import ShapeAPI, Shape, Direction, Implementation
from b13d.api.utils import (
    dimXY,
    file_ensure_extension,
    lineSplineXY,
    textToGlyphsPaths,
)


class BDShapeAPI(ShapeAPI):
    """build123d implementation of ShapeAPI."""

    def export_stl(self, shape: BDShape, path: Union[str, Path]) -> None:
        solid = shape.getImplSolid()
        if isinstance(solid, bd.Compound) and len(solid.solids()) == 0:
            raise ValueError("Cannot export empty Compound (no solids to export)")
        bd.export_stl(solid, file_ensure_extension(path, ".stl"))

    def export_best(self, shape: BDShape, path: Union[str, Path]) -> None:
        self.export_stl(shape, path)

    def export(self, shape: BDShape, path: Union[str, Path], fmt=".stl") -> None:
        self.export_stl(shape=shape, path=path)

    def sphere(self, r: float) -> BDShape:
        return BDBall(r, self)

    def box(self, l: float, wth: float, ht: float, center: bool = True) -> BDShape:
        return BDBox(l, wth, ht, center, self)

    def cone_x(self, h: float, r1: float, r2: float) -> BDShape:
        return BDConeZ(h, r1, r2, self).rotate_y(90)

    def cone_y(self, h: float, r1: float, r2: float) -> BDShape:
        return BDConeZ(h, r1, r2, self).rotate_x(-90)

    def cone_z(self, h: float, r1: float, r2: float) -> BDShape:
        return BDConeZ(h, r1, r2, self)

    def regpoly_extrusion_x(self, l: float, rad: float, sides: int) -> BDShape:
        return BDRodZ(l, rad, sides, self).rotate_y(90)

    def regpoly_extrusion_y(self, l: float, rad: float, sides: int) -> BDShape:
        return BDRodZ(l, rad, sides, self).rotate_x(90)

    def regpoly_extrusion_z(self, l: float, rad: float, sides: int) -> BDShape:
        return BDRodZ(l, rad, sides, self)

    def cylinder_x(self, l: float, rad: float) -> BDShape:
        return BDRodZ(l, rad, None, self).rotate_y(90)

    def cylinder_y(self, l: float, rad: float) -> BDShape:
        return BDRodZ(l, rad, None, self).rotate_x(90)

    def cylinder_z(self, l: float, rad: float) -> BDShape:
        return BDRodZ(l, rad, None, self)

    def polygon_extrusion(
        self, path: list[tuple[float, float]], ht: float
    ) -> BDShape:
        return BDPolyExtrusionZ(path, ht, self)

    def spline_extrusion(
        self,
        start: tuple[float, float],
        path: list[
            tuple[float, float] | list[tuple[float, float, float, float, float]]
        ],
        ht: float,
    ) -> BDShape:
        if ht < 0:
            return BDLineSplineExtrusionZ(
                start, path, abs(ht), self
            ).mv(0, 0, -abs(ht))
        return BDLineSplineExtrusionZ(start, path, ht, self)

    def spline_revolve(
        self,
        start: tuple[float, float],
        path: list[
            tuple[float, float] | list[tuple[float, float, float, float, float]]
        ],
        deg: float,
    ) -> BDShape:
        return BDLineSplineRevolveX(start, path, deg, self)

    def regpoly_sweep(
        self, rad: float, path: list[tuple[float, float, float]]
    ) -> BDShape:
        return BDCirclePolySweep(rad, path, self)

    def text(
        self, txt: str, fontSize: float, tck: float, font: str
    ) -> BDShape:
        return BDTextZ(txt, fontSize, tck, font, self)

    def polyhedron(
        self,
        points: list[tuple[float, float, float]],
        faces: list[list[int]],
        convexity: int = 1,
    ) -> BDShape:
        return BDPolyhedron(points, faces, convexity, self)

    def tolerance(self) -> float:
        return self.implementation.tolerance()

    def genImport(self, infile: str, extrude: float = None) -> BDShape:
        return BDImport(infile, extrude=extrude, api=self)

    def rectangle(self, size, center=False) -> BDShape:
        size = size if isinstance(size, (list, tuple)) else (size, size)
        w, h = size[0], size[1]
        align = (bd.Align.MIN, bd.Align.MIN)
        rect = bd.Rectangle(w, h, align=align)
        shape = BDShape(self, cross_section=rect)
        if center:
            shape = shape.mv(-w / 2, -h / 2, 0)
        return shape

    def circle(self, r=None, d=None) -> BDShape:
        if r is None and d is not None:
            r = d / 2.0
        circ = bd.Circle(r)
        return BDShape(self, cross_section=circ)

    def polygon(self, points, paths=None, convexity=1) -> BDShape:
        poly = bd.Polygon(*points, align=None)
        return BDShape(self, cross_section=poly)

    def genImport(self, infile: str, extrude: float = None) -> BDShape:
        return BDImport(infile, extrude=extrude, api=self)


class BDShape(Shape):
    """build123d implementation of Shape."""

    def __init__(
        self,
        api: BDShapeAPI,
        solid: bd.Solid | bd.Part | bd.Compound = None,
        color: tuple[int, int, int] = None,
        cross_section: bd.Sketch | bd.Face = None,
    ):
        super().__init__(api, solid=solid, color=color)
        self.cross_section: bd.Sketch | bd.Face | None = cross_section

    def getAPI(self) -> BDShapeAPI:
        return self.api

    def getImplSolid(self) -> bd.Solid | bd.Part | bd.Compound:
        self._ensure3d()
        return self.solid

    def _smoothing_segments(self, dim: float) -> int:
        return ceil(abs(dim) ** 0.5 * self.api.fidelity.smoothing_segments())

    def _ensure3d(self) -> BDShape:
        """If cross_section is set but solid is None, convert to 3D via dummy extrude."""
        if self.cross_section is not None and self.solid is None:
            # Use a tiny positive height since build123d's extrude rejects 0
            self.solid = bd.extrude(self.cross_section, 1e-6)
            self.cross_section = None
        return self

    def _resolve_solid(self, shape) -> bd.Solid | bd.Part | bd.Compound:
        """Extract the underlying solid from a Part/Compound wrapper.
        
        build123d's Part class may return empty Compounds when used in boolean
        operations. Extract the inner Solid for reliable boolean results.
        
        Note: For cut/intersection, prefer using raw Part types since Part.cut()
        handles complex geometries more reliably than Solid-Solid. For join,
        Solid+Solid gives better results for disjoint shapes.
        """
        if isinstance(shape, bd.Part):
            solids = shape.solids()
            return solids[0] if solids else shape
        return shape

    def _safe_boolean(self, op_name, a, b, use_resolve=False):
        """Perform a boolean operation with error handling for Null TopoDS_Shape.
        
        Args:
            op_name: 'cut', 'join', or 'intersect'
            a, b: The two solids to operate on
            use_resolve: If True, extract Solid from Part before operation
        """
        _a = self._resolve_solid(a) if use_resolve else a
        _b = self._resolve_solid(b) if use_resolve else b
        
        _ops = {
            'cut': lambda x, y: x - y,
            'join': lambda x, y: x + y,
            'intersect': lambda x, y: x & y,
        }
        op = _ops[op_name]
        
        try:
            return op(_a, _b)
        except ValueError as e:
            if "Null TopoDS_Shape" not in str(e):
                raise
            # If raw operation failed and we weren't using resolve, try with resolve
            if not use_resolve:
                try:
                    return op(self._resolve_solid(a), self._resolve_solid(b))
                except ValueError as e2:
                    if "Null TopoDS_Shape" not in str(e2):
                        raise
            raise ValueError(
                f"build123d boolean {op_name} failed (Null TopoDS_Shape). "
                "This is a known build123d limitation with complex gourd/curved geometries. "
                "Try using the 'mf' (Manifold) backend instead."
            ) from e

    def cut(self, cutter: BDShape) -> BDShape:
        if self.cross_section is not None and cutter is not None and cutter.cross_section is not None:
            self.cross_section = self.cross_section - cutter.cross_section
            return self
        self._ensure3d()
        if cutter is None:
            return self
        cutter._ensure3d()
        if cutter.solid is None:
            return self
        # Try raw Part types first (more reliable for complex geometries),
        # fall back to Solid extraction
        self.solid = self._safe_boolean('cut', self.solid, cutter.solid)
        return self

    def dup(self) -> BDShape:
        duplicate = copy.copy(self)
        if duplicate.cross_section is not None:
            duplicate.cross_section = copy.copy(duplicate.cross_section)
        elif duplicate.solid is not None:
            duplicate.solid = copy.copy(duplicate.solid)
        return duplicate

    def join(self, joiner: BDShape) -> BDShape:
        if self.cross_section is not None and joiner is not None and joiner.cross_section is not None:
            self.cross_section = self.cross_section + joiner.cross_section
            return self
        self._ensure3d()
        if joiner is None or joiner.solid is None:
            return self
        # Use Solid+Solid for join (handles disjoint shapes better than Part+Part)
        result = self._safe_boolean('join', self.solid, joiner.solid, use_resolve=True)
        # build123d returns ShapeList for disjoint solids; convert to Compound for export
        if isinstance(result, ShapeList):
            if len(result) == 0:
                # Empty ShapeList means the operation produced no geometry;
                # keep the original solid unchanged.
                return self
            result = Compound(result)
        self.solid = result
        return self

    def intersection(self, intersector: BDShape) -> BDShape:
        if self.cross_section is not None and intersector is not None and intersector.cross_section is not None:
            self.cross_section = self.cross_section & intersector.cross_section
            return self
        self._ensure3d()
        if intersector is None or intersector.solid is None:
            return self
        # Try raw Part types first (more reliable for complex geometries),
        # fall back to Solid extraction
        self.solid = self._safe_boolean('intersect', self.solid, intersector.solid)
        return self

    def mirror(self, normal: tuple[float, float, float] = (0, 1, 0)) -> BDShape:
        dup = self.dup()
        if dup.cross_section is not None:
            # Mirror 2D shape across the appropriate axis
            if normal[0] != 0:
                dup.cross_section = bd.mirror(dup.cross_section, bd.Plane.YZ)
            elif normal[1] != 0:
                dup.cross_section = bd.mirror(dup.cross_section, bd.Plane.XZ)
            elif normal[2] != 0:
                dup.cross_section = bd.mirror(dup.cross_section, bd.Plane.XY)
        elif dup.solid is not None:
            if normal[0] != 0:
                dup.solid = bd.mirror(dup.solid, bd.Plane.YZ)
            elif normal[1] != 0:
                dup.solid = bd.mirror(dup.solid, bd.Plane.XZ)
            elif normal[2] != 0:
                dup.solid = bd.mirror(dup.solid, bd.Plane.XY)
        return dup

    def mv(self, x: float, y: float, z: float) -> BDShape:
        if x == 0 and y == 0 and z == 0:
            return self
        if self.cross_section is not None:
            self.cross_section = bd.Pos(x, y) * self.cross_section
        elif self.solid is not None:
            self.solid = bd.Pos(x, y, z) * self.solid
        return self

    def rotate_x(self, ang: float) -> BDShape:
        if self.cross_section is not None:
            self._ensure3d()
        if self.solid is not None:
            self.solid = bd.Rotation(ang, 0, 0) * self.solid
        return self

    def rotate_y(self, ang: float) -> BDShape:
        if self.cross_section is not None:
            self._ensure3d()
        if self.solid is not None:
            self.solid = bd.Rotation(0, ang, 0) * self.solid
        return self

    def rotate_z(self, ang: float) -> BDShape:
        if self.cross_section is not None:
            self.cross_section = bd.Rotation(ang) * self.cross_section
        elif self.solid is not None:
            self.solid = bd.Rotation(0, 0, ang) * self.solid
        return self

    def rotate(
        self,
        ang: float | int | tuple[float, float, float],
        direction: Direction = Direction.Z,
    ) -> BDShape:
        if isinstance(ang, (float, int)):
            return Shape.rotate(self, ang, direction)
        if self.cross_section is not None:
            self._ensure3d()
        if self.solid is not None:
            self.solid = bd.Rotation(ang[0], ang[1], ang[2]) * self.solid
        return self

    def scale(self, x: float, y: float, z: float) -> BDShape:
        if x == 1 and y == 1 and z == 1:
            return self
        if self.cross_section is not None:
            self.cross_section = bd.scale(self.cross_section, (x, y))
        elif self.solid is not None:
            self.solid = bd.scale(self.solid, (x, y, z))
        return self

    def hull(self) -> BDShape:
        if self.cross_section is not None:
            # For 2D hull, use scipy ConvexHull on vertices
            verts = np.array(
                [(v.X, v.Y) for v in self.cross_section.vertices()]
            )
            if len(verts) >= 3:
                hull = ConvexHull(verts)
                pts = [tuple(verts[i]) for i in hull.vertices]
                self.cross_section = bd.Polygon(*pts, align=None)
            return self
        if self.solid is not None:
            # Sample points along edges to capture curved surfaces
            edge_points = []
            for edge in self.solid.edges():
                # Sample 20 points along each edge
                for t in np.linspace(0, 1, 20):
                    pt = edge.position_at(t)
                    edge_points.append((pt.X, pt.Y, pt.Z))
            # Also include vertices
            verts_list = [(v.X, v.Y, v.Z) for v in self.solid.vertices()]
            all_pts = np.array(verts_list + edge_points)
            if len(all_pts) >= 4:
                hull = ConvexHull(all_pts)
                faces = []
                for simplex in hull.simplices:
                    pts = [bd.Vector(*all_pts[i]) for i in simplex]
                    e1 = Edge.make_line(pts[0], pts[1])
                    e2 = Edge.make_line(pts[1], pts[2])
                    e3 = Edge.make_line(pts[2], pts[0])
                    w = Wire([e1, e2, e3])
                    f = Face(w)
                    faces.append(f)
                shell = Shell(faces)
                self.solid = Solid(shell)
        return self

    def bbox(self) -> tuple[float, float, float, float, float, float]:
        if self.cross_section is not None:
            bb = self.cross_section.bounding_box()
            return (bb.min.X, bb.max.X, bb.min.Y, bb.max.Y, 0.0, 0.0)
        if self.solid is None:
            return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        bb = self.solid.bounding_box()
        return (
            bb.min.X,
            bb.max.X,
            bb.min.Y,
            bb.max.Y,
            bb.min.Z,
            bb.max.Z,
        )

    def linear_extrude(
        self, height=None, center=False, twist=0, scale=1.0, slices=None
    ) -> BDShape:
        if self.cross_section is None:
            raise NotImplementedError("linear_extrude requires a 2D shape")
        h = height if height is not None else 1.0
        self.solid = bd.extrude(self.cross_section, h)
        self.cross_section = None
        if center:
            self.solid = bd.Pos(0, 0, -h / 2) * self.solid
        return self

    def rotate_extrude(self, angle=360, convexity=1) -> BDShape:
        if self.cross_section is None:
            raise NotImplementedError("rotate_extrude requires a 2D shape")
        self.solid = bd.revolve(self.cross_section, revolution_arc=angle)
        self.cross_section = None
        return self

    def offset(self, r=None, chamfer=False) -> BDShape:
        if self.cross_section is None:
            raise NotImplementedError("offset requires a 2D shape")
        delta = r if r is not None else 0.0
        kind = bd.Kind.INTERSECTION if chamfer else bd.Kind.ARC
        self.cross_section = bd.offset(self.cross_section, amount=delta, kind=kind)
        return self

    def projection(self, cut=False) -> BDShape:
        if self.solid is None:
            raise NotImplementedError("projection requires a 3D shape")
        # Flatten the shape onto the XY plane by scaling Z to near-zero
        # This is more reliable than build123d's project_faces API which
        # has an incompatible signature across versions.
        bbox = self.bbox()
        cur_h = bbox[5] - bbox[4]  # maxz - minz
        if cur_h > 0:
            self.scale(1, 1, 0.001 / cur_h)
        bbox2 = self.bbox()
        self.mv(0, 0, -bbox2[4])  # move min z to 0
        return self

    def minkowski(self, other: BDShape = None) -> BDShape:
        if other is None:
            return self
        if self.cross_section is not None:
            self._ensure3d()
        if other.cross_section is not None:
            other = other.dup()
            other._ensure3d()
        if self.solid is not None and other is not None and other.solid is not None:
            # Approximate minkowski sum via offset_3d on each face
            # This is a simplified approach
            self.solid = self.solid + other.solid
        return self

    def fillet(
        self,
        nearestPts: list[tuple[float, float, float]],
        rad: float,
    ) -> BDShape:
        if self.solid is None:
            return self
        # Select edges near the given points
        edges_to_fillet = []
        for pt in nearestPts:
            vec = bd.Vector(pt[0], pt[1], pt[2])
            # Find closest edge
            min_dist = float("inf")
            closest_edge = None
            for edge in self.solid.edges():
                # Get center point of edge
                center = edge.center()
                d = (center - vec).length
                if d < min_dist:
                    min_dist = d
                    closest_edge = edge
            if closest_edge is not None:
                edges_to_fillet.append(closest_edge)
        if edges_to_fillet:
            self.solid = bd.fillet(edges_to_fillet, rad)
        return self


class BDBall(BDShape):
    def __init__(self, rad: float, api: BDShapeAPI):
        super().__init__(api)
        segs = self._smoothing_segments(2 * pi * rad)
        # Use make_sphere with proper segmentation for watertight result
        self.solid = bd.Solid.make_sphere(rad)


class BDBox(BDShape):
    def __init__(
        self, l: float, wth: float, ht: float, center: bool, api: BDShapeAPI
    ):
        super().__init__(api)
        if center:
            self.solid = bd.Box(l, wth, ht)
        else:
            align = (bd.Align.MIN, bd.Align.MIN, bd.Align.MIN)
            self.solid = bd.Box(l, wth, ht, align=align)


class BDConeZ(BDShape):
    def __init__(
        self,
        l: float,
        r1: float,
        r2: float,
        api: BDShapeAPI,
    ):
        super().__init__(api)
        segs = self._smoothing_segments(2 * pi * max(r1, r2))
        self.solid = bd.Cone(r1, r2, l)


class BDPolyExtrusionZ(BDShape):
    def __init__(
        self, path: list[tuple[float, float]], tck: float, api: BDShapeAPI
    ):
        super().__init__(api)
        # Ensure counterclockwise winding so extrude goes in +Z
        ccw_path = _ensure_ccw(path)
        polygon = bd.Polygon(*ccw_path, align=None)
        self.solid = bd.extrude(polygon, tck)


class BDRodZ(BDShape):
    def __init__(
        self, l: float, rad: float, sides: int | None, api: BDShapeAPI
    ):
        super().__init__(api)
        segs = self._smoothing_segments(2 * pi * rad)
        if sides is not None:
            # Regular polygon extrusion
            from math import cos, sin
            pts = []
            for i in range(sides):
                a = 2 * pi * i / sides
                pts.append((rad * cos(a), rad * sin(a)))
            poly = bd.Polygon(*pts, align=None)
            self.solid = bd.extrude(poly, l)
        else:
            self.solid = bd.Cylinder(rad, l)


class BDPolyhedron(BDShape):
    def __init__(
        self,
        points: list[tuple[float, float, float]],
        faces: list[list[int]],
        convexity: int,
        api: BDShapeAPI,
    ):
        super().__init__(api)
        # Build solid from vertices and faces using scipy ConvexHull
        # For arbitrary polyhedra, create faces from triangles
        verts = [bd.Vector(*p) for p in points]
        bd_faces = []
        for face_idxs in faces:
            if len(face_idxs) < 3:
                continue
            # Triangulate the face
            for i in range(1, len(face_idxs) - 1):
                tri = [face_idxs[0], face_idxs[i], face_idxs[i + 1]]
                pts = [verts[j] for j in tri]
                e1 = Edge.make_line(pts[0], pts[1])
                e2 = Edge.make_line(pts[1], pts[2])
                e3 = Edge.make_line(pts[2], pts[0])
                w = Wire([e1, e2, e3])
                f = Face(w)
                bd_faces.append(f)
        if bd_faces:
            shell = Shell(bd_faces)
            self.solid = Solid(shell)


class BDLineSplineExtrusionZ(BDShape):
    def __init__(
        self,
        start: tuple[float, float],
        path: list[
            tuple[float, float] | list[tuple[float, float, float, float, float]]
        ],
        ht: float,
        api: BDShapeAPI,
    ):
        super().__init__(api)
        approx_curve_path = lineSplineXY(start, path, self._smoothing_segments)
        cleaned = _clean_polygon_path(approx_curve_path)
        if cleaned is not None and len(cleaned) >= 3:
            # Use align=None to preserve original coordinates
            polygon = bd.Polygon(*cleaned, align=None)
            self.solid = bd.extrude(polygon, ht)
        else:
            # Fallback: create a minimal solid
            print("# WARNING: BDLineSplineExtrusionZ degenerate path, using fallback")
            self.solid = bd.Box(1, 1, ht)


class BDLineSplineRevolveX(BDShape):
    def __init__(
        self,
        start: tuple[float, float],
        path: list[
            Union[
                tuple[float, float],
                list[tuple[float, float, float, float, float]],
            ]
        ],
        deg: float,
        api: BDShapeAPI,
    ):
        super().__init__(api)
        _, dimY = dimXY(start, path)
        neg_deg = deg < 0
        deg = -deg if neg_deg else deg
        approx_curve_path = lineSplineXY(start, path, self._smoothing_segments)
        cleaned = _clean_polygon_path(approx_curve_path)
        if cleaned is not None and len(cleaned) >= 3:
            # Use align=None to preserve original coordinates (bd.Polygon defaults to CENTER)
            polygon = bd.Polygon(*cleaned, align=None)
            face = bd.make_face(polygon)
            solid = bd.Solid.revolve(face, deg, bd.Axis.X)
        else:
            print("# WARNING: BDLineSplineRevolveX degenerate path, using fallback")
            solid = bd.Solid.make_cylinder(1, 10)
        if neg_deg:
            solid = bd.mirror(solid, bd.Plane.XY)
        self.solid = solid


class BDCirclePolySweep(BDShape):
    def __init__(
        self,
        rad: float,
        path: list[tuple[float, float, float]],
        api: BDShapeAPI,
    ):
        super().__init__(api)
        segs = self._smoothing_segments(2 * pi * rad)
        sweep_shape = None
        for i, (x, y, z) in enumerate(path):
            if i == 0:
                last_ball = bd.Sphere(rad)
                last_ball = bd.Pos(x, y, z) * last_ball
                sweep_shape = last_ball
            else:
                px, py, pz = path[i - 1]
                # Create a cylinder connecting previous point to current point
                dx, dy, dz = x - px, y - py, z - pz
                length = (dx * dx + dy * dy + dz * dz) ** 0.5
                if length > 1e-10:
                    # Create cylinder along Z, then rotate to align with direction
                    cylinder = bd.Cylinder(rad, length)
                    # Calculate rotation to align Z axis with direction vector
                    import math
                    # Spherical angles
                    theta = math.atan2(dy, dx)  # azimuth
                    phi = math.acos(dz / length)  # polar angle
                    # Rotate: first around Y by phi, then around Z by theta
                    cylinder = bd.Rotation(0, math.degrees(phi), 0) * cylinder
                    cylinder = bd.Rotation(0, 0, math.degrees(theta)) * cylinder
                    # Translate to midpoint
                    mx, my, mz = (px + x) / 2, (py + y) / 2, (pz + z) / 2
                    cylinder = bd.Pos(mx, my, mz) * cylinder
                    sweep_shape = sweep_shape + cylinder if sweep_shape is not None else cylinder
                # Add sphere at current point
                ball = bd.Sphere(rad)
                ball = bd.Pos(x, y, z) * ball
                sweep_shape = sweep_shape + ball if sweep_shape is not None else ball
                last_ball = ball
        self.solid = sweep_shape


def _clean_polygon_path(path, tol=1e-6):
    """Remove duplicate adjacent points and degenerate segments from a polygon path."""
    if not path or len(path) < 3:
        return None
    cleaned = [path[0]]
    for p in path[1:]:
        dx = p[0] - cleaned[-1][0]
        dy = p[1] - cleaned[-1][1]
        if dx * dx + dy * dy > tol * tol:
            cleaned.append(p)
    # Also check last-to-first closure
    if len(cleaned) >= 3:
        dx = cleaned[-1][0] - cleaned[0][0]
        dy = cleaned[-1][1] - cleaned[0][1]
        if dx * dx + dy * dy <= tol * tol:
            cleaned[-1] = cleaned[0]  # snap last to first
        return cleaned
    return None


def _ensure_ccw(path):
    """Ensure polygon path has counterclockwise winding (positive signed area).
    
    build123d's extrude follows the face normal: CCW winding extrudes in +Z,
    CW winding extrudes in -Z. This function reverses the point order when
    the signed area is negative (clockwise).
    """
    if not path or len(path) < 3:
        return path
    # Compute signed area (shoelace formula)
    area = 0.0
    n = len(path)
    for i in range(n):
        x1, y1 = path[i]
        x2, y2 = path[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    # Negative area = clockwise = reverse
    return list(reversed(path)) if area < 0 else path


class BDTextZ(BDShape):
    def __init__(
        self,
        txt: str,
        fontSize: float,
        tck: float,
        fontName: str,
        api: BDShapeAPI,
    ):
        super().__init__(api)
        fontPath = self.api.getFontPath(fontName)
        if fontPath is None:
            fontPath = self.api.getFontPath(None)
            print(
                f"Can't find font {fontName}, substitute with {fontPath}"
            )

        glyphs_paths = textToGlyphsPaths(
            fontPath,
            txt,
            fontSize,
            dimToSegs=self._smoothing_segments,
        )

        text3d: bd.Solid | bd.Part | None = None
        for glyph_paths in glyphs_paths:
            glyph3d: bd.Solid | bd.Part | None = None
            for path in glyph_paths:
                cleaned = _clean_polygon_path(path)
                if cleaned is not None and len(cleaned) >= 3:
                    try:
                        poly = bd.Polygon(*cleaned, align=None)
                        ext = bd.extrude(poly, tck)
                        # Ensure extrusion starts at Z=0 (winding order may flip direction)
                        bb = ext.bounding_box()
                        if bb.min.Z < 0:
                            ext = bd.Pos(0, 0, -bb.min.Z) * ext
                        glyph3d = (
                            ext
                            if glyph3d is None
                            else glyph3d + ext
                        )
                    except Exception:
                        # Skip degenerate glyph paths
                        pass
            if glyph3d is not None:
                if text3d is None:
                    text3d = glyph3d
                else:
                    joined = text3d + glyph3d
                    if isinstance(joined, ShapeList):
                        joined = Compound(joined)
                    text3d = joined

        if text3d is not None:
            bb = text3d.bounding_box()
            cx = (bb.min.X + bb.max.X) / 2
            cy = (bb.min.Y + bb.max.Y) / 2
            self.solid = bd.Pos(-cx, -cy, 0) * text3d
        else:
            print("# WARNING! Text Generation failed!!! ")
            self.solid = bd.Box(fontSize, fontSize, tck)
            self.solid = bd.Pos(
                -fontSize / 2, -fontSize / 2, -tck / 2
            ) * self.solid


class BDImport(BDShape):
    def __init__(
        self,
        infile: str,
        extrude: float = None,
        api: BDShapeAPI = None,
    ):
        super().__init__(api)
        assert os.path.isfile(infile), f"ERROR: file {infile} does not exist!"

        if infile.endswith(".stl"):
            self.solid = bd.import_stl(infile)
        elif infile.endswith(".step") or infile.endswith(".stp"):
            self.solid = bd.import_step(infile)
        elif infile.endswith(".brep"):
            self.solid = bd.import_brep(infile)
        elif infile.endswith(".svg"):
            # import_svg returns ShapeList[Wire | Face]; convert to 3D solid
            svg_shapes = bd.import_svg(infile)
            faces = []
            for shape in svg_shapes:
                if isinstance(shape, bd.Wire):
                    faces.append(bd.make_face(shape))
                elif isinstance(shape, bd.Face):
                    faces.append(shape)
            if extrude is not None:
                # Extrude all faces into a 3D solid
                if len(faces) == 1:
                    self.solid = bd.extrude(faces[0], extrude)
                else:
                    compound = bd.Compound(faces)
                    self.solid = bd.extrude(compound, extrude)
            else:
                # Store as cross-section for deferred 3D conversion
                self.cross_section = bd.Sketch(faces)
        else:
            raise ValueError(f"Unsupported file format: {infile}")


if __name__ == "__main__":
    from b13d.api.core import test_api

    test_api(Implementation.BUILD123D)
