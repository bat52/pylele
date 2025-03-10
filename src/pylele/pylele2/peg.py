#!/usr/bin/env python3

"""
    Pylele Peg
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

from b13d.api.core import Shape
from b13d.api.constants import FIT_TOL
from b13d.api.solid import main_maker, test_loop
from pylele.config_common import PegConfig, TunerType
from pylele.pylele2.base import LeleBase


class LelePeg(LeleBase):
    """Pylele Peg Generator class"""

    def gen(self) -> Shape:
        """Generate Peg"""
        cutAdj = FIT_TOL if self.isCut else 0
        if TunerType[self.cli.tuner_type].value.is_peg():
            cfg: PegConfig = TunerType[self.cli.tuner_type].value
        elif TunerType[self.cli.tuner_type] == TunerType.TURNAROUND:
            cfg: PegConfig = TunerType[self.cli.tuner_type].value.peg_config
        else:
            assert f"Unsupported Peg for tuner type {self.cli.tuner_type}"
        joinTol = 2 * self.cfg.tolerance
        strRad = self.cfg.STR_RAD + cutAdj
        holeHt = cfg.holeHt
        majRad = cfg.majRad + cutAdj
        minRad = cfg.minRad + cutAdj
        midTck = cfg.midTck
        botLen = cfg.botLen
        btnRad = cfg.btnRad + cutAdj
        topCutTck = cfg.topCutTck if self.isCut else 2  # big value for cutting
        botCutTck = botLen - midTck / 3 if self.isCut else 2

        top = self.api.cylinder_z(topCutTck + joinTol, majRad).mv(0, 0, topCutTck / 2)
        mid = self.api.cylinder_z(midTck + joinTol, minRad).mv(0, 0, -midTck / 2)       

        if self.isCut:
            btnConeTck = botLen - midTck - 2 * cutAdj
            btn = self.api.cone_z(btnConeTck + joinTol, btnRad, majRad).mv(
                0, 0, -midTck - btnConeTck
            )
            bot = self.api.cylinder_z(botCutTck + joinTol, btnRad).mv(
                0, 0, -botLen - botCutTck / 2 + 2 * cutAdj
            )
            botEnd = (
                self.api.sphere(btnRad)
                .scale(1, 1, 0.5 if self.cli.separate_end else 1)
                .mv(0, 0, -botLen - botCutTck)
            )
            bot += botEnd
        else:
            stemHt = holeHt + 4 * strRad
            
            # top stem
            top  += self.api.cylinder_z(stemHt + joinTol, minRad / 2).mv(0, 0, stemHt / 2)
            # top stem hole
            top  -= self.api.cylinder_x(2 * minRad, strRad).mv(0, 0, holeHt)

            bot = self.api.cylinder_z(botCutTck + joinTol, majRad).mv(
                0, 0, -midTck - botCutTck / 2
            )
            bot += self.api.cylinder_z(botLen + joinTol, minRad / 2).mv(
                0, 0, -midTck - botLen / 2
            )

            # handle
            btn = self.api.box(btnRad * 2, btnRad / 2, btnRad).mv(
                0, 0, -midTck - botLen - botCutTck / 2 + btnRad / 2
            )

        return top + mid + btn + bot

def main(args=None):
    """Generate Peg"""
    return main_maker(module_name=__name__, class_name="LelePeg", args=args)

def test_peg(self, apis=None):
    """Test Peg"""

    tests = {
        "cut": ["-C","-refv","30799"],
        "gotoh": ["-t", "gotoh","-refv","2658"],
    }
    test_loop(module=__name__, tests=tests, apis=apis)


def test_peg_mock(self):
    """Test Peg"""
    test_peg(self, apis=["mock"])


if __name__ == "__main__":
    main()
