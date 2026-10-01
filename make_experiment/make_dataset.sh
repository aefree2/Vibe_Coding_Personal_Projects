#!/usr/bin/env bash
set -euo pipefail

OK_LOG="cloned_ok.txt"
FAIL_LOG="cloned_fail.txt"
NAMES=("SideProject" "Vibecoding")
PYLINT_LOG="../dataset_features/pylint.json" 

python3 clean_data_sheet.py --names "${NAMES[@]}" 

to_ssh() {
  local u="${1%$'\r'}"
  u="${u%.git}"
  if [[ "$u" =~ ^https?://github\.com/([^/]+)/([^/]+)$ ]]; then
    printf 'git@github.com:%s/%s.git\n' "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}"
  else
    printf '%s\n' "$u"
  fi
}

resume_mode=1
last_done=""

if [[ -f "$OK_LOG" && -s "$OK_LOG" ]]; then
  last_done="$(tail -n 1 "$OK_LOG")"
  resume_mode=0
  echo "Resuming after: $last_done"
fi

while IFS=, read -r col1 col2; do
    col1="${col1%$'\r'}"
    col2="${col2%$'\r'}"

    [[ -z "$col1" ]] && continue

    if [[ "$resume_mode" -eq 0 ]]; then
        if [[ "$col1" == "$last_done" ]]; then
            resume_mode=1
        fi
        continue
    fi

    echo "I got: $col1|$col2"
    short_name=$(echo "$col1" | cut -d '/' -f5)
    printf 'URL=%q\n' "$col1"

    if git clone "$(to_ssh "$col1")"; then
        echo "$col1" >> "$OK_LOG"

        cd "$short_name"
        if git checkout "$col2"; then
          cd ..
          python3 make_dataset.py --file_name "$short_name" --url "$col1" --commit "$col2"
          echo "starting pylint"
          echo "Linting: '$short_name'"

          set +e
          pylint "$short_name" --output-format=json \
              < /dev/null \
              >> "$PYLINT_LOG" \
              2>> "pylint_err.txt"
          pylint_status=$?
          set -e

          echo "Pylint exit code: $pylint_status" >> "pylint_err.txt"
          echo "ending pylint"
                  else
          cd ..
          echo "$col1" >> "$FAIL_LOG"
        fi

        echo "deleting now"
        rm -r "$short_name"
    else
        echo "$col1" >> "$FAIL_LOG"
    fi

    sleep 5
done < ../dataset_features/new_csv.csv #remember to make this a comand line argument