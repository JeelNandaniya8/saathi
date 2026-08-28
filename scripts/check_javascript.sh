#!/usr/bin/env bash
set -euo pipefail

for page in account.html chat.html dashboard.html saathi.html support.html; do
  sed -n '/<script>/,/<\/script>/p' "$page" | sed '1d;$d' | node --check -
done

node --check service-worker.js
