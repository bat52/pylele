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
from pylele.parts.worm_gear import WormGear

class WormGearHolder(WormGear):
    """ Generate Worm Gear Holder"""

    def gen_parser(self, parser=None):
        parser = WormGear.gen_parser(self,parser=parser)
        parser.add_argument("-g", "--gears_enable", help="Enable Generation of gears", action="store_true")    
        return parser

    def configure(self):
        WormGear.configure(self)

        self.wall_thickness = 1.4
        self.holder_thickness = self.worm_diam + 2*self.wall_thickness + 2*self.cut_tolerance
        self.holder_width = 2*(self.gear_diam/2 + self.gear_teeth + self.wall_thickness)

    def gen(self) -> Shape:
        
        ## gear
        gear = self.api.cylinder_z(
            self.holder_thickness,
            rad = self.holder_width/2
            )
        
        gear_cut = self.api.cylinder_z(
            self.holder_thickness,
            rad = self.gear_out_rad + self.cut_tolerance
            ).mv(0,0,-self.wall_thickness)

        ## drive
        holder_x = self.worm_diam + 2*self.worm_drive_teeth + self.gear_diam/2 + self.wall_thickness
        drive = self.api.box(
            holder_x,
            self.holder_width,
            self.holder_thickness,
            )

        # align drive with gear
        drive = drive.mv(holder_x/2,0,0)

        # assemble holder
        holder = drive + gear
        if self.cli.implementation.has_hull():
            holder = holder.hull()
        holder = holder - gear_cut

        # prepare common worm gear arguments
        worm_gear_args = [
            '-i', self.cli.implementation,
            '-d',
            ]
        if self.cli.minkowski_enable:
            worm_gear_args += ['-me']
        if self.cli.carved_gear:
            worm_gear_args += ['-cg']

        # carve tuner hole
        gears_cut = WormGear( args =
            worm_gear_args + ['-C']
        ).gen_full()
        holder -= gears_cut
        
        # extrude the cut toward the bottom
        extrude_steps = 10
        for i in range(extrude_steps):
            holder -= gears_cut.mv(0,0,-i*self.wall_thickness/extrude_steps)

        if self.cli.gears_enable:
            holder += WormGear( args =
                worm_gear_args
            ).gen_full()

        return holder

def main(args=None):
    """ Generate a Tube """
    return main_maker(module_name=__name__,
                class_name='WormGearHolder',
                args=args)

def test_worm_gear_holder(self,apis=[Implementation.SOLID2]):
    """ Test worm gear """
    test_loop(module=__name__,apis=apis)

def test_worm_gear_holder_mock(self):
    """ Test worm gear holder """
    test_loop(module=__name__,apis=[Implementation.MOCK])

if __name__ == '__main__':
    main(args=sys.argv[1:]+['-i',Implementation.SOLID2])
    # main()

