#!/usr/bin/env python3

"""
    Pylele Worm
"""

import os
import argparse
from pylele_api import Shape
from pylele_base import LeleBase
from pylele_config import WormConfig, FIT_TOL

def pylele_worm_parser(parser = None):
    """
    Pylele Worm Parser
    """
    if parser is None:
        parser = argparse.ArgumentParser(description='Pylele Worm Configuration')

    parser.add_argument("-whh", "--worm_hole_heigth",
                    help="Worm Hole Heigth [mm]",
                    type=float,
                    default=23
                    )
    parser.add_argument("-wsl", "--worm_slit_length",
                    help="Worm Slit Length [mm]",
                    type=float,
                    default=10
                    )
    parser.add_argument("-wsw", "--worm_slit_width",
                    help="Worm Slit Width [mm]",
                    type=float,
                    default=3
                    )
    parser.add_argument("-wdit", "--worm_disk_thickness",
                    help="Worm Disk Thickness [mm]",
                    type=float,
                    default=5
                    )
    parser.add_argument("-wdir", "--worm_disk_radius",
                    help="Worm Disk Radius [mm]",
                    type=float,
                    default=7.7
                    )
    parser.add_argument("-war", "--worm_axle_radius",
                    help="Worm Axle Radius [mm]",
                    type=float,
                    default=3
                    )
    parser.add_argument("-wal", "--worm_axle_length",
                    help="Worm Axle Length [mm]",
                    type=float,
                    default=6 # original worm tuner has 8mm axle
                    )
    parser.add_argument("-wdrr", "--worm_drive_radius",
                    help="Worm Drive Radius [mm]",
                    type=float,
                    default=4
                    )
    parser.add_argument("-wdrl", "--worm_drive_length",
                    help="Worm Drive Length [mm]",
                    type=float,
                    default=14
                    )
    parser.add_argument("-wdro", "--worm_drive_offset",
                    help="Worm Drive Offser [mm]",
                    type=float,
                    default=9.75
                    )
    parser.add_argument("-wga", "--worm_gap_adjust",
                    help="Worm Gap Adjust [mm]",
                    type=float,
                    default=1
                    )
    parser.add_argument("-wbt", "--worm_button_thickness",
                    help="Worm Button Thickness [mm]",
                    type=float,
                    default=9.5
                    )
    parser.add_argument("-wbw", "--worm_button_width",
                    help="Worm Button Width [mm]",
                    type=float,
                    default=16
                    )
    parser.add_argument("-wbh", "--worm_button_heigth",
                    help="Worm Button heigth [mm]",
                    type=float,
                    default=8
                    )
    parser.add_argument("-wbkl", "--worm_button_key_length",
                    help="Worm Button Key Length [mm]",
                    type=float,
                    default=6
                    )
    parser.add_argument("-wbkr", "--worm_button_key_radius",
                    help="Worm Button Key Radius [mm]",
                    type=float,
                    default=2.25
                    )
    parser.add_argument("-wbkbr", "--worm_button_key_base_radius",
                    help="Worm Button Key Base Radius [mm]",
                    type=float,
                    default=3.8
                    )
    parser.add_argument("-wbkbh", "--worm_button_key_base_heigth",
                    help="Worm Button Key Base Heigth [mm]",
                    type=float,
                    default=3
                    )
    return parser

class LeleWorm(LeleBase):
    """ Pylele Worm Generator class """

    def configure(self):

        super().configure()

        self.cfg.tnrCfg = WormConfig(
            holeHt  = self.cli.worm_hole_heigth,
            slitLen = self.cli.worm_slit_length,
            slitWth = self.cli.worm_slit_width,
            diskTck = self.cli.worm_disk_thickness,
            diskRad = self.cli.worm_disk_radius,
            axleRad = self.cli.worm_axle_radius,
            axleLen = self.cli.worm_axle_length,
            driveRad = self.cli.worm_drive_radius,
            driveLen = self.cli.worm_drive_length,
            driveOffset = self.cli.worm_drive_offset,
            gapAdj = self.cli.worm_gap_adjust,
            buttonTck = self.cli.worm_button_thickness,
            buttonWth = self.cli.worm_button_width,
            buttonHt = self.cli.worm_button_heigth,
            buttonKeyLen = self.cli.worm_button_key_length,
            buttonKeyRad = self.cli.worm_button_key_radius,
            buttonKeybaseRad = self.cli.worm_button_key_base_radius,
            buttonKeybaseHt = self.cli.worm_button_key_base_radius,
            # code: str = 'W',
        )
    
    def gen(self) -> Shape:
        """ Generate Worm """

        cutAdj = FIT_TOL if self.isCut else 0

        sltLen = self.cfg.tnrCfg.slitLen
        sltWth = self.cfg.tnrCfg.slitWth
        drvRad = self.cfg.tnrCfg.driveRad + cutAdj
        dskRad = self.cfg.tnrCfg.diskRad + cutAdj
        dskTck = self.cfg.tnrCfg.diskTck + 2*cutAdj
        axlRad = self.cfg.tnrCfg.axleRad + cutAdj
        axlLen = self.cfg.tnrCfg.axleLen + 2*cutAdj
        offset = self.cfg.tnrCfg.driveOffset
        drvLen = self.cfg.tnrCfg.driveLen + 2*cutAdj

        # Note: Origin is middle of slit, near tip of axle
        axlX = 0
        axlY = -.5  # sltWth/2 -axlLen/2
        axlZ = 0
        axl = self.api.genRodY(axlLen, axlRad).mv(axlX, axlY, axlZ)
        if self.isCut:
            axlExtCut = self.api.genBox(
                100, axlLen, 2*axlRad).mv(50 + axlX, axlY, axlZ)
            axl = axl.join(axlExtCut)

        dskX = axlX
        dskY = axlY - axlLen/2 - dskTck/2
        dskZ = axlZ
        dsk = self.api.genRodY(dskTck, dskRad).mv(dskX, dskY, dskZ)
        if self.isCut:
            dskExtCut = self.api.genBox(
                100, dskTck, 2*dskRad).mv(50 + dskX, dskY, dskZ)
            dsk = dsk.join(dskExtCut)

        drvX = dskX
        drvY = dskY
        drvZ = dskZ + offset
        drv = self.api.genRodX(drvLen, drvRad).mv(drvX, drvY, drvZ)
        if self.isCut:
            drvExtCut = self.api.genRodX(100, drvRad).mv(50 + drvX, drvY, drvZ)
            drv = drv.join(drvExtCut)

        worm = axl.join(dsk).join(drv)

        if self.isCut:
            slit = self.api.genBox(sltLen, sltWth, 100).mv(0, 0, 50 - 2*axlRad)
            worm = worm.join(slit)

        self.shape = worm
        return worm 
    
    def gen_parser(self,parser=None):
        """
        pylele Command Line Interface
        """
        return super().gen_parser( parser=pylele_worm_parser(parser=parser) )

def worm_main(args = None):
    """ Generate Worm """
    solid = LeleWorm(args=args)
    solid.export_args() # from cli
    solid.export_configuration()
    solid.exportSTL()
    return solid

def test_worm():
    """ Test Worm """

    component = 'worm'
    tests = {
        'cut'     : ['-C'],
        'cadquery': ['-i','cadquery'],
        'blender' : ['-i','blender']
    }

    for test,args in tests.items():
        print(f'# Test {component} {test}')
        outdir = os.path.join('./test',component,test)
        args += ['-o', outdir]
        worm_main(args=args)

if __name__ == '__main__':
    worm_main()
