const state = {
  dashboard: null,
};

const elements = {
  refreshButton: document.getElementById('refreshButton'),
  sensorStateBadge: document.getElementById('sensorStateBadge'),
  laptopTemp: document.getElementById('laptopTemp'),
  sensorTemp: document.getElementById('sensorTemp'),
  fan1Speed: document.getElementById('fan1Speed'),
  fan2Speed: document.getElementById('fan2Speed'),
  currentColor: document.getElementById('currentColor'),
  currentColorSwatch: document.getElementById('currentColorSwatch'),
  fanJson: document.getElementById('fanJson'),
  argbJson: document.getElementById('argbJson'),
  sensorJson: document.getElementById('sensorJson'),
  controllerJson: document.getElementById('controllerJson'),
  controllerForm: document.getElementById('controllerForm'),
  coldColor: document.getElementById('coldColor'),
  hotColor: document.getElementById('hotColor'),
  coldColorText: document.getElementById('coldColorText'),
  hotColorText: document.getElementById('hotColorText'),
  addPointButton: document.getElementById('addPointButton'),
  curveRows: document.getElementById('curveRows'),
  curveRowTemplate: document.getElementById('curveRowTemplate'),
  curveCanvas: document.getElementById('curveCanvas'),
  saveStatus: document.getElementById('saveStatus'),
  simulatedTemp: document.getElementById('simulatedTemp'),
  simulatedTempValue: document.getElementById('simulatedTempValue'),
};

function prettyJson(data) {
  return JSON.stringify(data, null, 2);
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function normalizeHexColor(value, fallback = '#0000FF') {
  const candidate = String(value || '').trim().toUpperCase();
  if (/^#[0-9A-F]{6}$/.test(candidate)) {
    return candidate;
  }
  return fallback;
}

function setStatus(message, type = '') {
  elements.saveStatus.textContent = message;
  elements.saveStatus.className = `save-status ${type}`.trim();
}

function createCurveRow(point = { temp: 40, fan_speed: 50 }) {
  const row = elements.curveRowTemplate.content.firstElementChild.cloneNode(true);
  row.querySelector('.curve-temp').value = point.temp;
  row.querySelector('.curve-speed').value = point.fan_speed;
  row.querySelector('.remove-point-button').addEventListener('click', () => {
    row.remove();
    if (!elements.curveRows.children.length) {
      createCurveRow();
    }
    drawCurve();
  });

  row.querySelectorAll('input').forEach((input) => {
    input.addEventListener('input', drawCurve);
  });

  elements.curveRows.appendChild(row);
  return row;
}

function getCurveFromForm() {
  return Array.from(elements.curveRows.querySelectorAll('.curve-row'))
    .map((row) => ({
      temp: Number(row.querySelector('.curve-temp').value),
      fan_speed: Number(row.querySelector('.curve-speed').value),
    }))
    .filter((point) => Number.isFinite(point.temp) && Number.isFinite(point.fan_speed))
    .sort((a, b) => a.temp - b.temp);
}

function fillCurveForm(curve) {
  elements.curveRows.innerHTML = '';
  (curve || []).forEach((point) => createCurveRow(point));
  if (!elements.curveRows.children.length) {
    createCurveRow();
  }
}

function drawCurve() {
  const canvas = elements.curveCanvas;
  const ctx = canvas.getContext('2d');
  const width = canvas.width;
  const height = canvas.height;
  const padding = { top: 24, right: 24, bottom: 38, left: 48 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const curve = getCurveFromForm();
  const coldColor = normalizeHexColor(elements.coldColorText.value, '#0000FF');
  const hotColor = normalizeHexColor(elements.hotColorText.value, '#FF0000');

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = '#0F172A';
  ctx.fillRect(0, 0, width, height);

  const temps = curve.map((point) => point.temp);
  const speeds = curve.map((point) => point.fan_speed);
  const minTemp = Math.min(...temps, 20);
  const maxTemp = Math.max(...temps, 100);
  const tempSpan = Math.max(1, maxTemp - minTemp);
  const speedMax = Math.max(100, ...speeds);

  ctx.strokeStyle = 'rgba(148, 163, 184, 0.18)';
  ctx.lineWidth = 1;
  for (let i = 0; i <= 5; i += 1) {
    const y = padding.top + (plotHeight / 5) * i;
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(width - padding.right, y);
    ctx.stroke();
  }

  ctx.beginPath();
  ctx.moveTo(padding.left, padding.top);
  ctx.lineTo(padding.left, height - padding.bottom);
  ctx.lineTo(width - padding.right, height - padding.bottom);
  ctx.strokeStyle = 'rgba(226, 232, 240, 0.35)';
  ctx.lineWidth = 1.5;
  ctx.stroke();

  ctx.fillStyle = 'rgba(148, 163, 184, 0.9)';
  ctx.font = '12px Inter, Arial, sans-serif';
  ctx.fillText('Fan speed %', 10, padding.top - 4);
  ctx.fillText('Temp °C', width - 78, height - 12);

  if (!curve.length) {
    return;
  }

  const points = curve.map((point) => {
    const x = padding.left + ((point.temp - minTemp) / tempSpan) * plotWidth;
    const y = height - padding.bottom - (clamp(point.fan_speed, 0, speedMax) / speedMax) * plotHeight;
    return { x, y, ...point };
  });

  const gradient = ctx.createLinearGradient(padding.left, 0, width - padding.right, 0);
  gradient.addColorStop(0, coldColor);
  gradient.addColorStop(1, hotColor);

  ctx.beginPath();
  points.forEach((point, index) => {
    if (index === 0) {
      ctx.moveTo(point.x, point.y);
    } else {
      ctx.lineTo(point.x, point.y);
    }
  });
  ctx.strokeStyle = gradient;
  ctx.lineWidth = 4;
  ctx.stroke();

  points.forEach((point, index) => {
    ctx.beginPath();
    ctx.arc(point.x, point.y, 6, 0, Math.PI * 2);
    ctx.fillStyle = index === 0 ? coldColor : index === points.length - 1 ? hotColor : '#E5E7EB';
    ctx.fill();
    ctx.strokeStyle = '#0B1120';
    ctx.lineWidth = 2;
    ctx.stroke();

    ctx.fillStyle = 'rgba(226, 232, 240, 0.9)';
    ctx.fillText(`${point.temp}°`, point.x - 12, height - padding.bottom + 18);
    ctx.fillText(`${point.fan_speed}%`, point.x - 14, point.y - 12);
  });
}

function applyControllerToForm(controller) {
  const cold = normalizeHexColor(controller.cold_color, '#0000FF');
  const hot = normalizeHexColor(controller.hot_color, '#FF0000');
  elements.coldColor.value = cold;
  elements.hotColor.value = hot;
  elements.coldColorText.value = cold;
  elements.hotColorText.value = hot;
  fillCurveForm(controller.curve || []);
  drawCurve();
}

function renderDashboard(data) {
  const { summary, fans, argb, sensor, temp_controller: controller } = data;
  state.dashboard = data;

  elements.laptopTemp.textContent = `${Number(summary.laptop_temp).toFixed(2)}°C`;
  elements.sensorTemp.textContent = `${Number(summary.sensor_temp).toFixed(2)}°C`;
  elements.fan1Speed.textContent = `${summary.fan_1_speed}%`;
  elements.fan2Speed.textContent = `${summary.fan_2_speed}%`;
  elements.currentColor.textContent = summary.current_color;
  elements.currentColorSwatch.style.background = summary.current_color;

  elements.sensorStateBadge.textContent = sensor.online ? 'Sensor online' : 'Sensor offline';
  elements.sensorStateBadge.className = `status-badge ${sensor.online ? 'online' : 'offline'}`;

  elements.fanJson.textContent = prettyJson(fans);
  elements.argbJson.textContent = prettyJson(argb);
  elements.sensorJson.textContent = prettyJson(sensor);
  elements.controllerJson.textContent = prettyJson(controller);

  elements.simulatedTemp.value = Math.round(sensor.object_temp);
  elements.simulatedTempValue.textContent = `${Math.round(sensor.object_temp)}°C`;

  applyControllerToForm(controller);
}

async function loadDashboard() {
  const response = await fetch('/dashboard/data');
  if (!response.ok) {
    throw new Error('Failed to load dashboard data');
  }
  const data = await response.json();
  renderDashboard(data);
}

async function saveController(event) {
  event.preventDefault();
  const payload = {
    cold_color: normalizeHexColor(elements.coldColorText.value, '#0000FF'),
    hot_color: normalizeHexColor(elements.hotColorText.value, '#FF0000'),
    curve: getCurveFromForm(),
  };

  if (!payload.curve.length) {
    setStatus('At least one curve point is required.', 'error');
    return;
  }

  const response = await fetch('/temp_controller/data', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Failed to save controller' }));
    setStatus(error.error || 'Failed to save controller', 'error');
    return;
  }

  setStatus('Controller updated.', 'success');
  await loadDashboard();
}

async function simulateTemperature() {
  const value = Number(elements.simulatedTemp.value);
  elements.simulatedTempValue.textContent = `${value}°C`;

  const response = await fetch('/dashboard/simulate_temp', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ object_temp: value }),
  });

  if (response.ok) {
    await loadDashboard();
  }
}

function bindColorMirrors(colorInput, textInput, fallback) {
  colorInput.addEventListener('input', () => {
    textInput.value = colorInput.value.toUpperCase();
    drawCurve();
  });

  textInput.addEventListener('input', () => {
    const normalized = normalizeHexColor(textInput.value, fallback);
    if (/^#[0-9A-F]{6}$/.test(String(textInput.value).trim().toUpperCase())) {
      colorInput.value = normalized;
    }
    drawCurve();
  });
}

function bindEvents() {
  elements.refreshButton.addEventListener('click', loadDashboard);
  elements.controllerForm.addEventListener('submit', saveController);
  elements.addPointButton.addEventListener('click', () => {
    createCurveRow();
    drawCurve();
  });

  elements.simulatedTemp.addEventListener('input', () => {
    elements.simulatedTempValue.textContent = `${elements.simulatedTemp.value}°C`;
  });
  elements.simulatedTemp.addEventListener('change', simulateTemperature);

  bindColorMirrors(elements.coldColor, elements.coldColorText, '#0000FF');
  bindColorMirrors(elements.hotColor, elements.hotColorText, '#FF0000');
}

async function init() {
  bindEvents();
  try {
    await loadDashboard();
  } catch (error) {
    console.error(error);
    setStatus('Could not load dashboard data.', 'error');
  }
}

init();
