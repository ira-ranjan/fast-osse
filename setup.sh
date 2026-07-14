#!/bin/bash
#PBS -A P93300012
#PBS -N split_output
#PBS -j oe
#PBS -q main
#PBS -l walltime=02:00:00
#PBS -l select=1:ncpus=1:mem=32gb
#PBS -J 0-NN

# ── Configuration ────────────────────────────────────────────────────────────
INPUT_DIR="/glade/derecho/scratch/iranjan/archive/EEP_MITgcm185Lvgrid_Whitt2026hgrid/ocn/hist/"
OUTPUT_DIR="/glade/derecho/scratch/iranjan/EEP-osse-1"
PYTHON_SCRIPT="/glade/work/iranjan/fast-osse/split_one_hz_file.py"
STATIC_FILE="/glade/derecho/scratch/iranjan/archive/EEP_MITgcm185Lvgrid_Whitt2026hgrid/ocn/hist/EEP_MITgcm185Lvgrid_Whitt2026hgrid.mom6.h.static.nc"
OCEAN_GEOM_FILE="/glade/derecho/scratch/iranjan/archive/EEP_MITgcm185Lvgrid_Whitt2026hgrid/ocn/hist/EEP_MITgcm185Lvgrid_Whitt2026hgrid.mom6.h.ocean_geometry.nc"
PMO_EXEC="/glade/work/iranjan/DART/models/MOM6/work/perfect_model_obs"
INPUT_NML="/glade/work/iranjan/fast-osse/input.nml"
# ─────────────────────────────────────────────────────────────────────────────

# Build array of matching files at submission time
mapfile -t FILES < <(ls ${INPUT_DIR}/*.mom6.h.z.????-??-???.nc 2>/dev/null | sort)
NN=${#FILES[@]}

if [ ${NN} -eq 0 ]; then
    echo "No h.z files found in ${INPUT_DIR}"
    exit 1
fi

# Each array job picks its file by index
FILE=${FILES[$PBS_ARRAY_INDEX]}

if [ -z "${FILE}" ]; then
    echo "No file for index ${PBS_ARRAY_INDEX}"
    exit 1
fi

echo "Array index: ${PBS_ARRAY_INDEX}"
echo "Processing file: ${FILE}"

source /glade/work/iranjan/fastosse/bin/activate

python ${PYTHON_SCRIPT} "${FILE}" "${OUTPUT_DIR}" "${STATIC_FILE}" "${OCEAN_GEOM_FILE}" "${PMO_EXEC}" "${INPUT_NML}"



