# Student workspace frontend

The post-login Dashboard, Chat, Notes and Planner use the existing Flask pages and vanilla JavaScript controllers. No packages, build process, API endpoints, schema changes or provider calls are added.

- `workspace-hub.css` contains shared semantic colours, typography, controls and responsive compositions. Dark mode, reduced motion, native scripts and large-text preferences remain supported.
- `dashboard.html` composes the returned Today tasks, reminder and recent conversation. The focus action uses the first returned task; an empty response opens Planner instead. No completion percentage or saved object is invented.
- `chat.html` retains the streaming, cancellation, attachments, file-only selection, quota and retry controllers.
- `workspace.js` retains the account-owned Notes editor, version checks and draft recovery. Opening Notes focuses its heading; choosing New note explicitly focuses its title.
- Planner retains its existing forms and handlers. Its list precedes the creation form on phones; Add task focuses that form. Mobile navigation tracks the current workspace view.

Modified CSS, JavaScript and language catalogs have versioned asset URLs for existing service-worker caches.

The Dashboard groups revision and timer actions into one support surface. Task completion has an individually named 44px control; its pending state ends when the request settles. Chat presents three study starting points and two secondary actions on both desktop and mobile. A starting point prepares a draft, preserves existing writing and only selects modes actually returned for the account. The loading skeleton includes visible translated status text. Shared warm surface and accent tokens also cover dark mode.

## Verification

```sh
bash scripts/check_javascript.sh
NODE_PATH=/tmp/saathi-browser-tests/node_modules node tests/workspace_browser.cjs
SAATHI_UI_REVIEW=1 SAATHI_UI_ARTIFACTS=artifacts/ui \
  NODE_PATH=/tmp/saathi-browser-tests/node_modules node tests/workspace_browser.cjs
```

The browser suites cover 1280, 768, 390, 360 and 320px. UI checks include light/dark contrast, all 13 retained workspace views, real note-controller save and reopen through isolated versioned API fixtures, focus-task selection, mobile navigation, EN/GU/HI labels and a 520px-high chat viewport. Additional cases exercise pending/failed task completion, visible native loading states, every empty-chat starting point, protected drafts and unavailable modes in both themes. Existing controller regressions cover exact retries, Stop, receipt destinations and note/task save races.

Fixtures are synthetic and external browser requests are blocked. These checks do not establish physical-device keyboard behaviour, live AI recovery, Classroom availability, reminder delivery, production success rate or first-word latency. This frontend change makes no new claim about those acceptance gates.
