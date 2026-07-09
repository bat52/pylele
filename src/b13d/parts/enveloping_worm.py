#!/usr/bin/env python3

"""
    Enveloping Worm Solid
    Native implementation modeled after BOSL2 enveloping_worm() function
    https://github.com/BelfrySCAD/BOSL2/blob/master/gears.scad
"""

from math import sin, cos, pi, asin, tan, atan, sqrt

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from b13d.api.solid import Solid, test_loop, main_maker, Implementation
from b13d.api.core import Shape

try:
    from solid2.extensions.bosl2.gears \
import enveloping_worm as bosl2_enveloping_worm
    BOSL2_AVAILABLE = True
except ImportError:
    bosl2_enveloping_worm = None
    BOSL2_AVAILABLE = False


def _rack2d_tooth_profile(circ_pitch, pa_deg, clearance, backlash, helical):
    """Rack tooth parameters."""
    trans_pitch = circ_pitch / cos(helical)
    trans_pa = atan(tan(pa_deg * pi / 180) / cos(helical))
    mod = circ_pitch / pi
    if clearance is None:
        clearance = 0.25 * mod
    adendum = mod
    dedendum = mod + clearance
    tthick = trans_pitch / pi * (pi / 2) - backlash
    ax = adendum * tan(trans_pa)
    dx = dedendum * tan(trans_pa)
    poff = tthick / 2
    return (trans_pitch, adendum, dedendum, poff, ax, dx)


def _rack_profile_offset(y, trans_pitch, adendum, dedendum, poff, ax, dx):
    """Tooth depth at position y along the rack.
    Returns signed offset from pitch circle (positive = tooth).
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


def _lookup(x, table):
    """OpenSCAD lookup() equivalent."""
    if not table:
        return 0.0
    low_k = low_v = high_k = high_v = None
    for k, v in table:
        if k <= x:
            if low_k is None or k > low_k:
                low_k, low_v = k, v
        if k >= x:
            if high_k is None or k < high_k:
                high_k, high_v = k, v
    if low_k is None:
        return high_v
    if high_k is None:
        return low_v
    if abs(high_k - low_k) < 1e-12:
        return low_v
    return low_v + (high_v - low_v) * (x - low_k) / (high_k - low_k)


def gen_enveloping_worm_vnf(circ_pitch, mate_teeth, d, starts=1,
                              left_handed=False, pressure_angle=20,
                              backlash=0, clearance=None, arc=None,
                              gear_spin=0):
    """Generate enveloping worm VNF.

    The enveloping worm wraps around the mated gear's pitch circle.
    We generate the worm surface by sweeping tooth profiles around
    the worm axis, where the tooth depth and radius vary along the
    axis to create the hourglass / enveloping shape.
    """
    helical = asin(starts * circ_pitch / pi / d)
    (trans_pitch, adendum, dedendum, poff, ax, dx) = \
        _rack2d_tooth_profile(circ_pitch, pressure_angle, clearance, backlash, helical)

    pr = circ_pitch * mate_teeth / pi / 2 / cos(helical)

    arc_deg = arc if arc is not None else 2 * pressure_angle
    arc_half = arc_deg / 2

    hsteps = max(12, int(pi * d / (circ_pitch / 8)))
    vsteps = hsteps

    taper_table = [
        (-180.0, 0.0), (-arc_half, 0.0),
        (-arc_half * 0.85, 0.75), (-arc_half * 0.8, 0.93),
        (-arc_half * 0.75, 1.0), (arc_half * 0.75, 1.0),
        (arc_half * 0.8, 0.93), (arc_half * 0.85, 0.75),
        (arc_half, 0.0), (180.0, 0.0),
    ]

    rows = []
    for i in range(hsteps):
        u = i / hsteps
        theta = (1.0 - u) * 2 * pi

        row = []
        for j in range(vsteps):
            v = j / (vsteps - 1)
            phi = (v - 0.5) * arc_deg * pi / 180

            dist_along_rack = phi * pr
            z_rack = dist_along_rack + starts * trans_pitch * u

            h = _rack_profile_offset(z_rack, trans_pitch, adendum, dedendum,
                                      poff, ax, dx)

            taper = _lookup(phi * 180 / pi, taper_table)

            worm_radius = d / 2 + h * taper

            x = worm_radius * cos(theta)
            y = worm_radius * sin(theta)
            z = (pr + adendum) * sin(phi)

            row.append((x, y, z))

        rows.append(row)

    trows = list(zip(*rows))
    verts = []
    r = len(trows)
    c = len(trows[0])
    for ri in range(r):
        for ci in range(c):
            verts.append(trows[ri][ci])

    faces = []
    for ri in range(r - 1):
        for ci in range(c):
            c_next = (ci + 1) % c
            a = ri * c + ci
            b = ri * c + c_next
            d2 = (ri + 1) * c + ci
            e = (ri + 1) * c + c_next
            faces.append([a, b, e])
            faces.append([e, d2, a])

    zs = [v[2] for v in verts]
    zmin = min(zs)
    zmax = max(zs)

    bot_cap = len(verts)
    verts.append((0, 0, zmin))
    for ci in range(c):
        c_next = (ci + 1) % c
        faces.append([c_next, ci, bot_cap])

    top_cap = len(verts)
    verts.append((0, 0, zmax))
    for ci in range(c):
        c_next = (ci + 1) % c
        a = (r - 1) * c + ci
        b = (r - 1) * c + c_next
        faces.append([a, b, top_cap])

    if not left_handed:
        verts = [(x, -y, z) for x, y, z in verts]

    if gear_spin != 0:
        sa = gear_spin * pi / 180
        csa, ssa = cos(sa), sin(sa)
        verts = [(x * csa - y * ssa, x * ssa + y * csa, z) for x, y, z in verts]

    return verts, faces


class EnvelopingWorm(Solid):
    """ Generate an Enveloping Worm """

    def gen_parser(self, parser=None):
        parser = super().gen_parser(parser=parser)
        parser.add_argument("-cp", "--circ_pitch",
                            help="Circular pitch",
                            type=float, default=3.5)
        parser.add_argument("-wd", "--worm_diam",
                            help="Worm pitch diameter at middle",
                            type=float, default=8)
        parser.add_argument("-ws", "--worm_starts",
                            help="Number of starts",
                            type=int, default=1)
        parser.add_argument("-pa", "--pressure_angle",
                            help="Pressure angle in degrees",
                            type=float, default=29)
        parser.add_argument("-mt", "--mate_teeth",
                            help="Number of teeth of the mated worm gear",
                            type=int, default=14)
        parser.add_argument("-bl", "--backlash",
                            help="Backlash gap",
                            type=float, default=0)
        parser.add_argument("-cl", "--clearance",
                            help="Clearance gap",
                            type=float, default=None)
        parser.add_argument("-ar", "--arc",
                            help="Arc angle of mated gear to envelop, degrees",
                            type=float, default=None)
        parser.add_argument("-gs", "--gear_spin",
                            help="Rotational offset, degrees",
                            type=float, default=0)
        parser.add_argument("-lh", "--left_handed",
                            help="Left-handed worm",
                            action="store_true")
        return parser

    def configure(self):
        Solid.configure(self)

    def gen_enveloping_worm_bosl2(self) -> Shape:
        bworm = bosl2_enveloping_worm(
            circ_pitch=self.cli.circ_pitch,
            mate_teeth=self.cli.mate_teeth,
            d=self.cli.worm_diam,
            starts=self.cli.worm_starts,
            pressure_angle=self.cli.pressure_angle,
            arc=self.cli.arc,
            left_handed=self.cli.left_handed,
            backlash=self.cli.backlash,
            clearance=self.cli.clearance,
            gear_spin=self.cli.gear_spin,
        )
        return self.api.genShape(solid=bworm)

    def gen_enveloping_worm_native(self) -> Shape:
        verts, faces = gen_enveloping_worm_vnf(
            circ_pitch=self.cli.circ_pitch,
            mate_teeth=self.cli.mate_teeth,
            d=self.cli.worm_diam,
            starts=self.cli.worm_starts,
            pressure_angle=self.cli.pressure_angle,
            backlash=self.cli.backlash,
            clearance=self.cli.clearance,
            arc=self.cli.arc,
            gear_spin=self.cli.gear_spin,
        )
        return self.api.polyhedron(points=verts, faces=faces)

    def gen(self) -> Shape:
        if self.cli.implementation == Implementation.SOLID2 and BOSL2_AVAILABLE:
            return self.gen_enveloping_worm_bosl2()
        return self.gen_enveloping_worm_native()


def main(args=None):
    """ Generate an Enveloping Worm """
    return main_maker(module_name=__name__,
                class_name='EnvelopingWorm',
                args=args)


def test_enveloping_worm(self=None, apis=None):
    tests = {
        'default': ['-refv', '448.39'],
        'two_start': ['-ws', '2', '-refv', '460.08'],
    }
    test_loop(module=__name__, tests=tests, apis=apis)


def test_enveloping_worm_mock(self=None):
    test_enveloping_worm(self,apis=['mock'])


if __name__ == '__main__':
    main()
