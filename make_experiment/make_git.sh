


#!/usr/bin/env bash
#!/usr/bin/env bash
set -euo pipefail

INPUT="$1"
TOKEN="$2"
HISTORY="$3"
CURR_DATE="$4"
HIST_DATE="$5"


GOOD="../dataset_features/${1}_good_links.txt"
BAD="../dataset_features/${1}_bad_links.txt"
ALL="../dataset_features/${1}_seen_links.txt"
CHECKPOINT="../dataset_features/${1}_checkpoint.txt"
TIMING="../dataset_features/${1}_times.txt"



mkdir -p ../dataset_features
touch "$GOOD" "$BAD" "$ALL" "$TIMING"

resume_mode=1
last_url=""

# If checkpoint exists, resume after that URL
if [[ -f "$CHECKPOINT" ]]; then
    last_url=$(cat "$CHECKPOINT")
    resume_mode=0
    echo "Resuming after: $last_url"
fi

starts=$(date +%s)


while IFS= read -r url || [[ -n "$url" ]]; do

    url=${url%$'\r'}
    [[ -z "$url" ]] && continue

    start=$(date +%s)

    # Skip until checkpoint URL is reached
    if [[ "$resume_mode" -eq 0 ]]; then
        if [[ "$url" == "$last_url" ]]; then
            resume_mode=1
        fi
        continue
    fi

    repo=$(echo "$url" | sed -E 's#https://github.com/([^/]+/[^/]+).*#\1#')

    status=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: token $TOKEN" \
        -H "User-Agent: repo-checker" \
        -H "Accept: application/vnd.github+json" \
        "https://api.github.com/repos/$repo")

    if [[ "$status" == "200"  ||  "$status" == "301" ]]; then

        python3 find_history.py \
            --url "$url" \
            --experiment_name "$1" \
            --checkpoint_file "../main_exp_sheet.csv" \
            --token "$TOKEN" \
            --before_date "$HIST_DATE"\
            --current_date "$CURR_DATE"\
            --history "$HISTORY"

        echo "$url" >> "$GOOD"
        echo "GOOD"
        end=$(date +%s)

        runtime=$((end - start))
        echo "Program ${url}: ${runtime} seconds" >> "$TIMING"

    else
        echo "$url", "$status" >> "$BAD"
        echo "BAD ($status)"
    fi

    echo "$url" >> "$ALL"

    # checkpoint after every URL
    echo "$url" > "$CHECKPOINT"

    sleep 0.2

done < ../dataset_features/$1\_github.txt

end=$(date +%s)
runtime=$((end - starts))
echo "Total time: ${runtime} seconds" >> "$TIMING"

echo "Finished."
echo "Good links saved to $GOOD"
echo "Bad links saved to $BAD"
if [[ "$HISTORY" == "True" ]]; then
    echo "Retrying timed out experiments."
    starts=$(date +%s)
    bash retry_timeouts.sh $INPUT $TOKEN
    end=$(date +%s)
    runtime=$((end - starts))
    echo "Retry Time: ${runtime} seconds" >> "$TIMING"
fi
