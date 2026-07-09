#!/usr/bin/env python3

"""
    Worm Solid
    Native implementation modeled after BOSL2 worm() function
    https://github.com/BelfrySCAD/BOSL2/blob/master/gears.scad
"""

from math import sin, cos, pi, asin, tan, atan

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from b13d.api.solid import Solid, test_loop, main_maker, Implementation
from b13d.api.core import Shape

try:
    from solid2.extensions.bosl2.gears import worm as bosl2_worm
    BOSL2_AVAILABLE = True
except ImportError:
    bosl2_worm = None
    BOSL2_AVAILABLE = False


def _rack2d_tooth_profile(circ_pitch, pa_deg, clearance, backlash, helical, profile_shift=0):
    """Generate parameters for a single rack tooth.
    
    Returns (trans_pitch, adendum, dedendum, poff, ax, dx) for computing
    the rack profile at any y position.
    """
    trans_pitch = circ_pitch / cos(helical)
    trans_pa = atan(tan(pa_deg * pi / 180) / cos(helical))
    mod = circ_pitch / pi

    if clearance is None:
        clearance = 0.25 * mod

    adendum = mod * (1 + profile_shift)
    dedendum = mod * (1 - profile_shift) + clearance
    tthick = trans_pitch / pi * (pi / 2 + 2 * profile_shift * tan(pa_deg * pi / 180)) - backlash

    ax = adendum * tan(trans_pa)
    dx = dedendum * tan(trans_pa)
    poff = tthick / 2

    return (trans_pitch, adendum, dedendum, poff, ax, dx)


def _rack_profile_offset(y, trans_pitch, adendum, dedendum, poff, ax, dx):
    """Compute rack profile x-offset at a given y (along rack length).
    
    Maps a y-position along the rack to the signed x-offset from pitch circle.
    Uses a modular mapping so any y value works.
    """
    y_mod = y % trans_pitch
    if y_mod < 0:
        y_mod += trans_pitch

    if y_mod <= poff - ax:
        return adendum
    elif y_mod <= poff + dx:
        t = (y_mod - (poff - ax)) / (dx + ax)
        return adendum - t * (adendum + dedendum)
    elif y_mod <= trans_pitch - (poff + dx):
        return -dedendum
    elif y_mod <= trans_pitch - (poff - ax):
        t = (y_mod - (trans_pitch - poff - dx)) / (dx + ax)
        return -dedendum + t * (adendum + dedendum)
    else:
        return adendum


def gen_worm_vnf(circ_pitch, d, l, starts=1, left_handed=False,
                  pressure_angle=20, backlash=0, clearance=None,
                  gear_spin=0):
    """Generate worm vertices and faces (VNF) equivalent to BOSL2 worm().
    
    Returns (vertices, faces) where vertices is a list of (x,y,z) tuples
    and faces is a list of face index lists.
    """
    helical = asin(starts * circ_pitch / pi / d)
    (trans_pitch, adendum, dedendum, poff, ax, dx) = _rack2d_tooth_profile(
        circ_pitch, pressure_angle, clearance, backlash, helical
    )

    steps = max(36, int(pi * d / (circ_pitch / 8)))
    zsteps = int(l / trans_pitch / starts * steps)
    if zsteps < 1:
        zsteps = 1
    zstep = l / zsteps

    verts = []
    for j in range(zsteps + 1):
        for i in range(steps):
            u = i / steps - 0.5
            ang = 2 * pi * (1 - u) + pi / 2
            z = j * zstep - l / 2
            zoff = trans_pitch * starts * u
            h = _rack_profile_offset(z + zoff, trans_pitch, adendum, dedendum, poff, ax, dx)
            r = d / 2 + h
            x = r * cos(ang)
            y = r * sin(ang)
            verts.append((x, y, z))

    faces = []

    for j in range(zsteps):
        for i in range(steps):
            i_next = (i + 1) % steps
            a = j * steps + i
            b = j * steps + i_next
            c = (j + 1) * steps + i_next
            d_face = (j + 1) * steps + i
            faces.append([a, c, b])
            faces.append([a, d_face, c])

    cap_center_bot = len(verts)
    verts.append((0, 0, -l / 2))
    for i in range(steps):
        i_next = (i + 1) % steps
        faces.append([i, i_next, cap_center_bot])

    cap_center_top = len(verts)
    verts.append((0, 0, l / 2))
    top_start = zsteps * steps
    for i in range(steps):
        i_next = (i + 1) % steps
        faces.append([top_start + i_next, top_start + i, cap_center_top])

    if left_handed:
        verts = [(x, -y, z) for x, y, z in verts]
        faces = [[f[0], f[2], f[1]] for f in faces]

    if gear_spin != 0:
        sa = gear_spin * pi / 180
        csa, ssa = cos(sa), sin(sa)
        verts = [(x * csa - y * ssa, x * ssa + y * csa, z) for x, y, z in verts]

    return verts, faces


class Worm(Solid):
    """ Generate a Worm """

    def gen_parser(self, parser=None):
        parser = super().gen_parser(parser=parser)
        parser.add_argument("-cp", "--circ_pitch",
                            help="Circular pitch, the distance between teeth centers around the pitch circle.",
                            type=float, default=3.5)
        parser.add_argument("-wd", "--worm_diam",
                            help="The pitch diameter of the worm gear.",
                            type=float, default=8)
        parser.add_argument("-l", "--length",
                            help="Length of the worm.",
                            type=float, default=12.43)
        parser.add_argument("-ws", "--worm_starts",
                            help="Number of starts of the worm drive",
                            type=int, default=1)
        parser.add_argument("-pa", "--pressure_angle",
                            help="Controls how straight or bulged the tooth sides are. In degrees.",
                            type=float, default=29)
        parser.add_argument("-lh", "--left_handed",
                            help="Left-handed worm.",
                            action="store_true")
        parser.add_argument("-bl", "--backlash",
                            help="Backlash gap between meshing teeth.",
                            type=float, default=0)
        parser.add_argument("-cl", "--clearance",
                            help="Clearance gap at the bottom of tooth valleys.",
                            type=float, default=None)
        return parser

    def configure(self):
        Solid.configure(self)
        self.cut_tolerance = 0.3
        self.tol = self.cut_tolerance if self.isCut else 0

    def gen_worm_bosl2(self) -> Shape:
        bworm = bosl2_worm(
            circ_pitch=self.cli.circ_pitch,
            d=self.cli.worm_diam,
            starts=self.cli.worm_starts,
            l=self.cli.length,
            pressure_angle=self.cli.pressure_angle,
            left_handed=self.cli.left_handed,
            backlash=self.cli.backlash,
            clearance=self.cli.clearance,
        )
        return self.api.genShape(solid=bworm)

    def gen_worm_native(self) -> Shape:
        verts, faces = gen_worm_vnf(
            circ_pitch=self.cli.circ_pitch,
            d=self.cli.worm_diam,
            l=self.cli.length,
            starts=self.cli.worm_starts,
            left_handed=self.cli.left_handed,
            pressure_angle=self.cli.pressure_angle,
            backlash=self.cli.backlash,
            clearance=self.cli.clearance,
        )
        return self.api.polyhedron(points=verts, faces=faces)

    def gen(self) -> Shape:
        if self.cli.implementation == Implementation.SOLID2 and BOSL2_AVAILABLE:
            return self.gen_worm_bosl2()
        return self.gen_worm_native()


def main(args=None):
    """ Generate a Worm """
    return main_maker(module_name=__name__,
                class_name='Worm',
                args=args)


def test_worm(apis=None):
    tests = {
        'default': ['-refv', '640.35'],
        'l_handed': ['-lh'],
        'two_start': ['-ws', '2', '-refv', '639.37'],
    }
    test_loop(module=__name__, tests=tests, apis=apis)


def test_worm_mock():
    test_worm(apis=['mock'])


if __name__ == '__main__':
    main()
