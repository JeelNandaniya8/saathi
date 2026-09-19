#!/usr/bin/env bash
set -euo pipefail

for page in account.html chat.html dashboard.html saathi.html support.html; do
  sed -n '/<script>/,/<\/script>/p' "$page" | sed '1d;$d' | node --check -
done

node --check service-worker.js
node --check theme.js
node --check workspace.js
node --check recovery.js
node --check daily-workspace.js
for script in workspace-hub.js i18n.js locale-gu.js lazy-tools.js dashboard-study.js dashboard-mindmaps.js dashboard-care.js; do node --check "$script"; done

node tests/stream_reader.cjs
node tests/voice_call.cjs

node tests/workspace_behavior.cjs
node tests/workspace_extras.cjs

node tests/daily_workspace.cjs
node tests/recovery.cjs
node tests/chat_recovery.cjs
node tests/chat_editing.cjs
