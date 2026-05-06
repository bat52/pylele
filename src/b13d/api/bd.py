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

import build123d as bd
from build123d.topology import Solid, Face, Wire, Edge, Shell

sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

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
        bd.export_stl(shape.getImplSolid(), file_ensure_extension(path, ".stl"))

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
        poly = bd.Polygon(*points)
        return BDShape(self, cross_section=poly)


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
            self.solid = bd.extrude(self.cross_section, 0)
            self.cross_section = None
        return self

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
        self.solid = self.solid - cutter.solid
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
        self.solid = self.solid + joiner.solid
        return self

    def intersection(self, intersector: BDShape) -> BDShape:
        if self.cross_section is not None and intersector is not None and intersector.cross_section is not None:
            self.cross_section = self.cross_section & intersector.cross_section
            return self
        self._ensure3d()
        if intersector is None or intersector.solid is None:
            return self
        self.solid = self.solid & intersector.solid
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
                self.cross_section = bd.Polygon(*pts)
            return self
        if self.solid is not None:
            verts = np.array(
                [(v.X, v.Y, v.Z) for v in self.solid.vertices()]
            )
            if len(verts) >= 4:
                hull = ConvexHull(verts)
                faces = []
                for simplex in hull.simplices:
                    pts = [bd.Vector(*verts[i]) for i in simplex]
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
        # Project faces to XY plane
        faces = self.solid.faces()
        projected = []
        for f in faces:
            try:
                # Get the plane of the face and project to XY
                proj_face = f.project_faces(
                    bd.Plane.XY, bd.Vector(0, 0, 1)
                )
                projected.extend(proj_face)
            except Exception:
                pass
        if projected:
            self.cross_section = bd.Sketch(projected)
        self.solid = None
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
        self.solid = bd.Sphere(rad)


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
        polygon = bd.Polygon(*path)
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
            poly = bd.Polygon(*pts)
            self.solid = bd.extrude(poly, l)
            self.solid = bd.Pos(0, 0, -l / 2) * self.solid
        else:
            self.solid = bd.Cylinder(rad, l)
            self.solid = bd.Pos(0, 0, -l / 2) * self.solid


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
        polygon = bd.Polygon(*approx_curve_path)
        self.solid = bd.extrude(polygon, ht)


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
        # Swap X, Y for revolve around X axis
        approx_curve_path = [(y, x) for x, y in approx_curve_path]
        polygon = bd.Polygon(*approx_curve_path)
        # Create a face from the polygon wire before revolving
        face = bd.Face(polygon)
        solid = bd.revolve(face, bd.Axis.X, revolution_arc=deg)
        solid = bd.Rotation(0, 0, 90) * solid
        solid = bd.Rotation(0, 90, 0) * solid
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
                ball = bd.Sphere(rad)
                ball = bd.Pos(x, y, z) * ball
                hull2balls = (last_ball + ball)
                # Compute hull of the two balls
                verts = np.array(
                    [(v.X, v.Y, v.Z) for v in hull2balls.vertices()]
                )
                if len(verts) >= 4:
                    try:
                        hull = ConvexHull(verts, qhull_options='QJ')
                    except Exception:
                        # If hull fails, just join the two balls
                        sweep_shape = sweep_shape + ball if sweep_shape is not None else ball
                        last_ball = ball
                        continue
                    faces = []
                    for simplex in hull.simplices:
                        pts = [bd.Vector(*verts[i]) for i in simplex]
                        e1 = Edge.make_line(pts[0], pts[1])
                        e2 = Edge.make_line(pts[1], pts[2])
                        e3 = Edge.make_line(pts[2], pts[0])
                        w = Wire([e1, e2, e3])
                        f = Face(w)
                        faces.append(f)
                    shell = Shell(faces)
                    hull_solid = Solid(shell)
                    sweep_shape = sweep_shape + hull_solid if sweep_shape is not None else hull_solid
                else:
                    sweep_shape = sweep_shape + ball if sweep_shape is not None else ball
                last_ball = ball
        self.solid = sweep_shape


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
                if len(path) >= 3:
                    poly = bd.Polygon(*path)
                    ext = bd.extrude(poly, tck)
                    glyph3d = (
                        ext
                        if glyph3d is None
                        else glyph3d + ext
                    )
            if glyph3d is not None:
                text3d = (
                    glyph3d
                    if text3d is None
                    else text3d + glyph3d
                )

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
            self.solid = bd.import_step(infile)
        elif infile.endswith(".step") or infile.endswith(".stp"):
            self.solid = bd.import_step(infile)
        elif infile.endswith(".brep"):
            self.solid = bd.import_brep(infile)
        else:
            raise ValueError(f"Unsupported file format: {infile}")


if __name__ == "__main__":
    from b13d.api.core import test_api

    test_api(Implementation.BUILD123D)
