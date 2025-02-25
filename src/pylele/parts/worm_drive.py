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

    def configure(self):
        Solid.configure(self)

        # gear &  worm common parameters
        self.modulus = 3/2
        self.circ_pitch = 4      # The circular pitch, the distance between teeth centers around the pitch circle. Default: 5
        self.worm_diam = 10
        self.worm_starts = 1
        self.teeth = 14          # The number of teeth in the mated worm gear.
        # self.pressure_angle = 25 # 32
        self.pressure_angle = 29

        # inferred parameters
        self.gear_diam = 14.6
        self.worm_drive_teeth = 1.43
        self.gear_teeth = 3
        
        # hex hole
        self.hex_hole = 4.3

        # drive parameters
        self.drive_h = self.worm_diam + self.gear_teeth
        self.drive_teeth_l = 2*0.98

        # drive cylindrical extension
        self.disk_h = (self.gear_diam - self.drive_h + 2)/2

        # distance between worm and gear
        self.dist = worm_dist(circ_pitch=self.circ_pitch,
                    d=self.worm_diam,
                    starts=self.worm_starts,
                    teeth=self.teeth,
                    # [profile_shift],
                    pressure_angle=self.pressure_angle
                    )

        # cut tolerance
        self.cut_tolerance = 0.3
        self.tol = self.cut_tolerance if self.isCut else 0

    def gen_parser(self, parser=None):
        parser = super().gen_parser(parser=parser)
        parser.add_argument("-e", "--enveloping_worm", help="Enveloping Worm", action="store_true")
        return parser

    def gen(self) -> Shape:
        assert self.isCut or (self.cli.implementation in [Implementation.SOLID2, Implementation.MOCK])
        
        # if self.cli.gear_enable:
        #    gear = self.gen_gear()
    
        drive = self.gen_drive()
        return drive

    def gen_drive(self, minkowski_en = False) -> Shape:
        """ Generate Drive """

        ## drive
        if self.isCut:
            drive = self.api.cylinder_z(
                l = self.drive_h+2*self.tol,
                rad=self.worm_diam/2+self.drive_teeth_l/2+self.tol
                )
        else:
            if not self.cli.enveloping_worm:
                bworm = worm(circ_pitch=self.circ_pitch,
                                d=self.worm_diam,
                                starts=self.worm_starts,
                                l=self.drive_h,
                                pressure_angle=self.pressure_angle,
                                mod = self.modulus
                                )
            else:
                bworm = enveloping_worm(
                                circ_pitch=self.circ_pitch,
                                d=self.worm_diam,
                                starts=self.worm_starts,
                                # l=20 , # self.drive_h,
                                pressure_angle=self.pressure_angle,
                                mod = self.modulus,
                                mate_teeth = self.teeth,
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

        # drive cylindrical extension
        disk_low = self.api.cylinder_z(l=self.disk_h+self.tol, rad=self.worm_diam/2+self.tol)
        disk_high = disk_low.dup()
        disk_low  <<= (0,0,-(self.drive_h+self.disk_h)/2)
        disk_high <<= (0,0, (self.drive_h+self.disk_h)/2)
        drive += disk_low + disk_high

        # drive extension
        drive_ext = self.api.cylinder_z(l=self.drive_h+2*self.disk_h+2*20*self.tol + 2*2,
                                        rad=self.hex_hole/2+2+2*self.tol
                                        )
        drive += drive_ext
        
        # hex key hole
        if not self.isCut:
            hex_cut = Pencil(
                args = ['-i', self.cli.implementation,
                        '-s', f'{self.hex_hole}',
                        '-d','0',
                        '-fh','0'
                        ]
            ).gen_full()
            drive -= hex_cut.rotate_y(90)
        
        # align drive with gear
        # drive = drive.rotate_x(90).mv((self.gear_diam+self.worm_diam)/2,0,0)
        drive = drive.rotate_x(90).mv(self.dist,0,0)
        
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
