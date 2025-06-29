#!/usr/bin/env python3

"""
    Pylele Bridge
"""
from math import floor
import argparse
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

from b13d.api.solid import Solid
from b13d.api.core import Shape
from b13d.api.constants import FIT_TOL
from b13d.api.solid import main_maker, test_loop

def bridge_parser(parser=None):
    """
    Bridge Parser
    """
    if parser is None:
        parser = argparse.ArgumentParser(description="Pylele Bridge Configuration")

    parser.add_argument(
        "-bw",
        "--bridge_width",
        help="Override Bridge Width [mm]",
        type=float,
        default=50.0,
    )
    parser.add_argument(
        "-bl",
        "--bridge_length",
        help="Bridge Length [mm]",
        type=float,
        default=20.0,
    )
    parser.add_argument(
        "-bh",
        "--bridge_height",
        help="Bridge Height [mm]",
        type=float,
        default=10.0,
    )
    parser.add_argument(
        "-bsr",
        "--bridge_string_radius",
        help="Bridge String Radius [mm]",
        type=float,
        default=1,
    )
    parser.add_argument(
        "-bpiezo",
        "--bridge_piezo",
        help="Add space for a piezo microphone under the bridge",
        action="store_true",
    )
    parser.add_argument(
        "-bph",
        "--bridge_piezo_heigth",
        help="Bridge Piezo Heigth [mm]",
        type=float,
        default=1.5,
    )
    parser.add_argument(
        "-bpw",
        "--bridge_piezo_width",
        help="Bridge Piezo Width [mm]",
        type=float,
        default=2,
    )
    parser.add_argument("-ns", "--nstrings", help="number of strings", type=int, default=4)
    parser.add_argument("-ss", "--string_spacing", help="strings spacing [mm]", type=float, default=10)
    return parser

class Bridge(Solid):
    """Bridge Generator class"""

    def gen_strings_cut(self) -> Shape:
        """Generate strings cut"""
        brdgWth = self.cli.bridge_width
        brdgHt = self.cli.bridge_height

        string_template = self.api.cylinder_x(
            brdgWth, self.cli.bridge_string_radius
        ).mv(0, 0, brdgHt + self.cli.bridge_string_radius)

        if self.cli.nstrings % 2 == 0:
            starty = -(self.cli.nstrings/2 - 0.5)
        else:
            starty = -floor(self.cli.nstrings/2)

        strings_cut = None
        for idx in range(self.cli.nstrings):
            shifty = (starty+idx)*self.cli.string_spacing
            string = string_template.dup().mv(0,shifty,0)
            strings_cut = string + strings_cut

        return strings_cut

    def gen_bridge_core(self) -> Shape:
        """Generate Bridge"""

        cut_tol = FIT_TOL if self.isCut else 0
        strRad = self.cli.bridge_string_radius
        brdgWth = self.cli.bridge_width + cut_tol
        brdgLen = self.cli.bridge_length + cut_tol
        brdgHt = self.cli.bridge_height + cut_tol

        brdg = self.api.box(brdgLen, brdgWth, brdgHt).mv(
            0, 0, brdgHt / 2
        )

        if not self.isCut:
            cutRad = brdgLen / 2 - strRad
            cutHt = brdgHt - 2
            cutScaleZ = cutHt / cutRad

            frontCut = (
                self.api.cylinder_y(2 * brdgWth, cutRad)
                .scale(1, 1, cutScaleZ)
                .mv( -cutRad - strRad, 0, brdgHt)
            )

            backCut = (
                self.api.cylinder_y(2 * brdgWth, cutRad)
                .scale(1, 1, cutScaleZ)
                .mv( cutRad + strRad, 0, brdgHt)
            )

            brdg += self.api.cylinder_y(brdgWth, strRad).mv(0, 0, brdgHt)
            brdg = brdg - frontCut - backCut

        return brdg
    
    def gen_piezo_mic(self) -> Shape:
        """Generate Piezo Microphone"""
        cut_tol = FIT_TOL if self.isCut else 0
        brdgWth = self.cli.bridge_width + cut_tol

        mic_cut = self.api.box(
            self.cli.bridge_piezo_width, brdgWth, self.cli.bridge_piezo_heigth
        )
        mic_cut = mic_cut.mv(0, 0, self.cli.bridge_piezo_heigth / 2)
        return mic_cut
    
    def gen_piezo_wire(self) -> Shape:
        """Generate Piezo Wire"""
        cut_tol = FIT_TOL if self.isCut else 0
        brdgWth = self.cli.bridge_width + cut_tol

        wire_rad = 2
        wire = self.api.cylinder_z(15, wire_rad).mv(
            0, brdgWth / 2 - wire_rad, 0
        )
        return wire

    def gen(self) -> Shape:
        """Generate Bridge"""

        # bridge core
        brdg = self.gen_bridge_core()

        # strings cut
        if not self.isCut:
            brdg -= self.gen_strings_cut()
        
        # piezo stuff
        if self.cli.bridge_piezo:
            if not self.isCut:
                brdg -= self.gen_piezo_mic()
            else:
                brdg -= self.gen_piezo_wire()

        return brdg

    def gen_parser(self, parser=None):
        """generate bridge parser"""
        parser = bridge_parser(parser=parser)
        return super().gen_parser(parser=parser)

def main(args=None):
    """Generate Bridge"""
    return main_maker(module_name=__name__, class_name="Bridge", args=args)


def test_bridge(self, apis=None):
    """Test Bridge"""
    tests = {
        "default" : [],
        "cut": ["-C"],
        "piezo": ["-bpiezo"],
        "cut_piezo": ["-C", "-bpiezo"],
    }
    test_loop(module=__name__, tests=tests, apis=apis)

def test_bridge_mock(self):
    """Test Bridge"""
    test_bridge(self, apis=["mock"])

if __name__ == "__main__":
    main()
