#!/usr/bin/env python3

""" Pylele Configuration Module """

import argparse
from math import atan, inf, sqrt, tan

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

from b13d.api.core import Fidelity, Implementation, StringEnum
from b13d.api.utils import radians, degrees, accumDiv
from b13d.api.constants import FIT_TOL, FILLET_RAD, ColorEnum
from pylele.config_common import SEMI_RATIO, LeleScaleEnum, TunerConfig, PegConfig, WormConfig, TunerType

DEFAULT_FLAT_BODY_THICKNESS=25

class LeleBodyType(StringEnum):
    """ Body Type """
    GOURD = 'gourd'
    FLAT  = 'flat'
    HOLLOW = 'hollow'
    TRAVEL = 'travel'

    def is_flat(self) -> bool:
        """ Is Flat Body """
        return self in [LeleBodyType.FLAT, LeleBodyType.HOLLOW, LeleBodyType.TRAVEL]
    
    def is_solid(self) -> bool:
        """ Is Flat Body """
        return self in [LeleBodyType.FLAT, LeleBodyType.TRAVEL]

WORM_SLIT = ['-wah','-wsl','35']
WORM    = ['-t','worm'   ,'-e','65'] + WORM_SLIT
BIGWORM = ['-t','bigworm','-e','90','-fbt','33','-g','11'] + WORM_SLIT
FATWORM = ['-t','fatworm','-e','90','-fbt','25','-g','13'] + WORM_SLIT
TUNEBRIDGE = ['-brt','tunable',"-bta"]
TRAVEL = ['-bt', LeleBodyType.TRAVEL,'-wt', '6','-cbar','0.125', '-s', LeleScaleEnum.TRAVEL.name]

CONFIGURATIONS = {
        'default'        : [],
        'worm'           : WORM    , # gourd
        'flat'           : BIGWORM    + 
                           TUNEBRIDGE +
                            ['-bt', LeleBodyType.FLAT,
                            '-cbar','0.125',
                            '-cbr','1.8',
                            '-s',LeleScaleEnum.CONCERT.name],
        'hollow'         : BIGWORM + ['-bt', LeleBodyType.HOLLOW],
        'travel'         : FATWORM + TRAVEL + # TUNEBRIDGE + 
                           ['-cbr','1.2','-nsr','0.45','-fbsr','0.55'],
                            # '-s',LeleScaleEnum.CONCERT.name],
        'travelele'      : TRAVEL  + 
                            ['-t','turnaround',
                            #'-nsp', '1',
                            '-e','65',
                            '-cbr','1.5',
                            '-fbt','20',
                            '-fbsr','0.6',
                            '-x','PyTravelele - Merlin 2025:4:Arial'] + WORM_SLIT # + TUNEBRIDGE
    }

class AttrDict(dict):
    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        self[key] = value

def pylele_config_parser(parser = None):
    """
    Pylele Base Element Parser
    """
    if parser is None:
        parser = argparse.ArgumentParser(description='Pylele Configuration')

    ## config overrides ###########################################

    parser.add_argument("-cfg", "--configuration",
                        help="Configuration",
                        type=str,choices=CONFIGURATIONS.keys(),
                        default=None)

    ## Numeric config options ###########################################
    parser.add_argument("-s", "--scale_length",
                        help=f"Scale Length [mm], or {LeleScaleEnum.list()}, default: {LeleScaleEnum.SOPRANO.name}={LeleScaleEnum.SOPRANO.value}",
                        type=LeleScaleEnum.type, default=LeleScaleEnum.SOPRANO)
    parser.add_argument("-n", "--num_strings", help="Number of strings, default 4",
                        type=int, default=4)
    parser.add_argument("-a", "--action", help="Strings action [mm], default 2",
                        type=float, default=2)
    parser.add_argument("-g", "--nut_string_gap", help="Strings gap at nut [mm], default 9",
                        type=float, default=9)
    parser.add_argument("-e", "--end_flat_width", help="Flat width at tail end [mm]",
                        type=float, default=0)
    parser.add_argument("-nsp", "--num_spines", help="Number of neck spines",
                        type=int, default=3, choices=[*range(4)])
    parser.add_argument("-mnwa", "--min_neck_wide_angle", help="Minimum Neck Widening angle [deg]",
                        type=float, default=1.2)
    parser.add_argument("-cbr", "--chamber_bridge_ratio", help="Chamber/Bridge width",
                        type=float, default=3)
    parser.add_argument("-cbar", "--chamber_back_ratio", help="Chamber Back/Front length",
                        type=float, default=1/2)
    parser.add_argument("-fbsr", "--fretboard_ratio", help="Fretboad/Scale length ratio",
                        type=float, default=0.635)
    parser.add_argument("-fbra", "--fretboard_rise_angle", help="Fretboad rise angle",
                        type=float, default=1)
    parser.add_argument("-nsr", "--neck_ratio", help="Neck/Scale length ratio",
                        type=float, default=0.55)

    ## Body Type config options ###########################################

    parser.add_argument("-bt", "--body_type",
                    help="Body Type",
                    type=LeleBodyType,
                    choices=list(LeleBodyType),
                    default=LeleBodyType.GOURD
                    )

    parser.add_argument("-fbt", "--flat_body_thickness", 
                        help=f"Body thickness [mm] when flat body, default {DEFAULT_FLAT_BODY_THICKNESS}",
                        type=float, default=DEFAULT_FLAT_BODY_THICKNESS)

    ## Chamber config options ###########################################

    parser.add_argument("-wt", "--wall_thickness", help="Chamber Wall Thickness [mm], default 4",
                        type=float, default=4)

    ## Non-Numeric config options #######################################

    parser.add_argument("-t", "--tuner_type", help=f"Type of tuners, default; {TunerType.FRICTION.name}",
                        type=str.upper, choices=TunerType.list(), default=TunerType.FRICTION.name)

    ## Cut options ######################################################

    parser.add_argument("-T", "--separate_top",
                        help="Split body top from body back.",
                        action='store_true')
    parser.add_argument("-BT", "--separate_bottom",
                        help="Split body bottom from body.",
                        action='store_true')
    parser.add_argument("-N", "--separate_neck",
                        help="Split neck from body.",
                        action='store_true')
    parser.add_argument("-F", "--separate_fretboard",
                        help="Split fretboard from neck back.",
                        action='store_true')
    parser.add_argument("-B", "--separate_bridge",
                        help="Split bridge from body.",
                        action='store_true')
    parser.add_argument("-G", "--separate_guide",
                        help="Split guide from body.",
                        action='store_true')
    parser.add_argument("-E", "--separate_end",
                        help="Split end block from body.",
                        action='store_true')
    parser.add_argument("-all",
                        "--all",
                        help="Show all cut part in assembly",
                        action="store_true",)
    parser.add_argument("-ad", "--all_distance", help="Distance between parts when showing all",
                        type=float, default=10)

    return parser

def tzAdj(tY: float, tnrType: TunerType, endWth: float, top_ratio: float) -> float:
    """ Adjust Tuner Z """
    return 0 if tnrType.is_worm() or tY > endWth/2 \
        else (((endWth/2)**2 - tY**2)**.5 * top_ratio/2 + .5)

class LeleConfig:
    """ Pylele Configuration Class """
    TOP_RATIO = 1/8
    BOT_RATIO = 2/3
    EMBOSS_DEP = .5
    FRET_HT = 1
    FRETBD_SPINE_TCK = 2
    FRETBD_TCK = 2
    GUIDE_RAD = 1.55
    GUIDE_SET = 0
    MAX_FRETS = 24
    NUT_HT = 1.5
    SPINE_HT = 10
    SPINE_WTH = 2
    STR_RAD = .6
    extMidTopTck = .5

    def gen_parser(self,parser=None):
        """
        Solid Command Line Interface
        """
        return pylele_config_parser(parser=parser)

    def parse_args(self, args=None):
        """ Parse Command Line Arguments """
        return self.gen_parser().parse_args(args=args)

    def is_odd_strs(self) -> bool:
        return self.cli.num_strings % 2 == 1
    
    def configure_tuners(self):
        """ Configure Tuners
            cli inputs: 
                scale_length
                end_flat_width
                tuner_type
                num_string
            parameter inputs:
                self.bodyBackLen
                self.bodyWth
                self.extMidTopTck
                self.TOP_RATIO
            parameter outputs:
                self.tnrXYZs
                self.tZBase
                self.tMidZ
        """

        # Tuner config
        # approx spline bout curve with ellipse but 'fatter'
        scaleLen=float(self.cli.scale_length)
        endWth = self.cli.end_flat_width
        tnrType=TunerType[self.cli.tuner_type].value
        tnrSetback = tnrType.tailAllow()
        numStrs=self.cli.num_strings

        tXMax = self.bodyBackLen - tnrSetback
        fatRat = .7 + (endWth/self.bodyWth)/2
        tYMax = fatRat*self.bodyWth - tnrSetback
        tX = tXMax
        tY = 0

        if tnrType.is_peg():
            tZBase = (self.extMidTopTck + 2)
        elif tnrType.is_worm():
            tZBase = (-tnrType.driveRad - tnrType.diskRad - tnrType.axleRad)
        else:
            assert False, f'Unsupported Tuner Type {tnrType}'
        self.tZBase = tZBase

        self.tMidZ = self.tZBase + tzAdj(tY, tnrType=tnrType, endWth=endWth, top_ratio=self.TOP_RATIO)
        tZ = self.tMidZ
        tDist = self.tnrGap
        # start calc from middle out
        self.tnrXYZs = [(scaleLen + tX, 0, tZ)] if self.is_odd_strs() else []
        for p in range(numStrs//2):
            if tY + tDist < endWth/2:
                tY += tDist if self.is_odd_strs() or p > 0 else tDist/2
                # tX remain same
                tZ = self.tZBase + tzAdj(tY, tnrType=tnrType, endWth=endWth, top_ratio=self.TOP_RATIO)
            else:
                """
                Note: Ellipse points seperated by arc distance calc taken from
                https://gamedev.stackexchange.com/questions/1692/what-is-a-simple-algorithm-for-calculating-evenly-distributed-points-on-an-ellip

                view as the back of ukulele, which flips XY, diff from convention & post
                  X
                  ^
                  |
                b +-------._  (y,x)
                  |         `@-._
                  |              `-.
                  |                 `.
                  |                   \
                 -+--------------------+---> Y
                 O|                    a

                y' = y + d / sqrt(1 + b²y² / (a²(a²-y²)))
                x' = b sqrt(1 - y'²/a²)
                """
                tY = tY + (tDist if self.is_odd_strs() or p > 0 else tDist/2) \
                    / sqrt(1 + tXMax**2 * tY**2 / (tYMax**2 * (tYMax**2 - tY**2)))
                tX = tXMax * sqrt(1 - tY**2/tYMax**2)
                tZ = self.tZBase

            self.tnrXYZs.extend(
                [(scaleLen + tX, tY, tZ), (scaleLen + tX, -tY, tZ)],
            )

    def __init__(
        self,
        args = None,
        cli = None
    ):
        if cli is None:
            self.cli = self.parse_args(args=args)
        else:
            self.cli = cli

        scaleLen=float(self.cli.scale_length)
        action=self.cli.action
        numStrs=self.cli.num_strings
        nutStrGap=self.cli.nut_string_gap
        wallTck=self.cli.wall_thickness
        self.tolerance = self.cli.implementation.tolerance()
        tnrType=TunerType[self.cli.tuner_type].value

        # Length based configs
        self.fretbdLen = scaleLen * self.cli.fretboard_ratio
        self.chmFront = scaleLen - self.fretbdLen - wallTck
        self.chmBack = self.cli.chamber_back_ratio * self.chmFront
        (tnrFront, tnrBack, _, _, _, _) = tnrType.dims()

        self.bodyBackLen = self.chmBack + tnrFront + tnrBack
        if not self.cli.body_type in [LeleBodyType.TRAVEL]:
            self.bodyBackLen += wallTck

        self.tailX = scaleLen + self.bodyBackLen
        self.nutWth = max(2,numStrs) * nutStrGap
        tnrSetback = tnrType.tailAllow()
        if tnrType.is_peg():
            self.neckWideAng = self.cli.min_neck_wide_angle
            self.tnrGap = tnrType.minGap()
        else:
            tnrX = scaleLen + self.bodyBackLen - tnrSetback
            tnrW = tnrType.minGap() * numStrs
            tnrNeckWideAng = degrees(atan((tnrW - self.nutWth)/2/tnrX))
            self.neckWideAng = max(self.cli.min_neck_wide_angle, tnrNeckWideAng)
            tnrsWth = self.nutWth + 2*tnrX*tan(radians(self.neckWideAng))
            self.tnrGap = tnrsWth / numStrs

        self.brdgWth = nutStrGap*(max(2,numStrs)-.5) + \
            2 * tan(radians(self.neckWideAng)) * scaleLen
        brdgStrGap = self.brdgWth / (numStrs-.5)
        self.brdgStrGap = brdgStrGap

        self.neckLen = scaleLen * self.cli.neck_ratio
        self.extMidBotTck = max(0, 10 - numStrs**1.25)

        # Neck configs
        self.neckWth = self.nutWth + \
            2 * tan(radians(self.neckWideAng)) * self.neckLen

        # Fretboard configs
        self.fretbdWth = self.nutWth + \
            2 * tan(radians(self.neckWideAng)) * self.fretbdLen
        self.fretbdHt = self.FRETBD_TCK + \
            tan(radians(self.cli.fretboard_rise_angle)) * self.fretbdLen

        # Chamber Configs
        self.chmWth = self.brdgWth * self.cli.chamber_bridge_ratio
        self.rimWth = wallTck/2

        # Head configs
        self.headLen = 2 * numStrs + scaleLen / 60 #12

        # Body Configs
        self.bodyWth = self.chmWth + 2*wallTck
        self.bodyFrontLen = scaleLen - self.neckLen

        # Bridge configs
        f12Len = scaleLen/2
        f12Ht = self.FRETBD_TCK \
            + tan(radians(self.cli.fretboard_rise_angle)) * f12Len \
            + self.FRET_HT
        self.brdgZ = self.bodyWth/2 * self.TOP_RATIO + self.extMidTopTck - 1.5
        self.brdgHt = 2*(f12Ht + action - self.NUT_HT - self.STR_RAD/2) \
            - self.brdgZ
        self.brdgLen = nutStrGap

        # Tuners Configuration
        self.configure_tuners()

        # Guide config (Only for Pegs)
        if tnrType.is_peg():
            self.guideHt = 6 + numStrs/2
            self.guideX = scaleLen + .95*self.chmBack
            self.guideZ = -self.GUIDE_SET \
                + self.TOP_RATIO * sqrt(self.bodyBackLen**2 - self.chmBack**2)
            self.guideWth = self.nutWth \
                + 2*tan(radians(self.neckWideAng))*self.guideX+ 2*self.GUIDE_RAD
            gGap = self.guideWth/numStrs
            self.guidePostGap = gGap
            gGapAdj = self.GUIDE_RAD

            # start calc from middle out
            gY = gGapAdj if self.is_odd_strs() else gGap/2 + gGapAdj + .5*self.STR_RAD
            self.guideYs = [gGapAdj +2*self.STR_RAD, -gGapAdj -2*self.STR_RAD] \
                if self.is_odd_strs() else [gY + self.STR_RAD, -gY - self.STR_RAD]
            for _ in range((numStrs-1)//2):
                gY += gGap
                self.guideYs.extend([gY + gGapAdj, -gY -gGapAdj])

        # Strings config
        strOddMidPath = [
            (-self.headLen, 0, -self.FRETBD_SPINE_TCK - .2*self.SPINE_HT),
            (0, 0, self.FRETBD_TCK + self.NUT_HT + self.STR_RAD/2),
            (scaleLen, 0, self.brdgZ + self.brdgHt + 1.5*self.STR_RAD),
        ]

        if tnrType.is_peg():  # Worm drives has no string guide
            strOddMidPath.append(
                (self.guideX, 0,
                 self.guideZ + self.guideHt - self.GUIDE_RAD - 1.5*self.STR_RAD)
            )

        strOddMidPath.append(
            (scaleLen + self.bodyBackLen - tnrSetback, 0,
             self.tMidZ + tnrType.strHt())
        )

        strEvenMidPathR = []
        strEvenMidPathL = []
        strEvenMidBrdgDY = brdgStrGap/2 - nutStrGap/2
        strEvenMidAng = atan(strEvenMidBrdgDY/scaleLen)

        # even middle string pair points is just odd middle string points with DY
        # following same widening angle except ending point uing pegY and pegZ + peg hole height
        for pt in strOddMidPath:
            strY = (self.tnrGap/2) if pt == strOddMidPath[-1] \
                else nutStrGap/2 + pt[0]*tan(strEvenMidAng)
            strZ = (
                self.tZBase + tnrType.strHt()) if pt == strOddMidPath[-1] else pt[2]
            strEvenMidPathR.append((pt[0], strY, strZ))
            strEvenMidPathL.append((pt[0], -strY, strZ))

        # add initial middle string if odd else middle string pairs
        self.stringPaths = [strOddMidPath] if self.is_odd_strs() \
            else [strEvenMidPathR, strEvenMidPathL]

        # add strings from middle out
        for si in range((numStrs-1)//2):
            strCnt = si+1
            strLastPath = self.stringPaths[-1]
            strPathR = []
            strPathL = []
            for pt in strLastPath:
                if pt == strLastPath[-1]:
                    strPegXYZ = self.tnrXYZs[
                        2*si + (1 if self.is_odd_strs() else 2)
                    ]
                    strX = strPegXYZ[0]
                    strY = strPegXYZ[1]
                    strZ = strPegXYZ[2] + tnrType.strHt()
                else:
                    strBrdgDY = (strCnt + (0 if self.is_odd_strs() else .5))\
                        * (brdgStrGap - nutStrGap)
                    strEvenAng = atan(strBrdgDY/scaleLen)
                    strX = pt[0]
                    strY = nutStrGap*(strCnt + (0 if self.is_odd_strs() else .5))\
                        + strX*tan(strEvenAng)
                    strZ = pt[2]
                strPathR.append((strX, strY, strZ))
                strPathL.append((strX, -strY, strZ))
            self.stringPaths.append(strPathR)
            self.stringPaths.append(strPathL)

    def __repr__(self):
        class_vars_str = '\n'.join(f"{key}={value!r}" for key, value in self.__class__.__dict__.items() \
                if not callable(value) and not key.startswith("__"))
        instance_vars_str = '\n'.join(f"{key}={value!r}" for key, value in vars(self).items())
        return f"{self.__class__.__name__}\n{class_vars_str}\n{instance_vars_str}"

def main():
    """ Pylele Configuration """
    parser = pylele_config_parser()
    cli = parser.parse_args()

    if not cli.configuration is None:
        # print(AttrDict(vars(cli)))
        cli = parser.parse_args(args=CONFIGURATIONS[cli.configuration])

    print(AttrDict(vars(cli)))
    cfg = LeleConfig(cli=cli)
    # print(cfg)
    return cfg

if __name__ == '__main__':
    main()
