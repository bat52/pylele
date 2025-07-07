#!/usr/bin/env python3

"""
    Pylele Texts
"""

import os
import argparse
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

from b13d.api.core import Shape
from b13d.api.solid import main_maker, test_loop
from pylele.pylele2.base import LeleBase
from pylele.pylele2.body import LeleBody

DEFAULT_LABEL_SIZE = 9
DEFAULT_LABEL_SIZE_BIG = 24
DEFAULT_LABEL_SIZE_SMALL = 6
DEFAULT_LABEL_FONT = "Verdana"


def pylele_texts_parser(parser=None):
    """
    Pylele Texts Element Parser
    """
    if parser is None:
        parser = argparse.ArgumentParser(description="Pylele Configuration")

    ## text options ######################################################

    parser.add_argument(
        "-X", "--no_text", help="Skip text labeling", action="store_true"
    )

    parser.add_argument(
        "-txtr", "--text_rotation", help="Text Rotation [degrees]", type=float, default=0
    )

    parser.add_argument(
        "-txtl", "--text_logo", help="Text Logo filename", type=str, default=""
    )

    parser.add_argument(
        "-txtls", "--text_logo_scale", help="Text Logo scale", type=float, default=1
    )

    parser.add_argument(
        "-txtly", "--text_logo_y", help="Text Logo Y position", type=float, default=0
    )

    parser.add_argument(
        "-x",
        "--texts_size_font",
        help="Comma-separated text[:size[:font]] tuples, "
        + "default Pylele:28:Arial,:8,'mind2form.com © 2024':8:Arial",
        type=lambda x: [
            (l[0], 10 if len(l) < 2 else int(l[1]), "Arial" if len(l) < 3 else l[2])
            for l in (tsfs.split(":") for tsfs in x.split(","))
        ],
        default=[
            ("PYLELE", DEFAULT_LABEL_SIZE_BIG, DEFAULT_LABEL_FONT),
            ("", DEFAULT_LABEL_SIZE_SMALL, None),  # for empty line
            ("mind2form.com © 2024", DEFAULT_LABEL_SIZE, DEFAULT_LABEL_FONT),
        ],
    )

    return parser


class LeleTexts(LeleBase):
    """Pylele Texts Generator class"""
    TEXT_TCK = 30

    def gen(self) -> Shape:
        """Generate Texts"""

        scLen = float(self.cli.scale_length)
        backRat = self.cli.chamber_back_ratio
        dep = self.cfg.EMBOSS_DEP

        tsf = self.cli.texts_size_font

        txtTck = self.TEXT_TCK
        bodyWth = self.cfg.bodyWth
        botRat = self.cfg.BOT_RATIO
        midBotTck = self.cfg.extMidBotTck
        cutTol = self.api.tolerance()

        txtZ = -botRat * bodyWth / 2 - midBotTck - 2
        allHt = sum([1.2 * size for _, size, _ in tsf])
        tx = 1.05 * scLen - allHt / (1 + backRat)
        ls: Shape = None
        for txt, sz, fnt in tsf:
            if not txt is None and not fnt is None:
                # orig impl uses mirror() instead of rotate_x(180)
                # but Blender text mirroring can lead to weird output
                l = (
                    self.api.text(txt, sz, txtTck, fnt)
                    .rotate_z(90 + self.cli.text_rotation)
                    .rotate_x(180)
                    .mv(tx + sz / 2, 0, txtZ + txtTck)
                )
                ls = l + ls
            tx += sz

        if self.cli.text_logo and os.path.isfile(self.cli.text_logo):
            # add logo text
            logo = self.api.genImport(self.cli.text_logo, extrude=txtTck).rotate_z(-90)
            logo = logo.scale(self.cli.text_logo_scale, self.cli.text_logo_scale, 1)
            logo <<= (self.cfg.neckLen, self.cli.text_logo_y, txtZ - txtTck/2)
            ls += logo
        
        botCut = LeleBody(cli=self.cli, isCut=True).mv(0, 0, cutTol)

        txtCut = ls.cut(botCut.shape).mv(0, 0, dep)

        return txtCut

    def gen_parser(self, parser=None):
        """
        pylele Command Line Interface
        """
        return super().gen_parser(parser=pylele_texts_parser(parser=parser))


def main(args=None):
    """Generate texts"""
    return main_maker(
        module_name=__name__,
        class_name="LeleTexts",
        args=args,
    )


def test_texts(self, apis=None):
    """Test texts"""
    tests = {"default": ["-x", "TEST:30"]}
    test_loop(
        module=__name__,
        apis=apis,
        tests=tests,
    )


def test_texts_mock(self):
    """Test texts"""
    test_texts(self, apis=["mock"])


if __name__ == "__main__":
    main(sys.argv[1:] + ["-x", "TEST:30"])
