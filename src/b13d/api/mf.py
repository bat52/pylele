#!/usr/bin/env python3

from __future__ import annotations
import copy
from math import pi, ceil
try:
    from manifold3d import Manifold, CrossSection, FillRule, Mesh, JoinType
    MF_AVAILABLE = True
except ImportError:
    Manifold = None
    CrossSection = None
    FillRule = None
    Mesh = None
    JoinType = None
    MF_AVAILABLE = False
import numpy as np
import os
from pathlib import Path
import sys
from typing import Union
from svgpathtools import svg2paths, Arc
import trimesh
import numpy as np
from enum import Enum

sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

from b13d.api.core import ShapeAPI, Shape, test_api, Direction, Implementation
from b13d.api.utils import dimXY, file_ensure_extension, lineSplineXY, textToGlyphsPaths

def _triangulate_faces(faces: list[list[int]]) -> np.ndarray:
    triangles = []
    for face in faces:
        if len(face) < 3:
            continue
        for i in range(1, len(face) - 1):
            triangles.append([face[0], face[i], face[i + 1]])
    return np.array(triangles, dtype=np.int64)


"""
    Encapsulate Manifold3d implementation specific calls
"""


class MFShapeAPI(ShapeAPI):

    def export_stl(self, shape: MFShape, path: Union[str, Path]) -> None:

        def calculate_normals(vertices, faces):
            # Vertices shape: (vn, 3), Faces shape: (fn, 3)

            # Get the vertices for each face using the face indices
            v1 = vertices[faces[:, 0]]
            v2 = vertices[faces[:, 1]]
            v3 = vertices[faces[:, 2]]

            # Calculate two edge vectors for each triangle
            edge1 = v2 - v1
            edge2 = v3 - v1

            # Compute the cross product (normal) of each triangle's edge vectors
            normals = np.cross(edge1, edge2)

            # Normalize the resulting normals
            normal_magnitudes = np.linalg.norm(normals, axis=1).reshape(-1, 1)
            normalized_normals = normals / np.where(
                normal_magnitudes == 0, 1, normal_magnitudes
            )  # Avoid divide by zero
            return normalized_normals

        def face_idxs_to_vertices(vertices, faces):
            """
            Translate face indices to face vertices.

            Parameters:
            - vertices: numpy array of shape (vn, 3), representing vertex coordinates.
            - faces: numpy array of shape (fn, 3), representing indices of the vertices that form each triangular face.

            Returns:
            - face_vertices: numpy array of shape (fn, 3, 3) where each face is represented by its corresponding vertex coordinates.
            """
            # Use numpy advanced indexing to map face indices to actual vertex coordinates
            face_vertices = vertices[faces]
            return face_vertices

        # define a numpy datatype for the data section of a binary STL file
        # everything in STL is always Little Endian
        # this works natively on Little Endian systems, but blows up on Big Endians
        # so we always specify byteorder
        stl_dtype = np.dtype(
            [
                ("normals", "<f4", (3)),
                ("vertices", "<f4", (3, 3)),
                ("attributes", "<u2"),
            ]
        )
        # define a numpy datatype for the header of a binary STL file
        stl_dtype_header = np.dtype([("header", np.void, 80), ("face_count", "<u4")])

        obj_mesh = shape.getImplSolid().to_mesh()
        vertices = obj_mesh.vert_properties
        face_tri_idxs = obj_mesh.tri_verts
        face_normals = calculate_normals(vertices, face_tri_idxs)

        header = np.zeros(1, dtype=stl_dtype_header)
        header["face_count"] = len(face_tri_idxs)
        export = header.tobytes()
        packed = np.zeros(len(face_tri_idxs), dtype=stl_dtype)
        packed["normals"] = face_normals
        packed["vertices"] = face_idxs_to_vertices(vertices, face_tri_idxs)
        export += packed.tobytes()

        # Open a file in binary write mode and write the data to it
        with open(file_ensure_extension(path, ".stl"), "wb") as file:
            file.write(export)

    def export_best(self, shape: MFShape, path: Union[str, Path]) -> None:
        self.export_stl(shape, path)

    def export(self, shape: MFShape, path: Union[str, Path],fmt=".stl") -> None:
        self.export_stl(shape=shape,path=path)

    def sphere(self, r: float) -> MFShape:
        return MFBall(r, self)

    def box(self, l: float, wth: float, ht: float, center: bool = True) -> MFShape:
        return MFBox(l, wth, ht, center, self)

    def cone_x(self, h: float, r1: float, r2: float) -> MFShape:
        return MFConeZ(h, r1, r2, None, self).rotate_y(90)

    def cone_y(self, h: float, r1: float, r2: float) -> MFShape:
        return MFConeZ(h, r1, r2, None, self).rotate_x(-90)

    def cone_z(self, h: float, r1: float, r2: float) -> MFShape:
        return MFConeZ(h, r1, r2, None, self)

    def regpoly_extrusion_x(self, l: float, rad: float, sides: int) -> MFShape:
        return MFRodZ(l, rad, sides, self).rotate_y(90)

    def regpoly_extrusion_y(self, l: float, rad: float, sides: int) -> MFShape:
        return MFRodZ(l, rad, sides, self).rotate_x(90)

    def regpoly_extrusion_z(self, l: float, rad: float, sides: int) -> MFShape:
        return MFRodZ(l, rad, sides, self)

    def cylinder_x(self, l: float, rad: float) -> MFShape:
        return MFRodZ(l, rad, None, self).rotate_y(90)

    def cylinder_y(self, l: float, rad: float) -> MFShape:
        return MFRodZ(l, rad, None, self).rotate_x(90)

    def cylinder_z(self, l: float, rad: float) -> MFShape:
        return MFRodZ(l, rad, None, self)

    def polygon_extrusion(self, path: list[tuple[float, float]], ht: float) -> MFShape:
        return MFPolyExtrusionZ(path, ht, self)

    def spline_extrusion(
        self,
        start: tuple[float, float],
        path: list[
            tuple[float, float] | list[tuple[float, float, float, float, float]]
        ],
        ht: float,
    ) -> MFShape:
        if ht < 0:
            return MFLineSplineExtrusionZ(start, path, abs(ht), self).mv(0, 0, -abs(ht))
        return MFLineSplineExtrusionZ(start, path, ht, self)

    def spline_revolve(
        self,
        start: tuple[float, float],
        path: list[
            tuple[float, float] | list[tuple[float, float, float, float, float]]
        ],
        deg: float,
    ) -> MFShape:
        return MFLineSplineRevolveX(start, path, deg, self)

    def regpoly_sweep(
        self, rad: float, path: list[tuple[float, float, float]]
    ) -> MFShape:
        return MFCirclePolySweep(rad, path, self)

    def text(self, txt: str, fontSize: float, tck: float, font: str) -> MFShape:
        return MFTextZ(txt, fontSize, tck, font, self)

    def polyhedron(
        self,
        points: list[tuple[float, float, float]],
        faces: list[list[int]],
        convexity: int = 1,
    ) -> MFShape:
        return MFPolyhedron(points, faces, convexity, self)

    def tolerance(self) -> float:
        return self.implementation.tolerance()
    
    def genImport(self, infile: str, extrude: float = None) -> MFShape:
        return MFImport(infile, extrude=extrude)

    def rectangle(self, size, center=False) -> MFShape:
        size = size if isinstance(size, (list, tuple)) else (size, size)
        w, h = size[0], size[1]
        pts = [(0, 0), (w, 0), (w, h), (0, h)]
        cs = CrossSection([pts], FillRule.EvenOdd)
        if center:
            cs = cs.translate((-w/2, -h/2))
        return MFShape(self, cross_section=cs)

    def circle(self, r=None, d=None) -> MFShape:
        if r is None and d is not None:
            r = d / 2.0
        segs = 64
        from math import cos, sin, pi
        pts = []
        for i in range(segs):
            a = 2 * pi * i / segs
            pts.append((r * cos(a), r * sin(a)))
        cs = CrossSection([pts], FillRule.EvenOdd)
        return MFShape(self, cross_section=cs)

    def polygon(self, points, paths=None, convexity=1) -> MFShape:
        cs = CrossSection([list(points)], FillRule.EvenOdd)
        return MFShape(self, cross_section=cs)

    def genImport(self, infile: str, extrude: float = None) -> MFShape:
        return MFImport(infile, extrude=extrude, api=self)

class MFShape(Shape):

    def __init__(self, api: MFShapeAPI, solid: Manifold = None,
                 color: tuple[int, int, int] = None,
                 cross_section: CrossSection = None):
        super().__init__(api, solid=solid, color=color)
        self.cross_section: CrossSection = cross_section

    def getAPI(self) -> MFShapeAPI:
        return self.api

    def getImplSolid(self) -> Manifold:
        return self.solid

    def _smoothing_segments(self, dim: float) -> int:
        return ceil(abs(dim) ** 0.5 * self.api.fidelity.smoothing_segments())

    def _ensure3d(self) -> MFShape:
        """If cross_section is set but solid is None, convert to 3D via dummy extrude."""
        if self.cross_section is not None and self.solid is None:
            self.solid = Manifold.extrude(self.cross_section, 0)
            self.cross_section = None
        return self

    def cut(self, cutter: MFShape) -> MFShape:
        if self.cross_section is not None and cutter.cross_section is not None:
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

    def dup(self) -> MFShape:
        duplicate = copy.copy(self)
        if duplicate.cross_section is not None:
            duplicate.cross_section = CrossSection(
                duplicate.cross_section.decompose(), FillRule.EvenOdd
            )
        elif duplicate.solid is not None:
            duplicate.solid = Manifold.compose(
                self.solid.decompose()
            )
        return duplicate

    def join(self, joiner: MFShape) -> MFShape:
        if self.cross_section is not None and joiner is not None and joiner.cross_section is not None:
            self.cross_section = self.cross_section + joiner.cross_section
            return self
        self._ensure3d()
        if joiner is None or joiner.solid is None:
            return self
        self.solid = self.solid + joiner.solid
        return self

    def intersection(self, intersector: MFShape) -> MFShape:
        if self.cross_section is not None and intersector is not None and intersector.cross_section is not None:
            self.cross_section &= intersector.cross_section
            return self
        self._ensure3d()
        if intersector is None or intersector.solid is None:
            return self
        self.solid ^= intersector.solid
        return self

    def mirror(self, normal=(0, 1, 0)) -> MFShape:
        dup = copy.copy(self)
        if self.cross_section is not None:
            dup.cross_section = self.cross_section.mirror((1, 0))
        elif self.solid is not None:
            dup.solid = self.solid.mirror(normal)
        return dup

    def mv(self, x: float, y: float, z: float) -> MFShape:
        if x == 0 and y == 0 and z == 0:
            return self
        if self.cross_section is not None:
            self.cross_section = self.cross_section.translate((x, y))
        elif self.solid is not None:
            self.solid = self.solid.translate((x, y, z))
        return self

    def rotate_x(self, ang: float) -> MFShape:
        if self.cross_section is not None:
            self._ensure3d()
        if self.solid is not None:
            self.solid = self.solid.rotate((ang, 0, 0))
        return self

    def rotate_y(self, ang: float) -> MFShape:
        if self.cross_section is not None:
            self._ensure3d()
        if self.solid is not None:
            self.solid = self.solid.rotate((0, ang, 0))
        return self

    def rotate_z(self, ang: float) -> MFShape:
        if self.cross_section is not None:
            self.cross_section = self.cross_section.rotate(ang)
        elif self.solid is not None:
            self.solid = self.solid.rotate((0, 0, ang))
        return self
    
    def rotate(self, ang: float | int | tuple[float,float,float], direction: Direction = Direction.Z) -> MFShape:
        if isinstance(ang,float) or isinstance(ang,int):
            return Shape.rotate(self, ang, direction)
        if self.cross_section is not None:
            self._ensure3d()
        if self.solid is not None:
            self.solid = self.solid.rotate((ang[0], ang[1], ang[2]))
        return self

    def scale(self, x: float, y: float, z: float) -> MFShape:
        if x == 1 and y == 1 and z == 1:
            return self
        if self.cross_section is not None:
            self.cross_section = self.cross_section.scale((x, y))
        elif self.solid is not None:
            self.solid = self.solid.scale((x, y, z))
        return self
    
    def hull(self) -> MFShape:
        if self.cross_section is not None:
            self.cross_section = self.cross_section.hull()
        elif self.solid is not None:
            self.solid = self.solid.hull()
        return self

    def bbox(self) -> tuple[float, float, float, float, float, float]:
        if self.cross_section is not None:
            bb_rect = self.cross_section.bounding_box()
            return (bb_rect[0], bb_rect[1],
                    bb_rect[2], bb_rect[3],
                    0.0, 0.0)
        if self.solid is None:
            return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        mf_bb = self.solid.bounding_box()
        return (mf_bb[MFBBoxEnum.MINX.value],
                mf_bb[MFBBoxEnum.MAXX.value],
                mf_bb[MFBBoxEnum.MINY.value],
                mf_bb[MFBBoxEnum.MAXY.value],
                mf_bb[MFBBoxEnum.MINZ.value],
                mf_bb[MFBBoxEnum.MAXZ.value],
                )

    def linear_extrude(self, height=None, center=False, twist=0, scale=1.0, slices=None) -> MFShape:
        if self.cross_section is None:
            raise NotImplementedError("linear_extrude requires a 2D shape")
        h = height if height is not None else 1.0
        self.solid = Manifold.extrude(self.cross_section, h)
        self.cross_section = None
        if center:
            self.solid = self.solid.translate((0, 0, -h / 2))
        return self

    def rotate_extrude(self, angle=360, convexity=1) -> MFShape:
        if self.cross_section is None:
            raise NotImplementedError("rotate_extrude requires a 2D shape")
        self.solid = Manifold.revolve(self.cross_section, revolve_degrees=angle)
        self.cross_section = None
        return self

    def offset(self, r=None, chamfer=False) -> MFShape:
        if self.cross_section is None:
            raise NotImplementedError("offset requires a 2D shape")
        delta = r if r is not None else 0.0
        jt = JoinType.Round if not chamfer else JoinType.Tangential
        self.cross_section = self.cross_section.offset(delta, join_type=jt)
        return self

    def projection(self, cut=False) -> MFShape:
        if self.solid is None:
            raise NotImplementedError("projection requires a 3D shape")
        # Project to XY plane: get all vertices and flatten Z
        mesh = self.solid.to_mesh()
        verts = mesh.vert_properties
        # Get unique 2D vertices projected onto XY plane
        pts_2d = list(set((v[0], v[1]) for v in verts))
        # Sort by angle around centroid for a valid polygon
        cx = sum(p[0] for p in pts_2d) / len(pts_2d)
        cy = sum(p[1] for p in pts_2d) / len(pts_2d)
        pts_2d.sort(key=lambda p: (p[0] - cx) ** 2 + (p[1] - cy) ** 2,
                    reverse=True)
        import math
        pts_2d.sort(key=lambda p: math.atan2(p[1] - cy, p[0] - cx))
        self.cross_section = CrossSection([pts_2d], FillRule.EvenOdd)
        self.solid = None
        return self

    def minkowski(self, other=None) -> MFShape:
        if self.cross_section is not None:
            self._ensure3d()
        if other is not None:
            if other.cross_section is not None:
                other = other.dup()
                other._ensure3d()
            self.solid = self.solid.minkowski_sum(other.solid)
        return self

class MFBBoxEnum(Enum):
    MINX = 0
    MINY = 1
    MINZ = 2
    MAXX = 3
    MAXY = 4
    MAXZ = 5

class MFBall(MFShape):
    def __init__(self, rad: float, api: MFShapeAPI):
        super().__init__(api)
        segs = self._smoothing_segments(2 * pi * rad)
        self.solid = Manifold.sphere(rad, circular_segments=segs)


class MFBox(MFShape):
    def __init__(self, l: float, wth: float, ht: float, center: bool, api: MFShapeAPI ):
        super().__init__(api)
        self.ln = l
        self.wth = wth
        self.ht = ht
        self.solid = Manifold.cube((l, wth, ht))
        if center:
            self.solid = self.solid.translate((-l / 2, -wth / 2, -ht / 2))


class MFConeZ(MFShape):
    def __init__(
        self,
        l: float,
        r1: float,
        r2: float,
        sides: float,
        api: MFShapeAPI,
    ):
        super().__init__(api)
        segs = sides if sides is not None else self._smoothing_segments(2 * pi * max(r1, r2))
        self.solid = Manifold.cylinder(l, r1, r2, circular_segments=segs)


class MFPolyExtrusionZ(MFShape):
    def __init__(self, path: list[tuple[float, float]], tck: float, api: MFShapeAPI):
        super().__init__(api)
        polygon = CrossSection([path], FillRule.EvenOdd)
        self.solid = Manifold.extrude(polygon, tck)


class MFRodZ(MFShape):
    def __init__(self, l: float, rad: float, sides: float, api: MFShapeAPI):
        super().__init__(api)
        segs = sides if sides is not None else self._smoothing_segments(2 * pi * rad)
        self.solid = Manifold.cylinder(l, rad, circular_segments=segs).translate(
            (0, 0, -l / 2)
        )

class MFPolyhedron(MFShape):
    def __init__(
        self,
        points: list[tuple[float, float, float]],
        faces: list[list[int]],
        convexity: int,
        api: MFShapeAPI,
    ):
        super().__init__(api)
        # Note: Manifold.hull_points creates a convex hull from vertices.
        # This works correctly for most polyhedra but may differ from OpenSCAD's
        # behavior for non-convex or degenerate polyhedra.
        self.solid = Manifold.hull_points(points)


# draw mix of straight lines from pt to pt, or draw spline with [(x,y,dx,dy), ...], then extrude on Z-axis
class MFLineSplineExtrusionZ(MFShape):
    def __init__(
        self,
        start: tuple[float, float],
        path: list[
            tuple[float, float] | list[tuple[float, float, float, float, float]]
        ],
        ht: float,
        api: MFShapeAPI,
    ):
        super().__init__(api)
        self.path = path
        self.ht = ht
        approx_curve_path = lineSplineXY(start, path, self._smoothing_segments)
        polygon = CrossSection([approx_curve_path], FillRule.EvenOdd)
        self.solid = Manifold.extrude(polygon, ht)


class MFLineSplineRevolveX(MFShape):
    def __init__(
        self,
        start: tuple[float, float],
        path: list[
            Union[tuple[float, float], list[tuple[float, float, float, float, float]]]
        ],
        deg: float,
        api: MFShapeAPI,
    ):
        super().__init__(api)
        _, dimY = dimXY(start, path)
        neg_deg = deg < 0
        deg = -deg if neg_deg else deg
        segs = ceil(self._smoothing_segments(2 * pi * dimY) * deg / 360.0)
        self.path = path
        self.deg = deg
        approx_curve_path = lineSplineXY(start, path, self._smoothing_segments)
        approx_curve_path = [(y, x) for x, y in approx_curve_path]  # swap X, Y
        polygon = CrossSection([approx_curve_path], FillRule.EvenOdd)
        solid = Manifold.revolve(polygon, revolve_degrees=deg, circular_segments=segs)
        solid = solid.rotate((0, 0, 90)).rotate((0, 90, 0))
        if neg_deg:
            solid = solid.mirror((0, 0, 1))
        self.solid = solid


class MFCirclePolySweep(MFShape):
    def __init__(
        self,
        rad: float,
        path: list[tuple[float, float, float]],
        api: MFShapeAPI,
    ):
        super().__init__(api)
        self.path = path
        self.rad = rad
        segs = self._smoothing_segments(2 * pi * rad)
        sweep_shape = None
        for i, (x, y, z) in enumerate(path):
            if i == 0:
                last_ball = Manifold.sphere(rad, circular_segments=segs).translate(
                    (x, y, z)
                )
                sweep_shape = last_ball
            else:
                ball = Manifold.sphere(rad, circular_segments=segs).translate((x, y, z))
                hull2balls = (last_ball + ball).hull()
                sweep_shape += hull2balls
                last_ball = ball
        self.solid = sweep_shape


class MFTextZ(MFShape):

    def __init__(
        self,
        txt: str,
        fontSize: float,
        tck: float,
        fontName: str,
        api: MFShapeAPI,
    ):
        super().__init__(api)

        self.txt = txt
        self.fontSize = fontSize
        self.tck = tck
        self.font = fontName
        fontPath = self.api.getFontPath(fontName)
        if fontPath is None:
            fontPath = self.api.getFontPath(None) # Just get some font, hopefully good
            print(f"Can't find font {fontName}, substitude with {fontPath}")

        glyphs_paths = textToGlyphsPaths(
            fontPath, txt, fontSize, dimToSegs=self._smoothing_segments
        )

        text3d: Manifold = None
        for glyph_paths in glyphs_paths:

            glyph3d: Manifold = None

            cross_section = CrossSection(glyph_paths, FillRule.EvenOdd)
            if cross_section.area() > 0:
                glyph3d = Manifold.extrude(cross_section, tck)

            if glyph3d is not None:
                text3d = glyph3d if text3d is None else text3d + glyph3d

        if text3d is not None:
            (_, _, _, xmax, ymax, _) = text3d.bounding_box()
            self.solid = text3d.translate((-xmax / 2, -ymax / 2, 0))
        else:
            print('# WARNING! Text Generation failed!!! ')
            self.solid = Manifold.cube((fontSize, fontSize, tck)).translate((-fontSize / 2, -fontSize / 2, -tck / 2))

def arc_to_points(arc, num_points=100):
    """
    Approximate an Arc object as a series of points.
    
    Parameters:
        arc (svgpathtools.path.Arc): The Arc object to approximate.
        num_points (int): Number of points to sample along the arc.
        
    Returns:
        List[Tuple[float, float]]: List of (x, y) points.
    """
    points = []
    for t in np.linspace(0, 1, num_points):
        point = arc.point(t)  # Get a point along the arc using its parameter t (0 to 1)
        points.append((point.real, point.imag))
    return points

def svg_to_extruded_geometry(svg_path: str, extrusion_height: float):
    """
    Reads an SVG file and converts it into a z-extruded 3D geometry.
    
    Parameters:
        svg_path (str): Path to the SVG file.
        extrusion_height (float): Height to extrude the 2D geometry along the z-axis.
    
    Returns:
        Mesh: A manifold3d Mesh object representing the extruded geometry.
    """
    # Step 1: Parse paths from the SVG file
    paths, _ = svg2paths(svg_path)
    
    # Step 2: Extract 2D points from the paths
    all_points = []
    for path in paths:
        for segment in path:
            if isinstance(segment, Arc):
                # Approximate arcs with points
                arc_points = arc_to_points(segment)
                all_points.extend(arc_points)
            else:
                # Handle Line, CubicBezier, QuadraticBezier
                points = [segment.point(t) for t in np.linspace(0, 1, 100)]
                all_points.extend([(p.real, p.imag) for p in points])
    
    # Step 3: Use manifold3d to extrude the points into a 3D geometry
    if not all_points:
        raise ValueError("No valid paths found in SVG file.")
    
    # Create a 2D polygon from the points
    # polygon = CrossSection(all_points, FillRule.EvenOdd)
    # polygon.add_polygon(all_points)
    
    # Extrude the 2D polygon along the z-axis
    # extruded_geometry = Manifold.extrude(polygon, extrusion_height)
    
    return all_points

def load_mesh(file_path: str):
    """
    Load a mesh from a file.
    
    Parameters:
        file_path (str): Path to the mesh file.
    
    Returns:
        trimesh.base.Trimesh: A trimesh object representing the mesh.
    """
    mesh = trimesh.load_mesh(file_path)

    # Convert trimesh data to manifold-compatible format
    vertices = np.array(mesh.vertices, dtype=np.float32)
    faces = np.array(mesh.faces, dtype=np.int32)

    # Create a manifold.Mesh object
    mesh_manifold = Mesh(vert_properties=vertices, tri_verts=faces)

    # Create a manifold object from the mesh
    return Manifold(mesh_manifold)

def load_svg(file_path: str, extrude: float):
    """
    Load an SVG file and extrude it into a 3D geometry.
    """
    path = svg_to_extruded_geometry(svg_path=file_path,extrusion_height=extrude)
    polygon = CrossSection([path], FillRule.EvenOdd)
    return Manifold.extrude(polygon, extrude)

class MFImport(MFShape):
    def __init__(
        self,
        infile: str,
        extrude: float = None,
        api: MFShapeAPI = MFShapeAPI,
    ):
        super().__init__(api)
        assert os.path.isfile(infile), f"ERROR: file {infile} does not exist!"
        
        if infile.endswith(".svg"):
            self.solid = load_svg(infile, extrude)
        elif infile.endswith(".stl"):
            self.solid = load_mesh(infile)
        else:
            raise ValueError(f"Unsupported file format: {infile}")
        

if __name__ == "__main__":
    test_api(Implementation.MANIFOLD)
