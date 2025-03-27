#!/usr/bin/env python3

"""
    Tuner Knob
"""

import argparse

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from b13d.api.solid import Solid, test_loop, main_maker, Implementation
from b13d.api.core import Shape

def tuner_knob_hole_gen_parser(self, parser=None):
    if parser is None:
        parser = argparse.ArgumentParser(description='Tuner Knob Hole Parser')
    parser.add_argument("-z", "--knob_height", help="knob height", type=float, default=16)
    parser.add_argument("-rd", "--round_hole_diameter", help="round hole diameter", type=float, default=4.5)
    parser.add_argument("-sd", "--square_hole_diam", help="squared hole size", type=float, default=3.8)
    return parser

class TunerKnobHole(Solid):
    """ Generate Tuner Knob Hole """

    def gen_parser(self, parser=None):
        parser = super().gen_parser(parser=parser)
        parser = tuner_knob_hole_gen_parser(self, parser=parser)
        return parser

    def gen(self) -> Shape:
        """ generate tuner knob """
        tol = self.api.tolerance()
        
        # round hole
        round_hole = self.api.cylinder_z(
            l=self.cli.knob_height + tol,
            rad=self.cli.round_hole_diameter/2
        )
       
        # squared hole
        hole_sides = self.api.cylinder_z(
            l=self.cli.knob_height + tol,
            rad=self.cli.round_hole_diameter/2 + tol
        )
        hole_sides -= self.api.box(
            self.cli.square_hole_diam,
            self.cli.round_hole_diameter + 2*tol,
            self.cli.knob_height + 2*tol,
        )
        # hole_sides = hole_sides.intersection(knob.dup())
        # hole_sides = hole_sides.intersection(round_hole.dup())

        return round_hole - hole_sides
        
def main(args=None):
    """ Generate the Knob Hole """
    return main_maker(module_name=__name__,
                class_name='TunerKnobHole',
                args=args)

def test_tuner_knob_hole(self,apis=None):
    """ Test Tuner Knob Hole"""
    tests={'default':[]}
    test_loop(module=__name__,tests=tests,apis=apis)

def test_tuner_knob_hole_mock(self):
    """ Test Tuner Knob Hole Mock """
    test_tuner_knob_hole(self, apis=[Implementation.MOCK])

if __name__ == '__main__':
    main()
