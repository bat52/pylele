#!/usr/bin/env python3

"""
Converts a .stl file from binary format to ascii
Uses stl2ascii tool included with numpy-stl
"""

import sys
import os
# sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))
# from b13d.conversion.stlascii2stlbin import stl_is_bin

def stlbin2stlascii(infile,outfile='') -> str:
    """ Converts an binary .stl into a ASCII """
    assert os.path.isfile(infile), f"ERROR: Input File {infile} does not exist!"

    if True: # stl_is_bin(infile):
        if outfile=='':
            fname,fext = os.path.splitext(infile)
            outfile = f'{fname}_ascii{fext}'

        cmdstr = f'stl2ascii {infile} {outfile}'
        os.system(cmdstr)
        assert os.path.isfile(outfile), f"ERROR: Output File {outfile} does not exist!"
        return outfile

    print(f'WARNING: .stl {infile} is already in ASCII format!')
    return infile

if __name__ == '__main__':
    stlbin2stlascii(sys.argv[1])
