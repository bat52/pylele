#!/usr/bin/env bash
# This script is used to run the pylele2.sh script with specific options for the travelele configuration.

SCRIPT_DIR=$(dirname "$(realpath "${BASH_SOURCE[0]}")")
# LOG=pylele.log
# 
python3 $SCRIPT_DIR/pylele/pylele2/all_assembly.py \
-cfg travelele \
--separate_fretboard --separate_head_top --separate_neck \
--separate_frets --separate_dots --separate_nut \
--separate_top --separate_bottom --separate_bridge \
--separate_end --separate_rim \
-bpiezo -ft wire --jack_hole_en \
--text_rotation 270 --text_logo ./src/m1.svg --text_logo_scale 0.01 --text_logo_y 10 \
--fretboard_rise_angle 0.5 \
$@ # > $LOG 
# head $LOG

# tuners: drive
TEETH=11
COMMON_TUNERS_ARGS="-mirror --teeth $TEETH"
python3 $SCRIPT_DIR/pylele/parts/worm_drive.py ${COMMON_TUNERS_ARGS} $@

# tuners: gear
python3 $SCRIPT_DIR/pylele/parts/worm_gear.py ${COMMON_TUNERS_ARGS} \
--carved_gear --friction_shaft_enable \
$@

# tuners: holder
python3 $SCRIPT_DIR/pylele/parts/worm_gear_holder.py ${COMMON_TUNERS_ARGS} \
$@
