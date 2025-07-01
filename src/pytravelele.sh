#!/usr/bin/env bash
# This script is used to run the pylele2.sh script with specific options for the travelele configuration.

SCRIPT_DIR=$(dirname "$(realpath "${BASH_SOURCE[0]}")")
# LOG=pylele.log
python3 $SCRIPT_DIR/pylele/pylele2/all_assembly.py \
-cfg travelele -N -FB -T -F -B -bpiezo -NU -FR -D -ft wire -E -HT -RIM -jhe $@ # > $LOG 
# head $LOG
