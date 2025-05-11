#!/usr/bin/env python3

"""
    6.5mm jack holder
"""

from math import pi, sin, cos

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from b13d.api.solid import Solid, test_loop, main_maker, Implementation, create_parser_from_class
from b13d.api.utils import radians
from b13d.api.core import Shape, BBoxEnum
from b13d.parts.rounded_rectangle_extrusion import RoundedRectangle
# from pylele.parts.jack_hole_6p5mm import JackHole6p5
from pylele.parts.jack_6p5mm import Jack6p5

class JackHolderConfig(object):
    """ Jack Holder Generator class"""

    # screw cylinder
    main_cylinder_d: float = 30
    main_cylinder_h: float = 60
    main_cylinder_angle: float = 30
    jack_hole_d: float = 8.6
    wall_thickness: float = 2
    screw_hole_d: float = 3
    screw_holes_en: bool = True
    hull_en = False
    jack_en = False

class JackHolder(Solid):
    """ Generate a 6.5mm jack holder"""

    def gen_parser(self, parser=None):  
        parser = super().gen_parser(parser=parser)        
        parser = create_parser_from_class(JackHolderConfig, parser=parser)        
        return parser

    def gen(self) -> Shape:
        """ generate 6,5mm jack holder"""
        tol = self.api.tolerance()

        main_cylinder = self.gen_main_cylinder()
        main_cylinder -= self.gen_cut_box()
        plate = self.gen_plate()
        main_cylinder += plate
        main_cylinder -= self.gen_cut_plate_border()
        if self.cli.hull_en:
            main_cylinder = main_cylinder.hull()

        main_cylinder -= self.gen_inner_cylinder()
        main_cylinder -= self.gen_jack_hole()
        if self.cli.screw_holes_en:
            main_cylinder -= self.gen_screw_holes(plate)
        if self.cli.jack_en:         
            main_cylinder += self.gen_jack()

        return main_cylinder

    def gen_main_cylinder(self) -> Shape:
        """ generate main cylinder """

        # main cylinder
        main_cylinder = self.api.cylinder_rounded_z(l=self.cli.main_cylinder_h,
                                rad=self.cli.main_cylinder_d/2,
                                domeRatio=0.2)

        main_cylinder <<= (0, 0, -main_cylinder.bottom() - self.cli.wall_thickness)
        main_cylinder = main_cylinder.rotate_y(self.cli.main_cylinder_angle)    

        return main_cylinder

    def gen_plate(self) -> Shape:
        """ generate plate """
        # plate
        self.cosa = cos(radians(self.cli.main_cylinder_angle))
        self.sina = sin(radians(self.cli.main_cylinder_angle))

        self.plate_h = self.cli.main_cylinder_h * self.cosa + \
                        2 * self.cli.screw_hole_d + \
                        4 * self.cli.wall_thickness
                       # elf.cli.main_cylinder_d * self.sina + \
        
        plate = RoundedRectangle(args = [
                                    "-x", str(self.cli.wall_thickness),
                                    "-y", str(self.cli.main_cylinder_d),
                                    "-z", str(self.plate_h),
                                    "-r", str(self.cli.screw_hole_d),
                                    '-rx', # '-ry', # '-rz',
                                    "-i", self.cli.implementation
                                    ], 
                                    ).gen_full()
        
        plate_zshift = self.plate_h/2 - self.cli.main_cylinder_d/2 * self.sina - \
                self.cli.screw_hole_d - self.cli.wall_thickness        
        self.plate_zshift = plate_zshift

        plate <<= (
            self.cli.main_cylinder_d/2 * self.cosa + self.cli.wall_thickness/2,
            0,
            plate_zshift
        )    
        return plate
    
    def gen_cut_plate_border(self) -> Shape:
        """ generate cut plate border """

        plate = self.gen_plate()

        # cut plate border
        plate_cut=self.api.box(2*self.cli.wall_thickness,
                               2*self.cli.main_cylinder_d,
                               2*self.plate_h
                               )
        plate_cut <<= (
            plate.left()-plate_cut.left(),
            plate.center()[1]-plate_cut.center()[1],
            plate.center()[2]-plate_cut.center()[2]
        )
        plate_cut -= plate
        return plate_cut

    def gen_cut_box(self) -> Shape:
        """ generate cut box """
        # cut box
        box_h = self.cli.main_cylinder_h * 2
        cut_box = self.api.box(self.cli.main_cylinder_d,
                               self.cli.main_cylinder_d,
                               box_h)
        cut_box <<= (
            self.cli.main_cylinder_d,
            0,
            0
        )
        return cut_box

    def gen_inner_cylinder(self) -> Shape:
        """ generate inner cylinder """
        # inner cylinder
        inner_cylinder = self.api.cylinder_z(
                                l=self.cli.main_cylinder_h - 4*self.cli.wall_thickness,
                                rad=self.cli.main_cylinder_d/2 - self.cli.wall_thickness,
                                )
        inner_cylinder <<= (0, 0, self.cli.main_cylinder_h/2 - self.cli.wall_thickness)
        inner_cylinder = inner_cylinder.rotate_y(self.cli.main_cylinder_angle)
        return inner_cylinder

    def gen_jack_hole(self) -> Shape:
        """ generate jack hole """
        # jack hole
        if False:
            jack_hole = JackHole6p5(cli=self.cli, isCut=False).gen_full()
        else:
            jack_hole = self.api.cylinder_z(
                                l=8*self.cli.wall_thickness,
                                rad=self.cli.jack_hole_d/2,
                                )        
            jack_hole = jack_hole.rotate_y(self.cli.main_cylinder_angle)
        return jack_hole
    
    def gen_screw_holes(self, plate) -> Shape:
        """ generate screw holes """

        # screw holes 
        screw_hole = self.api.cylinder_x(
                                l=self.cli.main_cylinder_d,
                                rad=self.cli.screw_hole_d/2,
                                )
        
        screw_center_to_border = self.cli.wall_thickness + self.cli.screw_hole_d/2

        yscrew_left    = plate.back()   - screw_center_to_border        
        zscrew_bottom  = plate.bottom() + screw_center_to_border        
        zscrew_top     = plate.top()    - screw_center_to_border

        # screw left bottom
        screw_hole_lb = screw_hole.dup()
        screw_hole_lb <<= ( 0, 
                        yscrew_left, 
                        zscrew_bottom)
        
        # screw left top
        screw_hole_lt = screw_hole.dup()
        screw_hole_lt <<= ( 0, 
                        yscrew_left, 
                        zscrew_top)
        
        screw_holes_l = screw_hole_lb + screw_hole_lt
        screw_holes_r = screw_holes_l.mirror()
        
        return screw_holes_l + screw_holes_r
        
    def gen_jack(self) -> Shape:
        """ generate jack """
        jack = Jack6p5(args=['-i',self.cli.implementation], isCut=True).gen_full()
        jack = jack.rotate_y(self.cli.main_cylinder_angle)
        return jack

def main(args=None):
    """ Generate Jack Holder """
    return main_maker(module_name=__name__,
                class_name='JackHolder',
                args=args)

def test_jack_holder(self,
                     apis=[
                         Implementation.MANIFOLD,
                         Implementation.SOLID2,
                         Implementation.CADQUERY,
                         Implementation.TRIMESH,
                         # Implementation.BLENDER,                         
                         ]):
    """ Test Jack Holder """
    tests={'default':[]}
    test_loop(module=__name__,tests=tests,apis=apis)

def test_jack_holder_mock(self):
    """ Test Jack Holder 6.5mm """
    test_jack_holder(self, apis=[Implementation.MOCK])

if __name__ == '__main__':
    main()
