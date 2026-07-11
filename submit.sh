#!/bin/bash


INPUT_DIR="/glade/derecho/scratch/iranjan/archive/EEP_MITgcm185Lvgrid_Whitt2026hgrid/ocn/hist/" # directory containing mom6.h.z. files
JOB_SCRIPT="setup.sh" # bash script which calls python script for splitting files

NN=$(ls ${INPUT_DIR}/*.mom6.h.z.????-??-???.nc 2>/dev/null | wc -l) # NN = number of mom6.h.z files

if [ "${NN}" -eq 0 ]; then
    echo "No h.z files found in ${INPUT_DIR}"
    exit 1
fi

echo "Found ${NN} files, submitting job array 0-$((NN-1))"
sed "s/NN/$((NN-1))/" ${JOB_SCRIPT} > ${JOB_SCRIPT%.sh}_submit.sh # replaces NN with actual number
qsub ${JOB_SCRIPT%.sh}_submit.sh #submits the main script