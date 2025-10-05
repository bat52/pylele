#!/usr/bin/env python3

""" Converts a .scad file into a .stl mesh """

import sys
import os
import argparse
from packaging import version

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from b13d.api.utils import wait_assert_file_exist

OPENSCAD='openscad --export-format binstl'
IMPLICITCAD='~/.cabal/bin/extopenscad'

def scad2stl_parser(parser=None):
    """
    scad2stl Command Line Interface
    """
    if parser is None:
        parser = argparse.ArgumentParser(description='scad2stl configuration')

    ## options ######################################################
    parser.add_argument("-os", "--openscad", help="openscad executable command (ignored when --implicit is selected).",
                         type=str,default=OPENSCAD)
    parser.add_argument("--implicit",
                    help="Use implicitCAD (extopenscad) as solidpython2 backend",
                    action='store_true')
    return parser


def openscad_version(command=OPENSCAD):
    """ Returns openscad version """
    tmplog = 'log.txt'
    if os.name == 'nt':
        # Windows
        cmdstr = f'{command} -v > {tmplog} 2>&1'
    else:
        # Unix/Linux/Mac
        cmdstr = f'{command} -v 2>&1 | cat > {tmplog}'
    os.system(cmdstr)

    assert os.path.isfile(tmplog), f'ERROR: file {tmplog} does not exist!'

    with open(tmplog, encoding='utf-8') as f:
        lines = f.readlines()

    # print(f'<{lines}>')
    version_str = lines[0]
    ans = version_str.split()
    # print(ans)
    ver=ans[2]
    # print(ver)

    # Remove .snap or other terminators if present
    ver_list = ver.split('.')
    ver = '.'.join(ver_list[:3])

    # print(ver)

    # remove temporary file
    os.system(f'rm {tmplog}')

    return ver

def openscad_manifold_ok(command=OPENSCAD) -> bool:
    """ check manifold available """
    # https://github.com/openscad/openscad/issues/391#issuecomment-1718145488
    ver = openscad_version(command)
    # print(ver)
    if version.parse(ver) > version.parse("2023.09"):
        return True
    return False

def openscad_manifold_opt(command=OPENSCAD) -> str:
    """ generate manifold option enable, if available """
    if command==IMPLICITCAD:
        return ''
    if openscad_manifold_ok(command):
        return '--enable=manifold'
    return ''

def assert_if_log_contains_error(file_path):
    """
    Checks if the given file contains the string 'ERROR:'.

    :param file_path: Path to the text file.
    :return: True if 'ERROR:' is found, otherwise False.
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            if "ECHO:" in line:
                print(line)
            assert not "ERROR:" in line, line

def scad2stl(infile, command=OPENSCAD, implicit = False) -> str:
    """ Converts a .scad/.csg file into a .stl mesh """
    assert os.path.isfile(infile), f'File {infile} does not exist!!!'

    fname, fext = os.path.splitext(infile)
    assert fext in ['.scad','.csg']
    fout = fname+'.stl'
    log = fname+'_openscad.log'

    if implicit:
        command = IMPLICITCAD

    manifold = openscad_manifold_opt(command=command)
    
    if os.name == 'nt':
        # Windows
        cmdstr = f'{command} {manifold} -o {fout} {infile} > {log} 2>&1'
    else:
        # Unix/Linux/Mac
        cmdstr = f'{command} {manifold} -o {fout} {infile} 2>&1 | cat > {log}'
    os.system(cmdstr)

    # make sure logfile exist
    wait_assert_file_exist(fname=log)
    assert_if_log_contains_error(log)

    wait_assert_file_exist(fname=fout)
    return fout

def scad2stl_main(args:list) -> None:
    """ Converts a .scad file into a .stl mesh """
    parser = scad2stl_parser()
    cli = parser.parse_args(args=args[1:])
    scad2stl(args[0],implicit=cli.implicit,command=cli.openscad)

if __name__ == '__main__':
    scad2stl_main(sys.argv[1:])
