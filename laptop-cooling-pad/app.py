from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request, send_from_directory

BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)

# Embedded dummy backend data
INITIAL_FAN_DATA = {
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

INITIAL_ARGB_DATA = [
    {"pin": 6, "state": False, "r": 255, "g": 255, "b": 255},
    {"pin": 7, "state": False, "r": 255, "g": 255, "b": 255},
]

INITIAL_SENSOR_DATA = {
    "module": "MLX90614",
    "online": True,
    "object_temp": 23.79001,
    "ambient_temp": 30.35001,
    "i2c_address": 90,
    "sda_pin": 4,
    "scl_pin": 5,
}

INITIAL_TEMP_CONTROLLER_DATA = {
    "cold_color": "#0000FF",
    "hot_color": "#FF0000",
    "curve": [{"temp": 41, "fan_speed": 50}],
}

STATE = {
    "fan_data": deepcopy(INITIAL_FAN_DATA),
    "argb_data": deepcopy(INITIAL_ARGB_DATA),
    "sensor_data": deepcopy(INITIAL_SENSOR_DATA),
    "temp_controller": deepcopy(INITIAL_TEMP_CONTROLLER_DATA),
}


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    color = color.strip().lstrip("#")
    if len(color) != 6:
        raise ValueError("Color must be a 6-digit hex value.")
    return tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#" + "".join(f"{clamp(int(channel), 0, 255):02X}" for channel in rgb)


def normalize_curve(curve: list[dict[str, Any]]) -> list[dict[str, int]]:
    normalized: list[dict[str, int]] = []
    for point in curve:
        temp = int(round(float(point["temp"])))
        fan_speed = int(round(float(point["fan_speed"])))
        normalized.append(
            {
                "temp": temp,
                "fan_speed": int(clamp(fan_speed, 0, 100)),
            }
        )
    normalized.sort(key=lambda item: item["temp"])
    return normalized


def interpolate(a: float, b: float, ratio: float) -> float:
    return a + (b - a) * ratio


def fan_speed_from_curve(temp: float, curve: list[dict[str, int]]) -> int:
    if not curve:
        return 0

    if len(curve) == 1:
        return curve[0]["fan_speed"] if temp >= curve[0]["temp"] else 0

    if temp <= curve[0]["temp"]:
        return curve[0]["fan_speed"]

    for left, right in zip(curve, curve[1:]):
        if left["temp"] <= temp <= right["temp"]:
            span = max(1, right["temp"] - left["temp"])
            ratio = (temp - left["temp"]) / span
            return int(round(interpolate(left["fan_speed"], right["fan_speed"], ratio)))

    return curve[-1]["fan_speed"]


def color_from_temp(temp: float, curve: list[dict[str, int]], cold_color: str, hot_color: str) -> str:
    cold_rgb = hex_to_rgb(cold_color)
    hot_rgb = hex_to_rgb(hot_color)

    if not curve:
        return cold_color.upper()

    if len(curve) == 1:
        ratio = 1.0 if temp >= curve[0]["temp"] else 0.0
    else:
        low_temp = curve[0]["temp"]
        high_temp = curve[-1]["temp"]
        if high_temp == low_temp:
            ratio = 1.0 if temp >= high_temp else 0.0
        else:
            ratio = clamp((temp - low_temp) / (high_temp - low_temp), 0.0, 1.0)

    mixed = tuple(int(round(interpolate(cold_rgb[i], hot_rgb[i], ratio))) for i in range(3))
    return rgb_to_hex(mixed)


def sync_runtime_state() -> None:
    controller = STATE["temp_controller"]
    sensor = STATE["sensor_data"]
    fans = STATE["fan_data"]["fans"]
    strips = STATE["argb_data"]

    curve = normalize_curve(controller["curve"])
    controller["curve"] = curve

    object_temp = float(sensor["object_temp"])
    shared_speed = fan_speed_from_curve(object_temp, curve)
    current_color = color_from_temp(
        object_temp,
        curve,
        controller["cold_color"],
        controller["hot_color"],
    )
    r, g, b = hex_to_rgb(current_color)

    for fan in fans:
        fan["speed"] = shared_speed
        fan["displayed_rpm"] = shared_speed * 50
        fan["ema_rpm"] = fan["displayed_rpm"]

    for strip in strips:
        strip["state"] = shared_speed > 0
        strip["r"] = r
        strip["g"] = g
        strip["b"] = b


sync_runtime_state()


@app.route("/")
def index() -> Any:
    return send_from_directory(BASE_DIR, "templates/index.html")


@app.route("/styles.css")
def styles() -> Any:
    return send_from_directory(BASE_DIR, "static/styles.css")


@app.route("/script.js")
def script() -> Any:
    return send_from_directory(BASE_DIR, "static/script.js")


@app.get("/fan/data")
def get_fan_data() -> Any:
    sync_runtime_state()
    return jsonify(STATE["fan_data"])


@app.get("/argb/data")
def get_argb_data() -> Any:
    sync_runtime_state()
    return jsonify(STATE["argb_data"])


@app.get("/mlx90614/data")
def get_sensor_data() -> Any:
    return jsonify(STATE["sensor_data"])


@app.get("/temp_controller/data")
def get_temp_controller_data() -> Any:
    sync_runtime_state()
    return jsonify(STATE["temp_controller"])


@app.post("/temp_controller/data")
def update_temp_controller_data() -> Any:
    payload = request.get_json(silent=True) or {}

    cold_color = str(payload.get("cold_color", STATE["temp_controller"]["cold_color"])).strip()
    hot_color = str(payload.get("hot_color", STATE["temp_controller"]["hot_color"])).strip()
    curve = payload.get("curve", STATE["temp_controller"]["curve"])

    if not isinstance(curve, list) or not curve:
        return jsonify({"error": "curve must be a non-empty array"}), 400

    try:
        hex_to_rgb(cold_color)
        hex_to_rgb(hot_color)
        normalized_curve = normalize_curve(curve)
    except (ValueError, KeyError, TypeError):
        return jsonify({"error": "invalid payload"}), 400

    STATE["temp_controller"] = {
        "cold_color": "#" + cold_color.lstrip("#").upper(),
        "hot_color": "#" + hot_color.lstrip("#").upper(),
        "curve": normalized_curve,
    }
    sync_runtime_state()
    return jsonify(STATE["temp_controller"])


@app.get("/dashboard/data")
def get_dashboard_data() -> Any:
    sync_runtime_state()
    fans = STATE["fan_data"]["fans"]
    argb = STATE["argb_data"]
    controller = STATE["temp_controller"]
    current_color = rgb_to_hex((argb[0]["r"], argb[0]["g"], argb[0]["b"]))

    return jsonify(
        {
            "sensor": STATE["sensor_data"],
            "fans": STATE["fan_data"],
            "argb": STATE["argb_data"],
            "temp_controller": controller,
            "summary": {
                "laptop_temp": STATE["sensor_data"]["object_temp"],
                "sensor_temp": STATE["sensor_data"]["ambient_temp"],
                "fan_1_speed": fans[0]["speed"] if fans else 0,
                "fan_2_speed": fans[1]["speed"] if len(fans) > 1 else 0,
                "current_color": current_color,
                "argb_enabled": any(strip["state"] for strip in argb),
            },
        }
    )


@app.post("/dashboard/simulate_temp")
def simulate_temp() -> Any:
    payload = request.get_json(silent=True) or {}
    try:
        object_temp = float(payload.get("object_temp", STATE["sensor_data"]["object_temp"]))
    except (TypeError, ValueError):
        return jsonify({"error": "object_temp must be numeric"}), 400

    STATE["sensor_data"]["object_temp"] = round(object_temp, 2)
    sync_runtime_state()
    return jsonify(STATE["sensor_data"])


if __name__ == "__main__":
    app.run(debug=True)
