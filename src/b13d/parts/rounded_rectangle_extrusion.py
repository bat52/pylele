#!/usr/bin/env python3

"""
    Rounded Box Solid
"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from b13d.api.solid import Solid, test_loop, main_maker, Implementation
from b13d.api.core import Shape

class RoundedRectangle(Solid):
    """ Generate a Rounded Rectangle extruded along Z """

    def gen_parser(self, parser=None):
        parser = super().gen_parser(parser=parser)
        parser.add_argument("-x", "--x", help="X [mm]", type=float, default=5)
        parser.add_argument("-y", "--y", help="Y [mm]", type=float, default=6)
        parser.add_argument("-z", "--z", help="Z [mm]", type=float, default=4)
        parser.add_argument("-r", "--r", help="Rounding radius [mm]", type=float, default=1)
        parser.add_argument("-rx", "--rx", help="Round along X", action='store_true')
        parser.add_argument("-ry", "--ry", help="Round along Y", action='store_true')
        parser.add_argument("-rz", "--rz", help="Round along Z", action='store_true')
        return parser

    def gen_fillet(self) -> Shape:
        """ cadquery implementation """
        # assert self.cli.implementation in [Implementation.CADQUERY]

        # Main cube
        box = self.api.box(self.cli.x,
                              self.cli.y,
                              self.cli.z)

        xcoords,ycoords,zcoords = self._coords()

        # round edges along x
        if self.cli.rx:
            for y in ycoords:
                for z in zcoords:
                    box = box.fillet([(0,y,z)], self.cli.r)

        # round edges along y
        if self.cli.ry:
            for x in xcoords:
                for z in zcoords:
                    box = box.fillet([(x,0,z)], self.cli.r)

        # round edges along z
        if self.cli.rz:
            for x in xcoords:
                for y in ycoords:
                    box = box.fillet([(x,y,0)], self.cli.r)

        return box

    def gen_default(self) -> Shape:
        """ default implementation """

        # Compute core box dimensions
        core_x = self.cli.x if self.cli.rx else self.cli.x - 2 * self.cli.r
        core_y = self.cli.y if self.cli.ry else self.cli.y - 2 * self.cli.r
        core_z = self.cli.z if self.cli.rz else self.cli.z - 2 * self.cli.r

        box = self.api.box(core_x, core_y, core_z)
        xcoords, ycoords, zcoords = self._coords()

        # Add lateral faces along X
        if not self.cli.rx:
            for xpos in xcoords:
                lbox = self.api.box(2 * self.cli.r, core_y, core_z)
                lbox <<= (xpos, 0, 0)
                box += lbox

        # Add lateral faces along Y
        if not self.cli.ry:
            for ypos in ycoords:
                lbox = self.api.box(core_x, 2 * self.cli.r, core_z)
                lbox <<= (0, ypos, 0)
                box += lbox

        # Add lateral faces along Z
        if not self.cli.rz:
            for zpos in zcoords:
                lbox = self.api.box(core_x, core_y, 2 * self.cli.r)
                lbox <<= (0, 0, zpos)
                box += lbox

        # If rounding is enabled along an axis, add full-length cylinders
        if self.cli.rx:
            for ypos in ycoords:
                for zpos in zcoords:
                    edge = self.api.cylinder_x(self.cli.x, rad=self.cli.r)
                    edge <<= (0, ypos, zpos)
                    box += edge

        if self.cli.ry:
            for xpos in xcoords:
                for zpos in zcoords:
                    edge = self.api.cylinder_y(self.cli.y, rad=self.cli.r)
                    edge <<= (xpos, 0, zpos)
                    box += edge

        if self.cli.rz:
            for xpos in xcoords:
                for ypos in ycoords:
                    edge = self.api.cylinder_z(self.cli.z, rad=self.cli.r)
                    edge <<= (xpos, ypos, 0)
                    box += edge
        
        return box

    def _coords(self):
        
        xcoords = [-self.cli.x/2+self.cli.r, self.cli.x/2-self.cli.r]
        ycoords = [-self.cli.y/2+self.cli.r, self.cli.y/2-self.cli.r]
        zcoords = [-self.cli.z/2+self.cli.r, self.cli.z/2-self.cli.r]

        return xcoords,ycoords,zcoords

    def gen_solidpython(self) -> Shape:
        """ solidpython implementation """

        xcoords,ycoords,zcoords = self._coords()

        box = None
        # round edges along x
        if self.cli.rx:
            for y in ycoords:
                for z in zcoords:
                    edge = self.api.cylinder_x(self.cli.x,self.cli.r)
                    edge <<= (0,y,z)
                    box = edge + box

        # round edges along y
        if self.cli.ry:
            for x in xcoords:
                for z in zcoords:
                    edge = self.api.cylinder_y(self.cli.y,self.cli.r)
                    edge <<= (x,0,z)
                    box = edge + box

        # round edges along y
        if self.cli.rz:
            for x in xcoords:
                for y in ycoords:
                    edge = self.api.cylinder_z(self.cli.z,self.cli.r)
                    edge <<= (x,y,0)
                    box = edge + box

        if box is None:
            # no rounding
            return self.api.box(self.cli.x,
                              self.cli.y,
                              self.cli.z)
        else:
            # hull from the corners
            return box.hull()

    def gen(self) -> Shape:
        """ generate rounded box """
        
        if self.cli.implementation in [Implementation.CADQUERY, Implementation.BLENDER, Implementation.MOCK]:
            # apis that support fillet
            # return self.gen_fillet()
            return self.gen_default()
        elif self.cli.implementation in [ Implementation.SOLID2, 
                                         Implementation.TRIMESH, 
                                         Implementation.MANIFOLD,
                                         ]:
            # apis that support hull
            return self.gen_solidpython()
        
        assert False

def main(args=None):
    """ Generate a Rounded Box """
    return main_maker(module_name=__name__,
                class_name='RoundedRectangle',
                args=args)

def test_rounded_rectangle(self,apis=None):
    """ Test Rounded Box """
    tests={'x':['-rx'],
           'y':['-ry'],
           'z':['-rz'],
           'secx':['-secx','0','10'],
           'secy':['-secy','0','10'],
           'secz':['-secz','0','10'],
           }
    test_loop(module=__name__,tests=tests,apis=apis)

def test_rounded_rectangle_mock(self):
    """ Test Tube Mock """
    ## Cadquery and Blender
    test_rounded_rectangle(self, apis=['mock'])

if __name__ == '__main__':
    main()
