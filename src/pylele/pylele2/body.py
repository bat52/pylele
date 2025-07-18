#!/usr/bin/env python3

"""
    Pylele Body
"""

import argparse
import os
import sys
from math import tan, inf

sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

from b13d.api.core import Shape
from b13d.api.solid import main_maker, test_loop, FIT_TOL, ColorEnum
from b13d.api.utils import radians
from pylele.config_common import TunerType
from pylele.pylele2.config import LeleBodyType
from pylele.pylele2.base import LeleBase
# from pylele.pylele2.chamber import pylele_chamber_parser

def genBodyPath(
                 scaleLen: float,
                 neckLen: float,
                 neckWth: float,
                 bodyWth: float,
                 bodyBackLen: float,
                 endWth: float,
                 neckWideAng: float,
                 isCut: bool = False,
                 body_type: LeleBodyType = LeleBodyType.GOURD,
                ) -> list[tuple[float, float, float, float]]:
    
    cutAdj = FIT_TOL if isCut else 0
    nkLen = neckLen
    nkWth = neckWth + 2*cutAdj
    bWth = bodyWth + 2*cutAdj
    bBkLen = bodyBackLen + cutAdj
    eWth = min(bWth, endWth) + (2*cutAdj if endWth > 0 else 0)
    
    neckDX = 1
    neckDY = neckDX * tan(radians(neckWideAng))

    body_origin = (nkLen,0)

    if body_type == LeleBodyType.TRAVEL:
        body_start = (nkLen - nkWth/2,0)
        bodySpline = [
            #                x,                y,         dx/dy, dx              , dy
            (nkLen - nkWth/2  ,                0,            inf,                 0),
            (nkLen + neckDX   , nkWth/2         , neckDY/neckDX),
            (nkLen+50         , bWth/2          , neckDY/neckDX),
            (scaleLen         , bWth/2          , 0            , .6              ),
            (scaleLen + bBkLen, eWth/2 +.1      , -inf         , (1-eWth/bWth)/2),
        ]

    elif body_type.is_flat():
        body_start = (nkLen - nkWth/2,0)
        bodySpline = [
            #                x,                y,         dx/dy, dx              , dy
            (nkLen - nkWth/2  ,                0,            inf,                 0),
            (nkLen + neckDX   , nkWth/2 + neckDY, neckDY/neckDX, .5              , .3),
            (scaleLen         , bWth/2          , 0            , .6              ),
            (scaleLen + bBkLen, eWth/2 +.1      , -inf         , (1-eWth/bWth)/2),
        ]

    else:
        body_start  = (nkLen, nkWth/2)
        bodySpline = [
            #                x,                y,         dx/dy, dx              , dy
            (nkLen + neckDX   , nkWth/2 + neckDY, neckDY/neckDX, .5              , .3),
            (scaleLen         , bWth/2          , 0            , .6              ),
            (scaleLen + bBkLen, eWth/2 +.1      , -inf         , (1-eWth/bWth)/2),
        ]

    bodyPath = [
        body_start,
        bodySpline,
        (scaleLen + bBkLen, eWth/2),
    ]

    if eWth > 0:
        bodyPath.insert(3,(scaleLen + bBkLen, 0))

    return body_origin, bodyPath

def pylele_body_parser(parser=None):
    """
    Pylele Body Element Parser
    """
    if parser is None:
        parser = argparse.ArgumentParser(description="Pylele Configuration")

    return parser

class LeleBody(LeleBase):
    """Pylele Body Generator class"""

    def gourd_shape(self, top: bool = True, custom_ratio = None):
        """generate the top or bottom of a gourd body"""

        if top:
            angle = 180
        else:
            angle = -180

        if custom_ratio is None:
            if top:
                ratio = self.cfg.TOP_RATIO
            else:
                ratio = self.cfg.BOT_RATIO
        else:
            ratio = custom_ratio

        bot_below = (
            self.api.spline_revolve(self.cfg.body_origin, self.cfg.body_path, angle)
            .scale(1, 1, ratio)
        )

        return bot_below
    
    def gourd_flat_extrusion(self, thickness: float, half: bool = False):
        bot = self.api.spline_extrusion(self.cfg.body_origin, self.cfg.body_path, thickness)
        if not half:
            return bot.mirror_and_join()
        return bot

    def configure(self):
        LeleBase.configure(self)

        self.cfg.body_origin, self.cfg.body_path = genBodyPath(
                 scaleLen = float(self.cli.scale_length),
                 neckLen = self.cfg.neckLen,
                 neckWth = self.cfg.neckWth,
                 bodyWth = self.cfg.bodyWth,
                 bodyBackLen = self.cfg.bodyBackLen,
                 endWth = self.cli.end_flat_width,
                 neckWideAng = self.cfg.neckWideAng,
                 isCut = self.isCut,
                 body_type=self.cli.body_type
                 )

    def gen_flat_body_bottom(self):
        """Generate the thin rounded bottom of a flat body"""
        bot_below = self.gourd_shape(top = False, custom_ratio=self.cfg.TOP_RATIO)
        bot_below <<= (0, 0, -self.cli.flat_body_thickness + self.api.tolerance())
        return bot_below

    def gen(self) -> Shape:
        """Generate Body"""
        midTck = self.cfg.extMidBotTck
        joinTol = self.api.tolerance()

        if self.cli.body_type == LeleBodyType.GOURD:
            # Gourd body
            bot = self.gourd_shape(top = False)

            if midTck > 0:
                # Generates flat middle section of body
                bot <<= (0, 0, joinTol - midTck)
                bot += self.gourd_flat_extrusion(thickness=-midTck)

        elif self.cli.body_type.is_solid():

            # Flat body
            bot = self.gourd_flat_extrusion(thickness=-self.cli.flat_body_thickness)
            if not self.cli.separate_bottom:
                bot += self.gen_flat_body_bottom()

        elif self.cli.body_type == LeleBodyType.HOLLOW:

            # Flat body
            # outer wall
            midR = self.gourd_flat_extrusion(thickness=-self.cli.flat_body_thickness, half=True)
            # inner wall
            midR2 = midR.dup().mv(0,-self.cli.wall_thickness,0)
            midR -= midR2
            bot = midR.mirror_and_join()
            if not self.cli.separate_bottom:
                bot += self.gen_flat_body_bottom()

        else:
            assert (
                self.cli.body_type in LeleBodyType.list()
            ), f"Unsupported Body Type {self.cli.body_type}"

        return bot.set_color(ColorEnum.ORANGE)

    def gen_parser(self, parser=None):
        """
        pylele Command Line Interface
        """
        parser = pylele_body_parser(parser=parser)
        # parser = pylele_chamber_parser(parser=parser)
        return super().gen_parser(parser=parser)

def main(args=None):
    """Generate body"""
    return main_maker(module_name=__name__, class_name="LeleBody", args=args)

def test_body(self, apis=None):
    """Test body"""

    ## Cadquery and blender
    tests = {
        "tail_end": ["-t", TunerType.WORM.name, "-e", "90", "-E","-refv","934731"],
        "flat": ["-bt", str(LeleBodyType.FLAT), "-fbt", "50", "-refv", "1405935"],
        "flat_worm": [
            "-bt",
            str(LeleBodyType.FLAT),
            "-t",
            TunerType.WORM.name,
            "-e",
            "90",
            "-E",
            "-refv", "794710"
        ],
        "hollow": ["-bt", str(LeleBodyType.HOLLOW),"-refv","194714"],
        "separate_bottom" : ["-BT"]
    }

    test_loop(module=__name__, apis=apis, tests=tests)

def test_body_mock(self):
    """Test body"""
    test_body(self, apis=["mock"])

if __name__ == "__main__":
    main()
