#!/usr/bin/env python3

"""
    Pylele Frets
"""

import os
import math
import sys
import argparse
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

from api.pylele_api import Shape, ShapeAPI
from pylele2.pylele_base import LeleBase, test_loop, main_maker, LeleStrEnum, FIT_TOL, SEMI_RATIO
from api.pylele_utils import radians, accumDiv

FRET_WIRE_WIDTH=0.5

class FretType(LeleStrEnum):
    """ Pylele Fret Type """
    ROUND = 'round'
    WIRE  = 'wire'

def pylele_frets_parser(parser = None):
    """
    Pylele Fret Assembly Parser
    """
    if parser is None:
        parser = argparse.ArgumentParser(description='Pylele Fret Configuration')

    parser.add_argument("-ft", "--fret_type",
                    help="Fret Type",
                    type=FretType,
                    choices=list(FretType),
                    default=FretType.ROUND
                    )
    return parser

def gen_fret(api:ShapeAPI, y, h, ftype:FretType = FretType.ROUND):
    """ Generate a fret """

    # main fret rod
    fret = api.genRodY(2 * y, h)
    # cut rod angles
    d = 4*h
    fret -= api.genBox( d, d, d).rotateX(45).mv(0, -y, d/2)
    fret -= api.genBox( d, d, d).rotateX(45).mv(0,  y, d/2)

    if ftype == FretType.WIRE:
        # cut bottom
        fret -= api.genBox(2*h, 2*y, h).mv(0,0,-h/2)
        # generate fret wire hole
        fret += api.genBox(FRET_WIRE_WIDTH, 2*y, h).mv(0,0,-h/2)

    return fret
class LeleFrets(LeleBase):
    """ Pylele Frets Generator class """

    def gen(self) -> Shape:
        """ Generate Frets """

        fbTck = self.cfg.FRETBD_TCK
        fWth = self.cfg.nutWth - 1  # to be narrower than fretbd
        scLen = float(self.cli.scale_length)
        fbLen = self.cfg.fretbdLen
        fHt = self.cfg.FRET_HT
        maxFrets = self.cfg.MAX_FRETS
        wideAng = self.cfg.neckWideAng
        riseAng = self.cfg.fretbdRiseAng

        # Not generating frets, if they are cut ?
        fx = 0
        gap = (scLen / 2) / accumDiv(1, 12, SEMI_RATIO)
        count = 0
        frets =  None
        while (fx < (fbLen - gap - 2 * fHt)):
            fx = fx + gap
            fy = fWth / 2 + math.tan(radians(wideAng)) * fx
            fz = fbTck + math.tan(radians(riseAng)) * fx
            
            fret = gen_fret(api=self.api, y=fy, h=fHt, ftype=self.cli.fret_type)
            fret <<= (fx, 0, fz)

            frets = fret + frets
            
            gap = gap / SEMI_RATIO
            count += 1
            if (count > maxFrets):  # prevent runaway loop
                break

        return frets

    def gen_parser(self, parser=None):
        """  Generate Fret Parser """
        parser=pylele_frets_parser(parser=parser)
        return super().gen_parser(parser=parser)

def main(args = None):
    """ Generate Frets """
    return main_maker(module_name=__name__,
                    class_name='LeleFrets',
                    args=args)

def test_frets(self,apis=None):
    """ Test Frets """
    
    tests = {}
    for ft in FretType:
        tests[ft] = ['-ft',ft]

    test_loop(module=__name__,tests=tests,apis=apis)

def test_frets_mock(self):
    """ Test Frets """
    test_frets(self, apis=['mock'])

if __name__ == '__main__':
    main()