#!/usr/bin/env python3

"""
    Pylele Head
"""

import argparse
from math import tan, inf

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

from b13d.api.core import Shape, Direction
from b13d.api.solid import main_maker, test_loop
from pylele.pylele2.strings import LeleStrings
from pylele.pylele2.head_top import LeleHeadTop

def pylele_head_parser(parser=None):
    """
    Pylele Head Parser
    """
    if parser is None:
        parser = argparse.ArgumentParser(description="Pylele Head parser")

    parser.add_argument(
        "-HT", "--separate_head_top", help="Split head top from neck.", action="store_true"
    )
    return parser

class LeleHead(LeleHeadTop):
    """Pylele Head Generator class"""    

    def gen(self) -> Shape:
        """Generate Head"""

        hdWth = self.cfg.headWth
        hdLen = self.cfg.headLen
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
            top = LeleHeadTop(cli=self.cli)
            if self.cli.separate_head_top and not self.cli.all:
                self.add_part(top)
            else:
                if self.cli.separate_head_top and self.cli.all:
                    top <<= (-2 * self.cli.all_distance, 0, self.cli.all_distance)
                hd += top.gen_full()
        
        frontCut = self.api.cylinder_y(2*hdWth, .7*spHt)
        frontCut *=  (.5, 1, 1)
        frontCut <<= (-hdLen, 0, -fspTck - .65*spHt)

        strings = LeleStrings(cli=self.cli,isCut=True).gen_full()

        hd = hd - frontCut - strings

        return hd

    def gen_parser(self,parser=None):
        """
        Head Command Line Interface
        """
        parser=pylele_head_parser(parser=parser)
        return super().gen_parser(parser=parser)

def main(args=None):
    """Generate Head"""
    return main_maker(module_name=__name__, class_name="LeleHead", args=args)

def test_head(self, apis=None):
    """Test Head"""
    tests = {
        'default':['-refv','6773'],
        'separate_head_top':['-HT'],
        }
    test_loop(module=__name__, apis=apis,tests=tests)

def test_head_mock(self):
    """Test Head"""
    test_head(self, apis=["mock"])

if __name__ == "__main__":
    main()
