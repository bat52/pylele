#!/usr/bin/env python3

"""
    Pylele Head
"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

from api.pylele_api import Shape, Direction
from pylele2.pylele_base import LeleBase, test_loop, main_maker
from pylele2.pylele_strings import LeleStrings

class LeleHead(LeleBase):
    """ Pylele Head Generator class """

    def gen(self) -> Shape:
        """ Generate Head """

        hdWth = self.cfg.headWth
        hdLen = self.cfg.headLen
        ntHt = self.cfg.NUT_HT
        fbTck = self.cfg.FRETBD_TCK
        spHt = self.cfg.SPINE_HT
        fspTck = self.cfg.FRETBD_SPINE_TCK
        topRat = self.cfg.TOP_HEAD_RATIO
        midTck = self.cfg.extMidBotTck
        botRat = self.cfg.BOT_RATIO
        orig = self.cfg.headOrig
        path = self.cfg.headPath
        joinTol = self.api.getJoinCutTol()

        hd = self.api.genLineSplineRevolveX(orig, path, -180)
        hd *= Direction(z=botRat)
        hd <<= Direction(z=joinTol/2 -midTck)

        if midTck > 0:
            midR = self.api.genLineSplineExtrusionZ(orig, path, midTck)
            midR <<= (0, 0, -midTck)
            hd += midR.mirrorXZ_and_join()

        if topRat > 0:
            top = self.api.genLineSplineRevolveX(orig, path, 180)
            top *=  (1, 1, topRat)
            top <<= (0, 0, -joinTol/2)
            hd += top

        topCut = self.api.genRodY(2*hdWth, hdLen)
        topCut <<= (-ntHt, 0, .8*hdLen + fbTck + ntHt)
        
        frontCut = self.api.genRodY(2*hdWth, .7*spHt)
        frontCut *=  (.5, 1, 1)
        frontCut <<= (-hdLen, 0, -fspTck - .65*spHt)
        
        strings = LeleStrings(cli=self.cli,isCut=True).gen_full()
    
        hd = hd - frontCut - topCut - strings

        return hd

def main(args = None):
    """ Generate Head """
    return main_maker(module_name=__name__,
                    class_name='LeleHead',
                    args=args)

def test_head(self,apis=None):
    """ Test Head """
    test_loop(module=__name__, apis=apis)

def test_head_mock(self):
    """ Test Head """
    test_head(self,apis=['mock'])

if __name__ == '__main__':
    main()
