#!/usr/bin/env python3

"""
    Pylele Spines
"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
from api.pylele_api import Shape
from pylele2.pylele_base import LeleBase, test_loop, main_maker, FIT_TOL

class LeleSpines(LeleBase):
    """ Pylele Spines Generator class """

    def gen(self) -> Shape:
        """ Generate Spines """

        cutAdj = (FIT_TOL + self.api.getJoinCutTol()) if self.isCut else 0
        spX = self.cfg.spineX
        spLen = self.cfg.spineLen+ 2*cutAdj
        spHt = self.cfg.SPINE_HT + 2*cutAdj
        spWth = self.cfg.SPINE_WTH + 2*cutAdj
        fspTck = self.cfg.FRETBD_SPINE_TCK  + 2*self.api.getJoinCutTol()

        shape = None
        for y_spine in self.cfg.spineY:
            spine = self.api.genBox(spLen, spWth, spHt)
            spine <<= (spX + spLen/2, y_spine, -fspTck - spHt/2)
            
            shape = spine + shape
        
        return shape

def main(args = None):
    """ Generate Spines """
    return main_maker(module_name=__name__,
                    class_name='LeleSpines',
                    args=args)

def test_spines(self):
    """ Test Spines """
    test_loop(module=__name__)
    
def test_spines_mock(self):
    """ Test Spines """
    test_loop(module=__name__, apis=['mock'])

if __name__ == '__main__':
    main()
