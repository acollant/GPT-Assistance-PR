#!/bin/bash

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" &&
    echo "search gpt" &&
    python3 scripts/search_gpt.py -n &&
    echo "collect participants gpt" &&
    python3 scripts/collect_participants.py -n &&
    echo "apply_filters" &&
    python3 scripts/apply_filters.py -n &&
    echo "Finished downloading data"


    # missing one exclusion