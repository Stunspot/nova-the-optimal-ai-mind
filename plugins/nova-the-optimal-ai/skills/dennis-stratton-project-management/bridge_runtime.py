<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><link rel="icon" href="/assets/dennis.ico" type="image/x-icon"><title>Project Bridge — See what needs next</title><link rel="stylesheet" href="/bridge.css"><link rel="stylesheet" href="/bridge-themes.css"><script src="/bridge.js" defer></script></head>
<body data-skin="proofspan">
<a class="skip" href="#main">Skip to the project route</a>
<header class="topbar">
  <a class="brand" href="/" aria-label="Project Bridge home"><img src="/assets/dennis.png" alt=""><span><small>DENNIS STRATTON</small><strong>Project Bridge</strong></span></a>
  <div class="top-actions">
    <label class="skin-control">Appearance <select id="skin"><option value="proofspan">Proofspan</option><option value="bridge">Ember bridge</option><option value="folio">Survey folio</option><option value="redline">Redline</option></select></label>
    <button id="chooseStore" type="button">Choose project folder</button>
    <button id="refresh" type="button">Refresh project</button>
    <button id="exit" type="button" class="quiet">Exit</button>
  </div>
</header>
<div id="status" class="status" role="status" aria-live="polite">Reading the selected project-record estate…</div>
<div class="layout">
  <aside id="portfolio" class="portfolio" aria-label="Project portfolio">
    <div class="portfolio-head"><div><small>PROJECT PORTFOLIO</small><span id="projectCount"></span></div></div>
    <label class="search-label">Find a project<input id="search" type="search" placeholder="Project name or intended outcome"></label>
    <nav id="projects" class="project-list" aria-label="Projects"></nav>
    <div id="emptyPortfolio" class="empty-portfolio" hidden><h2>No project records here yet</h2><p>Choose the folder that holds your Dennis project records, or take the fictional walkthrough.</p><button id="chooseEmpty" type="button">Choose project folder</button><button id="walkEmpty" type="button" class="secondary">Walk through an example</button></div>
    <div class="portfolio-bottom"><p id="storeLabel"></p><button id="walkButton" type="button" class="text-button">Walk through the fictional exhibition</button></div>
  </aside>
  <main id="main" tabindex="-1">
    <div id="welcome" class="welcome">
      <div class="welcome-visual" aria-hidden="true"><span class="route-dot"></span><span class="route-line"></span><span class="route-dot second"></span><span class="route-line last"></span><span class="route-dot third"></span></div>
      <small>PROJECT BRIDGE</small><h1>See what your projects need next.</h1>
      <p>Trace a practical commitment back to the outcome it serves, follow the dependencies that stand in its way, and open the evidence behind the current picture.</p>
      <p id="welcomeMessage" class="welcome-message">Your records remain in their Dennis project-record estate.</p>
      <div class="welcome-actions"><button id="walkWelcome" type="button">Walk through a community exhibition</button><button id="browseWelcome" type="button" class="secondary">Browse projects</button><button id="chooseWelcome" type="button" class="secondary">Choose project folder</button></div>
      <div class="privacy-note"><strong>Read-only companion.</strong> Browsing, comparing, and changing views never edit native project records. The app keeps only your reading position and a local comparison snapshot in a separate preferences folder.</div>
    </div>
    <article id="projectView" hidden>
      <div class="project-topline"><button id="showPortfolio" type="button" class="text-button">← Browse projects</button><span id="asOf"></span></div>
      <div class="title-block"><small id="projectIdentity"></small><div class="title-row"><div><h1 id="projectName"></h1><p id="projectOutcome" class="outcome"></p></div><span id="projectStatus" class="state-tag"></span></div>
        <div class="project-meta"><span id="owner"></span><span id="sourceTime"></span></div><section id="currentContext" class="current-context" aria-label="Current project context"><p><strong>Why this matters:</strong> <span id="purposeConnection"></span></p><p><strong>Next action:</strong> <span id="nextAction"></span></p><p><strong>Decision to resolve:</strong> <span id="nextDecision"></span></p></section>
      </div>
      <div id="changePanel" class="change-panel" hidden></div>
      <div class="workbench">
        <section class="route-panel panel" aria-labelledby="routeTitle">
          <div class="panel-heading"><div><small>CONNECTED DELIVERY ROUTE</small><h2 id="routeTitle">Outcome to next commitment</h2></div></div>
          <p class="route-explainer">Parent links show the recorded hierarchy. Dependency arrows show only IDs declared in the project record; they do not imply duration or critical path.</p>
          <div id="route" class="route" aria-label="Project route"></div>
          <div id="routeWarnings" class="route-warnings" hidden></div>
        </section>
        <aside id="inspector" class="inspector panel" aria-labelledby="inspectorTitle">
          <div class="panel-heading"><div><small>SELECTED COMMITMENT</small><h2 id="inspectorTitle">Choose a route station</h2></div></div>
          <div id="inspectorBody" class="inspector-body"><p>Select a declared work package to trace its purpose, dependencies and completion evidence.</p></div>
        </aside>
      </div>
      <section id="sourcePanel" class="source-panel panel" aria-labelledby="sourceTitle" hidden>
        <div class="panel-heading"><div><small>PROJECT EVIDENCE</small><h2 id="sourceTitle">Source</h2></div><button id="closeSource" type="button" class="quiet">Return to route</button></div>
        <div id="sourceMeta" class="source-meta"></div><div id="sourceContent" class="source-content"></div>
      </section>
      
    </article>
    <section id="closedScreen" class="closed-screen" hidden><small>PROJECT BRIDGE IS CLOSED</small><h1>Your project records are safe.</h1><p>The local reader has stopped. This browser tab is now inert; close it and use the Project Bridge launcher when you want to return.</p><button type="button" disabled>Reader stopped</button></section>
  </main>
</div>
</body></html>



