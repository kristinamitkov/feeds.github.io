#!/usr/bin/env bash

INIT=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --init)
            INIT=true
            shift
            ;;
    esac
done

python database.py --init --prune

while IFS=',' read -r arg1 arg2 arg3; do
    echo "Processing $arg1 $arg2 $arg3"

    if [ "$INIT" = true ]; then
        python database.py --title "$arg1" --url "$arg2"
        if [ -n "$arg3" ] && [[ "$arg3" =~ \.csv$ ]]; then
            python database.py --import "data/$arg3" || true
        fi
    else
        if [ -n "$arg3" ]; then
            if [[ "$arg3" =~ \.csv$ ]]; then
                python database.py --url "$arg2" --export "data/$arg3" || true
            fi
            git add -f "data/$arg3" || true
        fi
    fi

done < "scrape.txt"
