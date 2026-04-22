#!/usr/bin/env bash

while IFS=',' read -r arg1 arg2 arg3; do
    echo "Processing: $arg1 | $arg2 | $arg3"

    python database.py "$arg1" "$arg2"
    git add -f "data/$arg3"

done < "scrape.txt"
