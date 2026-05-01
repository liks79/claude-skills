#!/usr/bin/env bash
# recent.sh — Show most recently created or updated files in the repository
# Usage:
#   recent.sh        → Top 10 recent files (default)
#   recent.sh 20     → Top 20 recent files
set -eu

COUNT="${1:-10}"
if ! [[ "$COUNT" =~ ^[0-9]+$ ]]; then
  echo "Usage: recent.sh [N]  (N: number of files to show, default 10)" >&2
  exit 1
fi

REPO_ROOT=$(git rev-parse --show-toplevel)

# List git-tracked files sorted by modification time descending, extract top COUNT
mapfile -t FILES < <(
  git -C "$REPO_ROOT" ls-files -z \
    | xargs -0 stat --format="%Y %n" 2>/dev/null \
    | sort -rn \
    | awk -v n="$COUNT" 'NR<=n {print $2}'
)

echo "## Top ${COUNT} Recent Files (by Date)"
echo ""

current_date=""
for filepath in "${FILES[@]}"; do
  epoch=$(stat --format="%Y" "$REPO_ROOT/$filepath" 2>/dev/null || echo 0)
  date_day=$(date -d "@${epoch}" "+%Y-%m-%d" 2>/dev/null \
             || date -r "$epoch" "+%Y-%m-%d" 2>/dev/null \
             || echo "unknown")
  time_str=$(date -d "@${epoch}" "+%H:%M" 2>/dev/null \
             || date -r "$epoch" "+%H:%M" 2>/dev/null \
             || echo "??:??")

  if [[ "$date_day" != "$current_date" ]]; then
    [[ -n "$current_date" ]] && echo ""
    echo "### 📅 ${date_day}"
    current_date="$date_day"
  fi

  echo "• \`${filepath}\` · ${time_str}"
done

echo ""
echo "---"
echo "Showing ${#FILES[@]} files (sorted by modification time descending)"
