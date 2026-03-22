# app.py
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

# Core logic modified to emulate the exact list-based JSON structure
SCHEDULE_DATA = [
    {
        "id": 1,
        "start_time": 0,
        "end_time": 60,
        "day": 1,
        "displayed_color": "00ff00",
        "commands": ["$led set_hsv 85 255 255"]
    },
    {
        "id": 2,
        "start_time": 720,
        "end_time": 780,
        "day": 3,
        "displayed_color": "FF00FF",
        "commands": ["$led set_rgb 255 0 0", "$led turn_off"]
    }
]


@app.route('/schedule')
def home():
    return render_template('schedule.html')


@app.route('/schedule/json')
def schedule_json():
    # Because SCHEDULE_DATA is now a list, this automatically
    # returns a JSON array: [{...}, {...}]
    return jsonify(SCHEDULE_DATA)


@app.route('/schedule/set', methods=['POST'])
def schedule_set():
    global SCHEDULE_DATA
    single_event = request.get_json()

    if single_event:
        event_id = single_event.get("id")

        # Ensure ID is treated as an integer (if provided by front-end as string)
        if event_id is not None:
            try:
                event_id = int(event_id)
                single_event["id"] = event_id
            except ValueError:
                event_id = None  # Force generation of a new ID if it's invalid

        # Find the index of the event if it already exists
        existing_idx = next((index for (index, d) in enumerate(SCHEDULE_DATA) if d["id"] == event_id), None)

        if existing_idx is None:
            # New event: Find the highest existing integer ID and add 1
            new_id = max([e["id"] for e in SCHEDULE_DATA], default=0) + 1
            single_event["id"] = new_id
            event_id = new_id
            SCHEDULE_DATA.append(single_event)
        else:
            # Update the existing event in the list
            SCHEDULE_DATA[existing_idx] = single_event

        print(f"\n=== EVENT {event_id} SET ===")
        print(single_event)
        print("============================\n")
        return jsonify({"status": "success", "id": event_id}), 200

    return jsonify({"status": "error", "message": "Invalid event payload"}), 400


@app.route('/schedule/delete', methods=['POST'])
def schedule_delete():
    global SCHEDULE_DATA
    payload = request.get_json()

    if payload and "id" in payload:
        try:
            event_id = int(payload["id"])

            # Rebuild the list excluding the deleted event
            initial_len = len(SCHEDULE_DATA)
            SCHEDULE_DATA = [event for event in SCHEDULE_DATA if event["id"] != event_id]

            if len(SCHEDULE_DATA) < initial_len:
                print(f"\n=== EVENT {event_id} DELETED ===")
                print("================================\n")

            return jsonify({"status": "success"}), 200
        except ValueError:
            return jsonify({"status": "error", "message": "Invalid ID format"}), 400

    return jsonify({"status": "error", "message": "Missing ID"}), 400


if __name__ == '__main__':
    app.run(debug=True)