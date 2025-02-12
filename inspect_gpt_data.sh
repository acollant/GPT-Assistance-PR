#!/bin/bash

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" &&
    python3 scripts/get_chatgpt_filename.py -n &&
    python3 scripts/generate_gpt_json.py -n &&
    python3 scripts/get_gpt_inspection_data.py -n &&
    python3 scripts/exclude_no_gpt_pr.py -n &&
    python3 scripts/process_gpt_pr_phases -n &&
    echo "Finished Inspection data"
