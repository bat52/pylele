
from __future__ import annotations

import os
import sys
import importlib
from math import inf
from enum import Enum
from pathlib import Path
from abc import ABC, abstractmethod
from fontTools.ttLib import TTFont
from typing import Any, Union

from api.pylele_api_constants import DEFAULT_TEST_DIR

APIS_INFO = {
    'mock'     : { 'module':'api.mock_api','class':'MockShapeAPI'},
    'cadquery' : { 'module':'api.cq_api'  ,'class':'CQShapeAPI'},
    'blender'  : { 'module':'api.bpy_api' ,'class':'BlenderShapeAPI'},
    'trimesh'  : { 'module':'api.tm_api'  ,'class':'TMShapeAPI'},
    'solid2'   : { 'module':'api.sp2_api' ,'class':'Sp2ShapeAPI'},
}

# consider update to StrEnum for python 3.11 and above
# https://tsak.dev/posts/python-enum/
class LeleStrEnum(str,Enum):
    """ Pylele Enumerator for String Types """
    def __str__(self):
        return self.value
    def list(self):
        return list(self)
class Fidelity(LeleStrEnum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'

    def __repr__(self):
        return f"Fidelity({self.value} tol={self.exportTol()}, seg={self.smoothingSegments()})"

    def exportTol(self) -> float:
        match self:
            case Fidelity.LOW:
                return 0.001
            case Fidelity.MEDIUM:
                return 0.0005
            case Fidelity.HIGH:
                return 0.0001

    def smoothingSegments(self) -> float:
        match self:
            case Fidelity.LOW:
                return 7
            case Fidelity.MEDIUM:
                return 14
            case Fidelity.HIGH:
                return 19

    def code(self) -> str:
        return str(self)[0].upper()
class Implementation(LeleStrEnum):
    """ Pylele API implementations """
    MOCK = 'mock'
    CAD_QUERY = 'cadquery'
    BLENDER = 'blender'
    TRIMESH = 'trimesh'
    SOLID2 = 'solid2'

    def __repr__(self):
        return f"Implementation({self.value})"

    def code(self) -> str:
        """ Return Code that identifies Implementation """
        return str(self)[0].upper()

    def module_name(self):
        """ Returns the module name of the API """
        return APIS_INFO[self]['module']

    def class_name(self):
        """ Returns the class name of the API """
        return APIS_INFO[self]['class']
    
    def joinCutTol(self) -> float:
        # Tolerance for joins to have a little overlap
        return 0 if self == Implementation.CAD_QUERY else 0.01

def supported_apis() -> list:
    """ Returns the list of supported apis """
    ver = sys.version_info
    assert ver[0]==3

    apis = ['trimesh','cadquery','solid2']

    if ver[1] < 12:
        # blender bpy package currently not supported with python 3.12
        apis.append('blender')

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
        sapi = ShapeAPI.get(impl=impl, fidelity = Fidelity.LOW)
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

class Direction(object):
    """ A class to represent direction vectors """
    x = None
    y = None
    z = None

    def __init__(self, x: float = None, y: float = None, z: float = None):
        self.x = x
        self.y = y
        self.z = z

    def eval(self, op = '+'):

        if op == '+':
            neutral = 0
        elif op == '*':
            neutral = 1

        x = default_or_alternate(neutral, self.x)
        y = default_or_alternate(neutral, self.y)
        z = default_or_alternate(neutral, self.z)

        return x,y,z

def direction_operand(operand) -> Direction:
    """ returns a direction operand """
    if isinstance(operand,tuple):
        assert len(operand)==3
        return Direction(operand[0],operand[1],operand[2])
    if isinstance(operand,Direction):
        return operand
    assert False

class Shape(ABC):

    MAX_DIM = 2000 # for max and min dimensions

    @abstractmethod
    def getAPI(self) -> ShapeAPI:
        ...

    @abstractmethod
    def getImplSolid(self) -> Any:
        ...

    @abstractmethod
    def cut(self, cutter: Shape) -> Shape:
        ...

    @abstractmethod
    def dup(self) -> Shape:
        ...

    @abstractmethod
    def filletByNearestEdges(self,
        nearestPts: list[tuple[float, float, float]],
        rad: float,
    ) -> Shape:
        ...

    def halfByPlane(self, plane: tuple[bool, bool, bool]) -> Shape:
        halfCutter = self.getAPI().genBox(self.MAX_DIM, self.MAX_DIM, self.MAX_DIM).mv(
            self.MAX_DIM/2 if plane[0] else 0,
            self.MAX_DIM/2 if plane[1] else 0,
            self.MAX_DIM/2 if plane[2] else 0,
        )
        return self.cut(halfCutter)

    def half(self) -> Shape:
        return self.halfByPlane((False, True, False))

    @abstractmethod
    def join(self, joiner: Shape) -> Shape:
        ...

    @abstractmethod
    def mirrorXZ(self) -> Shape:
        ...

    def mirrorXZ_and_join(self) -> Shape:
        """ mirror midR and joins the two parts """
        joinTol = self.api.getJoinCutTol()
        midL = self.mirrorXZ()
        return midL.mv(0, joinTol, 0).join(self.mv(0, -joinTol, 0))

    @abstractmethod
    def mv(self, x: float, y: float, z: float) -> Shape:
        ...

    @abstractmethod
    def remove(self):
        ...

    @abstractmethod
    def rotateX(self, ang: float) -> Shape:
        ...

    @abstractmethod
    def rotateY(self, ang: float) -> Shape:
        ...

    @abstractmethod
    def rotateZ(self, ang: float) -> Shape:
        ...

    @abstractmethod
    def scale(self, x: float, y: float, z: float) -> Shape:
        ...

    @abstractmethod
    def show(self):
        ...

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

    def __mul__(self, operand) -> Shape:
        """ scale using * """
        if operand is None:
            return self
        direction = direction_operand(operand)
        x,y,z = direction.eval('*')
        return self.scale(x,y,z)

    def __lshift__(self, operand) -> Shape:
        """ move using << """
        if operand is None:
            return self
        direction = direction_operand(operand)
        x,y,z = direction.eval('+')
        return self.mv(x,y,z)
        
class ShapeAPI(ABC):

    @classmethod
    def get(self: type[ShapeAPI], impl: Implementation, fidelity: Fidelity) -> ShapeAPI:
        mod = importlib.import_module(impl.module_name())
        api = getattr(mod, impl.class_name())
        return api(fidelity)

    def getFontname2FilepathMap(self) -> dict[str, str]:

        font2path:dict[str, str] = {}

        # Define directories to search for fonts
        if sys.platform == 'win32':
            font_dirs = [
                os.path.join(os.environ['WINDIR'], 'Fonts')
            ]
        elif sys.platform == 'darwin':
            font_dirs = [
                '/Library/Fonts',
                '/System/Library/Fonts',
                os.path.expanduser('~/Library/Fonts')
            ]
        else:  # Assume Linux or other UNIX-like system
            font_dirs = [
                '/usr/share/fonts',
                '/usr/local/share/fonts',
                os.path.expanduser('~/.fonts')
            ]

        def list_fonts(directory):
            fonts = []

            # Helper function to get the string by its name ID
            def get_name(font:TTFont, nameID:int):
                name_record = font['name'].getName(nameID=nameID, platformID=3, platEncID=1)
                if name_record is None:
                    name_record = font['name'].getName(nameID=nameID, platformID=1, platEncID=0)
                return name_record.toStr() if name_record else 'Unknown'

            for root, _, files in os.walk(directory):
                for file in files:
                    if file.lower().endswith(('.ttf', '.otf')):
                        font_path = os.path.join(root, file)
                        try:
                            font = TTFont(font_path)
                            # Get the Font Family Name (name ID 1)
                            family = get_name(font, 1)
                            # Get the Font Subfamily Name (Style) (name ID 2)
                            style = get_name(font, 2)

                            font_name = family if style == "Normal" or style == "Regular" else family + " " + style
                            fonts.append((font_name, font_path))
                        except Exception as e:
                            print(f"Error reading {font_path}: {e}")
            return fonts

        # Collect fonts from all directories
        all_fonts = []
        for directory in font_dirs:
            if os.path.exists(directory):
                all_fonts.extend(list_fonts(directory))

        # Print the font names and paths
        for name, path in all_fonts:
            # print(f"Font: {name}, Path: {path}")
            font2path[name] = path

        return font2path

    def __init__(self) -> None:
        self.font2path:dict[str, str] = self.getFontname2FilepathMap()

    @abstractmethod
    def getFidelity(self) -> Fidelity:
        ...

    @abstractmethod
    def getImplementation(self) -> Implementation:
        ...

    def getFontPath(self, fontName: str) -> str:
        return self.font2path[fontName] if fontName in self.font2path else None

    @abstractmethod
    def setFidelity(self, fidel: Fidelity) -> None:
        ...

    @abstractmethod
    def exportSTL(self, shape: Shape, path: Union[str, Path]) -> None:
        ...

    @abstractmethod
    def exportBest(self, shape: Shape, path: Union[str, Path]) -> None:
        ...

    @abstractmethod
    def genBall(self, rad: float) -> Shape:
        ...

    @abstractmethod
    def genBox(self, l: float, wth: float, ht: float) -> Shape:
        ...

    @abstractmethod
    def genConeX(self, l: float, r1: float, r2: float) -> Shape:
        ...

    @abstractmethod
    def genConeY(self, l: float, r1: float, r2: float) -> Shape:
        ...

    @abstractmethod
    def genConeZ(self, l: float, r1: float, r2: float) -> Shape:
        ...

    @abstractmethod
    def genPolyRodX(self, l: float, rad: float, sides: int) -> Shape:
        ...

    @abstractmethod
    def genPolyRodY(self, l: float, rad: float, sides: int) -> Shape:
        ...

    @abstractmethod
    def genPolyRodZ(self, l: float, rad: float, sides: int) -> Shape:
        ...

    @abstractmethod
    def genRodX(self, l: float, rad: float) -> Shape:
        ...

    @abstractmethod
    def genRodY(self, l: float, rad: float) -> Shape:
        ...

    @abstractmethod
    def genRodZ(self, l: float, rad: float) -> Shape:
        ...

    def gen_rounded_edge_mask(self, direction, l, rad, rot=0, tol = 0.1) -> Shape:
        """ generate a mask to round an edge """

        radi = rad + tol
        if direction == 'x':
            mask  = self.genBox(l,radi,radi).mv(0,radi/2,radi/2)
            mask -= self.genRodX(l,rad=radi)
            mask  = mask.rotateX(rot)
        elif direction == 'y':
            mask  = self.genBox(radi,l,radi).mv(radi/2,0,radi/2)
            mask -= self.genRodY(l,rad=radi)
            mask  = mask.rotateY(rot)
        elif direction == 'z':
            mask  = self.genBox(radi,radi,l).mv(radi/2,radi/2,0)
            mask -= self.genRodZ(l,rad=radi)
            mask  = mask.rotateZ(rot)
        else:
            assert False

        return mask

    def genRndRodX(self, l: float, rad: float, domeRatio: float = 1) -> Shape:
        rndRodZ = self.genRndRodZ(l, rad, domeRatio)
        return rndRodZ.rotateY(90)

    def genRndRodY(self, l: float, rad: float, domeRatio: float = 1) -> Shape:
        rndRodX = self.genRndRodX(l, rad, domeRatio)
        return rndRodX.rotateZ(90)

    def genRndRodZ(self, l: float, rad: float, domeRatio: float = 1) -> Shape:
        stemLen = l - 2*rad*domeRatio
        rod = self.genRodZ(stemLen, rad)
        for bz in [stemLen/2, -stemLen/2]:
            ball = self.genBall(rad).scale(1, 1, domeRatio).mv(0, 0, bz)
            rod = rod.join(ball)
        return rod

    @abstractmethod
    def genPolyExtrusionZ(self, path: list[tuple[float, float]], ht: float) -> Shape:
        ...

    @abstractmethod
    def genLineSplineExtrusionZ(self,
        start: tuple[float, float],
        path: list[Union[tuple[float, float], list[tuple[float, float, float, float]]]],
        ht: float,
    ) -> Shape:
        ...

    @abstractmethod
    def genLineSplineRevolveX(self,
        start: tuple[float, float],
        path: list[Union[tuple[float, float], list[tuple[float, float, float, float]]]],
        deg: float,
    ) -> Shape:
        ...

    @abstractmethod
    def genCirclePolySweep(
        self,
        rad: float,
        path: list[tuple[float, float, float]],
    ) -> Shape:
        ...

    @abstractmethod
    def genTextZ(
        self,
        txt: str,
        fontSize: float,
        tck: float,
        font: str,
    ):
        ...

    def genQuarterBall(self, rad: float, pickTop: bool, pickFront: bool):
        maxDim = Shape.MAX_DIM
        ball = self.genBall(rad)
        topCut = self.genBox(maxDim, maxDim, maxDim).mv(0, 0, -maxDim/2 if pickTop else maxDim/2)
        frontCut = self.genBox(maxDim, maxDim, maxDim).mv(maxDim/2 if pickFront else -maxDim/2, 0, 0)
        return ball.cut(topCut).cut(frontCut)

    def genHalfDisc(self, rad: float, pickFront: bool, tck: float):
        maxDim = Shape.MAX_DIM
        rod = self.genRodZ(tck, rad)
        cutter = self.genBox(maxDim, maxDim, maxDim).mv(maxDim/2 if pickFront else -maxDim/2, 0, 0)
        return rod.cut(cutter)

    @abstractmethod
    def getJoinCutTol(self):
        ...

    def test(self, outpath: str | Path) -> None:

        expDir = outpath if isinstance(outpath, Path) else Path(outpath)
        if not expDir.exists():
            os.makedirs(expDir)
        elif not expDir.is_dir():
            print("Cannot export to non directory: %s" % expDir, file=sys.stderr)
            sys.exit(os.EX_SOFTWARE)

        implCode = self.getImplementation().code()

        # Simple Tests

        ball = self.genBall(10)
        self.exportSTL(ball, expDir / f"{implCode}-ball")

        box = self.genBox(10, 20, 30)
        self.exportSTL(box, expDir / f"{implCode}-box")

        xRod = self.genRodX(30, 5)
        self.exportSTL(xRod, expDir / f"{implCode}-xrod")

        yRod = self.genRodY(30, 5)
        self.exportSTL(yRod, expDir / f"{implCode}-yrod")

        zRod = self.genRodZ(30, 5)
        self.exportSTL(zRod, expDir / f"{implCode}-zrod")

        xCone = self.genConeX(30, 5, 2)
        self.exportSTL(xCone, expDir / f"{implCode}-xcone")

        yCone = self.genConeY(30, 5, 2)
        self.exportSTL(yCone, expDir / f"{implCode}-ycone")

        zCone = self.genConeZ(30, 5, 2)
        self.exportSTL(zCone, expDir / f"{implCode}-zcone")

        xSqRod = self.genPolyRodX(30, 5, 4)
        self.exportSTL(xSqRod, expDir / f"{implCode}-xsqrod")

        ySqRod = self.genPolyRodY(30, 5, 4)
        self.exportSTL(ySqRod, expDir / f"{implCode}-ysqrod")

        zSqRod = self.genPolyRodZ(30, 5, 4)
        self.exportSTL(zSqRod, expDir / f"{implCode}-zsqrod")

        xRndRod = self.genRndRodX(30, 5, 1/2)
        self.exportSTL(xRndRod, expDir / f"{implCode}-xrndrod")

        yRndRod = self.genRndRodY(30, 5, 1/2)
        self.exportSTL(yRndRod, expDir / f"{implCode}-yrndrod")

        zRndRod = self.genRndRodZ(30, 5, 1/2)
        self.exportSTL(zRndRod, expDir / f"{implCode}-zrndrod")

        zPolyExt = self.genPolyExtrusionZ([(0,0), (10,0), (0,10)], 5)
        self.exportSTL(zPolyExt, expDir / f"{implCode}-zpolyext")

        zTxt = self.genTextZ("ABC", 30, 10, "Courier New")
        self.exportSTL(zTxt, expDir / f"{implCode}-ztxt")

        zTxt = zTxt.rotateX(180)
        self.exportSTL(zTxt, expDir / f"{implCode}-ztxt-z180")

        qBall = self.genQuarterBall(10, True, True)
        self.exportSTL(qBall, expDir / f"{implCode}-qball")

        hDisc = self.genHalfDisc(10, True, 2)
        self.exportSTL(hDisc, expDir / f"{implCode}-hdisc")

        body = self.genLineSplineExtrusionZ(
            start = (215, 0),
            path = [
                (215, 23),
                [
                    (216, 23, .01, .5, .3),
                    (390, 76, 0, .6),
                    (481, 1, -inf),
                ],
                (481, 0),
            ],
            ht = 5,
        )
        self.exportSTL(body, expDir / f"{implCode}-body")

        dome = self.genLineSplineExtrusionZ(
            start = (0, 0),
            path = [
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
            ht = 5,
        )
        self.exportSTL(dome, expDir / f"{implCode}-splineext")

        donut = self.genLineSplineRevolveX(
            start = (0, 1),
            path = [
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
            deg = -225,
        )
        self.exportSTL(donut, expDir / f"{implCode}-splinerev")

        sweep = self.genCirclePolySweep(1, [(-20,0,0), (20,0,40), (40,20,40), (60,20,0)])
        self.exportSTL(sweep, expDir / f"{implCode}-sweep")

        edgex = self.gen_rounded_edge_mask(direction='x',l=30, rad = 10)
        self.exportSTL(edgex, expDir / f"{implCode}-edgex")

        edgey = self.gen_rounded_edge_mask(direction='y',l=30, rad = 10)
        self.exportSTL(edgey, expDir / f"{implCode}-edgey")

        edgez = self.gen_rounded_edge_mask(direction='z',l=30, rad = 10)
        self.exportSTL(edgez, expDir / f"{implCode}-edgez")

        # More complex tests

        objs = []

        box = self.genBox(10, 10, 2).mv(0, 0, -10)
        ball = self.genBall(5).scale(1, 2, 1)
        coneZ = self.genConeZ(10, 10, 5).mv(0, 0, 10)
        coneX = self.genConeX(10, 1, 2)
        rod = self.genRodZ(20, 1)
        obj1 = box + ball + coneZ + rod - coneX
        coneX.remove()
        obj1 = obj1.mv(10, 10, 11)
        objs.append(obj1)

        rx = self.genRodX(10, 3)
        ry = self.genRodY(10, 3)
        rz = self.genRodZ(10, 3)
        obj2 = rx.join(ry).join(rz).mv(10, -10, 5)
        objs.append(obj2)

        rr1 = self.genRndRodX(10, 3).scale(.5, 1, 1).mv(0, -20, 0)
        rr2 = self.genRndRodX(10, 3).scale(1, .5, 1).mv(0, 0, 0)
        rr3 = self.genRndRodX(10, 3).scale(1, 1, .5).mv(0, 20, 0)
        rr4 = self.genRndRodY(50, 1)
        obj3 = rr1.join(rr2).join(rr3).join(rr4).mv(0, 0, -20)
        objs.append(obj3)

        rrx = self.genRndRodX(10, 3, .25)
        rry = self.genRndRodY(10, 3, .5)
        rrz = self.genRndRodZ(10, 3)
        obj4 = rrx.join(rry).join(rrz).half().mv(-10, 10, 5)
        objs.append(obj4)

        pe = self.genPolyExtrusionZ([(-10, 30), (10, 30), (10, -30), (-10, -30)], 10)
        tz = self.genTextZ("Hello World", 10, 5, "Arial").rotateZ(90).mv(0, 0, 10)
        obj5 = pe.join(tz).mv(30, -30, 0)
        mirror = obj5.mirrorXZ().mv(10, 0, 0)
        obj5 = obj5.join(mirror)
        objs.append(obj5)

        rndBox = self.genBox(10, 10, 10).filletByNearestEdges([(5, 0, 5)], 1)
        obj6 = rndBox.mv(-10, -10, 5)
        objs.append(obj6)

        dome = self.genLineSplineExtrusionZ(
            start = (0, 0),
            path = [
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
            ht = 5,
        )
        obj7 = dome.rotateY(-45).mv(-10, 15, 0)
        objs.append(obj7)

        donutStart = (60, .1)
        donutPath = [
            (60, 10),
            (61, 10),
            [
                (62, 10, 0),
                (65, 5, -inf),
                (62, .1, 0),
            ],
            (60, .1),
        ]
        dome2 = self.genLineSplineRevolveX(donutStart, donutPath, 45).scale(1, 1, .5)
        dome3 = self.genLineSplineRevolveX(donutStart, donutPath, -270).mv(0, 0, self.getJoinCutTol())
        obj8 = dome2.join(dome3).mv(0, 0, -10)
        objs.append(obj8)

        obj9 = self.genCirclePolySweep(1, [(-20,0,0), (20,0,40), (40,20,40), (60,20,0)])
        objs.append(obj9)

        obj10 = self.genQuarterBall(10, True, True).scale(2, 1, .5).mv(-30, -20, 0)
        objs.append(obj10)

        obj11 = self.genHalfDisc(10, True, 10).scale(1.5, 1, 1).mv(-30, 20, 0)
        objs.append(obj11)

        # move operator shortcut
        obj12 = obj11 << Direction(x=1)
        obj13 = obj11 << Direction(y=1)
        obj14 = obj11 << Direction(z=1)
        obj15 = obj11 << (0,1,2)

        # scale operator shortcut
        obj16 = obj11 * Direction(x=1)
        obj17 = obj11 * Direction(y=1)
        obj18 = obj11 * Direction(z=1)
        obj19 = obj11 * (1,2,3)

        joined = None; [(joined := (obj if joined is None else joined.join(obj))) for obj in objs]
        self.exportSTL(joined, expDir / f"{implCode}-all")