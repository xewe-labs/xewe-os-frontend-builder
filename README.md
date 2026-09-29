# xewe-os-frontend-builder — prototype a device web UI in Flask, export it to an ESP32 sketch

XeWe OS tooling (prototype) · 2026-03-22 → 2026-04-22 · Solo: Max Dokukin · Status: Prototype, not developed since 2026-04

## Overview

A workflow for building the web interface of an ESP32 device without writing it in C++ first. The
interface is prototyped as a small Flask app (`app.py` + `templates/` + `static/`) on a laptop,
where HTML, CSS and JavaScript can be iterated quickly against fake data. `export/export.py` then
converts every template and static file into a C++ `PROGMEM` header and generates an Arduino
sketch whose `WebServer` routes serve those files at the same URLs. The API logic of `app.py` is
ported to the sketch with an LLM, using the fixed prompt in `export/app_py_to_ino_prompt.txt`. It
was used to prototype and export the dashboard of the
[laptop cooling pad](https://github.com/xewe-labs/xewe-os-laptop-cooling-pad), a
[XeWe OS](https://github.com/xewe-labs/xewe-os) example build.

## Highlights

- One command turns a Flask project into a sketch folder: `.h` per HTML/CSS/JS file, preserved folder layout, one `server.on(...)` route per file with the right MIME type (`export/export.py`, 157 lines)
- Jinja `{{ url_for('static', filename=...) }}` references are rewritten to plain `/static/...` paths during export
- The porting prompt fixes the parts LLMs get wrong: hyphen-vs-underscore file names, MIME types, ArduinoJson GET/POST/DELETE handlers, CORS preflight (`OPTIONS` → 204), serial debug output
- The laptop-cooling-pad prototype: 6 routes (`/`, `/api/state`, `/fan/data`, `/argb/data`, `/mlx90614/data`, `/ui/config`) with 2 PWM fans, 2 ARGB strips, an MLX90614 IR temperature sensor and an editable fan curve; hardware endpoints are read-only, only the UI config is writable

## How it works

```
laptop-cooling-pad/ (Flask: app.py, templates/index.html, static/script.js, static/styles.css)
  → python export/export.py <flask project> <output dir>
  → <name>_<timestamp>/ {templates/*_html.h, static/*_{js,css}.h, app.py, <name>_app.ino}
  → LLM + export/app_py_to_ino_prompt.txt → one complete .ino with the API ported from app.py
```

- **`export/export.py`** — walks `templates/` and `static/`, keeps only `.html`, `.css`, `.js`, writes each as `static const char <NAME>_<EXT>[] PROGMEM = R"rawliteral(...)rawliteral";`, maps `templates/index.html` to `/`, copies `app.py`, and generates `<name>_app.ino` with `#include`s, `setupRoutes()` (each route sends `Access-Control-Allow-Origin: *`), `setup()` and `loop()`. WiFi setup is left as a `TODO` for the porting step.
- **`export/app_py_to_ino_prompt.txt`** — the prompt: state as `std::map<String, String>`, static-file routing, ArduinoJson endpoints mirroring Flask, a global CORS helper and `onNotFound` preflight handling, debug prints.
- **`laptop-cooling-pad/`** — the Flask prototype (191-line `app.py`, 745 lines of HTML/CSS/JS).
- **`export/laptop-cooling-pad/`, `export/exports/`** — committed export runs: four for the cooling pad (2026-03-22; the first includes an LLM-completed 279-line sketch) and one for a schedule UI (2026-03-20).

## Results

| Metric | Value | Baseline / note |
|---|---|---|
| Exporter | 157 lines of Python, standard library only | `export/export.py` |
| Porting prompt | 38 lines | `export/app_py_to_ino_prompt.txt` |
| Prototype | 191-line Flask app + 745 lines of HTML/CSS/JS | `laptop-cooling-pad/` |
| Export runs committed | 5 (4 cooling pad, 1 schedule) | folder names carry the timestamps |

A tooling prototype has no measured results; the table lists what exists.

## Getting started

```bash
git clone https://github.com/xewe-labs/xewe-os-frontend-builder
cd xewe-os-frontend-builder

# run the prototype locally (http://127.0.0.1:5000)
pip install flask
python laptop-cooling-pad/app.py

# export it into a sketch folder
python export/export.py laptop-cooling-pad export/laptop-cooling-pad
```

Then open the generated `<name>_app.ino`, give an LLM the prompt from
`export/app_py_to_ino_prompt.txt` with the sketch and `app.py` pasted where it says, set your own
WiFi network in the result, and build it with the Arduino IDE or `arduino-cli` (libraries: `WiFi`,
`WebServer`, ArduinoJson). Requirements: Python 3 with Flask for the prototype; the exporter needs
only the standard library.

## Documents

- [export/export.py](export/export.py) · [export/app_py_to_ino_prompt.txt](export/app_py_to_ino_prompt.txt)
- Device built with it: [xewe-os-laptop-cooling-pad](https://github.com/xewe-labs/xewe-os-laptop-cooling-pad)
- Firmware family: [xewe-os](https://github.com/xewe-labs/xewe-os) · organization: [github.com/xewe-labs](https://github.com/xewe-labs)
