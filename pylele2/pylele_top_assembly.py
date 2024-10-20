#!/usr/bin/env python3

"""
    Pylele Top Assembly
"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
from api.pylele_api import Shape
from api.pylele_solid import Implementation
from pylele2.pylele_base import LeleBase, test_loop,main_maker, FILLET_RAD, LeleScaleEnum, LeleBodyType, TunerType
from pylele2.pylele_bridge import LeleBridge, pylele_bridge_parser
from pylele2.pylele_guide import LeleGuide
from pylele2.pylele_brace import LeleBrace
from pylele2.pylele_chamber import LeleChamber, pylele_chamber_parser
from pylele2.pylele_fretboard_joint import LeleFretboardJoint
from pylele2.pylele_tuners import LeleTuners
from pylele2.pylele_soundhole import LeleSoundhole
from pylele2.pylele_rim import LeleRim
from pylele2.pylele_worm import WormConfig, pylele_worm_parser
from pylele2.pylele_top import LeleTop
from pylele2.pylele_fretboard_assembly import LeleFretboardAssembly, pylele_fretboard_assembly_parser
from pylele2.pylele_strings import LeleStrings
from pylele2.pylele_worm_key import LeleWormKey

class LeleTopAssembly(LeleBase):
    """ Pylele Body Top Assembly Generator class """

    def gen(self) -> Shape:
        """ Generate Body Top Assembly """

        # top
        top = LeleTop(cli=self.cli)
        
        # tuners
        tuners = LeleTuners(cli=self.cli, isCut=True)
        top -= tuners

        if tuners.is_worm():
            # fillet worm tuners slit
            top = tuners.worm_fillet(top)

            if self.cli.worm_has_key:
                self.add_part(LeleWormKey(cli=self.cli))

        elif tuners.is_peg():
            # gen guide if using tuning pegs
            guide = LeleGuide(cli=self.cli)
            if self.cli.separate_guide:
                top -= LeleGuide(cli=self.cli, isCut=True)
                self.add_part(guide)
            else:
                top +=guide

        if self.cli.separate_top:
            top += LeleRim(cli=self.cli, isCut=False)
        if not self.cli.body_type in [LeleBodyType.FLAT]:
            top -= LeleChamber(cli=self.cli,isCut=True)
        if not self.cli.body_type in [LeleBodyType.FLAT,LeleBodyType.TRAVEL]:
            # soundhole
            sh  = LeleSoundhole(cli=self.cli, isCut=True)
            top -= sh
            top = sh.fillet(top)

            # brace
            top += LeleBrace(cli=self.cli)

        if self.cli.separate_fretboard or self.cli.separate_neck:
            top -= LeleFretboardJoint(cli=self.cli, isCut=True)\
                .mv(-self.api.getJoinCutTol(), 0, -self.api.getJoinCutTol())

        # gen bridge
        brdg = LeleBridge(cli=self.cli)
        if self.cli.separate_bridge:
            top -= LeleBridge(cli=self.cli, isCut=True)
            self.add_part(brdg)
        else:
            top += brdg

        return top.gen_full()
    
    def gen_parser(self,parser=None):
        """
        pylele Command Line Interface
        """
        parser=pylele_fretboard_assembly_parser(parser=parser)
        parser=pylele_chamber_parser(parser=parser)
        parser=pylele_worm_parser(parser=parser)
        parser=pylele_bridge_parser(parser=parser)
        return super().gen_parser( parser=parser )
    
def main(args=None):
    """ Generate Body Top Assembly """
    return main_maker(module_name=__name__,
                    class_name='LeleTopAssembly',
                    args=args)

def test_top_assembly(self, apis = None):
    """ Test Top Assembly """    

    test_scale_len = {}
    for sl in list(LeleScaleEnum):
        test_scale_len[sl.name] = ['-s',sl.name]

    tests = {
            'default'            : [],
            'separate_bridge'    : ['-B'],
            'separate_guide'     : ['-G'],
            'separate_top'       : ['-T'],
            'separate_neck'      : ['-N'],
            'separate_fretboard' : ['-F'],
            'gotoh_tuners'       : ['-t','gotoh'],
            'worm_tuners'        : ['-t','worm'],
            'big_worm_tuners'    : ['-t','bigWorm'],
            'bridge_piezo'       : ['-bpiezo','-B'],
        }

    tests_all = tests | test_scale_len
    test_loop(module=__name__,tests=tests_all,apis=apis)

def test_top_assembly_mock(self):
    """ Test Top Assembly """    
    test_top_assembly(self, apis=['mock'])

if __name__ == '__main__':
    main()
