#!/usr/bin/env python3

"""
    Tunable Bridge Saddle
"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from pylele.api.solid import Solid, test_loop, main_maker, Implementation
from pylele.api.core import Shape

class TunableSaddle(Solid):
    """ Generate a Tunable Saddle """

    def gen_parser(self, parser=None):
        parser = super().gen_parser(parser=parser)
        parser.add_argument("-x", "--x", help="X [mm]", type=float, default=2)
        parser.add_argument("-y", "--y", help="Y [mm]", type=float, default=4)
        parser.add_argument("-z", "--z", help="Z [mm]", type=float, default=4)
        parser.add_argument("-sh", "--saddle_heigth", help="saddle height [mm]", type=float, default=5)
        parser.add_argument("-r", "--r", help="String Radius [mm]", type=float, default=0.5)
        parser.add_argument("-t", "--t", help="Fit Tolerance [mm]", type=float, default=0.2)
        return parser

    def gen(self) -> Shape:
        """ generate tunable bridge holder """
        
        cutx = 40
        cut_tol = self.cli.t

        # base
        if self.cli.is_cut:
            base = self.api.box(cutx,self.cli.y+cut_tol,self.cli.z+cut_tol)
        else:
            base = self.api.box(self.cli.x,self.cli.y,self.cli.z)

        # saddle
        if self.cli.is_cut:
            saddle = self.api.box(cutx, self.cli.y -2 + cut_tol, self.cli.saddle_heigth)
        else:
            saddle = self.api.box(self.cli.x, self.cli.y -2, self.cli.saddle_heigth)
        saddle <<= (0,0,self.cli.z/2 + self.cli.saddle_heigth/2)

        # string hole
        string = self.api.cylinder_x(self.cli.x,rad=self.cli.r)
        string <<= (0,0,
                    self.cli.z/2+
                        self.cli.saddle_heigth
                    )
        return base + saddle - string
        
def main(args=None):
    """ Generate the tunable saddle """
    return main_maker(module_name=__name__,
                class_name='TunableSaddle',
                args=args)

def test_tunable_saddle(self,apis=None):
    """ Test Tunable Saddle """
    tests={'default':[]}
    test_loop(module=__name__,tests=tests,apis=apis)

def test_tunable_saddle_mock(self):
    """ Test Tunable Saddle Mock """
    test_tunable_saddle(self, apis=['mock'])

if __name__ == '__main__':
    main()