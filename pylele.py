#!/usr/bin/env python3

import datetime
import os
import sys
from pathlib import Path
from pylele_assemble import assemble, test
from pylele_cli import parseCLI
from pylele_config import Implementation, LeleConfig, FILLET_RAD, TunerType
from pylele_parts import Strings, Tuners, WormKey, Spines

"""
    Main Logic of Pylele
"""

def pylele_main():

    # parse inputs
    cli = parseCLI()

    # generate configurations
    cfg = LeleConfig(
        scaleLen=cli.scale_length,
        action=cli.action,
        numStrs=cli.num_strings,
        nutStrGap=cli.nut_string_gap,
        sepTop=cli.separate_top,
        sepFretbd=cli.separate_fretboard,
        sepNeck=cli.separate_neck,
        sepBrdg=cli.separate_bridge,
        sepEnd=cli.separate_end,
        endWth=cli.end_flat_width,
        wallTck=cli.wall_thickness,
        chmLift=cli.chamber_lift,
        chmRot=cli.chamber_rotate,
        fret2Dots=cli.dot_frets,
        txtSzFonts=cli.texts_size_font,
        modelLbl=cli.model_label,
        half=cli.half,
        tnrType=cli.tuner_type,
        fidelity=cli.fidelity,
        impl=cli.implementation,
    )

    expDir = Path.cwd()/"build"
    if not expDir.exists():
        expDir.mkdir()
    elif not expDir.is_dir():
        print("Cannot export to non directory: %s" % expDir, file=sys.stderr)
        sys.exit(os.EX_SOFTWARE)

    expDir = expDir / (datetime.datetime.now().strftime("%y%m%d-%H%M-")+cfg.genModelStr())
    if not expDir.exists():
        expDir.mkdir()

    with open(expDir / 'config.txt', 'w') as f:
        f.write(repr(cfg))
    
    parts = assemble(cfg)

    for p in parts:
        if cfg.half:
            p = p.half()
        p.exportSTL(str(expDir/f"{p.fileNameBase}.stl"))

def cqeditor_main():
    cfg = LeleConfig(scaleLen=330, endWth=90, chmLift=2,
        impl=Implementation.CAD_QUERY, tnrType=TunerType.WORM_TUNER,
        sepEnd=True, sepTop=True, sepNeck=True, sepFretbd=True)
    strs = Strings(cfg, isCut=False)
    tnrs = Tuners(cfg, isCut=False, fillets={FILLET_RAD:[]})
    key = None if not cfg.isWorm else WormKey(cfg, isCut=False)
    sps = None if cfg.numStrs < 2 else Spines(cfg, isCut=False)
    parts = assemble(cfg)
    parts.extend([strs, tnrs])
    if not sps is None:
        parts.append(sps)
    if not key is None:
        parts.append(key)
    for p in parts:
        if cfg.half:
            p = p.half()
        show_object(p.show(), name=p.fileNameBase, options={'color':p.color}) # type: ignore

if __name__ == '__main__':
    pylele_main()
elif __name__ == '__cq_main__':
    cqeditor_main()