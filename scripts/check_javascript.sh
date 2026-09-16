#!/usr/bin/env bash
set -euo pipefail

for page in account.html chat.html dashboard.html saathi.html support.html; do
  sed -n '/<script>/,/<\/script>/p' "$page" | sed '1d;$d' | node --check -
done

node --check service-worker.js
node --check theme.js
node --check workspace.js
node --check daily-workspace.js

node tests/stream_reader.cjs
node tests/voice_call.cjs

node tests/workspace_behavior.cjs
node tests/workspace_extras.cjs

node tests/daily_workspace.cjs
