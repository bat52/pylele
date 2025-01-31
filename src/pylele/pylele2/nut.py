#!/usr/bin/env python3

"""
    Pylele Nut
"""

import os
import argparse
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

from b13d.api.core import StringEnum, Shape, Direction
from b13d.api.constants import FIT_TOL
from b13d.api.solid import main_maker, test_loop
from pylele.pylele2.base import LeleBase
from pylele.pylele2.strings import LeleStrings


class NutType(StringEnum):
    """Nut Type"""

    NUT = "nut"
    ROUND = "round"
    ZEROFRET = "zerofret"


def pylele_nut_parser(parser=None):
    """
    Pylele Nut Parser
    """
    if parser is None:
        parser = argparse.ArgumentParser(description="Pylele Configuration")

    parser.add_argument(
        "-nt",
        "--nut_type",
        help="Nut Type",
        type=NutType,
        choices=list(NutType),
        default=NutType.NUT,
    )
    return parser


class LeleNut(LeleBase):
    """Pylele Nut Generator class"""

    def gen(self) -> Shape:
        """Generate Nut"""

        jcTol = self.cfg.tolerance
        fitTol = FIT_TOL
        fbTck = self.cfg.FRETBD_TCK
        ntHt = self.cfg.NUT_HT
        ntWth = self.cfg.nutWth + fbTck/4 + .5  # to be wider than fretbd
        f0X = -fitTol if self.isCut else 0

        DOME_RATIO = 1/4
        f0Top    = self.api.cylinder_rounded_y(ntWth, ntHt, DOME_RATIO)

        if self.cli.nut_type in [NutType.ROUND, NutType.ZEROFRET]:
            f0Top   -= self.api.box(2*ntHt, 2*ntWth, fbTck).mv(0, 0, -fbTck/2)

            f0Bot    = self.api.cylinder_rounded_y(ntWth, ntHt, 1/4)
            f0Bot   -= self.api.box(2*ntHt, 2*ntWth, fbTck).mv(0, 0, fbTck/2)
            f0Bot   *= Direction.Z * (fbTck/ntHt)
        elif self.cli.nut_type in [NutType.NUT]:
            f0Bot   = self.api.box(2*ntHt, ntWth - ntHt*(1 - 2*DOME_RATIO), fbTck).mv(0, 0, -fbTck/2)
            f0Bot  += self.api.box(  ntHt, ntWth - ntHt*(1 - 2*DOME_RATIO), ntHt).mv(ntHt/2, 0, ntHt/2)

        nut = f0Top.mv(0, 0, -jcTol) + f0Bot # lower top to make sure valid volume
        nut <<= (f0X, 0, fbTck)

        # Add strings cut
        if not self.cli.nut_type == NutType.ZEROFRET: # and not self.isCut:
            nut -= LeleStrings(isCut=True,cli=self.cli).gen_full()

        return nut

    def gen_parser(self, parser=None):
        """
        pylele Command Line Interface
        """
        return super().gen_parser(parser=pylele_nut_parser(parser=parser))


def main(args=None):
    """Generate Nut"""
    return main_maker(module_name=__name__, class_name="LeleNut", args=args)


def test_nut(self, apis=None):
    """Test Nut"""

    tests = {
        "separate_fretboard": ["-F"],
    }
    for nut_type in list(NutType):
        tests |= { nut_type : ["-nt", nut_type] }
    test_loop(module=__name__, tests=tests, apis=apis)


def test_nut_mock(self):
    """Test Nut"""
    test_nut(self, apis=["mock"])


if __name__ == "__main__":
    main()
