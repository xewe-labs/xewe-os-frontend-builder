#pragma once
#include <pgmspace.h>
static const char STYLES_CSS[] PROGMEM = R"rawliteral(
:root {
  --bg: #0a0f1f;
  --panel: #11182d;
  --panel-2: #18213c;
  --line: rgba(255, 255, 255, 0.08);
  --text: #edf2ff;
  --muted: #9aa7c8;
  --ok: #57d386;
  --warn: #ff6d8d;
  --shadow: 0 20px 48px rgba(0, 0, 0, 0.28);
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  color: var(--text);
  background:
    radial-gradient(circle at top left, rgba(0, 194, 255, 0.12), transparent 28%),
    radial-gradient(circle at top right, rgba(255, 90, 122, 0.10), transparent 24%),
    var(--bg);
}

.page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 28px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: end;
  gap: 16px;
  margin-bottom: 24px;
}

.eyebrow {
  margin: 0 0 6px 0;
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
}

h1,
h2,
h3,
p {
  margin: 0;
}

h1 {
  font-size: 28px;
  font-weight: 700;
}

h2 {
  font-size: 18px;
  font-weight: 650;
}

h3 {
  font-size: 15px;
  font-weight: 650;
}

.single-panel-layout {
  display: block;
}

.panel {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.02), transparent 100%), var(--panel);
  border: 1px solid var(--line);
  border-radius: 18px;
  box-shadow: var(--shadow);
  padding: 18px;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.subtle {
  color: var(--muted);
  font-size: 13px;
}

.control-block {
  background: var(--panel-2);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 16px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  color: var(--muted);
  font-size: 13px;
}

.inline-field {
  flex-direction: row;
  align-items: center;
  gap: 8px;
}

input[type="color"] {
  width: 56px;
  height: 40px;
  padding: 0;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: transparent;
  cursor: pointer;
}

input[type="number"] {
  width: 100%;
  background: #0d1326;
  color: var(--text);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 8px 10px;
}

.btn {
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 10px 14px;
  color: var(--text);
  font-weight: 700;
  cursor: pointer;
}

.btn-primary {
  background: linear-gradient(90deg, rgba(0, 194, 255, 0.22), rgba(255, 90, 122, 0.22));
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.05);
}

.btn-danger {
  background: rgba(255, 109, 141, 0.12);
  color: #ffc0cf;
  border-color: rgba(255, 109, 141, 0.22);
}

.curve-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.curve-color-pickers {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.curve-canvas-wrap {
  background: #0d1326;
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 14px;
}

#curveCanvas {
  width: 100%;
  height: auto;
  display: block;
  border-radius: 12px;
}

.gradient-bar {
  margin-top: 12px;
  height: 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.06);
  overflow: hidden;
}

.curve-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 16px;
}

.curve-table th,
.curve-table td {
  padding: 10px 6px;
  text-align: left;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  font-size: 13px;
}

.curve-table th {
  color: var(--muted);
  font-weight: 650;
}

.curve-actions {
  display: flex;
  gap: 10px;
  margin-top: 14px;
}

@media (max-width: 720px) {
  .page {
    padding: 16px;
  }

  .header {
    flex-direction: column;
    align-items: stretch;
  }

  .curve-head {
    flex-direction: column;
    align-items: stretch;
  }
}
)rawliteral";
