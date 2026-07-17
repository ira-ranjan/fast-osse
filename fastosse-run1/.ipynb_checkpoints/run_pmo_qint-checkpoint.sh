
#!/bin/bash
# Usage: run_pmo_parallel.sh <SPLIT_DIR> <MAX_CONCURRENT>
set -u
 
SPLIT_DIR="$1"
MAX_CONCURRENT="${2:-128}"   # default matches qinteractive's default 32-CPU allocation
LOG_DIR="/glade/derecho/scratch/iranjan/weekly_eep_osse/pmo_logs"
OUT_DIR="/glade/derecho/scratch/iranjan/weekly_eep_osse//outputs"
mkdir -p "${LOG_DIR}" "${OUT_DIR}"
export FORT_FMT_RECL=1024
 
mapfile -t SUBDIRS < <(find "${SPLIT_DIR}" -maxdepth 1 -mindepth 1 -type d ! -name "pmo_logs" ! -name "outputs" | sort)
NN=${#SUBDIRS[@]}
echo "Found ${NN} subdirectories, running with MAX_CONCURRENT=${MAX_CONCURRENT}"
 
running=0
fail_count=0
for WORK_DIR in "${SUBDIRS[@]}"; do
    NAME=$(basename "${WORK_DIR}")
    LOG="${LOG_DIR}/${NAME}.log"
    if [ ! -f "${WORK_DIR}/perfect_model_obs" ]; then
        echo "SKIP (no executable): ${NAME}"
        continue
    fi
    if [ ! -f "${WORK_DIR}/input.nml" ]; then
        echo "SKIP (no input.nml): ${NAME}"
        continue
    fi
    (
        cd "${WORK_DIR}"
        chmod +x perfect_model_obs
        ./perfect_model_obs < /dev/null > "${LOG}" 2>&1
        if [ $? -eq 0 ] && [ -f "obs_seq.out" ]; then
            cp "obs_seq.out" "${OUT_DIR}/${NAME}_obs_seq.out"
            rm -f "${LOG_DIR}/${NAME}.failed"
        else
            echo "FAILED:  ${NAME} (see ${LOG})"
            touch "${LOG_DIR}/${NAME}.failed"
        fi
    ) &
    running=$((running + 1))
    if [ ${running} -ge ${MAX_CONCURRENT} ]; then
        wait -n
        running=$((running - 1))
    fi
done
wait
 
# Report failures with a nonzero exit code so the calling Python code
# doesn't silently proceed to join/reshape on incomplete output.
fail_count=$(find "${LOG_DIR}" -maxdepth 1 -name "*.failed" | wc -l)
echo "All done. ${fail_count} failure(s)."
exit ${fail_count}