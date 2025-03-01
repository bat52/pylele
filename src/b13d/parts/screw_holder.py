#!/usr/bin/env python3

"""
    Screw Holder
"""

from argparse import ArgumentParser

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from b13d.api.solid import Solid, test_loop, main_maker
from b13d.api.core import Shape

from b13d.parts.screw import Screw, screw_parser

def screw_holder_parser(parser=None):
    """ Screw Holder Parser """
    
    if parser is None:
        parser = ArgumentParser(description="Screw Configuration")

    parser.add_argument("-shh", "--screw_holder_heigth",
                        help="Screw Holder Heigth [mm]",
                        type=float, default=10)
    parser.add_argument("-shw", "--screw_holder_wall",
                        help="Screw Holder Wall Thickness [mm]",
                        type=float, default=2)
    parser.add_argument("-co", "--cutter_only",
                    help="Cutter Only",
                    action="store_true")
    parser = screw_parser(parser=parser)

    return parser

class ScrewHolder(Screw):
    """ Generate Screw Holder """

    def gen_parser(self, parser=None):
        # parser = super().gen_parser(parser=parser)
        parser = Solid.gen_parser(self,parser=parser)
        parser = screw_holder_parser(parser=parser)
        return parser
    
    def configure(self):
        super().configure()
        self.holder_rad = self.cli.screw_diameter/2+self.cli.screw_holder_wall
        pass

    def gen_holder(self) -> Shape:
        holder = None

        if self.cli.screw_heigth > 0 and self.cli.screw_diameter > 0:
            holder = self.api.cylinder_z(l=self.cli.screw_holder_heigth,
                                        rad=self.holder_rad)
            holder <<= (0,0,self.cli.screw_holder_heigth/2)

            lateral_extension = self.api.box(
                self.holder_rad,
                2*self.holder_rad,
                self.cli.screw_holder_heigth
                ).mv(self.holder_rad/2,0,self.cli.screw_holder_heigth/2)

            head_cut = self.api.cylinder_z(l=self.cli.screw_holder_heigth,
                                        rad=self.cli.head_diameter/2 + self.tol)
            head_cut <<= (0,0,self.cli.screw_holder_heigth/2+self.cli.head_heigth)
            
            screw = self.gen_screw()
            screw <<= (0,0,self.cli.screw_holder_wall)

            return holder + lateral_extension - (screw + head_cut)
            # return lateral_extension
        
        assert False

    def gen_cutter(self) -> Shape:

        head_cut = self.api.cylinder_z(l=self.cli.screw_holder_heigth,
                                    rad=self.cli.head_diameter/2 + self.tol)
        head_cut <<= (0,0,self.cli.screw_holder_heigth/2+self.cli.head_heigth)
        
        screw = self.gen_screw()
        screw <<= (0,0,self.cli.screw_holder_wall)

        return screw + head_cut

    def gen(self) -> Shape:
        if self.cli.screw_heigth > 0 and self.cli.screw_diameter > 0:
            cutter = self.gen_cutter()
            if self.cli.cutter_only:
                return cutter
            holder = self.gen_holder()
            return holder - cutter
        assert False

def main(args=None):
    """ Generate a Screw """
    return main_maker(module_name=__name__,
                class_name='ScrewHolder',
                args=args)

def test_screw_holder(self,apis=None):
    """ Test Screw Holder """
    test_loop(module=__name__,apis=apis)

def test_screw_holder_mock(self):
    """ Test Screw Holder """
    test_screw_holder(self, apis=['mock'])

if __name__ == '__main__':
    main()
