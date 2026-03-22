#pragma once
#include <pgmspace.h>
static const char INDEX_HTML[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>XeWe Laptop Cooler</title>
  <link rel="stylesheet" href="/static/styles.css" />
</head>
<body>
  <div class="page">
    <header class="header">
      <div>
        <h1>XeWe Laptop Cooler</h1>
      </div>
    </header>

    <div class="control-block">
      <div class="curve-head">
        <h2>Curve</h2>
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

      <hr>
      <button id="addPointBtn" class="btn btn-secondary">Add Point</button>
      <button id="saveCurveBtn" class="btn btn-primary">Save Curve</button>

      <hr>

      <div class="curve-color-pickers">
        <label class="field inline-field">
          <span>Coldest Color</span>
          <input id="curveStartColor" type="color" />
        </label>

        <label class="field inline-field">
          <span>Hottest Color</span>
          <input id="curveEndColor" type="color" />
        </label>
      </div>

      <hr>

    </div>
  </div>

  <script src="/static/script.js"></script>
</body>
</html>
)rawliteral";
