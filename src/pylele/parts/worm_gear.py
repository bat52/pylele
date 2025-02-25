#!/usr/bin/env python3

"""
    Worm Gear (using solipython)
    Modeled after "Guitar Tuners that actually work"
    https://www.thingiverse.com/thing:6099101
    That I have reworked here
    https://www.thingiverse.com/thing:6664561
"""

from solid2.extensions.bosl2.gears import worm_gear, worm, enveloping_worm, worm_gear_thickness, worm_dist

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from b13d.api.solid import Solid, test_loop, main_maker, Implementation
from b13d.api.core import Shape
from b13d.parts.pencil import Pencil
from b13d.parts.torus import Torus
from pylele.parts.worm_drive import WormDrive

class WormGear(WormDrive):
    """ Generate Worm Gear """

    def gen_parser(self, parser=None):
        parser = WormDrive.gen_parser(self,parser=parser)
        parser.add_argument("-d", "--drive_enable", help="Enable Generation of drive", action="store_true")        
        parser.add_argument("-cg", "--carved_gear", help="Carve gear from drive", action="store_true")
        parser.add_argument("-me", "--minkowski_enable",
                            help="Enable minkowski-based rounding of drive when using carved_gear option",
                            action="store_true")
        return parser

    def configure(self):
        Solid.configure(self)

        # if self.cli.drive_enable or self.cli.carved_gear:
        WormDrive.configure(self)

        # gear outer radius
        self.gear_out_rad = self.gear_diam/2 + self.gear_teeth

        # shaft parameters
        self.shaft_h = 10
        self.shaft_diam = 8

        # string hole
        self.string_diam = 2

        if self.cli.carved_gear:
            self.gear_h = self.worm_diam
        elif False:
            self.gear_h = worm_gear_thickness(
                    circ_pitch=self.circ_pitch,
                    teeth=self.teeth,
                    worm_diam=self.worm_diam,
                )
        else:
            self.gear_h = self.worm_diam-2*self.worm_drive_teeth + 2*self.tol

    def gen(self) -> Shape:
        assert self.isCut or (self.cli.implementation in [Implementation.SOLID2, Implementation.MOCK])
        
        gear = self.gen_gear()

        if self.cli.drive_enable:
            return gear + self.gen_drive()
        
        return gear
    
    def gen_gear(self) -> Shape:
        """ Generate Gear """

        ## gear
        if self.isCut or self.cli.carved_gear:
            gear = self.api.cylinder_z(
                    l   = self.gear_h,
                    rad = self.gear_out_rad + self.tol
                    )
        else:
            gear = self.api.genShape(
                    solid=worm_gear(circ_pitch=self.circ_pitch,
                                    teeth=self.teeth,
                                    worm_diam=self.worm_diam,
                                    worm_starts=self.worm_starts,
                                    pressure_angle=self.pressure_angle,
                                    # mod = self.modulus,
                                    spin = 19,
                                    worm_arc = 59
                                    )
                )

        if self.cli.carved_gear:
            drive = self.gen_drive(minkowski_en=self.cli.minkowski_enable)
            tooth_arc = 360/self.teeth

            for _ in range(self.teeth):
                gear -= drive
                gear = gear.rotate_z(-tooth_arc)

        # shaft
        shaft = self.api.cylinder_z(l=self.shaft_h, rad=self.shaft_diam/2 + self.tol)

        if not self.isCut:
            # string hole
            string_cut = self.api.cylinder_x(l=2*self.worm_diam, rad=self.string_diam/2)
            string_cut <<= (0,0,self.shaft_h/2-self.string_diam)
            shaft -= string_cut

            # torus to shape shaft
            torus_rad = self.shaft_diam/4
            torus = Torus(
                args = ['-i', self.cli.implementation,
                        '-r1', f'{torus_rad}',
                        '-r2', f'{self.shaft_diam/2+torus_rad/2}'
                        ]
            ).gen_full()
            torus = torus.rotate_x(90)
            torus <<= (0,0,self.shaft_h/2 - self.string_diam)
            shaft -= torus
            
        shaft <<= (0,0,self.shaft_h/2)
        gear += shaft

        return gear

def main(args=None):
    """ Generate a Tube """
    return main_maker(module_name=__name__,
                class_name='WormGear',
                args=args)

def test_worm_gear(self,apis=[Implementation.SOLID2]):
    """ Test worm gear """
    tests = {'default':[],
             'cut'    :['-C']}
    test_loop(module=__name__,apis=apis, tests=tests)

def test_worm_gear_mock(self):
    """ Test worm gear """
    test_loop(module=__name__,apis=[Implementation.MOCK])

if __name__ == '__main__':
    main(args=sys.argv[1:]+['-i',Implementation.SOLID2])
