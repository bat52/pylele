#!/usr/bin/env python3

"""
    6.5mm jack
"""


import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from b13d.api.solid import Solid, test_loop, main_maker, Implementation
from b13d.api.core import Shape
from b13d.parts.torus import Torus

class Jack6p5(Solid):
    """ Generate a 6.5mm jack """

    def gen(self) -> Shape:
        """ generate 6,5mm jack """
        # tol = self.api.tolerance()

        # cylinder
        cyl_h = 25
        rad = 6.5/2
        cylinder = self.api.cylinder(l=cyl_h,
                                     rad=rad)
        
        # cone
        cone = self.api.cone(h=5,
                                    r1=rad,
                                    r2=0)
        cone <<= (0, 0, cyl_h/2)

        # torus
        r1 = 1.5
        r2 = rad + r1/2
        torus = Torus(args=[
            '-r1', f'{r1}',
            '-r2', f'{r2}'
            ]
            ).gen_full().rotate_x(90)
        torus <<= (0, 0, cyl_h/2 - r1)

        return cylinder + cone - torus
        
def main(args=None):
    """ Generate the Jack """
    return main_maker(module_name=__name__,
                class_name='Jack6p5',
                args=args)

def test_jack_6p5mm(self,apis=None):
    """ Test Jack 6.5mm """
    tests={'default':[]}
    test_loop(module=__name__,tests=tests,apis=apis)

def test_jack_6p5mm_mock(self):
    """ Test Jack 6.5mm """
    test_jack_6p5mm(self, apis=[Implementation.MOCK])

if __name__ == '__main__':
    main()
