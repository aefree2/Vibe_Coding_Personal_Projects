#!/bin/bash
source config.conf #may change to a safer pattern later
cd make_experiment/
# INPUT="$1"
# TOKEN="$2"
# HISTORY="$3"
# CURR_DATE="$4"
# HIST_DATE="$5"

for i in "${!SUB_NAMES[@]}"; do
    echo "${SUB_NAMES[i]} - History ${HISTORY[i]}"
    bash make_git.sh ${SUB_NAMES[i]} $TOKEN False ${CUTOFF_DATE[i]} ${EXPERIMENT_DATE[i]}
    #${HISTORY[i]}
done

bash make_dataset.sh