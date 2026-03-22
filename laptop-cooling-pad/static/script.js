const state = {
  fan_data: null,
  argb_data: null,
  sensor_data: null,
  ui_config: null,
};

const curveStartColor = document.getElementById("curveStartColor");
const curveEndColor = document.getElementById("curveEndColor");
const addPointBtn = document.getElementById("addPointBtn");
const saveCurveBtn = document.getElementById("saveCurveBtn");
const curveTableBody = document.getElementById("curveTableBody");
const curveGradientBar = document.getElementById("curveGradientBar");

const curveCanvas = document.getElementById("curveCanvas");
const ctx = curveCanvas.getContext("2d");

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
    renderCurveEditor();
    drawCurve();
  }

  renderInfo();
  renderRawData();
}

function renderInfo() {
  const fans = state.fan_data?.fans || [];
  const sensor = state.sensor_data;

  if (!sensor) return;

  const fan1 = fans[0] || {};
  const fan2 = fans[1] || {};

  const laptopTemp = Number(sensor.object_temp || 0);
  const sensorTemp = Number(sensor.ambient_temp || 0);

  const fan1Rpm = Number(fan1.displayed_rpm || 0);
  const fan2Rpm = Number(fan2.displayed_rpm || 0);
  const fan1Pct = Number(fan1.speed || 0);
  const fan2Pct = Number(fan2.speed || 0);

  document.getElementById("laptopTemp").textContent = `${laptopTemp.toFixed(2)}°C`;
  document.getElementById("sensorTemp").textContent = `${sensorTemp.toFixed(2)}°C`;

  document.getElementById("fan1Summary").textContent = `${fan1Rpm} RPM (${fan1Pct}%)`;
  document.getElementById("fan2Summary").textContent = `${fan2Rpm} RPM (${fan2Pct}%)`;

  const badge = document.getElementById("sensorOnlineBadge");
  badge.textContent = sensor.online ? "ONLINE" : "OFFLINE";
  badge.classList.toggle("online", !!sensor.online);
  badge.classList.toggle("offline", !sensor.online);

  document.getElementById(
    "sensorMeta"
  ).textContent = `${sensor.module} · I2C 0x${Number(sensor.i2c_address)
    .toString(16)
    .toUpperCase()} · SDA ${sensor.sda_pin} · SCL ${sensor.scl_pin}`;
}

function renderRawData() {
  if (!state.fan_data || !state.argb_data || !state.sensor_data) return;

  document.getElementById("fanJson").textContent = JSON.stringify(state.fan_data, null, 2);
  document.getElementById("argbJson").textContent = JSON.stringify(state.argb_data, null, 2);
  document.getElementById("sensorJson").textContent = JSON.stringify(state.sensor_data, null, 2);
}

function renderCurveEditor() {
  if (!state.ui_config) return;

  curveStartColor.value = state.ui_config.curve_edge_colors.start;
  curveEndColor.value = state.ui_config.curve_edge_colors.end;
  curveGradientBar.style.background = `linear-gradient(90deg, ${curveStartColor.value}, ${curveEndColor.value})`;

  curveTableBody.innerHTML = "";

  const points = sortCurve(state.ui_config.temp_curve);

  points.forEach((point, index) => {
    const row = document.createElement("tr");

    const tempCell = document.createElement("td");
    const tempInput = document.createElement("input");
    tempInput.type = "number";
    tempInput.min = "0";
    tempInput.max = "100";
    tempInput.value = point.temp;
    tempInput.dataset.index = index;
    tempInput.dataset.field = "temp";
    tempInput.addEventListener("input", handleCurveInput);
    tempCell.appendChild(tempInput);

    const speedCell = document.createElement("td");
    const speedInput = document.createElement("input");
    speedInput.type = "number";
    speedInput.min = "0";
    speedInput.max = "100";
    speedInput.value = point.speed;
    speedInput.dataset.index = index;
    speedInput.dataset.field = "speed";
    speedInput.addEventListener("input", handleCurveInput);
    speedCell.appendChild(speedInput);

    const actionCell = document.createElement("td");
    const removeBtn = document.createElement("button");
    removeBtn.className = "btn btn-danger";
    removeBtn.textContent = "Delete";
    removeBtn.disabled = points.length <= 2;
    removeBtn.addEventListener("click", () => {
      if (state.ui_config.temp_curve.length <= 2) return;
      state.ui_config.temp_curve.splice(index, 1);
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
  const index = Number(event.target.dataset.index);
  const field = event.target.dataset.field;
  const value = clamp(Number(event.target.value) || 0, 0, 100);

  state.ui_config.temp_curve[index][field] = value;
  drawCurve();
}

function getCurvePayload() {
  return sortCurve(
    state.ui_config.temp_curve.map((point) => ({
      temp: clamp(Number(point.temp) || 0, 0, 100),
      speed: clamp(Number(point.speed) || 0, 0, 100),
    }))
  );
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
  renderCurveEditor();
  drawCurve();
}

function drawCurve() {
  if (!state.ui_config) return;

  const startColor = curveStartColor.value;
  const endColor = curveEndColor.value;
  const points = getCurvePayload();

  curveGradientBar.style.background = `linear-gradient(90deg, ${startColor}, ${endColor})`;

  ctx.clearRect(0, 0, curveCanvas.width, curveCanvas.height);

  const pad = { top: 28, right: 24, bottom: 42, left: 56 };
  const width = curveCanvas.width - pad.left - pad.right;
  const height = curveCanvas.height - pad.top - pad.bottom;

  const x = (temp) => pad.left + (temp / 100) * width;
  const y = (speed) => pad.top + height - (speed / 100) * height;

  ctx.strokeStyle = "rgba(255,255,255,0.08)";
  ctx.lineWidth = 1;

  for (let i = 0; i <= 10; i++) {
    const xPos = x(i * 10);
    const yPos = y(i * 10);

    ctx.beginPath();
    ctx.moveTo(xPos, pad.top);
    ctx.lineTo(xPos, pad.top + height);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(pad.left, yPos);
    ctx.lineTo(pad.left + width, yPos);
    ctx.stroke();
  }

  ctx.fillStyle = "rgba(255,255,255,0.78)";
  ctx.font = "12px sans-serif";

  for (let i = 0; i <= 10; i++) {
    const label = i * 10;
    ctx.fillText(`${label}`, x(label) - 8, pad.top + height + 20);
    ctx.fillText(`${label}%`, 10, y(label) + 4);
  }

  ctx.fillText("Temp (°C)", curveCanvas.width / 2 - 24, curveCanvas.height - 10);

  ctx.save();
  ctx.translate(18, curveCanvas.height / 2 + 20);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText("Fan Speed (%)", 0, 0);
  ctx.restore();

  for (let i = 0; i < points.length - 1; i++) {
    const p1 = points[i];
    const p2 = points[i + 1];
    const t = points.length === 1 ? 0 : i / (points.length - 1);

    ctx.strokeStyle = interpolateColor(startColor, endColor, t);
    ctx.lineWidth = 4;
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.moveTo(x(p1.temp), y(p1.speed));
    ctx.lineTo(x(p2.temp), y(p2.speed));
    ctx.stroke();
  }

  points.forEach((point, index) => {
    const t = points.length === 1 ? 0 : index / (points.length - 1);

    ctx.beginPath();
    ctx.fillStyle = interpolateColor(startColor, endColor, t);
    ctx.arc(x(point.temp), y(point.speed), 6, 0, Math.PI * 2);
    ctx.fill();

    ctx.lineWidth = 2;
    ctx.strokeStyle = "#0d1326";
    ctx.stroke();
  });
}

curveStartColor.addEventListener("input", drawCurve);
curveEndColor.addEventListener("input", drawCurve);

addPointBtn.addEventListener("click", () => {
  state.ui_config.temp_curve.push({ temp: 70, speed: 100 });
  renderCurveEditor();
  drawCurve();
});

saveCurveBtn.addEventListener("click", saveCurve);

loadState();
setInterval(loadState, 1000);