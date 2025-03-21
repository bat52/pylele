#!/usr/bin/env python3

"""
    Pylele Strings
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

from b13d.api.core import Shape
from b13d.api.constants import FIT_TOL
from b13d.api.solid import main_maker, test_loop
from pylele.pylele2.base import LeleBase


class LeleStrings(LeleBase):
    """Pylele Strings Generator class"""

    def gen(self) -> Shape:
        """Generate Strings"""

        cutAdj = FIT_TOL if self.isCut else 0
        srad = self.cfg.STR_RAD + cutAdj
        paths = self.cfg.stringPaths

        strs = None
        for p in paths:
            strs = self.api.regpoly_sweep(srad, p) + strs

        return strs

def main(args=None):
    """Generate Strings"""
    return main_maker(module_name=__name__, class_name="LeleStrings", args=args)


def test_strings(self, apis=None):
    """Test String"""
    tests = {"cut": ["-C", "-refv", "2448"]}
    test_loop(module=__name__, tests=tests, apis=apis)


def test_strings_mock(self):
    """Test String"""
    test_strings(self, apis=["mock"])


if __name__ == "__main__":
    main()
