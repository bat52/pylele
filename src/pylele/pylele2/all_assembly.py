#!/usr/bin/env python3

"""
    Pylele All Assembly
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

from b13d.api.core import Shape
from b13d.api.solid import main_maker, test_loop
from pylele.pylele2.base import LeleBase
from pylele.pylele2.top_assembly import LeleTopAssembly
from pylele.pylele2.config import CONFIGURATIONS
from pylele.pylele2.bottom_assembly import LeleBottomAssembly, pylele_bottom_assembly_parser
from pylele.pylele2.bridge_assembly import pylele_bridge_assembly_parser
from pylele.pylele2.strings import LeleStrings
from pylele.pylele2.tuners import LeleTuners

class LeleAllAssembly(LeleBase):
    """Pylele All Assembly Generator class"""

    def gen(self) -> Shape:
        """Generate Body Bottom Assembly"""

        jcTol = self.api.tolerance()

        ## Body
        body = LeleBottomAssembly(cli=self.cli)
        body.gen_full()
        if body.has_parts():
            self.add_parts(body.parts)

        ## Top
        top = LeleTopAssembly(cli=self.cli)
        top.gen_full()
        if self.cli.separate_top and not self.cli.all:
            self.add_part(top)
        else:
            if self.cli.all:
                top <<= (0, 0, self.cli.all_distance)
            else:
                top <<= (0, 0, -jcTol)
            body += top
        if top.has_parts():
            self.add_parts(top.parts)

        ## Strings
        if self.cli.show_strings:
            body += LeleStrings(cli=self.cli)

        ## Tuners
        if self.cli.show_tuners:
            body += LeleTuners(cli=self.cli)

        return body.gen_full()

    def gen_parser(self,parser=None):
        """
        pylele Command Line Interface
        """
        parser = pylele_bottom_assembly_parser(parser=parser)
        parser = pylele_bridge_assembly_parser(parser=parser)

        parser.add_argument(
            "-str",
            "--show_strings",
            help="Show strings in all assembly, just to look nice",
            action="store_true",
        )

        parser.add_argument(
            "-tnr",
            "--show_tuners",
            help="Show tuners in all assembly, just to look nice",
            action="store_true",
        )

        return super().gen_parser(parser=parser)


def main(args=None):
    """Generate Body Bottom Assembly"""
    return main_maker(
        module_name="pylele.pylele2.all_assembly",
        class_name="LeleAllAssembly",
        args=args,
    )


def test_all_assembly(self, apis=None):
    """Test All Assembly"""

    tests = {
        "separate_bridge": ["-B"],
        "separate_top": ["-T"],
        "separate_neck": ["-N"],
        "separate_fretboard": ["-F"],
        "separate_all": ["-F", "-N", "-T", "-B", "-NU", "-FR", "-D", "-G", "-HT"],
        "gotoh_tuners": ["-t", "gotoh"],
    }

    # reference volumes
    refv = {
        'default'        :  '529039',
        'worm'           :  '579205',
        'flat'           : '1078970',
        'hollow'         :  '919553',
        'travel'         :  '837153',
        'travelele'      :  '403970'
    }

    test_config = {}
    for key,config in CONFIGURATIONS.items():
        test_config[key] = config + ['-refv',refv[key]]
        
    test_loop(
        module=__name__,
        apis=apis,
        tests=tests | test_config,
    )


def test_all_assembly_mock(self):
    """Test Bottom Assembly Mock"""
    test_all_assembly(self, apis=["mock"])


if __name__ == "__main__":
    main()
