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
        mesh.save(file_ensure_extension(path, ".stl"))

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
        return PVShape(self, mesh=pv.Polygon(points))


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
        self.solid = self.solid.boolean_subtract(cutter.solid)
        return self

    def dup(self) -> PVShape:
        duplicate = copy.copy(self)
        if self.solid is not None:
            duplicate.solid = self.solid.copy()
        return duplicate

    def join(self, joiner: PVShape) -> PVShape:
        if joiner is None:
            return self
        if self.solid is None:
            return self
        if joiner.solid is None:
            return self
        self.solid = self.solid.boolean_union(joiner.solid)
        return self

    def intersection(self, intersector: PVShape) -> PVShape:
        if intersector is None:
            return self
        if self.solid is None:
            return self
        if intersector.solid is None:
            return self
        self.solid = self.solid.boolean_intersection(intersector.solid)
        return self

    def mirror(self, normal=(0, 1, 0)) -> PVShape:
        dup = copy.copy(self)
        if self.solid is not None:
            origin = (0, 0, 0)
            dup.solid = self.solid.reflect(normal, origin, 0)
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
            points = self.solid.points
            hull = pv.PolyData(points).delaunay_2d()
            self.solid = hull
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
        self.solid = self.solid.extrude((0, 0, h), capping=True)
        return self

    def rotate_extrude(self, angle=360, convexity=1) -> PVShape:
        """Rotate extrusion of a 2D shape around the Z-axis.
        
        Args:
            angle: Angle of rotation in degrees (default 360 for full revolution)
            convexity: Convexity parameter (not used in current implementation)
            
        Note:
            Uses fixed resolution of 36 segments for the revolve operation.
        """
        if self.solid is None:
            raise NotImplementedError("rotate_extrude requires a 2D shape")
        self.solid = self.solid.revolve(angle, resolution=36)
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
        self.solid = pv.Cone(height=h, radius_bottom=r1, radius_top=r2, resolution=int(segs))


class PVPolyExtrusionZ(PVShape):
    def __init__(self, path: list[tuple[float, float]], tck: float, api: PVShapeAPI):
        super().__init__(api)
        polygon = pv.Polygon(path)
        self.solid = polygon.extrude((0, 0, tck), capping=True)


class PVRodZ(PVShape):
    def __init__(self, l: float, rad: float, sides: float, api: PVShapeAPI):
        super().__init__(api)
        segs = sides if sides is not None else self._smoothing_segments(2 * pi * rad)
        self.solid = pv.Cylinder(radius=rad, height=l, resolution=int(segs)).translate((0, 0, -l/2))


class PVPolyhedron(PVShape):
    def __init__(self, points: list[tuple[float, float, float]], faces: list[list[int]], convexity: int, api: PVShapeAPI):
        super().__init__(api)
        triangles = []
        for face in faces:
            if len(face) >= 3:
                for i in range(1, len(face) - 1):
                    triangles.append([face[0], face[i], face[i + 1]])
        faces_arr = np.array(triangles, dtype=np.int64).flatten()
        faces_arr = np.insert(faces_arr, 0, 3 * len(triangles))
        self.solid = pv.PolyData(np.array(points), faces_arr)


class PVLineSplineExtrusionZ(PVShape):
    def __init__(self, start: tuple[float, float], path: list, ht: float, api: PVShapeAPI):
        super().__init__(api)
        self.path = path
        self.ht = ht
        approx_curve_path = lineSplineXY(start, path, self._smoothing_segments)
        polygon = pv.Polygon(approx_curve_path)
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
        polygon = pv.Polygon(approx_curve_path)
        self.solid = polygon.revolve(deg, resolution=segs)
        self.solid = self.solid.rotate_z(90).rotate_y(90)
        if deg < 0:
            self.solid = self.solid.reflect((0, 0, 1), (0, 0, 0), 0)


class PVCirclePolySweep(PVShape):
    def __init__(self, rad: float, path: list[tuple[float, float, float]], api: PVShapeAPI):
        super().__init__(api)
        segs = self._smoothing_segments(2 * pi * rad)
        sweep_shape = None
        for i, (x, y, z) in enumerate(path):
            if i == 0:
                last_ball = pv.Sphere(radius=rad, phi_resolution=segs, theta_resolution=segs).translate((x, y, z))
                sweep_shape = last_ball
            else:
                ball = pv.Sphere(radius=rad, phi_resolution=segs, theta_resolution=segs).translate((x, y, z))
                hull2balls = pv.PolyData(np.vstack([last_ball.points, ball.points])).delaunay_3d().extract_surface()
                sweep_shape = sweep_shape.boolean_union(hull2balls)
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
            glyph3d = None
            for path in glyph_paths:
                if len(path) >= 3:
                    polygon = pv.Polygon(path)
                    extruded = polygon.extrude((0, 0, tck), capping=True)
                    glyph3d = extruded if glyph3d is None else glyph3d.boolean_union(extruded)
            if glyph3d is not None:
                text3d = glyph3d if text3d is None else text3d.boolean_union(glyph3d)

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

        if infile.endswith(".stl"):
            self.solid = pv.read(infile)
        elif infile.endswith(".svg"):
            import trimesh
            mesh = trimesh.load_path(infile)
            self.solid = pv.wrap(mesh)
            if extrude is not None:
                self.solid = self.solid.extrude((0, 0, extrude), capping=True)
        elif infile.endswith(".step") or infile.endswith(".stp"):
            self.solid = pv.read(infile)
        else:
            raise ValueError(f"Unsupported file format: {infile}")


if __name__ == "__main__":
    test_api(Implementation.PYVISTA)