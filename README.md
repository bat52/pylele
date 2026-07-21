# Pylele

(Pronounced as "Pie-Lay-Lay")

Python based Ukulele and other Stringed Instrument 3D Model Generator similar to previous projects from Brian Guan:
* [Gugulele OpenSCAD](https://github.com/bguan/gugulele)
* [Gugulele OnShape](https://cad.onshape.com/documents/5d1958b45f2484ebebb64adf/w/d0b2164f9e843f6c6ce251e7/e/f0e54aef28e6154294039ef1?renderMode=0&uiState=664913bd22703c32bc251667)

The Pylele repository is composed of 3 subprojects:
* **pylele**: a collection of tools to design and customize ukulele and other stringed instruments. It currently targets headless instruments. Two implementations are available (pylele1 and pylele2), plus a library of reusable parts (bridge, tunable bridge, tunable saddle, worm gear, worm drive, tuner knobs, jacks, etc.) and a resonance frequency analysis module.
* **B13D**: a portable Python 3D modeling library that acts as a common wrapper around multiple backends. Also provides unit-testing, helper functions, conversion tools (scad2stl, scad2csg, stl2glb, stlascii2stlbin, stlbin2stlascii, svg2dxf), and a library of reusable 3D parts (rounded box, screw, tube, torus, pencil, etc.). The "B1" prefix is a tribute to Brian Guan who started this repository.
* **B1scad**: an OpenSCAD-to-Python transpiler based on B13D. Includes a lexer, parser, AST nodes, and symbol table for interpreting .scad files. Still VERY experimental!

Pylele ukulele generation has two main implementations:
* **pylele1**: first monolithic implementation that is no longer actively developed, and therefore (supposedly) stable
* **pylele2**: second modular implementation, actively developed with more options, some of which are a bit experimental

### pylele2 Body Types

pylele2 supports four body types:
* **GOURD** - Traditional rounded/gourd-shaped body (default)
* **FLAT** - Flat solid body (like an electric ukulele)
* **HOLLOW** - Flat body with hollow chamber
* **TRAVEL** - Compact travel-sized body

### pylele2 Named Configurations

pylele2 includes several pre-configured instrument profiles:
* `default` - Basic soprano ukulele
* `worm` - Gourd body with worm gear tuners
* `flat` - Concert-scale flat body with big worm tuners and tunable bridge
* `hollow` - Hollow body with big worm tuners
* `travel` - Travel ukulele with fat worm tuners
* `travelele` - Travelele with turnaround tuners

### Tuner Types

The following tuner configurations are available:
* **FRICTION** - Standard friction pegs
* **CHEAP** - Low-cost friction pegs
* **GOTOH** - Gotoh-style pegs
* **WORM** - Worm gear tuners
* **BIGWORM** - Larger worm gear tuners
* **FATWORM** - pylele2 worm drive with 11 teeth
* **TURNAROUND** - Turnaround (pegless) tuners
* **TURNAROUND90** - 90-degree turnaround tuners

### B13D Backends

B13D is a portable Python 3D Modeling Library that acts as a common wrapper around the following backends:

Supported:
* [Manifold3D (mf)](https://github.com/elalish/manifold) (Fastest, used by trimesh and OpenSCAD)
* [Trimesh (tm)](https://github.com/mikedh/trimesh) (Fast, supports hull)
* [CadQuery (cq)](https://github.com/CadQuery/cadquery) (Most Accurate, supports fillet)
fillet, Python 3.10 and 3.11 only)
* [SolidPython2 (sp2)](https://github.com/jeff-dh/SolidPython) (Supports .stl, .svg, .scad, and [BOSL2](https://github.com/BelfrySCAD/BOSL2) library import, fast when using manifold option)
* [PythonSCAD (ps)](https://pythonscad.org/) (Native Python OpenSCAD interpreter, supports hull, linear_extrude, rotate_extrude, offset, and projection)

Experimental (Buggy)
* [Blender (bpy)](https://github.com/blender/blender) (*Still a little buggy...*, supports 
* [build123d (bd)](https://github.com/gumyr/build123d)(Evolution of cadquery)
* [PyVista (pv)](https://github.com/pyvista/pyvista) (VTK-based 3D plotting and mesh analysis, supports boolean operations)

## GUIs

Code and view generated models in your favorite development environment!

[VSCode](https://code.visualstudio.com/download)
![image](https://github.com/bguan/pylele/assets/1054657/0a9001a3-1a84-4bf9-a439-4f9434c259a3)

[CQ-editor](https://github.com/CadQuery/CQ-editor)
![image](https://github.com/bguan/pylele/assets/1054657/6e3b11f1-08fd-4d8d-aaa9-e8e563bf0d08)

## Made With pylele
* [pytravelele](https://www.thingiverse.com/thing:7163446)
* [pegless worm gear tuners for Travelele](https://www.thingiverse.com/thing:6664561)
* [Tunable bridge for Travelele](https://www.thingiverse.com/thing:6843509)
* [Small tuner knob for Travelele](https://www.thingiverse.com/thing:6943423)

## Installation

### Simplest

Install with pip.

```
pip install git+https://github.com/bat52/pylele@main
pylele1 --help # first implementation, more stable
pylele2 --help # newer implementation, more options available
```

Trimesh and Manifold APIs are installed by default. CadQuery and build123d backends are available as optional extras (see below).

To also enable the Blender (bpy) backend on Python 3.10 or 3.11, install with the optional extras:

```
pip install git+https://github.com/bat52/pylele@main[blender]
```

To enable the CadQuery (cq) backend:

```
pip install git+https://github.com/bat52/pylele@main[cadquery]
```

To enable the build123d (bd) backend:

```
pip install git+https://github.com/bat52/pylele@main[build123d]
```

To enable the PyVista (pv) backend:

```
pip install git+https://github.com/bat52/pylele@main[pyvista]
```

To enable the PythonSCAD (ps) backend:

```
pip install git+https://github.com/bat52/pylele@main[pythonscad]
```

Multiple extras can be combined, e.g.:

```
pip install git+https://github.com/bat52/pylele@main[cadquery,build123d,blender,pythonscad]
```

### Simple (for Ubuntu/Debian)

Install on Ubuntu/Debian should be as simple as running the script:

```
  ./install_dependencies.sh
  pip install -r requirements.txt
```

This was developed on Ubuntu 22.04.4.
CI is currently testing with Python 3.10, 3.11, 3.12.

### Detailed
* Python
  * **MacOS**
    * install xcode developer tools. Using admin user account, in terminal command line shell:
      ```
      xcode-select --install
      ```
    * install Homebrew. Using admin user account, in terminal command line shell:
      ```
      > /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
      ```
    * install Python 3.11 (Blender only supports this version). Using admin user account, in terminal command line shell:
      ```
      > brew install python@3.11
      ```
    * install Virtualenv.
      ```
      > brew install virtualenv
      ```
    * create a Python 3.11 based virtual env then activate it. Using admin user account, in terminal command line shell:
      ```
      > virtualenv --python=/opt/homebrew/bin/python3.11 venv3.11
      > . venv3.11/bin/activate
      ```
* [CadQuery](https://github.com/CadQuery/cadquery)
   * ***Note***: if you ever get error messages about bool8 missing from numpy, downgrade from numpy 2.x back to numpy 1.26.4 e.g.
     ```
     > pip install --force-reinstall numpy==1.26.4
     ```
  * Linux installation of dependencies (I tried on Intel I7 Asus laptop running Ubuntu 24.04 Noble Numbat)
    * In a terminal shell inside a Python 3.11+ virtual env:
      ```
      > pip install cadquery
      > pip install PyQt5 spyder pyqtgraph logbook
      > pip install git+https://github.com/CadQuery/CQ-editor.git
      ```
  * MacOS Apple Silicon installation (I tried on M2 Macbook Air running Sonoma 14.5)
    * Due to peculiar build magic for CAD Query OCP wrapper for OCCT not yet working with pip
      (reason why CQ devs encourage using conda instead of pip, but I prefer pip for other reasons),
      I needed to download and install prebuilt wheels for cadquery_ocp and nlopt
    * In a terminal shell inside a Python 3.11+ virtual env:
      ```
      > wget https://github.com/biggestT/cadquery-dist-macos-arm64/releases/download/v0.0.1/cadquery_ocp-7.7.0.1-cp311-cp311-macosx_11_0_arm64.whl
      > wget https://github.com/biggestT/cadquery-dist-macos-arm64/releases/download/v0.0.1/nlopt-2.7.1-cp311-cp311-macosx_14_0_arm64.whl
      > pip install cadquery_ocp-7.7.0.1-cp311-cp311-macosx_11_0_arm64.whl
      > pip install nlopt-2.7.1-cp311-cp311-macosx_14_0_arm64.whl
      > pip install --force-reinstall numpy==1.26.4
      > pip install cadquery
      > pip install PyQt5 spyder pyqtgraph logbook
      > pip install git+https://github.com/CadQuery/CQ-editor.git
      ```

## Console Scripts

The following command-line tools are available after installation:

| Command | Description |
|---------|-------------|
| `pylele1` | Generate ukulele model (pylele1 implementation) |
| `pylele2` | Generate ukulele model (pylele2 implementation) |
| `stl2glb` | Convert .stl mesh to .glb format |
| `stlascii2stlbin` | Convert ASCII .stl to binary .stl |
| `stlbin2stlascii` | Convert binary .stl to ASCII .stl |
| `scad2stl` | Convert .scad file to .stl mesh (via OpenSCAD) |
| `scad2csg` | Convert .scad file to .csg representation (via OpenSCAD) |
| `b1scad` | OpenSCAD-to-Python transpiler (experimental) |

## Similar Projects
* [ukulele.scad](https://github.com/roadyyy/ukulele.scad)
* [ParamUKE](https://github.com/berkbig/ParamUKE)
