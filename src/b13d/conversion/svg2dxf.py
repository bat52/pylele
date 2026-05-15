#!/usr/bin/env python3

"""
Converts a .svg file to .dxf
"""

import sys
import os
import shutil

# Check availability at module load time
SVG2DXF_AVAILABLE = shutil.which('svg2dxf') is not None

def _check_svg2dxf_available():
    """Check if svg2dxf CLI is available. Uses cached result."""
    return SVG2DXF_AVAILABLE

def svg2dxf_wrapper(infile, outfile='') -> str:
    """ Converts an SVG file to a DXF file """
    if not _check_svg2dxf_available():
        raise RuntimeError(
            "svg2dxf CLI tool not available. "
            "Install the svg2dxf extra with: pip install pylele[svg2dxf]"
        )
    
    assert os.path.isfile(infile), f"ERROR: Input File {infile} does not exist!"

    if outfile=='':
        fname,fext = os.path.splitext(infile)
        outfile = f'{fname}.dxf'

    # Ensure the output directory exists
    outdir = os.path.dirname(outfile)
    if outdir and not os.path.isdir(outdir):
        os.makedirs(outdir, exist_ok=True)

    cmdstr = f'svg2dxf {infile} -o {outfile}'
    ret = os.system(cmdstr)
    if ret != 0:
        raise RuntimeError(
            f"svg2dxf command failed with exit code {ret}: {cmdstr}"
        )
    assert os.path.isfile(outfile), f"ERROR: Output File {outfile} does not exist!"
    return outfile

if __name__ == '__main__':
    svg2dxf_wrapper(sys.argv[1])