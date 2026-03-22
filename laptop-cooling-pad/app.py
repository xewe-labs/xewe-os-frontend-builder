from copy import deepcopy
import math
import time

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# ------------------------------------------------------------
# Embedded backend data
# ------------------------------------------------------------
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
        {"temp": 25, "speed": 0},
        {"temp": 35, "speed": 25},
        {"temp": 45, "speed": 45},
        {"temp": 55, "speed": 70},
        {"temp": 65, "speed": 100},
    ],
    "curve_edge_colors": {
        "start": "#00c2ff",
        "end": "#ff5a7a",
    },
}

APP_START = time.time()


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def rgb_to_hex(r, g, b):
    return "#{:02x}{:02x}{:02x}".format(
        int(clamp(r, 0, 255)),
        int(clamp(g, 0, 255)),
        int(clamp(b, 0, 255)),
    )


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


def hex_to_rgb(value):
    value = normalize_hex_color(value, "#ffffff")
    return {
        "r": int(value[1:3], 16),
        "g": int(value[3:5], 16),
        "b": int(value[5:7], 16),
    }


def get_current_argb():
    zone = ARGB_DATA[0]
    return {
        "state": zone["state"],
        "r": zone["r"],
        "g": zone["g"],
        "b": zone["b"],
        "hex": rgb_to_hex(zone["r"], zone["g"], zone["b"]),
    }


def set_all_argb(state, r, g, b):
    for zone in ARGB_DATA:
        zone["state"] = bool(state)
        zone["r"] = int(clamp(r, 0, 255))
        zone["g"] = int(clamp(g, 0, 255))
        zone["b"] = int(clamp(b, 0, 255))


def set_all_fans(speed):
    speed = int(clamp(speed, 0, 100))

    for fan in FAN_DATA["fans"]:
        fan["speed"] = speed

        rpm = 0 if speed == 0 else int(400 + (speed / 100.0) * 2400)
        previous_ema = fan["ema_rpm"]
        ema = rpm if previous_ema == 0 else int(previous_ema * 0.7 + rpm * 0.3)

        fan["displayed_rpm"] = rpm
        fan["ema_rpm"] = ema


def curve_speed_for_temp(temp, curve_points):
    points = sorted(curve_points, key=lambda x: x["temp"])

    if temp <= points[0]["temp"]:
        return int(points[0]["speed"])

    if temp >= points[-1]["temp"]:
        return int(points[-1]["speed"])

    for i in range(len(points) - 1):
        left = points[i]
        right = points[i + 1]

        if left["temp"] <= temp <= right["temp"]:
            span = right["temp"] - left["temp"]
            if span == 0:
                return int(right["speed"])

            ratio = (temp - left["temp"]) / span
            speed = left["speed"] + ratio * (right["speed"] - left["speed"])
            return int(round(speed))

    return int(points[-1]["speed"])


def simulate_sensor():
    """
    Dummy behavior:
    - Object temp drifts based on a fake heat load.
    - Fan curve automatically sets BOTH fans to the same speed.
    - Ambient temp moves more slowly.
    """
    elapsed = time.time() - APP_START
    current_fan_speed = FAN_DATA["fans"][0]["speed"]

    heat_wave = 31.5 + math.sin(elapsed / 7.0) * 5.5
    target_object = heat_wave - current_fan_speed * 0.08
    target_ambient = 29.5 + math.cos(elapsed / 9.0) * 1.2 - current_fan_speed * 0.015

    MLX90614_DATA["object_temp"] += (target_object - MLX90614_DATA["object_temp"]) * 0.08
    MLX90614_DATA["ambient_temp"] += (target_ambient - MLX90614_DATA["ambient_temp"]) * 0.04

    auto_speed = curve_speed_for_temp(
        MLX90614_DATA["object_temp"],
        UI_CONFIG["temp_curve"],
    )
    set_all_fans(auto_speed)

    snapshot = deepcopy(MLX90614_DATA)
    snapshot["object_temp"] = round(snapshot["object_temp"], 2)
    snapshot["ambient_temp"] = round(snapshot["ambient_temp"], 2)
    return snapshot


def get_summary():
    current_argb = get_current_argb()
    fan_rpms = [fan["displayed_rpm"] for fan in FAN_DATA["fans"]]
    shared_speed = FAN_DATA["fans"][0]["speed"] if FAN_DATA["fans"] else 0

    return {
        "laptop_temp": round(MLX90614_DATA["object_temp"], 2),
        "sensor_temp": round(MLX90614_DATA["ambient_temp"], 2),
        "fan_speed_percent": shared_speed,
        "fan1_rpm": fan_rpms[0] if len(fan_rpms) > 0 else 0,
        "fan2_rpm": fan_rpms[1] if len(fan_rpms) > 1 else 0,
        "color_hex": current_argb["hex"],
        "color_state": current_argb["state"],
        "color_rgb": {
            "r": current_argb["r"],
            "g": current_argb["g"],
            "b": current_argb["b"],
        },
    }


def get_full_state():
    sensor = simulate_sensor()
    return {
        "fan_data": deepcopy(FAN_DATA),
        "argb_data": deepcopy(ARGB_DATA),
        "sensor_data": sensor,
        "ui_config": deepcopy(UI_CONFIG),
        "summary": get_summary(),
    }


# ------------------------------------------------------------
# Routes
# ------------------------------------------------------------
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

    # Shared fan control only
    if "speed" not in payload:
        return jsonify({"ok": False, "error": "Expected shared speed"}), 400

    set_all_fans(payload["speed"])
    return jsonify({"ok": True, "fan_data": deepcopy(FAN_DATA)})


@app.route("/argb/data", methods=["GET", "POST"])
def argb_data():
    if request.method == "GET":
        return jsonify(deepcopy(ARGB_DATA))

    payload = request.get_json(silent=True) or {}

    color_hex = normalize_hex_color(payload.get("hex", "#ffffff"), "#ffffff")
    rgb = hex_to_rgb(color_hex)
    state = bool(payload.get("state", False))

    if "r" in payload:
        rgb["r"] = int(clamp(payload["r"], 0, 255))
    if "g" in payload:
        rgb["g"] = int(clamp(payload["g"], 0, 255))
    if "b" in payload:
        rgb["b"] = int(clamp(payload["b"], 0, 255))

    set_all_argb(state, rgb["r"], rgb["g"], rgb["b"])
    return jsonify({"ok": True, "argb_data": deepcopy(ARGB_DATA)})


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
            return jsonify({"ok": False, "error": "temp_curve must have at least 2 points"}), 400

        cleaned = []
        for point in curve:
            if not isinstance(point, dict):
                continue

            temp = int(clamp(point.get("temp", 0), 0, 100))
            speed = int(clamp(point.get("speed", 0), 0, 100))
            cleaned.append({"temp": temp, "speed": speed})

        if len(cleaned) < 2:
            return jsonify({"ok": False, "error": "Not enough valid curve points"}), 400

        cleaned.sort(key=lambda x: x["temp"])
        UI_CONFIG["temp_curve"] = cleaned

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