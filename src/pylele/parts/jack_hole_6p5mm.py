#!/usr/bin/env python3

"""
    6.5mm jack hole
"""


import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from b13d.api.solid import Solid, test_loop, main_maker, Implementation
from b13d.api.core import Shape

class JackHole6p5(Solid):
    """ Generate a 6.5mm jack hole"""

    def gen(self) -> Shape:
        """ generate 6,5mm jack hole"""
        tol = self.api.tolerance()

        # screw cylinder
        screw_cylinder_d = 8.6
        screw_cylinder_h = 6
        screw_cylinder = self.api.cylinder(l=screw_cylinder_h,
                                rad=screw_cylinder_d/2)
        screw_cylinder <<= (0, 0, -screw_cylinder_h/2)

        # hold cylinder
        hold_cylinder_d = 19
        hold_cylinder_h = 5
        hold_cylinder = self.api.cylinder(l=hold_cylinder_h,
                                rad=hold_cylinder_d/2)
        hold_cylinder <<= (0, 0, hold_cylinder_h/2)

        # contact box
        box_h = 23
        box_w = 3.5
        box_gap = 2
        box = self.api.box(10, box_w, box_h)
        box <<= (0, hold_cylinder_d/2 + box_w/2, box_h/2 + box_gap)
        
        # cut cylinder  
        cut_cylinder_d = hold_cylinder_d + 2*box_w
        cut_cylinder_h = box_h + 1
        cut_cylinder = self.api.cylinder(l=cut_cylinder_h,
                                rad=cut_cylinder_d/2)
        cut_cylinder <<= (0, 0, cut_cylinder_h/2+box_gap)

        return screw_cylinder + hold_cylinder + box + cut_cylinder
        
def main(args=None):
    """ Generate Jack Hole """
    return main_maker(module_name=__name__,
                class_name='JackHole6p5',
                args=args)

def test_jack_hole_6p5mm(self,apis=None):
    """ Test Jack Hole 6.5mm """
    tests={'default':[]}
    test_loop(module=__name__,tests=tests,apis=apis)

def test_jack_hole_6p5mm_mock(self):
    """ Test Jack Hole 6.5mm """
    test_jack_hole_6p5mm(self, apis=[Implementation.MOCK])

if __name__ == '__main__':
    main()
