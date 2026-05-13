#!/usr/bin/env python3

from __future__ import annotations
import os
from pathlib import Path
import sys
from typing import Union

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))

from b13d.api.core import ShapeAPI, Shape, test_api
from b13d.api.utils import gen_stl_foo


class MockShapeAPI(ShapeAPI):
    """
    Mock Pylele API implementation for test
    """

    def export(self, shape: MockShape, path: Union[str, Path],fmt=".stl") -> None:
        return self.export_stl(shape=shape, path=path)

    def export_stl(self, shape: MockShape, path: str) -> None:
        gen_stl_foo(path)

    def export_best(self, shape: MockShape, path: Union[str, Path]) -> None:
        return self.export_stl(shape=shape, path=path)

    def sphere(self, r: float) -> MockShape:
        return MockShape(self)

    def box(self, l: float, wth: float, ht: float, center: bool = True) -> MockShape:
        if center:
            bbox = (-l/2, l/2, -wth/2, wth/2, -ht/2, ht/2)
        else:
            bbox = (0, l, 0, wth, 0, ht)
        return MockShape(self, bbox=bbox)

    def cone_x(self, h: float, r1: float, r2: float) -> MockShape:
        return MockShape(self)

    def cone_y(self, h: float, r1: float, r2: float) -> MockShape:
        return MockShape(self)

    def cone_z(self, h: float, r1: float, r2: float) -> MockShape:
        return MockShape(self)

    def regpoly_extrusion_x(self, l: float, rad: float, sides: int) -> MockShape:
        return MockShape(self)

    def regpoly_extrusion_y(self, l: float, rad: float, sides: int) -> MockShape:
        return MockShape(self)

    def regpoly_extrusion_z(self, l: float, rad: float, sides: int) -> MockShape:
        return MockShape(self)

    def cylinder_x(self, l: float, rad: float) -> MockShape:
        return MockShape(self)

    def cylinder_y(self, l: float, rad: float) -> MockShape:
        return MockShape(self)

    def cylinder_z(self, l: float, rad: float) -> MockShape:
        return MockShape(self)

    def polygon_extrusion(
        self, path: list[tuple[float, float]], ht: float
    ) -> MockShape:
        xs = [p[0] for p in path]
        ys = [p[1] for p in path]
        bbox = (min(xs), max(xs), min(ys), max(ys), 0, ht)
        return MockShape(self, bbox=bbox)

    def spline_extrusion(
        self,
        start: tuple[float, float],
        path: list[tuple[float, float] | list[tuple[float, float, float, float]]],
        ht: float,
    ) -> MockShape:
        return MockShape(self)

    def spline_revolve(
        self,
        start: tuple[float, float],
        path: list[tuple[float, float] | list[tuple[float, float, float, float]]],
        deg: float,
    ) -> MockShape:
        return MockShape(self)

    def regpoly_sweep(
        self, rad: float, path: list[tuple[float, float, float]]
    ) -> MockShape:
        return MockShape(self)

    def text(self, txt: str, fontSize: float, tck: float, font: str) -> MockShape:
        return MockShape(self)
    
    def polyhedron(
        self,
        points: list[tuple[float, float, float]],
        faces: list[list[int]],
        convexity: int = 1,
    ) -> MockShape:
        return MockShape(self)
    
    def genImport(self, infile: str, extrude: float = None) -> MockShape:
        assert os.path.exists(infile)
        assert isinstance(extrude, (int, float))
        return MockShape(self)

    def genShape(self, solid) -> MockShape:
        """ Currently just mimics SolidPython2 implementation """
        return MockShape(self)

    def rectangle(self, size, center=False) -> MockShape:
        return MockShape(self)

    def circle(self, r=None, d=None) -> MockShape:
        return MockShape(self)

    def polygon(self, points, paths=None, convexity=1) -> MockShape:
        return MockShape(self)

class MockShape(Shape):
    """
    Mock Pylele Shape implementation for test
    """

    def __init__(self, api, bbox=None):
        """Initialize mock shape with optional bounding box."""
        solid = object() if bbox is not None else None
        super().__init__(api, solid=solid)
        self._bbox = bbox if bbox is not None else (0, 1, 2, 3, 4, 5)

    def bbox(self):
        return self._bbox

    def cut(self, cutter: MockShape) -> MockShape:
        self.solid = None
        return self

    def dup(self) -> MockShape:
        return MockShape(self.api, bbox=tuple(self._bbox))

    def join(self, joiner: MockShape) -> MockShape:
        b1 = self._bbox
        b2 = joiner._bbox
        self._bbox = (
            min(b1[0], b2[0]), max(b1[1], b2[1]),
            min(b1[2], b2[2]), max(b1[3], b2[3]),
            min(b1[4], b2[4]), max(b1[5], b2[5]),
        )
        return self

    def intersection(self, intersector: MockShape) -> MockShape:
        return self

    def mirror(self, normal=(0, 1, 0)) -> MockShape:
        # Create a copy with reflected bbox across the plane through origin.
        bbox = list(self._bbox)
        if normal == (0, 1, 0):
            # Reflect Y: swap and negate MINY/MAXY
            bbox[2], bbox[3] = -bbox[3], -bbox[2]
        elif normal == (1, 0, 0):
            bbox[0], bbox[1] = -bbox[1], -bbox[0]
        elif normal == (0, 0, 1):
            bbox[4], bbox[5] = -bbox[5], -bbox[4]
        return MockShape(self.api, bbox=tuple(bbox))

    def mv(self, x: float, y: float, z: float) -> MockShape:
        self._bbox = (
            self._bbox[0] + x, self._bbox[1] + x,
            self._bbox[2] + y, self._bbox[3] + y,
            self._bbox[4] + z, self._bbox[5] + z,
        )
        return self

    def rotate_x(self, ang: float) -> MockShape:
        return self

    def rotate_y(self, ang: float) -> MockShape:
        return self

    def rotate_z(self, ang: float) -> MockShape:
        return self

    def scale(self, x: float, y: float, z: float) -> MockShape:
        # Scale bbox around origin
        self._bbox = (
            self._bbox[0] * x, self._bbox[1] * x,
            self._bbox[2] * y, self._bbox[3] * y,
            self._bbox[4] * z, self._bbox[5] * z,
        )
        return self
        
    def hull(self) -> MockShape:
        return self
    
    def linear_extrude(self, height=None, center=False, twist=0, scale=1.0, slices=None) -> MockShape:
        return self

    def rotate_extrude(self, angle=360, convexity=1) -> MockShape:
        return self

    def offset(self, r=None, chamfer=False) -> MockShape:
        return self

    def projection(self, cut=False) -> MockShape:
        return self

    def minkowski(self, other=None) -> MockShape:
        return self

if __name__ == "__main__":
    test_api("mock")
