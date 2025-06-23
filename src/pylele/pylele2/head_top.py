#!/usr/bin/env python3

"""
    Pylele Head Top
"""

import argparse
from math import tan, inf

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

from b13d.api.utils import radians
from b13d.api.core import Shape
from b13d.api.solid import main_maker, test_loop
from pylele.pylele2.base import LeleBase
from pylele.pylele2.strings import LeleStrings

class LeleHeadTop(LeleBase):
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

        topRat = self.TOP_HEAD_RATIO
        hdWth = self.cfg.headWth
        hdLen = self.cfg.headLen
        ntHt = self.cfg.NUT_HT
        fbTck = self.cfg.FRETBD_TCK
        orig = self.cfg.headOrig
        path = self.cfg.headPath
        joinTol = self.api.tolerance()

        top = None
        if topRat > 0:
            top = self.api.spline_revolve(orig, path, 180)
            top *=  (1, 1, topRat)
            top <<= (0, 0, -joinTol/2)
            
            topCut = self.api.cylinder_y(2*hdWth, hdLen)
            topCut <<= (-ntHt, 0, .8*hdLen + fbTck + ntHt)
            top -= topCut

            top -= LeleStrings(cli=self.cli,isCut=True).gen_full()

        return top    

def main(args=None):
    """Generate Head Top"""
    return main_maker(module_name=__name__, class_name="LeleHeadTop", args=args)

def test_head_top(self, apis=None):
    """Test Head Top"""
    tests = {
        'default':[],
        }
    test_loop(module=__name__, apis=apis,tests=tests)

def test_head_top_mock(self):
    """Test Head"""
    test_head_top(self, apis=["mock"])

if __name__ == "__main__":
    main()
