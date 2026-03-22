#pragma once
#include <pgmspace.h>
static const char SCRIPT_JS[] PROGMEM = R"rawliteral(
const state = {
  fan_data: null,
  argb_data: null,
  sensor_data: null,
  ui_config: null,
};

let curvePointIdCounter = 0;

const curveStartColor = document.getElementById("curveStartColor");
const curveEndColor = document.getElementById("curveEndColor");
const addPointBtn = document.getElementById("addPointBtn");
const saveCurveBtn = document.getElementById("saveCurveBtn");
const curveTableBody = document.getElementById("curveTableBody");

const curveCanvas = document.getElementById("curveCanvas");
const ctx = curveCanvas.getContext("2d", { alpha: true });

const CANVAS_ASPECT_RATIO = 960 / 440;
const MAX_DEVICE_PIXEL_RATIO = 3;

function makePointId() {
  curvePointIdCounter += 1;
  return `curve-point-${curvePointIdCounter}`;
}

function withPointIds(points = []) {
  return points.map((point) => ({
    ...point,
    _id: point._id ?? makePointId(),
  }));
}

function hexToRgb(hex) {
  const clean = hex.replace("#", "");
  return {
    r: parseInt(clean.slice(0, 2), 16),
    g: parseInt(clean.slice(2, 4), 16),
    b: parseInt(clean.slice(4, 6), 16),
  };
}

function interpolateColor(hexA, hexB, t) {
  const a = hexToRgb(hexA);
  const b = hexToRgb(hexB);
  const mix = (x, y) => Math.round(x + (y - x) * t);
  return `rgb(${mix(a.r, b.r)}, ${mix(a.g, b.g)}, ${mix(a.b, b.b)})`;
}

function sortCurve(points) {
  return [...points].sort((a, b) => Number(a.temp) - Number(b.temp));
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function normalizeCurve() {
  if (!state.ui_config?.temp_curve) return;

  state.ui_config.temp_curve = sortCurve(withPointIds(state.ui_config.temp_curve)).map((point) => ({
    ...point,
    temp: clamp(Number(point.temp) || 0, 0, 100),
    speed: clamp(Number(point.speed) || 0, 0, 100),
  }));
}

function getCurveRange(points) {
  const sorted = sortCurve(points);
  const minTemp = Number(sorted[0]?.temp ?? 0);
  const maxTemp = Number(sorted[sorted.length - 1]?.temp ?? 100);

  return {
    minTemp,
    maxTemp,
    span: Math.max(maxTemp - minTemp, 1),
  };
}

function getPointColor(temp, startColor, endColor, minTemp, maxTemp) {
  const span = Math.max(maxTemp - minTemp, 1);
  const safeTemp = clamp(Number(temp) || 0, minTemp, maxTemp);
  const t = (safeTemp - minTemp) / span;
  return interpolateColor(startColor, endColor, t);
}

function getCanvasLogicalSize() {
  const rect = curveCanvas.getBoundingClientRect();
  let width = Math.max(320, Math.round(rect.width));
  let height = Math.max(220, Math.round(rect.height));

  if (!height || Math.abs(width / height - CANVAS_ASPECT_RATIO) > 0.02) {
    height = Math.round(width / CANVAS_ASPECT_RATIO);
  }

  return { width, height };
}

function setupHiDPICanvas() {
  const { width, height } = getCanvasLogicalSize();
  const dpr = Math.min(window.devicePixelRatio || 1, MAX_DEVICE_PIXEL_RATIO);

  const displayWidth = Math.round(width * dpr);
  const displayHeight = Math.round(height * dpr);

  if (curveCanvas.width !== displayWidth || curveCanvas.height !== displayHeight) {
    curveCanvas.width = displayWidth;
    curveCanvas.height = displayHeight;
  }

  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = "high";

  return { width, height, dpr };
}

function crisp(value) {
  return Math.round(value) + 0.5;
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

async function loadState() {
  const data = await fetchJson("/api/state");
  state.fan_data = data.fan_data;
  state.argb_data = data.argb_data;
  state.sensor_data = data.sensor_data;

  if (!state.ui_config) {
    state.ui_config = data.ui_config;
    normalizeCurve();
    renderCurveEditor();
  }

  drawCurve();
}

function findCurvePointById(pointId) {
  return state.ui_config?.temp_curve?.find((point) => point._id === pointId);
}

function renderCurveEditor() {
  if (!state.ui_config) return;

  normalizeCurve();

  curveStartColor.value = state.ui_config.curve_edge_colors.start;
  curveEndColor.value = state.ui_config.curve_edge_colors.end;

  const points = state.ui_config.temp_curve;

  curveTableBody.innerHTML = "";

  points.forEach((point) => {
    const row = document.createElement("tr");

    const tempCell = document.createElement("td");
    const tempInput = document.createElement("input");
    tempInput.type = "number";
    tempInput.min = "0";
    tempInput.max = "100";
    tempInput.value = point.temp;
    tempInput.dataset.pointId = point._id;
    tempInput.dataset.field = "temp";
    tempInput.addEventListener("input", handleCurveInput);
    tempInput.addEventListener("blur", handleCurveCommit);
    tempCell.appendChild(tempInput);

    const speedCell = document.createElement("td");
    const speedInput = document.createElement("input");
    speedInput.type = "number";
    speedInput.min = "0";
    speedInput.max = "100";
    speedInput.value = point.speed;
    speedInput.dataset.pointId = point._id;
    speedInput.dataset.field = "speed";
    speedInput.addEventListener("input", handleCurveInput);
    speedInput.addEventListener("blur", handleCurveCommit);
    speedCell.appendChild(speedInput);

    const actionCell = document.createElement("td");
    const removeBtn = document.createElement("button");
    removeBtn.className = "btn btn-danger";
    removeBtn.textContent = "Delete";
    removeBtn.disabled = points.length <= 2;
    removeBtn.addEventListener("click", () => {
      if (state.ui_config.temp_curve.length <= 2) return;

      state.ui_config.temp_curve = state.ui_config.temp_curve.filter(
        (curvePoint) => curvePoint._id !== point._id
      );

      normalizeCurve();
      renderCurveEditor();
      drawCurve();
    });
    actionCell.appendChild(removeBtn);

    row.appendChild(tempCell);
    row.appendChild(speedCell);
    row.appendChild(actionCell);

    curveTableBody.appendChild(row);
  });
}

function handleCurveInput(event) {
  const pointId = event.target.dataset.pointId;
  const field = event.target.dataset.field;
  const point = findCurvePointById(pointId);

  if (!point) return;

  point[field] = clamp(Number(event.target.value) || 0, 0, 100);
  drawCurve();
}

function handleCurveCommit() {
  normalizeCurve();
  renderCurveEditor();
  drawCurve();
}

function getCurvePayload() {
  normalizeCurve();

  return state.ui_config.temp_curve.map((point) => ({
    temp: clamp(Number(point.temp) || 0, 0, 100),
    speed: clamp(Number(point.speed) || 0, 0, 100),
  }));
}

async function saveCurve() {
  const payload = {
    temp_curve: getCurvePayload(),
    curve_edge_colors: {
      start: curveStartColor.value,
      end: curveEndColor.value,
    },
  };

  const data = await fetchJson("/ui/config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  state.ui_config = data.ui_config;
  normalizeCurve();
  renderCurveEditor();
  drawCurve();
}

function drawGrid(ctx2d, x, y, pad, width, height) {
  ctx2d.strokeStyle = "rgba(255,255,255,0.08)";
  ctx2d.lineWidth = 1;
  ctx2d.setLineDash([]);

  for (let i = 0; i <= 10; i++) {
    const xPos = crisp(x(i * 10));
    const yPos = crisp(y(i * 10));

    ctx2d.beginPath();
    ctx2d.moveTo(xPos, pad.top);
    ctx2d.lineTo(xPos, pad.top + height);
    ctx2d.stroke();

    ctx2d.beginPath();
    ctx2d.moveTo(pad.left, yPos);
    ctx2d.lineTo(pad.left + width, yPos);
    ctx2d.stroke();
  }
}

function drawAxesLabels(ctx2d, x, y, logicalWidth, logicalHeight, pad, height) {
  ctx2d.fillStyle = "rgba(255,255,255,0.78)";
  ctx2d.font = "12px sans-serif";

  const xTickLabelY = pad.top + height + 28;
  const xAxisLabelY = pad.top + height + 56;
  const yTickLabelX = pad.left - 46;
  const yAxisLabelX = 14;

  ctx2d.textAlign = "center";
  ctx2d.textBaseline = "top";
  for (let i = 0; i <= 10; i++) {
    const label = i * 10;
    ctx2d.fillText(`${label}`, x(label), xTickLabelY);
  }

  ctx2d.textAlign = "right";
  ctx2d.textBaseline = "middle";
  for (let i = 0; i <= 10; i++) {
    const label = i * 10;
    ctx2d.fillText(`${label}%`, yTickLabelX, y(label));
  }

  ctx2d.textAlign = "center";
  ctx2d.textBaseline = "top";
  ctx2d.fillText("Temp (°C)", logicalWidth / 2, xAxisLabelY);

  ctx2d.save();
  ctx2d.translate(yAxisLabelX, pad.top + height / 2);
  ctx2d.rotate(-Math.PI / 2);
  ctx2d.textAlign = "center";
  ctx2d.textBaseline = "top";
  ctx2d.fillText("Fan Speed (%)", 0, 0);
  ctx2d.restore();
}

function drawCurve() {
  if (!state.ui_config) return;

  normalizeCurve();

  const { width: logicalWidth, height: logicalHeight } = setupHiDPICanvas();

  const startColor = curveStartColor.value;
  const endColor = curveEndColor.value;
  const points = state.ui_config.temp_curve;
  const { minTemp, maxTemp } = getCurveRange(points);

  ctx.clearRect(0, 0, logicalWidth, logicalHeight);

  const pad = { top: 28, right: 28, bottom: 92, left: 122 };
  const width = logicalWidth - pad.left - pad.right;
  const height = logicalHeight - pad.top - pad.bottom;

  const x = (temp) => pad.left + (temp / 100) * width;
  const y = (speed) => pad.top + height - (speed / 100) * height;

  drawGrid(ctx, x, y, pad, width, height);
  drawAxesLabels(ctx, x, y, logicalWidth, logicalHeight, pad, height);

  if (points.length > 1) {
    let stroke = startColor;

    if (maxTemp !== minTemp) {
      const lineGradient = ctx.createLinearGradient(x(minTemp), 0, x(maxTemp), 0);
      lineGradient.addColorStop(0, startColor);
      lineGradient.addColorStop(1, endColor);
      stroke = lineGradient;
    }

    ctx.strokeStyle = stroke;
    ctx.lineWidth = 4;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.setLineDash([]);
    ctx.beginPath();
    ctx.moveTo(x(points[0].temp), y(points[0].speed));

    for (let i = 1; i < points.length; i++) {
      ctx.lineTo(x(points[i].temp), y(points[i].speed));
    }

    ctx.stroke();
  }

  points.forEach((point) => {
    const pointColor = getPointColor(point.temp, startColor, endColor, minTemp, maxTemp);

    ctx.beginPath();
    ctx.fillStyle = pointColor;
    ctx.arc(x(point.temp), y(point.speed), 6, 0, Math.PI * 2);
    ctx.fill();

    ctx.lineWidth = 2;
    ctx.strokeStyle = "#0d1326";
    ctx.setLineDash([]);
    ctx.stroke();
  });

  const liveTemp = clamp(Number(state.sensor_data?.object_temp || 0), 0, 100);
  const liveSpeed = clamp(Number(state.fan_data?.fans?.[0]?.speed || 0), 0, 100);

  const liveX = x(liveTemp);
  const liveY = y(liveSpeed);

  ctx.setLineDash([6, 6]);
  ctx.lineWidth = 1.5;
  ctx.strokeStyle = "rgba(255,255,255,0.55)";

  ctx.beginPath();
  ctx.moveTo(liveX, liveY);
  ctx.lineTo(liveX, pad.top + height);
  ctx.stroke();

  ctx.beginPath();
  ctx.moveTo(pad.left, liveY);
  ctx.lineTo(liveX, liveY);
  ctx.stroke();

  ctx.setLineDash([]);
  ctx.beginPath();
  ctx.fillStyle = "#ffffff";
  ctx.arc(liveX, liveY, 7, 0, Math.PI * 2);
  ctx.fill();

  ctx.lineWidth = 3;
  ctx.strokeStyle = "#0d1326";
  ctx.stroke();

  ctx.fillStyle = "rgba(255,255,255,0.9)";
  ctx.font = "12px sans-serif";

  ctx.textAlign = "center";
  ctx.textBaseline = "bottom";
  ctx.fillText(`${liveTemp.toFixed(1)}°C`, liveX, pad.top + height + 14);

  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  ctx.fillText(`${liveSpeed.toFixed(0)}%`, pad.left - 12, liveY);
}

// UPDATE CANVAS LIVE WHILE DRAGGING
curveStartColor.addEventListener("input", drawCurve);
curveEndColor.addEventListener("input", drawCurve);

// PUSH TO BACKEND ONCE SELECTION IS CONFIRMED/RELEASED
curveStartColor.addEventListener("change", saveCurve);
curveEndColor.addEventListener("change", saveCurve);

addPointBtn.addEventListener("click", () => {
  if (!state.ui_config) return;

  normalizeCurve();

  const points = state.ui_config.temp_curve;
  const lastPoint = points[points.length - 1] ?? { temp: 65, speed: 80 };

  state.ui_config.temp_curve.push({
    _id: makePointId(),
    temp: clamp(lastPoint.temp + 5, 0, 100),
    speed: clamp(lastPoint.speed, 0, 100),
  });

  normalizeCurve();
  renderCurveEditor();
  drawCurve();
});

saveCurveBtn.addEventListener("click", saveCurve);

window.addEventListener("resize", drawCurve);

loadState();
setInterval(loadState, 1000);
)rawliteral";
