#pragma once
#include <pgmspace.h>
static const char INDEX_HTML[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Laptop Cooling Pad UI</title>
  <link rel="stylesheet" href="/static/styles.css" />
</head>
<body>
  <div class="page">
    <header class="header">
      <div>
        <p class="eyebrow">Dummy Flask UI</p>
        <h1>Laptop Cooling Pad Dashboard</h1>
      </div>
    </header>

    <main class="single-panel-layout">
      <section class="panel">
        <div class="panel-head">
          <h2>Temperature Curve</h2>
          <span class="subtle">Live point = laptop temp + current fan speed</span>
        </div>

        <div class="control-block">
          <div class="curve-head">
            <h3>Curve Editor</h3>
            <div class="curve-color-pickers">
              <label class="field inline-field">
                <span>Edge 1</span>
                <input id="curveStartColor" type="color" />
              </label>

              <label class="field inline-field">
                <span>Edge 2</span>
                <input id="curveEndColor" type="color" />
              </label>
            </div>
          </div>

          <div class="curve-canvas-wrap">
            <canvas id="curveCanvas" width="960" height="440"></canvas>
            <div id="curveGradientBar" class="gradient-bar"></div>
          </div>

          <table class="curve-table">
            <thead>
              <tr>
                <th>Temp (°C)</th>
                <th>Fan (%)</th>
                <th></th>
              </tr>
            </thead>
            <tbody id="curveTableBody"></tbody>
          </table>

          <div class="curve-actions">
            <button id="addPointBtn" class="btn btn-secondary">Add Point</button>
            <button id="saveCurveBtn" class="btn btn-primary">Save Curve</button>
          </div>
        </div>
      </section>
    </main>
  </div>

  <script src="/static/script.js"></script>
</body>
</html>
)rawliteral";
