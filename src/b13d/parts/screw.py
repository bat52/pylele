#!/usr/bin/env python3

"""
    Screw Solid
"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from b13d.api.solid import Solid, test_loop, main_maker
from b13d.api.core import Shape

class Screw(Solid):
    """ Generate a Screw """

    head_diameter = 5
    in_diameter = 3
    heigth = 5

    def gen_parser(self, parser=None):
        parser = super().gen_parser(parser=parser)
        parser.add_argument("-sd", "--screw_diameter", help="Screw diameter [mm]", type=float, default=3)
        parser.add_argument("-sh", "--screw_heigth", help="Screw Height [mm]", type=float, default=5)
        parser.add_argument("-hd", "--head_diameter", help="Head diameter [mm]", type=float, default=5)
        parser.add_argument("-hh", "--head_heigth", help="Head Height [mm]", type=float, default=2)
        return parser

    def gen(self) -> Shape:
        shape = None

        if self.cli.screw_heigth > 0 and self.cli.screw_diameter > 0:
            shape = self.api.cylinder_z(self.cli.screw_heigth, self.cli.screw_diameter/2)

        if self.cli.head_heigth > 0 and self.cli.head_diameter > 0 :
            head = self.api.cone_z(self.cli.head_heigth,
                                     r1=self.cli.screw_diameter/2,
                                     r2=self.cli.head_diameter/2)\
                                        .mv(0,0,self.cli.screw_heigth/2)
            if shape is None:
                shape = head
            else:
                shape += head

        return shape

def main(args=None):
    """ Generate a Screw """
    return main_maker(module_name=__name__,
                class_name='Screw',
                args=args)

def test_screw(self,apis=None):
    """ Test Screw """
    ## Cadquery and Blender
    tests={
        'head': ['-sh','0'],
        'body': ['-hh','0'],
        # 'default' : ['-f','high'],
        'volume': ['-refv','60.9']
        }
    test_loop(module=__name__,tests=tests,apis=apis)

def test_screw_mock(self):
    """ Test Screw """
    ## Cadquery and Blender
    test_screw(self, apis=['mock'])

if __name__ == '__main__':
    main()
