from copy import deepcopy
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# Raw backend data only.
# Backend stays lean:
# - serve raw data
# - accept UI config updates
# - no derived summary
# - no helper functions
# - no backend-side calculations for display

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


@app.route("/")
def index():
    """
    Serves the dashboard page.
    Frontend logic lives in templates/index.html + static/script.js.
    """
    return render_template("index.html")


@app.route("/api/state", methods=["GET"])
def api_state():
    """
    Single dashboard bootstrap / refresh endpoint.

    Returns only raw data blocks:
    - fan_data
    - argb_data
    - sensor_data
    - ui_config

    Frontend is responsible for all derived values and display calculations.
    """
    return jsonify(
        {
            "fan_data": deepcopy(FAN_DATA),
            "argb_data": deepcopy(ARGB_DATA),
            "sensor_data": deepcopy(MLX90614_DATA),
            "ui_config": deepcopy(UI_CONFIG),
        }
    )


@app.route("/fan/data", methods=["GET"])
def fan_data():
    """
    Raw fan endpoint.

    Read-only for this UI version.
    Returns backend fan structure exactly as stored.
    """
    return jsonify(deepcopy(FAN_DATA))


@app.route("/argb/data", methods=["GET"])
def argb_data():
    """
    Raw ARGB endpoint.

    Read-only for this UI version.
    Returns backend ARGB strip structure exactly as stored.
    """
    return jsonify(deepcopy(ARGB_DATA))


@app.route("/mlx90614/data", methods=["GET"])
def mlx90614_data():
    """
    Raw sensor endpoint.

    Read-only.
    Returns the MLX90614 payload exactly as stored.
    """
    return jsonify(deepcopy(MLX90614_DATA))


@app.route("/ui/config", methods=["GET", "POST"])
def ui_config():
    """
    UI-owned writable config endpoint.

    GET:
    - returns current UI config

    POST:
    - updates temp curve points
    - updates the 2 curve edge colors

    Expected payload:
    {
      "temp_curve": [{"temp": 25, "speed": 0}, ...],
      "curve_edge_colors": {"start": "#00c2ff", "end": "#ff5a7a"}
    }

    Notes for embedded port:
    - this is the only writable endpoint
    - hardware data endpoints remain read-only
    - frontend should send already-sanitized values
    """
    if request.method == "GET":
        return jsonify(deepcopy(UI_CONFIG))

    payload = request.get_json(silent=True) or {}

    if "temp_curve" in payload and isinstance(payload["temp_curve"], list):
        cleaned_curve = []

        for point in payload["temp_curve"]:
            if not isinstance(point, dict):
                continue
            if "temp" not in point or "speed" not in point:
                continue

            try:
                temp = int(point["temp"])
                speed = int(point["speed"])
            except (TypeError, ValueError):
                continue

            cleaned_curve.append({"temp": temp, "speed": speed})

        if len(cleaned_curve) >= 2:
            cleaned_curve.sort(key=lambda p: p["temp"])
            UI_CONFIG["temp_curve"] = cleaned_curve

    if "curve_edge_colors" in payload and isinstance(payload["curve_edge_colors"], dict):
        colors = payload["curve_edge_colors"]

        if "start" in colors and isinstance(colors["start"], str):
            UI_CONFIG["curve_edge_colors"]["start"] = colors["start"]

        if "end" in colors and isinstance(colors["end"], str):
            UI_CONFIG["curve_edge_colors"]["end"] = colors["end"]

    return jsonify({"ok": True, "ui_config": deepcopy(UI_CONFIG)})


if __name__ == "__main__":
    app.run(debug=True)