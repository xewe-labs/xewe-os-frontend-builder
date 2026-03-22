const state = {
  fan_data: null,
  argb_data: null,
  sensor_data: null,
  ui_config: null,
};

const fanList = document.getElementById("fanList");
const argbList = document.getElementById("argbList");
const curveTableBody = document.getElementById("curveTableBody");
const curveCanvas = document.getElementById("curveCanvas");
const ctx = curveCanvas.getContext("2d");

const refreshBtn = document.getElementById("refreshBtn");
const addPointBtn = document.getElementById("addPointBtn");
const saveCurveBtn = document.getElementById("saveCurveBtn");
const curveStartColor = document.getElementById("curveStartColor");
const curveEndColor = document.getElementById("curveEndColor");
const curveGradientPreview = document.getElementById("curveGradientPreview");

const fanCardTemplate = document.getElementById("fanCardTemplate");
const argbCardTemplate = document.getElementById("argbCardTemplate");

function rgbToHex(r, g, b) {
  return (
    "#" +
    [r, g, b]
      .map((value) => Number(value).toString(16).padStart(2, "0"))
      .join("")
  );
}

function hexToRgb(hex) {
  const clean = hex.replace("#", "");
  return {
    r: parseInt(clean.substring(0, 2), 16),
    g: parseInt(clean.substring(2, 4), 16),
    b: parseInt(clean.substring(4, 6), 16),
  };
}

function interpolateColor(hexA, hexB, t) {
  const a = hexToRgb(hexA);
  const b = hexToRgb(hexB);
  const mix = (start, end) => Math.round(start + (end - start) * t);
  return `rgb(${mix(a.r, b.r)}, ${mix(a.g, b.g)}, ${mix(a.b, b.b)})`;
}

function sortCurvePoints(points) {
  return [...points].sort((a, b) => a.temp - b.temp);
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

async function loadAllState() {
  const data = await fetchJson("/api/state");
  state.fan_data = data.fan_data;
  state.argb_data = data.argb_data;
  state.sensor_data = data.sensor_data;
  state.ui_config = data.ui_config;

  renderSensor();
  renderFans();
  renderArgb();
  renderCurveEditor();
  drawCurve();
}

async function refreshSensorOnly() {
  if (!state.sensor_data) return;
  const sensor = await fetchJson("/mlx90614/data");
  state.sensor_data = sensor;
  renderSensor();
}

function renderSensor() {
  const sensor = state.sensor_data;
  if (!sensor) return;

  document.getElementById("objectTemp").textContent = `${sensor.object_temp.toFixed(2)}°C`;
  document.getElementById("ambientTemp").textContent = `${sensor.ambient_temp.toFixed(2)}°C`;
  document.getElementById("sensorModule").textContent = sensor.module;
  document.getElementById("sensorI2c").textContent = `0x${Number(sensor.i2c_address).toString(16).toUpperCase()}`;

  const badge = document.getElementById("sensorStatus");
  badge.textContent = sensor.online ? "ONLINE" : "OFFLINE";
  badge.classList.toggle("online", sensor.online);
  badge.classList.toggle("offline", !sensor.online);

  document.getElementById(
    "sensorMeta"
  ).textContent = `SDA pin ${sensor.sda_pin} · SCL pin ${sensor.scl_pin}`;
}

function renderFans() {
  const fans = state.fan_data?.fans || [];
  fanList.innerHTML = "";

  fans.forEach((fan, index) => {
    const fragment = fanCardTemplate.content.cloneNode(true);
    const root = fragment.querySelector(".fan-card");
    const title = fragment.querySelector("h3");
    const meta = fragment.querySelector(".control-meta");
    const rpm = fragment.querySelector(".rpm-pill");
    const slider = fragment.querySelector(".fan-slider");
    const value = fragment.querySelector(".slider-value");

    title.textContent = `Fan ${index + 1}`;
    meta.textContent = `PWM pin ${fan.pin_pwm} · Tach ${fan.has_tach ? `pin ${fan.pin_tach}` : "not available"}`;
    rpm.textContent = `${fan.displayed_rpm} RPM`;
    slider.value = fan.speed;
    value.textContent = `${fan.speed}%`;

    slider.addEventListener("input", () => {
      value.textContent = `${slider.value}%`;
    });

    slider.addEventListener("change", async () => {
      const speed = Number(slider.value);

      await fetchJson("/fan/data", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ index, speed }),
      });

      state.fan_data.fans[index].speed = speed;
      state.fan_data.fans[index].displayed_rpm =
        speed === 0 ? 0 : Math.round(300 + (speed / 100) * 2500);
      state.fan_data.fans[index].ema_rpm = state.fan_data.fans[index].displayed_rpm;

      renderFans();
      refreshSensorOnly();
    });

    fanList.appendChild(root);
  });
}

function renderArgb() {
  const zones = state.argb_data || [];
  argbList.innerHTML = "";

  zones.forEach((zone, index) => {
    const fragment = argbCardTemplate.content.cloneNode(true);
    const root = fragment.querySelector(".argb-card");
    const title = fragment.querySelector("h3");
    const meta = fragment.querySelector(".control-meta");
    const toggle = fragment.querySelector(".argb-toggle");
    const colorInput = fragment.querySelector(".argb-color");
    const readout = fragment.querySelector(".rgb-readout");

    title.textContent = `ARGB Zone ${index + 1}`;
    meta.textContent = `Pin ${zone.pin}`;
    toggle.checked = zone.state;
    colorInput.value = rgbToHex(zone.r, zone.g, zone.b);
    readout.textContent = `RGB(${zone.r}, ${zone.g}, ${zone.b})`;

    async function pushArgb() {
      const rgb = hexToRgb(colorInput.value);
      const payload = {
        index,
        state: toggle.checked,
        r: rgb.r,
        g: rgb.g,
        b: rgb.b,
      };

      const response = await fetchJson("/argb/data", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      state.argb_data = response.argb_data;
      renderArgb();
    }

    toggle.addEventListener("change", pushArgb);
    colorInput.addEventListener("change", pushArgb);

    argbList.appendChild(root);
  });
}

function renderCurveEditor() {
  const config = state.ui_config;
  if (!config) return;

  curveStartColor.value = config.curve_edge_colors.start;
  curveEndColor.value = config.curve_edge_colors.end;
  curveGradientPreview.style.background = `linear-gradient(90deg, ${config.curve_edge_colors.start}, ${config.curve_edge_colors.end})`;

  curveTableBody.innerHTML = "";

  sortCurvePoints(config.temp_curve).forEach((point, index) => {
    const row = document.createElement("tr");

    const tempCell = document.createElement("td");
    const tempInput = document.createElement("input");
    tempInput.type = "number";
    tempInput.min = "0";
    tempInput.max = "100";
    tempInput.value = point.temp;
    tempInput.dataset.index = index;
    tempInput.dataset.field = "temp";
    tempCell.appendChild(tempInput);

    const speedCell = document.createElement("td");
    const speedInput = document.createElement("input");
    speedInput.type = "number";
    speedInput.min = "0";
    speedInput.max = "100";
    speedInput.value = point.speed;
    speedInput.dataset.index = index;
    speedInput.dataset.field = "speed";
    speedCell.appendChild(speedInput);

    const actionCell = document.createElement("td");
    const removeBtn = document.createElement("button");
    removeBtn.className = "icon-btn";
    removeBtn.textContent = "Delete";
    removeBtn.disabled = config.temp_curve.length <= 2;

    removeBtn.addEventListener("click", () => {
      if (state.ui_config.temp_curve.length <= 2) return;
      state.ui_config.temp_curve.splice(index, 1);
      renderCurveEditor();
      drawCurve();
    });

    tempInput.addEventListener("input", onCurveInputChange);
    speedInput.addEventListener("input", onCurveInputChange);

    actionCell.appendChild(removeBtn);

    row.appendChild(tempCell);
    row.appendChild(speedCell);
    row.appendChild(actionCell);

    curveTableBody.appendChild(row);
  });

  curveStartColor.oninput = () => {
    state.ui_config.curve_edge_colors.start = curveStartColor.value;
    curveGradientPreview.style.background = `linear-gradient(90deg, ${curveStartColor.value}, ${curveEndColor.value})`;
    drawCurve();
  };

  curveEndColor.oninput = () => {
    state.ui_config.curve_edge_colors.end = curveEndColor.value;
    curveGradientPreview.style.background = `linear-gradient(90deg, ${curveStartColor.value}, ${curveEndColor.value})`;
    drawCurve();
  };
}

function onCurveInputChange(event) {
  const index = Number(event.target.dataset.index);
  const field = event.target.dataset.field;
  const value = Number(event.target.value);

  state.ui_config.temp_curve[index][field] = Math.max(
    0,
    Math.min(100, Number.isNaN(value) ? 0 : value)
  );

  drawCurve();
}

function getCurvePointsFromState() {
  return sortCurvePoints(
    state.ui_config.temp_curve.map((point) => ({
      temp: Math.max(0, Math.min(100, Number(point.temp))),
      speed: Math.max(0, Math.min(100, Number(point.speed))),
    }))
  );
}

function drawCurve() {
  if (!state.ui_config) return;

  const startColor = state.ui_config.curve_edge_colors.start;
  const endColor = state.ui_config.curve_edge_colors.end;
  const points = getCurvePointsFromState();

  ctx.clearRect(0, 0, curveCanvas.width, curveCanvas.height);

  const padding = { top: 30, right: 24, bottom: 40, left: 56 };
  const chartWidth = curveCanvas.width - padding.left - padding.right;
  const chartHeight = curveCanvas.height - padding.top - padding.bottom;

  const x = (temp) => padding.left + (temp / 100) * chartWidth;
  const y = (speed) => padding.top + chartHeight - (speed / 100) * chartHeight;

  ctx.lineWidth = 1;
  ctx.strokeStyle = "rgba(255,255,255,0.08)";

  for (let i = 0; i <= 10; i++) {
    const temp = i * 10;
    const yPos = y(temp);
    const xPos = x(temp);

    ctx.beginPath();
    ctx.moveTo(padding.left, yPos);
    ctx.lineTo(padding.left + chartWidth, yPos);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(xPos, padding.top);
    ctx.lineTo(xPos, padding.top + chartHeight);
    ctx.stroke();
  }

  ctx.fillStyle = "rgba(255,255,255,0.75)";
  ctx.font = "12px sans-serif";

  for (let i = 0; i <= 10; i++) {
    const label = i * 10;
    ctx.fillText(`${label}`, x(label) - 10, padding.top + chartHeight + 20);
    ctx.fillText(`${label}%`, 10, y(label) + 4);
  }

  ctx.fillStyle = "rgba(255,255,255,0.9)";
  ctx.fillText("Temp (°C)", curveCanvas.width / 2 - 28, curveCanvas.height - 8);

  ctx.save();
  ctx.translate(16, curveCanvas.height / 2 + 20);
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
    ctx.strokeStyle = "#0f152a";
    ctx.stroke();
  });
}

async function saveCurveConfig() {
  const payload = {
    temp_curve: getCurvePointsFromState(),
    curve_edge_colors: {
      start: curveStartColor.value,
      end: curveEndColor.value,
    },
  };

  const response = await fetchJson("/ui/config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  state.ui_config = response.ui_config;
  renderCurveEditor();
  drawCurve();
}

refreshBtn.addEventListener("click", loadAllState);

addPointBtn.addEventListener("click", () => {
  state.ui_config.temp_curve.push({ temp: 70, speed: 100 });
  renderCurveEditor();
  drawCurve();
});

saveCurveBtn.addEventListener("click", saveCurveConfig);

loadAllState();
setInterval(refreshSensorOnly, 2000);