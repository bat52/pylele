#!/usr/bin/env python3

"""
    6.5mm jack female
"""


import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from b13d.api.solid import Solid, test_loop, main_maker, Implementation
from b13d.api.core import Shape
from b13d.api.constants import FIT_TOL
from b13d.parts.pencil import Pencil

class Jack6p5Female(Solid):
    """ Generate a 6.5mm jack """

    def gen(self) -> Shape:
        """ generate 6,5mm jack """
        # tol = self.api.tolerance()

        # cylinder
        cyl_h = 75
        rad = 12.5/2 + FIT_TOL
        cylinder = self.api.cylinder(l=cyl_h,
                                     rad=rad)
        
        if self.isCut:
            # box cut
            box = self.api.box(2*rad, 2*rad, cyl_h-10)
            box <<= (rad, 0, -box.top()+cylinder.top())
            cylinder += box
            # screw holder
            screw_width = 14 + FIT_TOL
            pencil = Pencil(self.api, 
                            args=[
                                '-s' ,f'{screw_width}',
                                '-d', '0',
                                '-fh', '0',
                                '-H', '3',
                            ]
                            ).gen_full()
            pencil = pencil.rotate_y(90).rotate_z(30)
            pencil <<= (0, 0, box.bottom()-pencil.bottom())
            cylinder += pencil            

        cylinder <<= (0, 0, cyl_h/2)
        return cylinder
        
def main(args=None):
    """ Generate the Jack """
    return main_maker(module_name=__name__,
                class_name='Jack6p5Female',
                args=args)

def test_jack_6p5mm_female(self,apis=None):
    """ Test Jack 6.5mm Female """
    tests={'default':[]}
    test_loop(module=__name__,tests=tests,apis=apis)

def test_jack_6p5mm_female_mock(self):
    """ Test Jack 6.5mm Female """
    test_jack_6p5mm_female(self, apis=[Implementation.MOCK])

if __name__ == '__main__':
    main()
