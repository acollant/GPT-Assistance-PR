#!/bin/bash

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" &&
    python3 scripts/get_gpt_pr_distance.py -n &&
    python3 scripts/collect_gpt_pr_stats.py -n && 
    echo "Finished Stats data"
