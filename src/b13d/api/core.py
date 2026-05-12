from __future__ import annotations

import os
import sys
import importlib
from math import inf
from enum import Enum
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Union

print(f"DEBUG: core.py imported from {__file__}")

sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from b13d.api.constants import DEFAULT_TEST_DIR
from b13d.api.utils import getFontname2FilepathMap

# consider update to StrEnum for python 3.11 and above
# https://tsak.dev/posts/python-enum/
class StringEnum(str, Enum):
    """ Enumerator for String Types"""

    def __str__(self):
        return self.value

    def list(self):
        return list(self)


class Fidelity(StringEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    def __repr__(self):
        return f"Fidelity({self.value} tol={self.tolerance()}, seg={self.smoothing_segments()})"

    def tolerance(self) -> float:
        match self:
            case Fidelity.LOW:
                return 0.001
            case Fidelity.MEDIUM:
                return 0.0005
            case Fidelity.HIGH:
                return 0.00025

    def smoothing_segments(self) -> float:
        match self:
            case Fidelity.LOW:
                return 6
            case Fidelity.MEDIUM:
                return 12
            case Fidelity.HIGH:
                return 17 # 18 causes weird chamber for blender, also too slow

    def code(self) -> str:
        return str(self)[0].upper()

class BBoxEnum(Enum):
    MINX = 0
    MAXX = 1
    MINY = 2
    MAXY = 3
    MINZ = 4
    MAXZ = 5

class Implementation(StringEnum):
    """Pylele API implementations"""

    MOCK = "mock"
    CADQUERY = "cq"
    BLENDER = "bpy"
    TRIMESH = "tm"
    SOLID2 = "sp2"
    MANIFOLD = "mf"
    BUILD123D = "bd"
    PYVISTA = "pv"

    def __repr__(self):
        return f"Implementation({self.value})"

    def code(self) -> str:
        """ Return Code that identifies Implementation """
        return str(self)[0].upper()

    def module_name(self):
        """Returns the module name of the API"""
        return APIS_INFO[self]["module"]

    def class_name(self):
        """Returns the class name of the API"""
        return APIS_INFO[self]["class"]

    def tolerance(self) -> float:
        """ Tolerance for joins to have a little overlap """
        return 0 if self == Implementation.CADQUERY else 0.02

    def get_api(self, fidelity: Fidelity = Fidelity.LOW) -> ShapeAPI:
        """ Get the handler to the selected implementation API """
        try:
            mod = importlib.import_module(self.module_name())
        except ImportError as e:
            raise ImportError(
                f"Backend '{self.value}' is not installed. "
                f"Install the required package to use it. Error: {e}"
            )
        api = getattr(mod, self.class_name())
        return api(implementation = self, fidelity=fidelity)
    
    def has_fillet(self):
        """Returns True if API supports fillet"""
        return APIS_INFO[self]["fillet"]

    def has_hull(self):
        """Returns True if API supports hull"""
        return APIS_INFO[self]["hull"]

APIS_INFO = {
    Implementation.MOCK      : {"module": "b13d.api.mock", "class": "MockShapeAPI", "fillet": False, "hull" : True},
    Implementation.CADQUERY  : {"module": "b13d.api.cq", "class": "CQShapeAPI", "fillet": True, "hull" : False},
    Implementation.BLENDER   : {"module": "b13d.api.bpy", "class": "BlenderShapeAPI", "fillet": True, "hull" : False},
    Implementation.TRIMESH   : {"module": "b13d.api.tm", "class": "TMShapeAPI", "fillet": False, "hull" : True},
    Implementation.SOLID2    : {"module": "b13d.api.sp2", "class": "Sp2ShapeAPI", "fillet": False, "hull" : True},
    Implementation.MANIFOLD  : {"module": "b13d.api.mf", "class": "MFShapeAPI", "fillet": False, "hull" : True},
    Implementation.BUILD123D : {"module": "b13d.api.bd", "class": "BDShapeAPI", "fillet": True, "hull" : True},
    Implementation.PYVISTA : {"module": "b13d.api.pv", "class": "PVShapeAPI", "fillet": False, "hull" : True},
}

def supported_apis() -> list:
    """Returns the list of supported apis, probing which backends are actually installed"""
    ver = sys.version_info
    assert ver[0] == 3

    # Always available (mandatory dependencies)
    apis = [Implementation.TRIMESH]

    # Probe optional backends by trying to import their modules
    # and checking the module's *_AVAILABLE flag (since the module file
    # itself may import successfully even when the backend package is missing)
    optional_impls = [
        (Implementation.SOLID2, "SP2_AVAILABLE"),
        (Implementation.MANIFOLD, "MF_AVAILABLE"),
        (Implementation.CADQUERY, "CQ_AVAILABLE"),
        (Implementation.BUILD123D, "BD_AVAILABLE"),
        (Implementation.BLENDER, "BPY_AVAILABLE"),
        (Implementation.PYVISTA, "PV_AVAILABLE"),
    ]
    for impl, avail_flag in optional_impls:
        try:
            mod = importlib.import_module(impl.module_name())
            if getattr(mod, avail_flag, False):
                apis.append(impl)
        except ImportError:
            pass

    # Python version gate for Blender (only supported with 3.10 and 3.11)
    # if Implementation.BLENDER in apis and ver[1] not in (10, 11):
    #    apis.remove(Implementation.BLENDER)

    return apis

def make_test_path(api_name,test_path=DEFAULT_TEST_DIR):
    """ Makes Test folder """
    out_path = os.path.join(Path.cwd(), test_path, api_name)

    if not os.path.isdir(out_path):
        os.makedirs(out_path)
    assert os.path.isdir(out_path)

    return out_path

def test_api(api):
    """ Test a Shape API """
    if api in supported_apis()+['mock']:
        impl = Implementation(api)
        sapi = impl.get_api(fidelity = Fidelity.LOW)
        outfname = make_test_path(impl.module_name())
        sapi.test(outfname)
    else:
        print(f'WARNING: Skipping test of {api} api, because unsupported with python version {sys.version}!')

def default_or_alternate(def_val, alt_val=None):
    """ Override default value with alternate value, if available"""
    if alt_val is None:
        return def_val
    return alt_val
    # return def_val if alt_val is None else al

DIRECTION_TO_TUPLE = {
    'X' : (1,0,0),
    'Y' : (0,1,0),
    'Z' : (0,0,1),
}

class Direction(StringEnum):
    """ A class to represent direction vectors """
    X = 'X'
    Y = 'Y'
    Z = 'Z'

    def eval(self):
        return DIRECTION_TO_TUPLE[self.value]

    def list():
        return Direction._member_names_

    def __add__(self, operand):
        return map(lambda x: operand * x, self.eval() )

    def __mul__(self, operand):
        retval = map(lambda x: operand * x if x == 1 else 1, self.eval() )
        return retval

class Shape(ABC):
 
    MAX_DIM = 2000  # for max and min dimensions
    api = None
    color : tuple[int, int, int] = None
    name : str = None
    solid = None

    def __init__(self,
                 api: ShapeAPI,
                 solid=None,
                 color : tuple[int, int, int] = None):
        self.api: ShapeAPI = api
        self.solid = solid
        self.color = color

    @abstractmethod
    def cut(self, cutter: Shape) -> Shape: ...

    @abstractmethod
    def dup(self) -> Shape: ...

    def fillet(
        self,
        nearestPts: list[tuple[float, float, float]],
        rad: float,
    ) -> Shape:
        print(f"Warning! Fillet not implemented yet for {self.api.implementation} api!")
        return self

    def half(self, plane: tuple[bool, bool, bool] = (False, True, False)) -> Shape:
        halfCutter = (
            self.api
            .box(self.MAX_DIM, self.MAX_DIM, self.MAX_DIM)
            .mv(
                self.MAX_DIM / 2 if plane[0] else 0,
                self.MAX_DIM / 2 if plane[1] else 0,
                self.MAX_DIM / 2 if plane[2] else 0,
            )
        )
        return self.cut(halfCutter)

    @abstractmethod
    def join(self, joiner: Shape) -> Shape: ...

    @abstractmethod
    def intersection(self, intersector: Shape) -> Shape: ...

    @abstractmethod
    def mirror(self, normal: tuple[float, float, float] = (0, 1, 0)) -> Shape: ...

    def mirror_and_join(self) -> Shape:
        """mirror midR and joins the two parts"""
        joinTol = self.api.tolerance()
        midL = self.mirror()
        return midL.mv(0, joinTol / 2, 0).join(self.mv(0, -joinTol / 2, 0))

    @abstractmethod
    def mv(self, x: float, y: float, z: float) -> Shape: ...

    @abstractmethod
    def rotate_x(self, ang: float) -> Shape: ...

    @abstractmethod
    def rotate_y(self, ang: float) -> Shape: ...

    @abstractmethod
    def rotate_z(self, ang: float) -> Shape: ...

    def rotate(self,  ang: float | tuple[float,float,float], direction: Direction = Direction.Z) -> Shape:
        """ Generate a cone, with direction as parameter """

        if direction.upper() == Direction.X:
            return self.rotate_x(ang)
        if direction.upper() == Direction.Y:
            return self.rotate_y(ang)
        if direction.upper() == Direction.Z:
            return self.rotate_z(ang)

        # default implemntation, if not available
        return self.rotate_x(ang[0]).rotate_y(ang[1]).rotate_z(ang[2])

    @abstractmethod
    def scale(self, x: float, y: float, z: float) -> Shape: ...

    def set_color(self, rgb: tuple[int, int, int] = None) -> Shape:
        if not rgb is None:
            self.color = rgb
        # return self
        print(f"Warning! set_color not implemented yet for {self.api.implementation} api!")
        return self

    def set_name(self, name: str) -> Shape:
        self.name = name
        return self

    def show(self):
        print(f"Warning! show not implemented yet for {self.api.implementation} api!")

    def __add__(self, operand) -> Shape:
        """ Join using + """
        if operand is None:
            return self
        assert isinstance(operand,Shape)
        return self.join(operand)

    def __sub__(self, operand) -> Shape:
        """ cut using - """
        if operand is None:
            return self
        assert isinstance(operand,Shape)
        return self.cut(operand)

    def __and__(self, operand) -> Shape:
        """ cut using - """
        if operand is None:
            return self
        assert isinstance(operand,Shape)
        return self.intersection(operand)

    def __mul__(self, operand: tuple[float, float, float] = (1,1,1)) -> Shape:
        """ scale using * """
        if operand is None:
            return self
        return self.scale(*operand)

    def __lshift__(self, operand: tuple[float, float, float] = (0,0,0)) -> Shape:
        """ move using << """
        if operand is None:
            return self
        return self.mv(*operand)
    
    @abstractmethod
    def bbox(self) -> tuple[float, float, float]: ...
        
    def top(self) -> float:
        """Get the top Z coordinate of the bounding box."""
        if self.solid is None:
            return 0
        bbox = self.bbox()
        return bbox[BBoxEnum.MAXZ.value]
    
    def bottom(self) -> float:  
        """Get the bottom Z coordinate of the bounding box."""
        if self.solid is None:
            return 0
        bbox = self.bbox()
        return bbox[BBoxEnum.MINZ.value]
    
    def left(self) -> float:
        """Get the left X coordinate of the bounding box."""
        if self.solid is None:
            return 0
        bbox = self.bbox()
        return bbox[BBoxEnum.MINX.value]
    
    def right(self) -> float:
        """Get the right X coordinate of the bounding box."""
        if self.solid is None:
            return 0
        bbox = self.bbox()
        return bbox[BBoxEnum.MAXX.value]
    
    def front(self) -> float:       
        """Get the front Y coordinate of the bounding box."""
        if self.solid is None:
            return 0
        bbox = self.bbox()
        return bbox[BBoxEnum.MINY.value]
    
    def back(self) -> float:    
        """Get the back Y coordinate of the bounding box."""
        if self.solid is None:
            return 0
        bbox = self.bbox()
        return bbox[BBoxEnum.MAXY.value]
    
    def center(self) -> tuple[float, float, float]:
        """Get the center of the bounding box."""
        if self.solid is None:
            return 0, 0, 0
        bbox = self.bbox()
        return (
            (bbox[BBoxEnum.MINX.value] + bbox[BBoxEnum.MAXX.value]) / 2,
            (bbox[BBoxEnum.MINY.value] + bbox[BBoxEnum.MAXY.value]) / 2,
            (bbox[BBoxEnum.MINZ.value] + bbox[BBoxEnum.MAXZ.value]) / 2,
        )
    
    def length(self) -> float:
        """Get the length (X) of the bounding box."""
        if self.solid is None:
            return 0
        bbox = self.bbox()
        return bbox[BBoxEnum.MAXX.value] - bbox[BBoxEnum.MINX.value]

    def width(self) -> float:
        """Get the width (Y) of the bounding box."""
        if self.solid is None:
            return 0
        bbox = self.bbox()
        return bbox[BBoxEnum.MAXY.value] - bbox[BBoxEnum.MINY.value]

    def height(self) -> float:
        """Get the height (Z) of the bounding box."""
        if self.solid is None:
            return 0
        bbox = self.bbox()
        return bbox[BBoxEnum.MAXZ.value] - bbox[BBoxEnum.MINZ.value]

    def linear_extrude(self, height=None, center=False, twist=0, scale=1.0, slices=None) -> Shape:
        raise NotImplementedError(f"linear_extrude not implemented for {self.api.implementation}")

    def rotate_extrude(self, angle=360, convexity=1) -> Shape:
        raise NotImplementedError(f"rotate_extrude not implemented for {self.api.implementation}")

    def offset(self, r=None, chamfer=False) -> Shape:
        raise NotImplementedError(f"offset not implemented for {self.api.implementation}")

    def projection(self, cut=False) -> Shape:
        raise NotImplementedError(f"projection not implemented for {self.api.implementation}")

    def minkowski(self, other: Shape = None) -> Shape:
        if other is None:
            return self
        raise NotImplementedError(f"minkowski not implemented for {self.api.implementation}")

class ShapeAPI(ABC):
    """ Prototype for Implementation API """

    implementation = None
    fidelity = None
    font2path = getFontname2FilepathMap()

    def __init__(
        self,
        implementation : Implementation,
        fidelity: Fidelity = Fidelity.LOW,
    ):
        self.implementation = implementation
        self.fidelity = fidelity

    def getFontPath(self, fontName: str) -> str:
        """
            given fontName return path to font file.
            If fontName is None, find the shortest name font to serve as default
        """
        if fontName is None:
            font_names = list(self.font2path.keys())
            font_names.sort(key=len)
            font_path = self.font2path[font_names[0]]
        else:
            font_path = self.font2path[fontName] if fontName in self.font2path else None

        return font_path

    @abstractmethod
    def export(self, shape: Shape, path: Union[str, Path], fmt: str) -> None: ...

    @abstractmethod
    def export_stl(self, shape: Shape, path: Union[str, Path]) -> None: ...

    @abstractmethod
    def export_best(self, shape: Shape, path: Union[str, Path]) -> None: ...

    def export_best_multishapes(
        self,
        shapes: list[Shape],
        assembly_name: str,
        path: Union[str, Path],
    ) -> None:
        joined: Shape = None
        for s in shapes:
            joined = s if joined is None else joined.join(s)
        self.export_stl(shape=joined, path=path)

    @abstractmethod
    def sphere(self, r: float) -> Shape: ...

    @abstractmethod
    def box(self, l: float, wth: float, ht: float, center: bool) -> Shape: ...

    def cube(self, l: float) -> Shape:
        return self.box(l=l,wth=l,ht=l)

    @abstractmethod
    def cone_x(self, h: float, r1: float, r2: float) -> Shape: ...

    @abstractmethod
    def cone_y(self, h: float, r1: float, r2: float) -> Shape: ...

    @abstractmethod
    def cone_z(self, h: float, r1: float, r2: float) -> Shape: ...

    def cone(self,  h: float, r1: float, r2: float, direction: Direction = Direction.Z) -> Shape:
        """ Generate a cone, with direction as parameter """
        if direction == Direction.X:
            return self.cone_x(h=h,r1=r1,r2=r2)
        if direction == Direction.Y:
            return self.cone_y(h=h,r1=r1,r2=r2)
        if direction == Direction.Z:
            return self.cone_z(h=h,r1=r1,r2=r2)
        assert False

    @abstractmethod
    def regpoly_extrusion_x(self, l: float, rad: float, sides: int) -> Shape: ...

    @abstractmethod
    def regpoly_extrusion_y(self, l: float, rad: float, sides: int) -> Shape: ...

    @abstractmethod
    def regpoly_extrusion_z(self, l: float, rad: float, sides: int) -> Shape: ...

    def cylinder(self,  l: float, rad: float, r2: float = None,
                 sides: int = None, direction: Direction = Direction.Z,
                 dome_ratio: float = None) -> Shape:
        """ Generate a cylinder, with direction as parameter """

        if not r2 is None:
            assert sides is None, 'Parameters sides and r2 cannot be both None!'
            return self.cone(h=l,r1=rad,r2=r2,direction=direction)

        if direction.upper() == Direction.X:
            if sides is None:
                if not dome_ratio is None:
                    return self.cylinder_rounded_x(l=l,rad=rad,domeRatio=dome_ratio)
                else:
                    return self.cylinder_x(l=l,rad=rad)
            else:
                return self.regpoly_extrusion_x(l=l,rad=rad, sides=sides)

        if direction.upper() == Direction.Y:
            if sides is None:
                if not dome_ratio is None:
                    return self.cylinder_rounded_y(l=l,rad=rad,domeRatio=dome_ratio)
                else:
                    return self.cylinder_y(l=l,rad=rad)
            else:
                return self.regpoly_extrusion_y(l=l,rad=rad, sides=sides)

        if direction.upper() == Direction.Z:
            if sides is None:
                if not dome_ratio is None:
                    return self.cylinder_rounded_z(l=l,rad=rad,domeRatio=dome_ratio)
                else:
                    return self.cylinder_z(l=l,rad=rad)
            else:
                return self.regpoly_extrusion_z(l=l,rad=rad, sides=sides)

        assert False

    @abstractmethod
    def cylinder_x(self, l: float, rad: float) -> Shape: ...

    @abstractmethod
    def cylinder_y(self, l: float, rad: float) -> Shape: ...

    @abstractmethod
    def cylinder_z(self, l: float, rad: float) -> Shape:
        ...

    def rounded_edge_mask(self, l, rad, direction: Direction = Direction.Z, rot=0, tol = 0.1) -> Shape:
        """ generate a mask to round an edge """

        radi = rad + tol
        if direction.upper() == Direction.X:
            mask  = self.box(l,radi,radi).mv(0,radi/2,radi/2)
        elif direction.upper() == Direction.Y:
            mask  = self.box(radi,l,radi).mv(radi/2,0,radi/2)
        elif direction.upper() == Direction.Z:
            mask  = self.box(radi,radi,l).mv(radi/2,radi/2,0)
        else:
            assert False

        mask -= self.cylinder(l,rad=radi,direction=direction)
        mask  = mask.rotate(rot,direction=direction)

        return mask

    def cylinder_rounded_x(self, l: float, rad: float, domeRatio: float = 1) -> Shape:
        return self.cylinder_rounded_z(l, rad, domeRatio).rotate_y(90)

    def cylinder_rounded_y(self, l: float, rad: float, domeRatio: float = 1) -> Shape:
        return self.cylinder_rounded_x(l, rad, domeRatio).rotate_z(90)

    def cylinder_rounded_z(self, l: float, rad: float, domeRatio: float = 1) -> Shape:
        stemLen = l - 2 * rad * domeRatio
        rod = self.cylinder_z(stemLen, rad)
        for bz in [stemLen / 2, -stemLen / 2]:
            ball = self.sphere(rad).scale(1, 1, domeRatio)
            ball <<= (0, 0, bz)
            rod += ball
        return rod

    @abstractmethod
    def polygon_extrusion(
        self, path: list[tuple[float, float]], ht: float
    ) -> Shape: ...

    @abstractmethod
    def spline_extrusion(
        self,
        start: tuple[float, float],
        path: list[Union[tuple[float, float], list[tuple[float, float, float, float]]]],
        ht: float,
    ) -> Shape: ...

    @abstractmethod
    def spline_revolve(
        self,
        start: tuple[float, float],
        path: list[Union[tuple[float, float], list[tuple[float, float, float, float]]]],
        deg: float,
    ) -> Shape: ...

    @abstractmethod
    def regpoly_sweep(
        self,
        rad: float,
        path: list[tuple[float, float, float]],
    ) -> Shape: ...

    @abstractmethod
    def text(
        self,
        txt: str,
        fontSize: float,
        tck: float,
        font: str,
    ): ...

    @abstractmethod
    def polyhedron(
        self,
        points: list[tuple[float, float, float]],
        faces: list[list[int]],
        convexity: int = 1,
    ) -> Shape: ...

    @abstractmethod
    def rectangle(self, size, center=False) -> Shape: ...

    @abstractmethod
    def circle(self, r=None, d=None) -> Shape: ...

    @abstractmethod
    def polygon(self, points, paths=None, convexity=1) -> Shape: ...

    @abstractmethod
    def genImport(self, infile: str, extrude: float = None) -> Shape:
        ...

    def sphere_quadrant(self, rad: float, pickTop: bool, pickFront: bool):
        maxDim = Shape.MAX_DIM
        ball = self.sphere(rad)
        topCut = self.box(maxDim, maxDim, maxDim).mv(
            0, 0, -maxDim / 2 if pickTop else maxDim / 2
        )
        frontCut = self.box(maxDim, maxDim, maxDim).mv(
            maxDim / 2 if pickFront else -maxDim / 2, 0, 0
        )
        return ball.cut(topCut).cut(frontCut)

    def cylinder_half(self, rad: float, pickFront: bool, tck: float):
        maxDim = Shape.MAX_DIM
        rod = self.cylinder_z(tck, rad)
        cutter = self.box(maxDim, maxDim, maxDim).mv(
            maxDim / 2 if pickFront else -maxDim / 2, 0, 0
        )
        return rod.cut(cutter)

    def tolerance(self):
        return self.implementation.tolerance()

    def _validate_stl(self, stl_path: Path, name: str, min_volume: float = 0):
        """Validate an STL file using trimesh: check watertightness and volume."""
        try:
            import trimesh
            mesh = trimesh.load(str(stl_path))
            # Handle both single mesh and Scene (multiple geometries)
            if isinstance(mesh, trimesh.Scene):
                # For scenes, check each geometry
                for geom in mesh.geometry.values():
                    if not geom.is_watertight:
                        print(f"  WARNING: {name} ({stl_path.name}) is NOT WATERTIGHT")
                        break
                # Use convex hull volume for scene
                vol = mesh.convex_hull.volume if hasattr(mesh, 'convex_hull') else 0
            else:
                if not mesh.is_watertight:
                    print(f"  WARNING: {name} ({stl_path.name}) is NOT WATERTIGHT")
                vol = mesh.volume
            if vol < min_volume:
                print(f"  WARNING: {name} ({stl_path.name}) volume={vol:.2f} < min={min_volume}")
        except Exception as e:
            print(f"  WARNING: {name} ({stl_path.name}) validation failed: {e}")

    def _numbered_name(self, counter: int, base_name: str) -> str:
        """Generate a numbered name like P-000-ball"""
        return f"{self.implementation.code()}-{counter:03d}-{base_name}"

    def _export_and_validate(self, shape: Shape, expDir: Path, base_name: str, min_volume: float = 0):
        """Export and validate a shape, returning the next counter value."""
        name = self._numbered_name(self._test_counter, base_name)
        self.export_stl(shape, expDir / name)
        self._validate_stl(expDir / f"{name}.stl", name, min_volume=min_volume)
        self._test_counter += 1
        return self._test_counter

    def test(self, outpath: str | Path) -> None:

        expDir = outpath if isinstance(outpath, Path) else Path(outpath)
        if not expDir.exists():
            os.makedirs(expDir)
        elif not expDir.is_dir():
            print("Cannot export to non directory: %s" % expDir, file=sys.stderr)
            sys.exit(os.EX_SOFTWARE)

        implCode = self.implementation.code()
        self._test_counter = 0

        # Simple Tests

        print(f"[{implCode}] Testing sphere...")
        ball = self.sphere(10)
        self._export_and_validate(ball, expDir, "ball", min_volume=3500)
        
        # print(f"[{implCode}] Testing sphere...")
        # self.export_best(ball, expDir / name)

        print(f"[{implCode}] Testing box...")
        box = self.box(10, 20, 30)
        self._export_and_validate(box, expDir, "box", min_volume=5000)

        print(f"[{implCode}] Testing cylinder_x...")
        xRod = self.cylinder_x(30, 5)
        self._export_and_validate(xRod, expDir, "xrod", min_volume=2000)

        print(f"[{implCode}] Testing cylinder_y...")
        yRod = self.cylinder_y(30, 5)
        self._export_and_validate(yRod, expDir, "yrod", min_volume=2000)

        print(f"[{implCode}] Testing cylinder_z...")
        zRod = self.cylinder_z(30, 5)
        self._export_and_validate(zRod, expDir, "zrod", min_volume=2000)

        print(f"[{implCode}] Testing cone_x...")
        xCone = self.cone_x(30, 5, 2)
        self._export_and_validate(xCone, expDir, "xcone", min_volume=1000)

        print(f"[{implCode}] Testing cone...")
        xCone2 = self.cone(30, 5, 2, 'X')
        self._export_and_validate(xCone2, expDir, "xcone2", min_volume=1000)

        print(f"[{implCode}] Testing cone_y...")
        yCone = self.cone_y(30, 5, 2)
        self._export_and_validate(yCone, expDir, "ycone", min_volume=1000)

        print(f"[{implCode}] Testing cone_z...")
        zCone = self.cone_z(30, 5, 2)
        self._export_and_validate(zCone, expDir, "zcone", min_volume=1000)

        print(f"[{implCode}] Testing regpoly_extrusion_x...")
        xSqRod = self.regpoly_extrusion_x(30, 5, 4)
        self._export_and_validate(xSqRod, expDir, "xsqrod", min_volume=1200)

        print(f"[{implCode}] Testing regpoly_extrusion_y...")
        ySqRod = self.regpoly_extrusion_y(30, 5, 4)
        self._export_and_validate(ySqRod, expDir, "ysqrod", min_volume=1200)

        print(f"[{implCode}] Testing regpoly_extrusion_z...")
        zSqRod = self.regpoly_extrusion_z(30, 5, 4)
        self._export_and_validate(zSqRod, expDir, "zsqrod", min_volume=1200)

        xRndRod = self.cylinder_rounded_x(30, 5, 1 / 2)
        self._export_and_validate(xRndRod, expDir, "xrndrod", min_volume=1800)

        yRndRod = self.cylinder_rounded_y(30, 5, 1 / 2)
        self._export_and_validate(yRndRod, expDir, "yrndrod", min_volume=1800)

        zRndRod = self.cylinder_rounded_z(30, 5, 1 / 2)
        self._export_and_validate(zRndRod, expDir, "zrndrod", min_volume=1800)

        zPolyExt = self.polygon_extrusion([(0, 0), (10, 0), (0, 10)], 5)
        self._export_and_validate(zPolyExt, expDir, "zpolyext", min_volume=10)

        zPolyhedron = self.polyhedron(
            points=[(0, 0, 0), (10, 0, 0), (0, 10, 0), (0, 0, 10)],
            faces=[[0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]],
            convexity=1,
        )
        self._export_and_validate(zPolyhedron, expDir, "zpolyhedron", min_volume=10)

        zTxt = self.text("ABC", 30, 10, "Courier New")
        self._export_and_validate(zTxt, expDir, "ztxt", min_volume=100)

        zTxt = zTxt.rotate_x(180)
        self._export_and_validate(zTxt, expDir, "ztxt-z180", min_volume=100)

        qBall = self.sphere_quadrant(10, True, True)
        self._export_and_validate(qBall, expDir, "qball", min_volume=100)

        hDisc = self.cylinder_half(10, True, 2)
        self._export_and_validate(hDisc, expDir, "hdisc", min_volume=10)

        body = self.spline_extrusion(
            start=(215, 0),
            path=[
                (215, 23),
                [
                    (216, 23, 0.01, 0.5, 0.3),
                    (390, 76, 0, 0.6),
                    (481, 1, -inf),
                ],
                (481, 0),
            ],
            ht=5,
        )
        self._export_and_validate(body, expDir, "body", min_volume=100)

        dome = self.spline_extrusion(
            start=(0, 0),
            path=[
                (-5, 0),
                (-5, 10),
                (0, 10),
                [
                    (1, 10, 0),
                    (5, 8, -inf),
                    (2.5, 5, -inf),
                    (5, 2, -inf),
                    (1, 0, 0),
                ],
                (0, 0),
            ],
            ht=5,
        )
        self._export_and_validate(dome, expDir, "splineext", min_volume=100)

        donut = self.spline_revolve(
            start=(0, 1),
            path=[
                (-5, 1),
                (-5, 9),
                (0, 9),
                [
                    (1, 9, 0),
                    (5, 7, -inf),
                    (2.5, 5, -inf),
                    (5, 3, -inf),
                    (1, 1, 0),
                ],
                (0, 1),
            ],
            deg=-225,
        )
        self._export_and_validate(donut, expDir, "splinerev", min_volume=100)

        sweep = self.regpoly_sweep(
            1, [(-20, 0, 0), (20, 0, 40), (40, 20, 40), (60, 20, 0)]
        )
        self._export_and_validate(sweep, expDir, "sweep", min_volume=100)

        edgex = self.rounded_edge_mask(direction='x',l=30, rad = 10)
        self._export_and_validate(edgex, expDir, "edgex", min_volume=100)

        edgey = self.rounded_edge_mask(direction='y',l=30, rad = 10)
        self._export_and_validate(edgey, expDir, "edgey", min_volume=100)

        edgez = self.rounded_edge_mask(direction='z',l=30, rad = 10)
        self._export_and_validate(edgez, expDir, "edgez", min_volume=100)

        # test join
        box = self.box(10, 20, 30).mv(0, 7, 0)
        xRod = self.cylinder_x(30, 5)
        jout = xRod.join(box)
        self._export_and_validate(jout, expDir, "bop-join", min_volume=100)

        # test cut
        box = self.box(10, 20, 30).mv(0, 7, 0)
        xRod = self.cylinder_x(30, 5)
        jout = xRod.cut(box)
        self._export_and_validate(jout, expDir, "bop-cut", min_volume=100)

        # test intersection
        box = self.box(10, 20, 30).mv(0, 7, 0)
        xRod = self.cylinder_x(30, 5)
        iout = xRod.intersection(box)
        self._export_and_validate(iout, expDir, "bop-intersect", min_volume=100)
        iout = xRod & box

        # test hull
        if self.implementation.has_hull():
            box = self.box(10, 20, 30).mv(0, 7, 0)
            xrod = self.cylinder_x(30, 5)
            jout = box + xrod
            jout.hull()
            self._export_and_validate(jout, expDir, "hull", min_volume=100)

        # test mirror
        box = self.box(10, 20, 30)
        mirrored = box.mirror()
        mout = mirrored.join(box)
        self._export_and_validate(mout, expDir, "mirror", min_volume=100)

        # More complex tests

        box = self.box(10, 10, 2).mv(0, 0, -10)
        ball = self.sphere(5).scale(1, 2, 1)
        coneZ = self.cone_z(10, 10, 5).mv(0, 0, 10)
        coneX = self.cone_x(10, 1, 2)
        rod = self.cylinder_z(20, 1)
        obj1 = box + ball + coneZ + rod - coneX
        obj1 = obj1.mv(10, 10, 11)
        self._export_and_validate(obj1, expDir, "obj1", min_volume=1000)
        joined = obj1

        rx = self.cylinder_x(10, 3)
        ry = self.cylinder_y(10, 3)
        rz = self.cylinder_z(10, 3)
        obj2 = rx.join(ry).join(rz).mv(10, -10, 5)
        self._export_and_validate(obj2, expDir, "obj2", min_volume=500)
        joined += obj2

        rr1 = self.cylinder_rounded_x(10, 3).scale(0.5, 1, 1).mv(0, -20, 0)
        rr2 = self.cylinder_rounded_x(10, 3).scale(1, 0.5, 1).mv(0, 0, 0)
        rr3 = self.cylinder_rounded_x(10, 3).scale(1, 1, 0.5).mv(0, 20, 0)
        rr4 = self.cylinder_rounded_y(50, 1)
        obj3 = rr1.join(rr2).join(rr3).join(rr4).mv(0, 0, -20)
        self._export_and_validate(obj3, expDir, "obj3", min_volume=400)
        joined += obj3

        rrx = self.cylinder_rounded_x(10, 3, 0.25)
        rry = self.cylinder_rounded_y(10, 3, 0.5)
        rrz = self.cylinder_rounded_z(10, 3)
        obj4 = rrx.join(rry).join(rrz).half().mv(-10, 10, 5)
        self._export_and_validate(obj4, expDir, "obj4", min_volume=200)
        joined += obj4

        pe = self.polygon_extrusion([(-10, 30), (10, 30), (10, -30), (-10, -30)], 10)
        tz = self.text("Hello World", 10, 5, "Arial").rotate_z(90).mv(0, 0, 10)
        obj5 = pe.join(tz).mv(30, -30, 0)
        mirror = obj5.mirror().mv(10, 0, 0)
        obj5 = obj5.join(mirror)
        self._export_and_validate(obj5, expDir, "obj5", min_volume=1000)
        joined += obj5

        if self.implementation.has_fillet():
            rndBox = self.box(10, 10, 10).fillet([(5, 0, 5)], 1)
            obj6 = rndBox.mv(-10, -10, 5)
            self._export_and_validate(obj6, expDir, "obj6", min_volume=900)
            joined += obj6

        dome = self.spline_extrusion(
            start=(0, 0),
            path=[
                (-5, 0),
                (-5, 10),
                (0, 10),
                [
                    (1, 10, 0),
                    (5, 8, -inf),
                    (3, 5, -inf),
                    (5, 2, -inf),
                    (1, 0, 0),
                ],
                (0, 0),
            ],
            ht=5,
        )
        obj7 = dome.rotate_y(-45).mv(-10, 15, 0)
        self._export_and_validate(obj7, expDir, "obj7", min_volume=400)
        joined += obj7

        donutStart = (60, 0.1)
        donutPath = [
            (60, 10),
            (61, 10),
            [
                (62, 10, 0),
                (65, 5, -inf),
                (62, 0.1, 0),
            ],
            (60, 0.1),
        ]
        dome2 = self.spline_revolve(donutStart, donutPath, 45).scale(1, 1, 0.5)
        dome3 = self.spline_revolve(donutStart, donutPath, -270).mv(
            0, 0, self.tolerance()
        )
        obj8 = dome2.join(dome3).mv(0, 0, -10)
        self._export_and_validate(obj8, expDir, "obj8", min_volume=1000)
        joined += obj8

        obj9 = self.regpoly_sweep(
            1, [(-20, 0, 0), (20, 0, 40), (40, 20, 40), (60, 20, 0)]
        )
        self._export_and_validate(obj9, expDir, "obj9", min_volume=1000)
        joined += obj9

        obj10 = self.sphere_quadrant(10, True, True).scale(2, 1, 0.5).mv(-30, -20, 0)
        self._export_and_validate(obj10, expDir, "obj10", min_volume=1000)
        joined += obj10

        obj11 = self.cylinder_half(10, True, 10).scale(1.5, 1, 1).mv(-30, 20, 0)
        self._export_and_validate(obj11, expDir, "obj11", min_volume=1000)
        joined += obj11

        # move operator shortcut
        obj12 = self.sphere(5) << (Direction.X + 2)
        self._export_and_validate(obj12, expDir, "obj12", min_volume=100)
        obj13 = self.sphere(5) << (Direction.Y + 2)
        self._export_and_validate(obj13, expDir, "obj13", min_volume=100)
        obj14 = self.sphere(5) << (Direction.Z + 2)
        self._export_and_validate(obj14, expDir, "obj14", min_volume=100)
        obj15 = self.sphere(5) << (0,1,2)
        self._export_and_validate(obj15, expDir, "obj15", min_volume=100)

        # scale operator shortcut
        obj16 = self.sphere(5) * (Direction.X * 2)
        self._export_and_validate(obj16, expDir, "obj16", min_volume=100)
        obj17 = self.sphere(5) * (Direction.Y * 2)
        self._export_and_validate(obj17, expDir, "obj17", min_volume=100)
        obj18 = self.sphere(5) * (Direction.Z * 2)
        self._export_and_validate(obj18, expDir, "obj18", min_volume=100)
        obj19 = self.sphere(5) * (1,2,3)
        self._export_and_validate(obj19, expDir, "obj19", min_volume=100)

        self._export_and_validate(joined, expDir, "all", min_volume=10000)

        