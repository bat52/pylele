#!/usr/bin/env python3

"""
    Rounded Face Rectangle Solid
"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from b13d.api.solid import Solid, test_loop, main_maker, Implementation
from b13d.api.core import Shape

class RoundedFaceRectangle(Solid):
    """ Generate a Rectangle with rounded faces towards one direction """

    def gen_parser(self, parser=None):
        parser = super().gen_parser(parser=parser)
        parser.add_argument("-x", "--x", help="X [mm]", type=float, default=10)
        parser.add_argument("-y", "--y", help="Y [mm]", type=float, default=20)
        parser.add_argument("-z", "--z", help="Z [mm]", type=float, default=40)
        parser.add_argument("-r", "--r", help="Rounding radius [mm]", type=float, default=1)
        parser.add_argument("-rx", "--rx", help="Round along X", action='store_true')
        parser.add_argument("-ry", "--ry", help="Round along Y", action='store_true')
        parser.add_argument("-rz", "--rz", help="Round along Z", action='store_true')
        return parser

    def _coords(self):
        
        xcoords = [-self.cli.x/2+self.cli.r, self.cli.x/2-self.cli.r]
        ycoords = [-self.cli.y/2+self.cli.r, self.cli.y/2-self.cli.r]
        zcoords = [-self.cli.z/2+self.cli.r, self.cli.z/2-self.cli.r]

        return xcoords,ycoords,zcoords

    def gen(self) -> Shape:
        """ cadquery implementation """

        # Main cube
        box = self.api.box(self.cli.x,
                              self.cli.y,
                              self.cli.z)

        # round edges along x
        if self.cli.rx:
            box += self.api.cylinder_x(l=self.cli.x,rad=self.cli.z/2).mv(0,self.cli.y/2,0)
            box += self.api.cylinder_x(l=self.cli.x,rad=self.cli.z/2).mv(0,-self.cli.y/2,0)

        # round edges along y
        if self.cli.ry:
            box += self.api.cylinder_y(l=self.cli.y,rad=self.cli.z/2).mv(self.cli.x/2,0,0)
            box += self.api.cylinder_y(l=self.cli.y,rad=self.cli.z/2).mv(-self.cli.x/2,0,0)

        # round edges along z
        if self.cli.rz:
            box += self.api.cylinder_z(l=self.cli.z,rad=self.cli.x/2).mv(0,self.cli.y/2, 0)
            box += self.api.cylinder_z(l=self.cli.z,rad=self.cli.x/2).mv(0,-self.cli.y/2, 0)

        return box

def main(args=None):
    """ Generate a Rounded Box """
    return main_maker(module_name=__name__,
                class_name='RoundedFaceRectangle',
                args=args)

def test_rounded_face_rectangle(self,apis=None):
    """ Test Rounded Face Rectangle """
    tests={'x':['-rx'],
           'y':['-ry'],
           'z':['-rz'],
           }
    test_loop(module=__name__,tests=tests,apis=apis)

def test_rounded_face_rectangle_mock(self):
    """ Test Rounded Face Rectangle Mock """
    ## Cadquery and Blender
    test_rounded_face_rectangle(self, apis=['mock'])

if __name__ == '__main__':
    main()
