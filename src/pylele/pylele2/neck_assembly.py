#!/usr/bin/env python3

"""
    Pylele Neck Assembly
"""

import argparse
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

from b13d.api.core import Shape
from b13d.api.solid import main_maker, test_loop
from pylele.pylele2.config import LeleBodyType
from pylele.pylele2.base import LeleBase
from pylele.pylele2.fretboard_assembly import (
    LeleFretboardAssembly,
    pylele_fretboard_assembly_parser,
    FretType,
    NutType,
)
from pylele.pylele2.fretboard_spines import LeleFretboardSpines
from pylele.pylele2.head import LeleHead, pylele_head_parser
from pylele.pylele2.neck_joint import LeleNeckJoint
from pylele.pylele2.neck import LeleNeck
from pylele.pylele2.nut import LeleNut
from pylele.pylele2.spines import LeleSpines


def pylele_neck_assembly_parser(parser=None):
    """
    Pylele Neck Assembly Parser
    """
    if parser is None:
        parser = argparse.ArgumentParser(description="Pylele Neck Assembly parser")
    parser = pylele_fretboard_assembly_parser(parser=parser)
    parser = pylele_head_parser(parser=parser)
    return parser

class LeleNeckAssembly(LeleBase):
    """Pylele Neck Assembly Generator class"""

    def gen(self) -> Shape:
        """Generate Neck Assembly"""

        jcTol = self.api.tolerance()

        ## Neck
        neck = LeleNeck(cli=self.cli)

        ## Neck Joint
        if self.cli.separate_neck:
            neck += LeleNeckJoint(cli=self.cli, isCut=self.isCut).mv(0, 0, -jcTol)

        if not self.isCut:
            ## Head
            head = LeleHead(cli=self.cli).mv(jcTol,0,0)
            neck += head
            self.add_parts(head.get_parts())

            ## Fretboard, only part of neck assembly if separate fretboard or separate neck
            ## if only separate top, fretboard is joined to top!
            if (self.cli.separate_fretboard or self.cli.separate_neck or not self.cli.separate_top):
                fretbd = LeleFretboardAssembly(cli=self.cli)
                fretbd.gen_full()
                if self.cli.separate_fretboard:
                    if self.cli.all:
                        fretbd <<= (-self.cli.all_distance, 0, self.cli.all_distance)
                        neck += fretbd
                    else:
                        self.add_part(fretbd)
                else:
                    neck += fretbd.mv(max(0.01, jcTol), 0, -jcTol) # HACK cadquery bug needs this
                    self.add_parts(fretbd.get_parts())

            if self.cli.separate_fretboard or self.cli.separate_top:
                neck -= LeleNut(cli=self.cli, isCut=True)

            ## Spines
            if self.cli.num_spines > 0:
                neck -= LeleSpines(cli=self.cli, isCut=True)

                ## Fretboard Spines
                if (self.cli.separate_fretboard or self.cli.separate_top):
                    neck -= LeleFretboardSpines(cli=self.cli, isCut=True)

        return neck.gen_full()

    def gen_parser(self,parser=None):
        """
        pylele Command Line Interface
        """
        return super().gen_parser(
            pylele_neck_assembly_parser(parser=parser)
        )


def main(args=None):
    """Generate Neck Assembly"""
    return main_maker(module_name=__name__, class_name="LeleNeckAssembly", args=args)


def test_neck_assembly(self, apis=None):
    """Test Neck Assembly"""

    tests = {
        'default'            : [],
        'fret_wire'          : ['-ft', str(FretType.WIRE)],
        'zerofret'           : ['-nt', str(NutType.ZEROFRET)],
        'separate_neck'      : ['-N'],
        'separate_fretboard' : ['-F'],
        'separate_nut'       : ['-NU'],
        'separate_frets'     : ['-FR'],
        'separate_all'       : ['-N','-FR','-NU','-F'],
        'flat_body'          : ['-bt',LeleBodyType.FLAT]
    }

    test_loop(module=__name__, tests=tests, apis=apis)


def test_neck_assembly_mock(self):
    """Test Neck Assembly"""
    test_neck_assembly(self, apis=["mock"])


if __name__ == "__main__":
    main()
