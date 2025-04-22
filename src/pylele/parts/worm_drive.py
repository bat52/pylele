#!/usr/bin/env python3

"""
    Worm Gear (using solipython)
    Modeled after "Guitar Tuners that actually work"
    https://www.thingiverse.com/thing:6099101
    That I have reworked here
    https://www.thingiverse.com/thing:6664561
"""

from solid2 import sphere, minkowski
from solid2.extensions.bosl2.gears import worm_gear, worm, enveloping_worm, worm_gear_thickness, worm_dist

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from b13d.api.solid import Solid, test_loop, main_maker, Implementation
from b13d.api.core import Shape
from b13d.parts.pencil import Pencil

class WormDrive(Solid):
    """ Generate Worm Drive """

    def gen_parser(self, parser=None):
        parser = super().gen_parser(parser=parser)
        parser.add_argument("-e", "--enveloping_worm", help="Enveloping Worm", action="store_true")
        parser.add_argument("-me", "--minkowski_en",
                            help="Enable minkowski-based rounding "
                            "of drive when using carved_gear option",
                            action="store_true")
        parser.add_argument("-cp", "--circ_pitch",
                            help="Circular pitch, the distance between teeth centers around the pitch circle.",
                            type=float, default = 3.5)
        parser.add_argument("-wd", "--worm_diam",
                            help="The pitch diameter of the worm gear.",
                            type=float, default = 8)
        parser.add_argument("-wed", "--worm_extension_diam",
                    help="Diameter of the extension drive rings.",
                    type=float, default = 10)
        parser.add_argument("-t", "--teeth",
                    help="Number of teeth of the worm gear.",
                    type=int, default = 14)
        parser.add_argument("-ws", "--worm_starts",
                    help="Number of star tooth of the worm drive",
                    type=int, default = 1)
        parser.add_argument("-pa", "--pressure_angle",
                    help="Controls how straight or bulged the tooth sides are. In degrees.",
                    type=float, default = 29)
        parser.add_argument("-wt", "--wall_thickness",
                    help="Wall thickness",
                    type=float, default = 4)
        parser.add_argument("-mirror", "--mirror_enable", help="Mirror to inverse thread direction", action="store_true")
        return parser

    def configure(self):
        Solid.configure(self)

        # gear &  worm common parameters
        # self.modulus = 3/2

        # inferred parameters
        if self.cli.teeth > 12:
            self.gear_diam = 14.6
        else:
            self.gear_diam = 11
        self.worm_drive_teeth = 1.43
        self.gear_teeth = 3
        
        # hex hole
        self.hex_hole = 4.3

        # drive parameters
        self.drive_h = self.cli.worm_diam + self.gear_teeth
        self.drive_teeth_l = 2*0.98

        # drive cylindrical extension
        self.disk_h = (self.gear_diam - self.drive_h + 2)/2

        # distance between worm and gear
        if self.cli.implementation == Implementation.SOLID2:
            self.dist = worm_dist(
                        circ_pitch=self.cli.circ_pitch,
                        d=self.cli.worm_diam,
                        starts=self.cli.worm_starts,
                        teeth=self.cli.teeth,
                        # [profile_shift],
                        pressure_angle=self.cli.pressure_angle
                        )
        else:
            self.dist = (self.gear_diam+self.cli.worm_diam)/2 # + self.worm_drive_teeth # + self.gear_teeth

        # cut tolerance
        self.cut_tolerance = 0.3
        self.tol = self.cut_tolerance if self.isCut else 0

    def gen(self) -> Shape:
        assert self.isCut or (self.cli.implementation in [Implementation.SOLID2, Implementation.MOCK])
    
        drive = self.gen_drive(minkowski_en=self.cli.minkowski_en)
        return drive

    def gen_worm(self, spin = 0, minkowski_en = False, cut_en = False) -> Shape:
        """ Generate worm """

        ## drive
        if self.isCut or cut_en:
            drive = self.api.cylinder_z(
                l = self.drive_h+2*self.tol,
                rad=self.cli.worm_diam/2+self.drive_teeth_l/2+self.tol
                )
        else:
            if not self.cli.enveloping_worm:
                bworm = worm(   circ_pitch=self.cli.circ_pitch,
                                d=self.cli.worm_diam,
                                starts=self.cli.worm_starts,
                                l=self.drive_h,
                                pressure_angle=self.cli.pressure_angle,
                                # mod = self.modulus,
                                spin = spin
                                )
            else:
                bworm = enveloping_worm(
                                circ_pitch=self.cli.circ_pitch,
                                d=self.cli.worm_diam,
                                starts=self.cli.worm_starts,
                                l=self.drive_h,
                                pressure_angle=self.cli.pressure_angle,
                                # mod = self.modulus,
                                mate_teeth = self.cli.teeth,
                                spin = spin
                                )
            
            if minkowski_en:
                # extend worm with fitting tolerance
                bworm = minkowski()(
                    bworm,
                    sphere(self.cut_tolerance)
                    )

            drive = self.api.genShape(
                    solid=bworm
                )

        return drive
    
    def simmetric_cylinders(self, rad, h, gap):
        """ Generate simmetric cylinders """
        disk_low = self.api.cylinder_z(l=h,
                                    rad=rad
                                    )
        disk_high = disk_low.dup()
        disk_low  <<= (0,0,-(h+gap)/2)
        disk_high <<= (0,0, (h+gap)/2)
        return disk_low + disk_high

    def gen_drive(self, spin = 0, minkowski_en = False, cut_en = False) -> Shape:
        """ Generate Drive """

        # worm
        worm_drive = self.gen_worm(spin=spin, minkowski_en=minkowski_en, cut_en=cut_en)

        # drive cylindrical extensions that keep the worm in place
        holders = self.simmetric_cylinders( rad=self.cli.worm_extension_diam/2+self.tol,
                                           h=self.disk_h+self.tol,
                                           gap=self.drive_h
        )

        # drive extension
        if self.isCut:
            drive_ext = self.simmetric_cylinders( rad=self.hex_hole/2+1+self.tol,
                                            h=self.cli.wall_thickness + self.disk_h+self.tol,
                                            gap=self.drive_h
            )
        else:
            drive_ext = None
        
        # hex key hole
        if not self.isCut:
            hex_cut = Pencil(
                args = ['-i', self.cli.implementation,
                        '-s', f'{self.hex_hole}',
                        '-d','0',
                        '-fh','0'
                        ]
            ).gen_full()
            hex_cut = hex_cut.rotate_y(90)
        else:
            hex_cut = None
        
        # align drive with gear
        drive = worm_drive + holders + drive_ext - hex_cut
        drive = drive.rotate_x(90)#.mv(self.dist,0,0)

        if self.cli.mirror_enable:
            drive = drive.mirror()
        
        return drive

def main(args=None):
    """ Generate a Worm """
    return main_maker(module_name=__name__,
                class_name='WormDrive',
                args=args)

def test_worm_drive(self,apis=[Implementation.SOLID2]):
    """ Test worm drive """
    tests = {'default':[],
             'cut'    :['-C']}
    test_loop(module=__name__,apis=apis, tests=tests)

def test_worm_drive_mock(self):
    """ Test worm drive """
    test_loop(module=__name__,apis=[Implementation.MOCK])

if __name__ == '__main__':
    main(args=sys.argv[1:]+['-i',Implementation.SOLID2])
