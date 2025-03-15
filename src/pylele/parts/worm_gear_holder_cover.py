#!/usr/bin/env python3

"""
    Worm Gear (using solipython)
    Modeled after "Guitar Tuners that actually work"
    https://www.thingiverse.com/thing:6099101
    That I have reworked here
    https://www.thingiverse.com/thing:6664561
"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from b13d.api.solid import Solid, test_loop, main_maker, Implementation
from b13d.api.core import Shape
from pylele.parts.worm_gear_holder import WormGearHolder

class WormGearHolderCover(WormGearHolder):
    """ Generate Worm Gear Holder"""
    
    def gen_parser(self, parser=None):
        parser = WormGearHolder.gen_parser(self,parser=parser)
        parser.add_argument("-he", "--holder_enable", help="Enable Generation of holder", action="store_true")
        return parser

    def gen(self) -> Shape:
        cover  = self.gen_holder_gears_cut(extrude_en = False).half([False,False,True])
        cover -= self.gen_holder_gears_cut(extrude_en = True, cut_en=True)        
    
        if self.cli.holder_enable:
            cover += self.gen_holder()
 
        return cover

def main(args=None):
    """ Generate Worm Gear Holder Cover """
    return main_maker(module_name=__name__,
                class_name='WormGearHolderCover',
                args=args)

def test_worm_gear_holder_cover(self,apis=[Implementation.SOLID2]):
    """ Test worm gear """
    test_loop(module=__name__,apis=apis)

def test_worm_gear_holder_cover_mock(self):
    """ Test worm gear holder """
    test_loop(module=__name__,apis=[Implementation.MOCK])

if __name__ == '__main__':
    # main(args=sys.argv[1:]+['-i',Implementation.SOLID2])
    main()

