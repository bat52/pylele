#!/usr/bin/env python3

"""
    Pylele Bridge Assembly
"""

import argparse
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

from b13d.api.core import Shape
from b13d.api.solid import main_maker, test_loop, StringEnum
from pylele.pylele2.base import LeleBase
from pylele.pylele2.bridge import pylele_bridge_parser, LeleBridge
from pylele.parts.tunable_bridge import TunableBridge


class BridgeType(StringEnum):
    """Bridge Type"""
    DEFAULT = "default"
    TUNABLE = "tunable"

def pylele_bridge_assembly_parser(parser=None):
    """
    Pylele Bridge Assembly Parser
    """
    if parser is None:
        parser = argparse.ArgumentParser(description="Pylele Bridge Assembly Configuration")

    parser = pylele_bridge_parser(parser=parser)
    parser.add_argument("-brt", "--bridge_type", help="Type of bridge",
                    type=str.lower, choices=list(BridgeType), default=BridgeType.DEFAULT)
    parser.add_argument("-tba", "--tunable_bridge_all", 
                    help="generate all tunable bridge for debug", action="store_true")
    return parser

class LeleBridgeAssembly(LeleBase):
    """Pylele Bridge Assembly Generator class"""

    def gen(self) -> Shape:
        """Generate Bridge"""
        if self.cli.bridge_type == BridgeType.DEFAULT:
            return LeleBridge(cli=self.cli).gen_full()
        if self.cli.bridge_type == BridgeType.TUNABLE:
            all_arg=['--all'] if self.cli.tunable_bridge_all else []

            return TunableBridge(args=['-i', self.cli.implementation,
                                       '-x', f'{self.cfg.brdgLen}',
                                       '-y', f'{self.cfg.brdgWth+self.cfg.brdgStrGap}',
                                       '-z', f'{self.cfg.brdgHt}',
                                       '--nstrings', f'{self.cli.num_strings}',
                                       '--string_spacing', f'{self.cfg.brdgStrGap}',
                                       ] + all_arg
                                 ).gen_full().mv(self.cli.scale_length,0,self.cfg.brdgZ + 2)

        assert False, f"Unsupported Bridge Type: {self.cli.bridge_type}"

    def gen_parser(self, parser=None):
        """generate bridge parser"""
        parser = pylele_bridge_assembly_parser(parser=parser)
        return super().gen_parser(parser=parser)

def main(args=None):
    """Generate Bridge Assembly"""
    return main_maker(module_name=__name__, class_name="LeleBridgeAssembly", args=args)


def test_bridge_assembly(self, apis=None):
    """Test Bridge Assembly"""
    tests = {
        "default" : [],
        "tunable" : ["-brt", "tunable"]
    }
    test_loop(module=__name__, tests=tests, apis=apis)


def test_bridge_assembly_mock(self):
    """Test Bridge Assembly Mock"""
    test_bridge_assembly(self, apis=["mock"])

if __name__ == "__main__":
    main()
