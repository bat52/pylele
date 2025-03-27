#!/usr/bin/env python3

"""
    Worm Gear (using solipython)
    Modeled after "Guitar Tuners that actually work"
    https://www.thingiverse.com/thing:6099101
    That I have reworked here
    https://www.thingiverse.com/thing:6664561
"""

from solid2.extensions.bosl2.gears import worm_gear, worm_gear_thickness

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from b13d.api.solid import test_loop, main_maker, Implementation
from b13d.api.core import Shape
from b13d.parts.torus import Torus
from pylele.parts.worm_drive import WormDrive
from pylele.parts.tuner_knob_hole import TunerKnobHole

class WormGear(WormDrive):
    """ Generate Worm Gear """

    def gen_parser(self, parser=None):
        parser = WormDrive.gen_parser(self,parser=parser)
        parser.add_argument("-d", "--drive_enable",
                            help="Enable Generation of drive",
                            action="store_true")
        parser.add_argument("-cg", "--carved_gear",
                            help="Carve gear from drive",
                            action="store_true")
        # friction shaft arguments
        parser.add_argument("-fse", "--friction_shaft_enable",
                            help="Use friction tuner shaft instead of 3D printing",
                            action="store_true")
        parser.add_argument("-fsrd", "--friction_round_hole_diameter",
                            help="friction shaft round hole diameter", 
                            type=float, default=4.9)
        parser.add_argument("-fssd", "--friction_square_hole_diameter", 
                            help="friction shaft squared hole size", 
                            type=float, default=4.2)

        return parser

    def configure(self):

        WormDrive.configure(self)

        # gear outer radius
        self.gear_out_rad = self.gear_diam/2 + self.gear_teeth

        # shaft parameters
        self.shaft_h = 33
        self.shaft_diam = 9

        # string hole
        self.string_diam = 2

        if self.cli.carved_gear:
            self.gear_h = self.cli.worm_diam
        elif False:
            self.gear_h = worm_gear_thickness(
                    circ_pitch=self.cli.circ_pitch,
                    teeth=self.cli.teeth,
                    worm_diam=self.worm_diam,
                )
        else:
            # infer gear height
            self.gear_h = self.cli.worm_diam-2*self.worm_drive_teeth + 2*self.tol

    def gen(self) -> Shape:
        assert self.isCut or (self.cli.implementation in [Implementation.SOLID2,
                                                          Implementation.MANIFOLD,
                                                          Implementation.MOCK]
                                                          )
        
        gear = self.gen_gear()

        if self.cli.drive_enable:
            gear += self.gen_drive_wrapper()
        
        return gear
    
    def gen_gear_cylinder(self) -> Shape:
        gear = self.api.cylinder_z(
                l   = self.gear_h,
                rad = self.gear_out_rad + self.tol
                )    
        return gear

    def gen_import_drive(self, minkowski_en = False) -> Shape:
        if minkowski_en:
            drive_stl = 'WormDriveRoundedAscii.stl'
        else:
            drive_stl = 'WormDriveAscii.stl'
        return self.api.genImport(
            os.path.join(os.path.dirname(__file__), drive_stl )
        )
    
    def gen_drive_wrapper(self, minkowski_en = False, cut_en = False):
        if self.cli.implementation == Implementation.SOLID2 or self.isCut or cut_en:
            drive = self.gen_drive(minkowski_en=minkowski_en, cut_en=cut_en)
        else:
            drive = self.gen_import_drive(minkowski_en=minkowski_en)
        return drive.mv(self.dist,0,0)

    def gen_carved_gear(self) -> Shape:
        """ Generate Carved Gear """
        
        # gear cylinder
        gear = self.gen_gear_cylinder()

        ## drive cut
        drive = self.gen_drive_wrapper(minkowski_en=self.cli.minkowski_en)
         
        # carve gear from drive profile
        tooth_arc = 360/self.cli.teeth

        for _ in range(self.cli.teeth):
            gear -= drive
            gear = gear.rotate_z(-tooth_arc)

        return gear
    
    def gen_gear(self, spin = 19) -> Shape:
        """ Generate Gear """

        ## gear
        if self.isCut or self.cli.implementation == Implementation.MOCK:
            gear = self.gen_gear_cylinder()
        elif self.cli.carved_gear:
            gear = self.gen_carved_gear()
        elif self.cli.implementation == Implementation.SOLID2:
            gear = self.api.genShape(
                    solid=worm_gear(circ_pitch=self.cli.circ_pitch,
                                    teeth=self.cli.teeth,
                                    worm_diam=self.cli.worm_diam,
                                    worm_starts=self.cli.worm_starts,
                                    pressure_angle=self.cli.pressure_angle,
                                    # mod = self.modulus,
                                    spin = spin,
                                    worm_arc = 59
                                    )
                )
        else:
            assert False, f"Native worm gear generation only supported with {Implementation.SOLID2} api"

        # shaft
        if self.cli.friction_shaft_enable:
            gear -= TunerKnobHole(
                args = [
                    '-i', self.cli.implementation,
                    '-rd', f'{self.cli.friction_round_hole_diameter}',
                    '-sd', f'{self.cli.friction_square_hole_diameter}'
                    ]
                ).gen_full()
        else:
            gear += self.gen_shaft()

        return gear

    def gen_shaft(self) -> Shape:
        """ Generate Shaft """

        # shaft
        shaft = self.api.cylinder_z(l=self.shaft_h, rad=self.shaft_diam/2 + self.tol)

        if self.isCut:
            # cut shaft hole on the other side too
            shaft2 = self.api.cylinder_z(l=self.shaft_h, rad=self.shaft_diam/2 + self.tol)
            shaft2 <<= (0,0,-self.shaft_h/2)
            shaft += shaft2
        else:
            # string hole
            string_cut = self.api.cylinder_x(l=2*self.cli.worm_diam, rad=self.string_diam/2)
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
        return shaft

def main(args=None):
    """ Generate a Tube """
    return main_maker(module_name=__name__,
                class_name='WormGear',
                args=args)

def test_worm_gear(self,apis=[Implementation.SOLID2]):
    """ Test worm gear """
    tests = {'default'  :[],
             'cut'      :['-C'],
             'carved'   :['-cg'],
             'friction' :['-fse']}
    test_loop(module=__name__,apis=apis, tests=tests)

def test_worm_gear_mock(self):
    """ Test worm gear """
    test_loop(module=__name__,apis=[Implementation.MOCK])

if __name__ == '__main__':
    # main(args=sys.argv[1:]+['-i',Implementation.SOLID2])
    main()
