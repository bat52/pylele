#!/usr/bin/env python3

"""
    Pylele Top
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

from b13d.api.core import Shape
from b13d.api.constants import FIT_TOL
from b13d.api.solid import main_maker, test_loop
from pylele.pylele2.body import LeleBody, LeleBodyType
from pylele.pylele2.rim import LeleRim
from pylele.pylele2.chamber import pylele_chamber_parser

class LeleBottom(LeleBody):
    """Pylele Bottom Generator class"""

    def gen(self) -> Shape:
        """Generate Bottom"""
        bot = self.gen_flat_body_bottom()
        
        if self.cli.body_type == LeleBodyType.TRAVEL and \
            self.cli.separate_bottom:

            rim = LeleRim(cli=self.cli, isCut=True).gen_full()
            rim <<= (0,0,-self.cli.flat_body_thickness)
            bot -= rim

        return bot
    
    def gen_parser(self, parser=None):
        parser=pylele_chamber_parser(parser=parser)
        return super().gen_parser(parser=parser)
    
def main(args=None):
    """Generate Top"""
    return main_maker(module_name=__name__, class_name="LeleBottom", args=args)

def test_bottom(self, apis = None):
    """Test Bottom"""
    tests = {
        "default" : [],
        "cut": ["-C"]
        }

    test_loop(module=__name__, tests=tests, apis=apis)

def test_bottom_mock(self):
    """Test Bottom"""
    test_bottom(self, apis=["mock"])

if __name__ == "__main__":
    main()
