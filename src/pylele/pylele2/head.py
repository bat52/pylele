#!/usr/bin/env python3

"""
    Pylele Head
"""

from math import tan, inf

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

from b13d.api.core import Shape, Direction
from b13d.api.solid import main_maker, test_loop
from b13d.api.utils import radians
from pylele.pylele2.base import LeleBase

from pylele.pylele2.strings import LeleStrings

class LeleHead(LeleBase):
    """Pylele Head Generator class"""
    TOP_HEAD_RATIO = 1/6
    HEAD_WTH_RATIO = 1.1  # to nutWth

    def configure_head(self):
        """ Configure head """
        
        self.cfg.headWth = self.cfg.nutWth * self.HEAD_WTH_RATIO
        headDX = 1
        headDY = headDX * tan(radians(self.cfg.neckWideAng))
        self.cfg.headOrig = (0, 0)
        self.cfg.headPath = [
            (0, self.cfg.nutWth/2),
            [
                (-headDX, self.cfg.nutWth/2 + headDY, headDY/headDX),
                (-self.cfg.headLen/2, self.cfg.headWth/2, 0),
                (-self.cfg.headLen, self.cfg.headWth/6, -inf),
            ],
            (-self.cfg.headLen, 0),
        ]

    def configure(self):
        LeleBase.configure(self)
        self.configure_head()

    def gen(self) -> Shape:
        """Generate Head"""

        hdWth = self.cfg.headWth
        hdLen = self.cfg.headLen
        ntHt = self.cfg.NUT_HT
        fbTck = self.cfg.FRETBD_TCK
        spHt = self.cfg.SPINE_HT
        fspTck = self.cfg.FRETBD_SPINE_TCK
        topRat = self.TOP_HEAD_RATIO
        midTck = self.cfg.extMidBotTck
        botRat = self.cfg.BOT_RATIO
        orig = self.cfg.headOrig
        path = self.cfg.headPath
        joinTol = self.api.tolerance()

        hd = self.api.spline_revolve(orig, path, -180)
        hd *= Direction.Z * botRat
        hd <<= Direction.Z + (joinTol/2 -midTck)

        if midTck > 0:
            midR = self.api.spline_extrusion(orig, path, midTck)
            midR <<= (0, 0, -midTck)
            hd += midR.mirror_and_join()

        if topRat > 0:
            top = self.api.spline_revolve(orig, path, 180)
            top *=  (1, 1, topRat)
            top <<= (0, 0, -joinTol/2)
            hd += top

        topCut = self.api.cylinder_y(2*hdWth, hdLen)
        topCut <<= (-ntHt, 0, .8*hdLen + fbTck + ntHt)
        
        frontCut = self.api.cylinder_y(2*hdWth, .7*spHt)
        frontCut *=  (.5, 1, 1)
        frontCut <<= (-hdLen, 0, -fspTck - .65*spHt)
        
        strings = LeleStrings(cli=self.cli,isCut=True).gen_full()
    
        hd = hd - frontCut - topCut - strings

        return hd


def main(args=None):
    """Generate Head"""
    return main_maker(module_name=__name__, class_name="LeleHead", args=args)


def test_head(self, apis=None):
    """Test Head"""
    tests = {'default':['-refv','6773']}
    test_loop(module=__name__, apis=apis,tests=tests)


def test_head_mock(self):
    """Test Head"""
    test_head(self, apis=["mock"])


if __name__ == "__main__":
    main()
