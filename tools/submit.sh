#!/bin/bash
# submit.sh - send one submission folder to GitHub with one command (for the maintainer).
#
#   tools/submit.sh <slug> ["commit message"]
#
# From anywhere inside the repository. It updates main (git pull --ff-only), then:
#   - a folder with claims.csv, constructions.csv or certificates.csv is committed on main and
#     pushed; table-page.yml (and certificate-check.yml for certificates) enter it;
#   - a folder with upgrade.csv must come in as a pull request (submissions/README.md), so it is
#     committed on a branch submit-<slug>, pushed, and the script prints the link to open the
#     pull request, then returns to main.
# Only submissions/<slug> is added. It stops if anything else is staged, if the folder does not
# exist, or if git reports an error. Works with the bash 3.2 of macOS.
set -euo pipefail
slug="${1:-}"
msg="${2:-}"
if [ -z "$slug" ]; then echo "usage: tools/submit.sh <slug> [\"commit message\"]" >&2; exit 2; fi
case "$slug" in *[!A-Za-z0-9._-]*) echo "bad folder name: $slug" >&2; exit 2 ;; esac
cd "$(git rev-parse --show-toplevel)"
dir="submissions/$slug"
[ -d "$dir" ] || { echo "no folder $dir" >&2; exit 1; }
branch=$(git rev-parse --abbrev-ref HEAD)
[ "$branch" = "main" ] || { echo "switch to main first (you are on $branch)" >&2; exit 1; }
if ! git diff --cached --quiet; then echo "something else is staged; commit or unstage it first" >&2; exit 1; fi
git pull --ff-only
[ -n "$msg" ] || msg="Submission $slug"
if [ -f "$dir/upgrade.csv" ]; then
  b="submit-$slug"
  git checkout -b "$b"
  git add "$dir"
  git commit -m "$msg"
  git push -u origin "$b"
  git checkout main
  url=$(git remote get-url origin | sed -e 's#^git@github.com:#https://github.com/#' -e 's#\.git$##')
  echo
  echo "Pushed branch $b. Open the pull request: $url/compare/$b?expand=1"
else
  git add "$dir"
  if git diff --cached --quiet; then echo "nothing new in $dir (already committed?)"; exit 0; fi
  git commit -m "$msg"
  git push
  echo
  echo "Pushed $dir to main. The table bot enters it in a few minutes."
fi
