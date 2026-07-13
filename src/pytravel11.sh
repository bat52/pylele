#!/usr/bin/env bash
# This script is used to run the pylele2.sh script with specific options for the travel11 configuration.

SCRIPT_DIR=$(dirname "$(realpath "${BASH_SOURCE[0]}")")

python3 $SCRIPT_DIR/pylele/pylele2/all_assembly.py \
-cfg travel11 \
-bpiezo -ft wire --jack_hole_en \
--fretboard_rise_angle 0.5 \
--show_tuners --no_text \
--separate_end \
$@
# --separate_end \
# --text_rotation 270 --text_logo ./src/m1.svg --text_logo_scale 0.01 --text_logo_y 10 \
# --separate_fretboard --separate_head_top --separate_neck \
# --separate_frets --separate_dots --separate_nut \
# --separate_top --separate_bottom --separate_bridge \
# --separate_rim \

# tuners: drive
# TEETH=11
# COMMON_TUNERS_ARGS="--teeth $TEETH"
# python3 $SCRIPT_DIR/pylele/parts/worm_drive.py -mirror ${COMMON_TUNERS_ARGS} $@

# tuners: gear
# python3 $SCRIPT_DIR/pylele/parts/worm_gear.py -mirror ${COMMON_TUNERS_ARGS} \
# --carved_gear --minkowski_en --concealed_worm -C \
# $@
