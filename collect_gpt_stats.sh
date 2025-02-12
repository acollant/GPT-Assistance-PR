#!/bin/bash

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" &&
    python3 scripts/stats.py -n &&
    echo "Finished Stats data"
