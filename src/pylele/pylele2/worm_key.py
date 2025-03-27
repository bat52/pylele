#!/usr/bin/env python3

"""
    Pylele Worm Key
"""

import argparse

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

from pylele.config_common import TunerType, WormConfig
from b13d.api.constants import FIT_TOL
from b13d.api.solid import main_maker, test_loop
from b13d.api.core import Shape, Implementation
from pylele.pylele2.base import LeleBase, pylele_base_parser
from b13d.parts.rounded_box import RoundedBox

def pylele_worm_key_parser(parser=None):
    """
    Pylele Worm Key Parser
    """
    if parser is None:
        parser = argparse.ArgumentParser(description="Pylele Worm Key parser")

    parser.add_argument("-wkch", "--worm_key_carved_hex",
                        help="Carved hex hole instead of 3d print hex shaft in worm key", 
                        action="store_true")

    return parser

class LeleWormKey(LeleBase):
    """Pylele Worm Key Generator class"""

    def gen_parser(self, parser=None):
        parser = super().gen_parser(parser=parser)
        return pylele_worm_key_parser(parser=parser)

    def gen(self) -> Shape:
        """Generate Worm Key"""
        isBlender = self.cli.implementation == Implementation.BLENDER
        joinTol = self.api.tolerance()
        tailX = self.cfg.tailX
        txyzs = self.cfg.tnrXYZs
        assert TunerType[self.cli.tuner_type].value.is_worm()
        wcfg: WormConfig = TunerType[self.cli.tuner_type].value
        cutAdj = (FIT_TOL + joinTol) if self.isCut else 0
        btnHt = wcfg.buttonHt + 2 * cutAdj
        btnWth = wcfg.buttonWth + 2 * cutAdj
        btnTck = wcfg.buttonTck + 2 * cutAdj
        kbHt = wcfg.buttonKeybaseHt + 2 * cutAdj
        kbRad = wcfg.buttonKeybaseRad + cutAdj
        kyRad = wcfg.buttonKeyRad + cutAdj
        kyLen = wcfg.buttonKeyLen + 2 * cutAdj
        gapAdj = wcfg.gapAdj

        if self.cli.worm_key_carved_hex:
            kyRad += 2 * cutAdj
            kyLen += btnHt

        key = self.api.regpoly_extrusion_x(kyLen, kyRad, 6)
        
        if self.cli.worm_key_carved_hex:
            key <<= (-btnHt, 0, 0)
        else:
            key <<= (joinTol -kyLen/2 -kbHt -btnHt, 0, 0)

        base = self.api.regpoly_extrusion_x(kbHt, kbRad, 36) if isBlender else self.api.cylinder_x(kbHt, kbRad)
        base = base.mv(-kbHt/2 -btnHt, 0, 0)

        if self.isCut:
            btn = self.api.box(100, btnTck, btnWth)\
                .mv(50 -btnHt, 0, 0)
            btn += self.api.cylinder_x(100 if self.isCut else btnHt, btnWth/2)\
                .scale(1, .5, 1)\
                .mv(50 -btnHt, btnTck/2, 0)
        else:
            box = RoundedBox(args=['-x', f'{btnHt}',
                                   '-y', f'{btnTck}',
                                   '-z', f'{btnWth}',
                                   '-i', self.cli.implementation]
                                   )\
                .mv(-btnHt/2, 0, 0)
            btn = box.gen_full()

        btn += base

        if self.cli.worm_key_carved_hex:
            btn -= key
            # screw hole
            btn -= self.api.cylinder_x(100, 1)
        else:
            btn += key

        maxTnrY = max([y for _, y, _ in txyzs])
        btn = btn.mv(tailX - joinTol, maxTnrY + btnTck + gapAdj/2, -1 -btnWth/2)
        return btn


def main(args=None):
    """Generate Worm Key"""
    return main_maker(module_name=__name__, class_name="LeleWormKey", args=args)


def test_worm_key(self, apis=None):
    """Test Worm Key"""
    tests = {
        "cut": ["-t", TunerType.WORM.name, "-C"],
        "big_worm": ["-t", TunerType.BIGWORM.name],
        "carved" : ["-t", TunerType.WORM.name, "-wkch"],
    }
    test_loop(module=__name__, tests=tests, apis=apis)


def test_worm_key_mock(self):
    """Test Worm Key"""
    test_worm_key(self, apis=[Implementation.MOCK])

if __name__ == "__main__":
    main(sys.argv[1:]+["-t",TunerType.WORM.name])

