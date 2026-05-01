#!/usr/bin/env bash
# github-urls.sh — Show GitHub URLs for recently changed files
# Usage:
#   github-urls.sh        → Top 5 recently changed files (default)
#   github-urls.sh 10     → Top 10 recently changed files
#   github-urls.sh --pr N → Specific PR
#   github-urls.sh <sha>  → Specific commit
set -euo pipefail

# Repo info (single call)
REMOTE_URL=$(git remote get-url origin 2>/dev/null)
OWNER_REPO=$(echo "$REMOTE_URL" | sed -E 's|.*github\.com[:/]||; s|\.git$||')
DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null \
  | sed 's|refs/remotes/origin/||' || echo "main")
BASE_URL="https://github.com/${OWNER_REPO}/blob/${DEFAULT_BRANCH}"

# Parse args
ARG1="${1:-}"
ARG2="${2:-}"
MODE="count"
COUNT=5
COMMIT_SHA=""
LABEL=""

if [[ -z "$ARG1" ]]; then
  MODE="count"; COUNT=5
elif [[ "$ARG1" =~ ^[0-9]+$ ]]; then
  MODE="count"; COUNT="$ARG1"
elif [[ "$ARG1" == "--pr" && -n "$ARG2" ]]; then
  MODE="commit"
  COMMIT_SHA=$(gh pr view "$ARG2" --json mergeCommit --jq '.mergeCommit.oid')
  LABEL="PR #${ARG2}"
elif [[ ! "$ARG1" =~ ^- ]]; then
  MODE="commit"; COMMIT_SHA="$ARG1"
  LABEL="Commit ${ARG1:0:7}"
fi

# ── COUNT MODE ───────────────────────────────────────────────────────────────
if [[ "$MODE" == "count" ]]; then
  declare -A SEEN
  FILES=()   # "STATUS\tFILE\tDATE"
  current_date=""

  # Single git log pass: format line + name-status lines interleaved
  while IFS= read -r line; do
    if [[ "$line" == DATE:* ]]; then
      current_date="${line#DATE:}"
    elif [[ "${line:0:1}" == "A" || "${line:0:1}" == "M" ]] \
      && [[ "${line:1:1}" == $'\t' ]]; then
      status="${line:0:1}"
      filepath="${line:2}"
      if [[ -z "${SEEN["$filepath"]+_}" ]]; then
        SEEN["$filepath"]=1
        FILES+=("${status}"$'\t'"${filepath}"$'\t'"${current_date}")
        [[ ${#FILES[@]} -ge $COUNT ]] && break
      fi
    fi
  done < <(git log --format="DATE:%ad" --date=short --name-status --diff-filter=AM --)

  # Output
  echo "## GitHub URLs — Top ${COUNT} Recently Changed Files"
  echo ""
  echo "---"
  echo ""

  if [[ ${#FILES[@]} -eq 0 ]]; then
    echo "No changed files found."
    exit 0
  fi

  for entry in "${FILES[@]}"; do
    IFS=$'\t' read -r status filepath date <<< "$entry"
    [[ "$status" == "A" ]] && badge="Added" || badge="Modified"
    echo "\`${filepath}\` · ${badge} · ${date}"
    echo "${BASE_URL}/${filepath}"
    echo ""
  done

  echo "---"
  echo "Total ${#FILES[@]} files"

# ── COMMIT MODE ──────────────────────────────────────────────────────────────
else
  SHA=$(git log -1 --format="%H" "$COMMIT_SHA")
  SHORT_SHA="${SHA:0:7}"
  DATE=$(git log -1 --format="%ad" --date=short "$COMMIT_SHA")
  TITLE=$(git log -1 --format="%s" "$COMMIT_SHA")
  [[ -z "$LABEL" ]] && LABEL="Commit ${SHORT_SHA}"

  # Single diff call
  declare -A FILE_STATUS
  while IFS=$'\t' read -r status filepath; do
    [[ "${status:0:1}" =~ ^[AM]$ && -n "$filepath" ]] || continue
    FILE_STATUS["$filepath"]="${status:0:1}"
  done < <(
    if git rev-parse "${COMMIT_SHA}^2" &>/dev/null; then
      git diff "${COMMIT_SHA}^1" "${COMMIT_SHA}" --name-status --diff-filter=AM
    else
      git diff-tree --no-commit-id -r --name-status --diff-filter=AM "$COMMIT_SHA"
    fi
  )

  echo "## GitHub URLs — ${LABEL}"
  echo ""
  echo "> ${TITLE}"
  echo "> \`${SHORT_SHA}\` · ${DATE}"
  echo ""
  echo "---"
  echo ""

  ADDED=(); MODIFIED=()
  for f in "${!FILE_STATUS[@]}"; do
    [[ "${FILE_STATUS[$f]}" == "A" ]] && ADDED+=("$f") || MODIFIED+=("$f")
  done
  IFS=$'\n' ADDED=($(sort <<<"${ADDED[*]+"${ADDED[*]}"}")); unset IFS
  IFS=$'\n' MODIFIED=($(sort <<<"${MODIFIED[*]+"${MODIFIED[*]}"}")); unset IFS

  TOTAL=$(( ${#ADDED[@]} + ${#MODIFIED[@]} ))
  if [[ $TOTAL -eq 0 ]]; then
    echo "No changed files found."
    exit 0
  fi

  if [[ ${#ADDED[@]} -gt 0 ]]; then
    echo "### Added (${#ADDED[@]})"
    echo ""
    for f in "${ADDED[@]}"; do
      echo "\`${f}\` · ${DATE}"
      echo "${BASE_URL}/${f}"
      echo ""
    done
    echo "---"
    echo ""
  fi

  if [[ ${#MODIFIED[@]} -gt 0 ]]; then
    echo "### Modified (${#MODIFIED[@]})"
    echo ""
    for f in "${MODIFIED[@]}"; do
      echo "\`${f}\` · ${DATE}"
      echo "${BASE_URL}/${f}"
      echo ""
    done
    echo "---"
    echo ""
  fi

  echo "Total ${TOTAL} files (Added ${#ADDED[@]}, Modified ${#MODIFIED[@]})"
fi
