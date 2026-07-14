#!/bin/bash
# submit_pmo_array.sh — run on login node to submit the job array

SPLIT_DIR="/glade/derecho/scratch/iranjan/EEP-osse-1/"
JOB_SCRIPT="run_pmo_array.pbs"

# Count subdirectories
mapfile -t SUBDIRS < <(find ${SPLIT_DIR} -maxdepth 1 -mindepth 1 -type d | sort)
NN=${#SUBDIRS[@]}

if [ ${NN} -eq 0 ]; then
    echo "No subdirectories found in ${SPLIT_DIR}"
    exit 1
fi

echo "Found ${NN} subdirectories, submitting job array 0-$((NN-1))"
sed "s|NN|$((NN-1))|g" ${JOB_SCRIPT} > run_pmo_array_submit.pbs
qsub run_pmo_array_submit.pbs