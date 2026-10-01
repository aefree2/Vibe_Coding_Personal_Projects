#!/usr/bin/env bash
INPUT="$1"
TOKEN="$2"

#This is going to need to be updated to actually read from the file, and based on specific values do different things
#OR, I can make the assumption that only historical things will need the timeout.
#I am currently going to work with the assumpution that only historical things will time out, because that's the only way they end up with the flag. 

for i in {1..10}; do
    echo "Run $i"
    python3 retry_timeouts.py --source $INPUT --checkpoint_file "../main_exp_sheet.csv" --token $TOKEN
done