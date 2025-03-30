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

from b13d.api.solid import test_loop, main_maker, Implementation
from b13d.api.core import Shape
from b13d.parts.screw_holder import ScrewHolder, screw_holder_parser
from pylele.parts.worm_gear import WormGear

class WormGearHolder(WormGear):
    """ Generate Worm Gear Holder"""

    def gen_parser(self, parser=None):
        parser = WormGear.gen_parser(self,parser=parser)
        parser.add_argument("-g", "--gears_enable", help="Enable Generation of gears", action="store_true")
        parser.add_argument("-mirror", "--mirror_enable", help="Mirror solid", action="store_true")
        parser = screw_holder_parser(parser=parser)
        return parser

    def configure(self):
        WormGear.configure(self)

        self.wall_thickness = 1.4
        self.holder_thickness = self.cli.worm_diam + 2*self.wall_thickness + 2*self.cut_tolerance
        self.holder_width = 2*(self.gear_diam/2 + self.gear_teeth + self.wall_thickness)

    def gen_screw_holder(self, cutter=False):
        """ Generate a screw holder """
        # sholder = self.api.cylinder_z(rad=self.cli.head_diameter/2+self.wall_thickness,
        #                    l=self.holder_thickness)

        args=[
                '-i', self.cli.implementation,
                '-sd', str(self.cli.screw_diameter),
                '-sh', str(self.cli.screw_heigth),
                '-hd', str(self.cli.head_diameter + self.cut_tolerance),
                '-hh', str(self.cli.head_heigth),
                '-shh', str(self.holder_thickness), # str(self.cli.screw_holder_heigth),
                '-shw', str(self.cli.screw_holder_wall),   
            ]
        if cutter:
            args += ['-co']

        screw = ScrewHolder(
            args=args
        ).gen_full()

        return screw.mv(0,0,-self.holder_thickness/2)
    
    def gen_screw_holders(self, cutter=False):
        holder_rad = self.cli.screw_diameter/2+self.cli.screw_holder_wall
        screw_holder_l = self.gen_screw_holder(cutter=cutter)
        screw_holder_r = screw_holder_l.dup()
        screw_holder_l.mv(-(self.holder_x/2+self.wall_thickness),
                                        self.holder_width/2 - holder_rad,
                                        0)

        screw_holder_r.rotate_z(180).mv(self.holder_x+self.wall_thickness, 
                                        -self.holder_width/2 + holder_rad, 0)
        return screw_holder_l + screw_holder_r
    
    def gen_gears_cut(self, cut_en = True) -> Shape:
        """ Generate the gears cut """

        tol = self.cut_tolerance if cut_en else 0
        cut_arg = ['-C'] if cut_en else []

        gear_cut = self.api.cylinder_z(
            self.holder_thickness - 2 * (self.wall_thickness + tol),
            rad = self.gear_out_rad + tol
            ).mv(0,0,-self.wall_thickness)

        # prepare common worm gear arguments
        worm_gear_args = [
            '-i', self.cli.implementation,
            '-d',
            ]
        if self.cli.minkowski_en:
            worm_gear_args += ['-me']
        if self.cli.carved_gear:
            worm_gear_args += ['-cg']

        # carve tuner hole
        gears_cut = WormGear( args =
            worm_gear_args + cut_arg
        ).gen_full()
    
        self.worm_gear_args = worm_gear_args

        return gear_cut + gears_cut

    def gen_holder_solid(self) -> Shape:
        
        ## gear
        gear = self.api.cylinder_z(
            self.holder_thickness,
            rad = self.holder_width/2
            )

        ## drive
        self.holder_x = self.cli.worm_diam + 2*self.worm_drive_teeth + self.gear_diam/2 + self.wall_thickness
        drive = self.api.box(
            self.holder_x,
            self.holder_width,
            self.holder_thickness,
            )

        # align drive with gear
        drive = drive.mv(self.holder_x/2,0,0)

        # assemble holder
        holder = drive + gear

        # add screw holders
        holder += self.gen_screw_holders()

        if self.cli.implementation.has_hull():
            holder = holder.hull()

        return holder
    
    def gen_holder_gears_cut(self, extrude_en = True, cut_en = True) -> Shape:
        holder = self.gen_holder_solid()

        # remove gear cuts
        gears_cut = self.gen_gears_cut(cut_en = cut_en)
        holder -= gears_cut
        
        # extrude the cut toward the bottom
        extrude_steps = 10 if extrude_en else 0
        for i in range(extrude_steps):
            holder -= gears_cut.mv(0,0,-i*self.wall_thickness/extrude_steps)
        
        return holder
    
    def gen_holder(self) -> Shape:
        holder = self.gen_holder_gears_cut(extrude_en=True)

        # remove screw holders cuts
        holder -= self.gen_screw_holders(cutter=True)

        if self.cli.gears_enable:
            holder += WormGear( args =
                self.worm_gear_args
            ).gen_full()

        if self.cli.mirror_enable:
            holder = holder.mirror()

        return holder
    
    def gen(self) -> Shape:
        return self.gen_holder()

def main(args=None):
    """ Generate the Worm Gear Holder """
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
    # main(args=sys.argv[1:]+['-i',Implementation.SOLID2])
    main()

