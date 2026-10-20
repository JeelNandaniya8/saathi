# Student workspace frontend

Dashboard, Chat, Notes and Planner retain the existing Flask pages and vanilla JavaScript controllers. The supplied conversation screenshot guides the visual system: a quiet sidebar, open reading area, right-aligned user bubbles and a compact rounded composer. Saathi keeps its own name, icons, providers and existing features.

`study-desk.css` owns the reference-based composition and semantic light/dark colours. `workspace-hub.css` retains the shared tool controls. The signed-in pages load a versioned stylesheet URL. Theme selection continues through the existing appearance preference.

Dashboard uses a full-width focus section above the returned plan, a reminder/conversation rail and compact tool shortcuts. Task completion retains a separate 44px control and the existing pending/error states. Focus is derived from returned account data; no progress or saved object is invented.

Dashboard and Chat use the existing `saathi-icon.svg` brand asset. Chat history and its toggle are on the right; the mobile drawer opens from that same edge.

Chat uses an open assistant reading area and right-aligned user bubbles. Author labels remain available to assistive technology. Empty and active conversations share one actual composer; it is never cloned or moved. Drafts, files, file-only selection, modes, quotas, streaming, Stop and retries stay connected to their existing controllers. Starting points prepare and persist a draft without sending a request. Short viewports retain the scrolling conversation arrangement.

Notes and Planner use the same neutral surfaces, typography and controls. Notes retains version checks, read-back and draft recovery. Planner retains its forms, handlers and mobile list-before-form order. Native scripts, larger-text preferences and reduced motion remain supported.

## Verification

```sh
bash scripts/check_javascript.sh
NODE_PATH=/tmp/saathi-browser-tests/node_modules node tests/workspace_browser.cjs
SAATHI_UI_REVIEW=1 SAATHI_UI_ARTIFACTS=artifacts/ui \
  NODE_PATH=/tmp/saathi-browser-tests/node_modules node tests/workspace_browser.cjs
```

Chromium fixtures cover 1280, 768, 390, 360 and 320px; all 13 workspace views; light/dark contrast; EN/GU/HI labels; native heading typography; a 520px-high chat viewport; sidebar reopening; and the relative position of the one composer and its starting points. Existing controller suites cover task/note save races, exact retries, cancellation, allowance states and verified receipt destinations.

Fixtures use synthetic responses and block external browser requests. These checks do not establish physical-device keyboard/upload behaviour, live AI recovery, Classroom availability, reminder delivery, production success rate or first-word latency. This UI change makes no new claim about those acceptance gates.
