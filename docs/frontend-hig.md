# Saathi frontend redesign

Scope: dashboard, conversation workspace, landing, account and public reading/support pages. Backend, API routes, database and Render configuration unchanged. Existing creator profile retained.

## Before audit (1 poor, 5 strong)

| Principle | Score | Evidence |
|---|---:|---|
| Clarity | 2 | 9–13px control labels; greeting changes after profile fetch; chat welcome flashes before history. |
| Deference | 2 | Gradient hero, tinted cards and repeated shadows compete with content. |
| Depth | 2 | Floating microphone overlaps navigation; nested translucent surfaces. |
| Consistency | 2 | Different control sizes; right chat navigation versus left dashboard navigation; mobile hides Dashboard/Sounds. |
| Accessibility | 2 | Several targets below 44px; small fixed type; inconsistent focus styling. |

## Priorities implemented

High: stable profile/chat loading placeholders; voice control in composer; consistent visible Dashboard/Sounds controls; 44px minimum control targets, system fonts, rem type scale and focus rings.

Medium: neutral light/dark surfaces, one blue action accent, compact scrolling navigation, left sidebar alignment, content-first spacing, input in normal layout flow.

Low: diffuse elevation for popovers, subtle separators, sampled spring transitions, reduced-motion overrides.

## Main layout before / after

Before:
```html
<main>
  <header>Title and uneven controls</header>
  <section>Welcome, then loading, then conversation</section>
  <div class="composer-zone"><!-- absolutely positioned input --></div>
</main>
<button class="voice-open-btn"><!-- floating outside composer --></button>
```

After (simplified structure; full implementation in chat.html):
```html
<main class="main">
  <header class="topbar"><!-- title, Sounds, Dashboard --></header>
  <section class="messages"><!-- one loading state, then history --></section>
  <div class="composer-zone">
    <form class="composer">
      <div class="composer-toolbar"><!-- mode selection --></div>
      <textarea aria-label="Message Saathi"></textarea>
      <div class="composer-actions"><!-- attachment, dictation, Voice, Send/Stop --></div>
    </form>
    <p id="replyStatus" role="status" hidden></p>
  </div>
</main>
```

Complete CSS: final HIG layer in experience.css, loaded last by dashboard.html and chat.html. Hover, pressed, focus and disabled states are included. Blue is darkened to #0066cc in light mode for white-label contrast; dark mode uses #70b7ff. This is not a completed WCAG conformance audit.

## Motion

| Interaction | Damping ratio target | Response | Movement |
|---|---:|---:|---|
| Modal entry | 0.8 | 300ms | 0.75rem upward, scale .98 to 1 |
| Sidebar | 0.8 | 300ms | Horizontal slide |
| Press feedback | 0.8 | 300ms | Scale to .97 |

Implemented using a sampled CSS linear() spring curve, not a runtime physics engine. Reduced motion removes all animation and transitions. Loading placeholders are static.

## Verification and limits

JavaScript syntax and eight behavior suites passed. Real Chromium interaction tests passed at 1280px and 390px, including navigation, editing, draft protection, failed sends and cancellation. Initial dashboard scroll is now asserted at zero: adding a default #overview fragment during bootstrap had scrolled the greeting off screen.

Axe WCAG A/AA checks found no violations on the tested initial dashboard, chat, landing, account and support states at 390px in both themes. Desktop checks cover the same pages, with a final targeted chat rerun after fixing shortcut contrast. No horizontal overflow was detected in these states. The account checkbox uses its larger associated label as the tap target. These checks are not a certification of every dynamic screen, dialog, assistive technology or browser.

Render served the previous HIG stylesheet successfully (HTTP 200) during this session. The follow-up commit still requires Render to finish deploying. No signed-in production AI call was made; provider response latency remains unverified. No backend or API changes were made.


The frontend shows waiting feedback after 8 seconds and clearer Stop guidance after 20 seconds, clearing it on streamed text or completion. It does not retry automatically. Provider latency/timeouts are not repaired by these frontend changes.
