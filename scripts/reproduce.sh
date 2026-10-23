#!/usr/bin/env bash
set -euo pipefail

# All versions in both arms are frozen before either independent readout.
experiment_root="${1:?Usage: scripts/reproduce.sh NEW_EXPERIMENT_DIRECTORY}"
moltweave evolve --output "$experiment_root/joint" --generations 4
moltweave evolve --output "$experiment_root/frozen-p" --generations 4 --freeze-p
moltweave evaluate --experiment "$experiment_root/joint"
moltweave evaluate --experiment "$experiment_root/frozen-p"
moltweave report --experiment "$experiment_root/joint"
moltweave report --experiment "$experiment_root/frozen-p"
