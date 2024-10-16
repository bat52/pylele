#!/usr/bin/env python3

"""
    Pylele Bottom Assembly
"""

import os

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

from api.pylele_api import Shape
from pylele2.pylele_base import LeleBase, test_loop, main_maker, LeleBodyType, TunerType
from pylele2.pylele_neck_joint import LeleNeckJoint
from pylele2.pylele_texts import LeleTexts, pylele_texts_parser
from pylele2.pylele_tail import LeleTail

from pylele2.pylele_body import LeleBody
from pylele2.pylele_spines import LeleSpines
from pylele2.pylele_fretboard_spines import LeleFretboardSpines
from pylele2.pylele_chamber import LeleChamber, pylele_chamber_parser
from pylele2.pylele_tuners import LeleTuners
from pylele2.pylele_fretboard_assembly import pylele_fretboard_assembly_parser
from pylele2.pylele_worm import pylele_worm_parser
from pylele2.pylele_config import CONFIGURATIONS

class LeleBottomAssembly(LeleBase):
    """ Pylele Body Bottom Assembly Generator class """
       
    def gen(self) -> Shape:
        """ Generate Body Bottom Assembly """
       
        ## Body
        body = LeleBody(cli=self.cli)

        ## Text
        if self.cli.text_en:
            body -= LeleTexts(cli=self.cli, isCut=True)

        ## Chamber
        if not self.cli.body_type in [LeleBodyType.FLAT, LeleBodyType.HOLLOW]:
            body -= LeleChamber(cli=self.cli, isCut=True)

        ## Spines
        if self.cli.num_strings > 1:
            body -= LeleSpines(cli=self.cli, isCut=True).mv(0, 0, self.api.getJoinCutTol())

        ## Neck Joint
        if self.cli.separate_neck:
            body -= LeleNeckJoint(cli=self.cli, isCut=True)\
                .mv(-self.api.getJoinCutTol(), 0, self.api.getJoinCutTol())

        ## Fretboard Spines
        if (self.cli.separate_fretboard or
            self.cli.separate_neck or
            self.cli.separate_top) and self.cli.num_spines > 0:
            body -= LeleFretboardSpines(cli=self.cli, isCut=True).mv(0, 0, -self.api.getJoinCutTol())
            
        ## Tuners
        if not self.cli.separate_end:
            body -= LeleTuners(cli=self.cli, isCut=True)
           
        ## Tail
        if TunerType[self.cli.tuner_type].value.is_worm():
            if self.cli.separate_end:
                body -= LeleTail(cli=self.cli, isCut=True)
            elif self.cli.body_type in [LeleBodyType.HOLLOW]:
                # join tail to body if flat hollow and not separate end
                body += LeleTail(cli=self.cli)

        return body.gen_full()
    
    def gen_parser(self,parser=None):
        """
        pylele Command Line Interface
        """
        parser=pylele_fretboard_assembly_parser(parser=parser)
        parser=pylele_chamber_parser(parser=parser)
        parser=pylele_texts_parser(parser=parser)
        parser=pylele_worm_parser(parser=parser)
        return super().gen_parser( parser=parser )
    
def main(args=None):
    """ Generate Body Bottom Assembly """
    return main_maker(
        module_name='pylele2.pylele_bottom_assembly',
        # module_name=__name__,
                      class_name='LeleBottomAssembly',
                      args=args)


def test_bottom_assembly(self,apis=None):
    """ Test Bottom Assembly """

    tests = {
        'default'            : [],
        'separate_top'       : ['-T'],
        'separate_neck'      : ['-N'],
        'separate_fretboard' : ['-F'],
        'text'               : ['-txt'],
    }

    test_body = {}
    for body in list(LeleBodyType):
        test_body[body] = ['-bt', body ]

    test_loop(module=__name__,
              apis=apis,
              tests=tests|test_body
              )

def test_bottom_assembly_mock(self):
    """ Test Bottom Assembly Mock """
    test_bottom_assembly(self,apis=['mock'])

if __name__ == '__main__':
    main()
