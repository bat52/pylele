#!/usr/bin/env python3

"""
    Pylele Top
"""

import os
from pylele_api import Shape
from pylele_base import LeleBase
from pylele_config import FIT_TOL, Fidelity

class LeleTop(LeleBase):
    """ Pylele Top Generator class """

    def gen(self) -> Shape:
        """ Generate Top """

        if self.isCut:
            origFidel = self.cfg.fidelity
            self.api.setFidelity(Fidelity.LOW)

        fitTol = FIT_TOL
        joinTol = self.cfg.joinCutTol
        cutAdj = (fitTol + joinTol) if self.isCut else 0
        topRat = self.cfg.TOP_RATIO
        midTck = self.cfg.extMidTopTck + cutAdj
        bOrig = self.cfg.bodyOrig
        bPath = self.cfg.bodyCutPath if self.isCut else self.cfg.bodyPath
        top = self.api.genLineSplineRevolveX(bOrig, bPath, 180).scale(1, 1, topRat)
        if midTck > 0:
            top = top.mv(0, 0, midTck)
            midR = self.api.genLineSplineExtrusionZ(
                bOrig, bPath, midTck if self.isCut else midTck)
            midL = midR.mirrorXZ()
            top = top.join(midL).join(midR)

        if self.isCut:
            self.api.setFidelity(origFidel)

        self.shape = top
        return top

def top_main(args=None):
    """ Generate Top """
    solid = LeleTop(args=args)
    solid.export_args() # from cli
    solid.export_configuration()
    solid.exportSTL()
    return solid

def test_top():
    """ Test Top """

    component = 'top'
    tests = {
        'cut'     : ['-C'],
        'cadquery': ['-i','cadquery'],
        'blender' : ['-i','blender']
    }

    for test,args in tests.items():
        print(f'# Test {component} {test}')
        outdir = os.path.join('./test',component,test)
        args += ['-o', outdir]
        top_main(args=args)


if __name__ == '__main__':
    top_main()
