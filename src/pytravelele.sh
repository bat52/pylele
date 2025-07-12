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
-bpiezo -ft wire --jack_hole_en -txtr 90 \
-txtl ./src/m1.svg -txtls 0.01 -txtly 10 \
--fretboard_rise_angle 0.5 \
$@ # > $LOG 
# head $LOG
