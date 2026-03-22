from copy import deepcopy
import math
import time

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# -------------------------------------------------------------------
# Embedded backend data
# -------------------------------------------------------------------
FAN_DATA = {
    "fans": [
        {
            "pin_pwm": 3,
            "has_tach": True,
            "speed": 0,
            "pin_tach": 0,
            "displayed_rpm": 0,
            "ema_rpm": 0,
        },
        {
            "pin_pwm": 10,
            "has_tach": True,
            "speed": 0,
            "pin_tach": 1,
            "displayed_rpm": 0,
            "ema_rpm": 0,
        },
    ]
}

ARGB_DATA = [
    {"pin": 6, "state": False, "r": 255, "g": 255, "b": 255},
    {"pin": 7, "state": False, "r": 255, "g": 255, "b": 255},
]

MLX90614_DATA = {
    "module": "MLX90614",
    "online": True,
    "object_temp": 23.79001,
    "ambient_temp": 30.35001,
    "i2c_address": 90,
    "sda_pin": 4,
    "scl_pin": 5,
}

UI_CONFIG = {
    "temp_curve": [
        {"temp": 25, "speed": 20},
        {"temp": 35, "speed": 35},
        {"temp": 45, "speed": 55},
        {"temp": 55, "speed": 75},
        {"temp": 65, "speed": 100},
    ],
    "curve_edge_colors": {
        "start": "#00c2ff",
        "end": "#ff4d6d",
    },
}

APP_START = time.time()


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def clamp(value, min_value, max_value):
    return max(min_value, min(max_value, value))


def update_fan_metrics(index, speed):
    fan = FAN_DATA["fans"][index]
    speed = int(clamp(speed, 0, 100))
    fan["speed"] = speed

    if speed == 0:
        rpm = 0
    else:
        rpm = int(300 + (speed / 100.0) * 2500)

    previous_ema = fan["ema_rpm"]
    ema = int((previous_ema * 0.7) + (rpm * 0.3)) if previous_ema else rpm

    fan["displayed_rpm"] = rpm
    fan["ema_rpm"] = ema


def simulate_sensor():
    """
    Dummy sensor behavior:
    - Higher average fan speed gradually lowers object temp.
    - Ambient temp moves more slowly.
    - Adds a tiny oscillation so the UI looks alive.
    """
    avg_speed = sum(f["speed"] for f in FAN_DATA["fans"]) / max(len(FAN_DATA["fans"]), 1)
    elapsed = time.time() - APP_START

    current_object = MLX90614_DATA["object_temp"]
    current_ambient = MLX90614_DATA["ambient_temp"]

    target_object = max(20.0, 36.0 - (avg_speed * 0.09))
    target_ambient = max(24.0, 30.35 - (avg_speed * 0.025))

    MLX90614_DATA["object_temp"] = current_object + (target_object - current_object) * 0.12
    MLX90614_DATA["ambient_temp"] = current_ambient + (target_ambient - current_ambient) * 0.05

    snapshot = deepcopy(MLX90614_DATA)
    snapshot["object_temp"] = round(snapshot["object_temp"] + math.sin(elapsed / 4.0) * 0.12, 2)
    snapshot["ambient_temp"] = round(snapshot["ambient_temp"] + math.cos(elapsed / 7.0) * 0.08, 2)
    return snapshot


def get_full_state():
    return {
        "fan_data": deepcopy(FAN_DATA),
        "argb_data": deepcopy(ARGB_DATA),
        "sensor_data": simulate_sensor(),
        "ui_config": deepcopy(UI_CONFIG),
    }


def normalize_hex_color(value, default="#ffffff"):
    if not isinstance(value, str):
        return default
    value = value.strip()
    if not value.startswith("#"):
        value = f"#{value}"
    if len(value) != 7:
        return default
    try:
        int(value[1:], 16)
        return value.lower()
    except ValueError:
        return default


# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/state", methods=["GET"])
def api_state():
    return jsonify(get_full_state())


@app.route("/fan/data", methods=["GET", "POST"])
def fan_data():
    if request.method == "GET":
        return jsonify(deepcopy(FAN_DATA))

    payload = request.get_json(silent=True) or {}

    if "index" in payload and "speed" in payload:
        index = int(payload["index"])
        if 0 <= index < len(FAN_DATA["fans"]):
            update_fan_metrics(index, payload["speed"])
        return jsonify({"ok": True, "fan_data": deepcopy(FAN_DATA)})

    if "fans" in payload and isinstance(payload["fans"], list):
        for idx, item in enumerate(payload["fans"]):
            if idx >= len(FAN_DATA["fans"]):
                break
            if isinstance(item, dict) and "speed" in item:
                update_fan_metrics(idx, item["speed"])
        return jsonify({"ok": True, "fan_data": deepcopy(FAN_DATA)})

    return jsonify({"ok": False, "error": "Invalid fan payload"}), 400


@app.route("/argb/data", methods=["GET", "POST"])
def argb_data():
    if request.method == "GET":
        return jsonify(deepcopy(ARGB_DATA))

    payload = request.get_json(silent=True) or {}

    if "index" in payload:
        index = int(payload["index"])
        if 0 <= index < len(ARGB_DATA):
            zone = ARGB_DATA[index]
            zone["state"] = bool(payload.get("state", zone["state"]))
            zone["r"] = int(clamp(payload.get("r", zone["r"]), 0, 255))
            zone["g"] = int(clamp(payload.get("g", zone["g"]), 0, 255))
            zone["b"] = int(clamp(payload.get("b", zone["b"]), 0, 255))
            return jsonify({"ok": True, "argb_data": deepcopy(ARGB_DATA)})

    if "zones" in payload and isinstance(payload["zones"], list):
        for idx, item in enumerate(payload["zones"]):
            if idx >= len(ARGB_DATA):
                break
            if not isinstance(item, dict):
                continue
            zone = ARGB_DATA[idx]
            zone["state"] = bool(item.get("state", zone["state"]))
            zone["r"] = int(clamp(item.get("r", zone["r"]), 0, 255))
            zone["g"] = int(clamp(item.get("g", zone["g"]), 0, 255))
            zone["b"] = int(clamp(item.get("b", zone["b"]), 0, 255))
        return jsonify({"ok": True, "argb_data": deepcopy(ARGB_DATA)})

    return jsonify({"ok": False, "error": "Invalid ARGB payload"}), 400


@app.route("/mlx90614/data", methods=["GET"])
def mlx90614_data():
    return jsonify(simulate_sensor())


@app.route("/ui/config", methods=["GET", "POST"])
def ui_config():
    if request.method == "GET":
        return jsonify(deepcopy(UI_CONFIG))

    payload = request.get_json(silent=True) or {}

    if "temp_curve" in payload:
        curve = payload["temp_curve"]
        if not isinstance(curve, list) or len(curve) < 2:
            return jsonify({"ok": False, "error": "temp_curve must contain at least 2 points"}), 400

        cleaned_curve = []
        for point in curve:
            if not isinstance(point, dict):
                continue
            temp = int(clamp(point.get("temp", 25), 0, 100))
            speed = int(clamp(point.get("speed", 0), 0, 100))
            cleaned_curve.append({"temp": temp, "speed": speed})

        if len(cleaned_curve) < 2:
            return jsonify({"ok": False, "error": "Not enough valid curve points"}), 400

        cleaned_curve.sort(key=lambda p: p["temp"])
        UI_CONFIG["temp_curve"] = cleaned_curve

    if "curve_edge_colors" in payload and isinstance(payload["curve_edge_colors"], dict):
        colors = payload["curve_edge_colors"]
        UI_CONFIG["curve_edge_colors"]["start"] = normalize_hex_color(
            colors.get("start", UI_CONFIG["curve_edge_colors"]["start"]),
            UI_CONFIG["curve_edge_colors"]["start"],
        )
        UI_CONFIG["curve_edge_colors"]["end"] = normalize_hex_color(
            colors.get("end", UI_CONFIG["curve_edge_colors"]["end"]),
            UI_CONFIG["curve_edge_colors"]["end"],
        )

    return jsonify({"ok": True, "ui_config": deepcopy(UI_CONFIG)})


if __name__ == "__main__":
    app.run(debug=True)