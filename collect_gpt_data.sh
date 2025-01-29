#!/bin/bash

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" &&
    python3 scripts/collect_gpt_data.py -n &&
    python3 scripts/preprocess_gpt_data.py -n &&
    python3 scripts/get_gpt_events.py -n &&
    python3 scripts/process_gpt_data.py -n &&
    echo "Finished collecting data"


    # missing one exclusion