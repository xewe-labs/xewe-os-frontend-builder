#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h> // Ensure you have ArduinoJson v6 or v7 installed
#include <map>
#include <vector>
#include <algorithm>

const char* ssid = "XeWe Labs";
const char* password = "Buildcoolshit";

WebServer server(80);

// --- State Management ---
// Main state for the Fan/ARGB Controller
std::map<String, String> appState;

// Generic state to fulfill the strict POST/DELETE ID rules requested
std::map<String, String> SCHEDULE_DATA;

// --- Auto-Generated Web Files ---
// (Assume these are included correctly in your environment)
#include "templates/index_html.h"
#include "static/styles_css.h"
#include "static/script_js.h"
// --------------------------------

// --- Helpers ---
void sendCORSHeaders() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.sendHeader("Access-Control-Allow-Methods", "POST, GET, OPTIONS, DELETE, PUT");
  server.sendHeader("Access-Control-Allow-Headers", "Content-Type");
}

void initData() {
  // Populate the default data exactly as it appears in the Flask app
  appState["fan_data"] = "{\"fans\":[{\"pin_pwm\":3,\"has_tach\":true,\"speed\":0,\"pin_tach\":0,\"displayed_rpm\":0,\"ema_rpm\":0},{\"pin_pwm\":10,\"has_tach\":true,\"speed\":0,\"pin_tach\":1,\"displayed_rpm\":0,\"ema_rpm\":0}]}";

  appState["argb_data"] = "[{\"pin\":6,\"state\":false,\"r\":255,\"g\":255,\"b\":255},{\"pin\":7,\"state\":false,\"r\":255,\"g\":255,\"b\":255}]";

  appState["sensor_data"] = "{\"module\":\"MLX90614\",\"online\":true,\"object_temp\":23.79001,\"ambient_temp\":30.35001,\"i2c_address\":90,\"sda_pin\":4,\"scl_pin\":5}";

  appState["ui_config"] = "{\"temp_curve\":[{\"temp\":25,\"speed\":0},{\"temp\":35,\"speed\":25},{\"temp\":45,\"speed\":45},{\"temp\":55,\"speed\":70},{\"temp\":65,\"speed\":100}],\"curve_edge_colors\":{\"start\":\"#00c2ff\",\"end\":\"#ff5a7a\"}}";
}

// Struct for sorting the temp curve
struct TempPoint {
  int temp;
  int speed;
  bool operator<(const TempPoint& other) const {
    return temp < other.temp;
  }
};

void setupRoutes() {
  // --- Static File Routing ---
  server.on("/", HTTP_GET, []() {
    Serial.println("[GET] / (index.html)");
    sendCORSHeaders();
    server.send_P(200, "text/html", INDEX_HTML);
  });

  server.on("/static/styles.css", HTTP_GET, []() {
    Serial.println("[GET] /static/styles.css");
    sendCORSHeaders();
    server.send_P(200, "text/css", STYLES_CSS);
  });

  server.on("/static/script.js", HTTP_GET, []() {
    Serial.println("[GET] /static/script.js");
    sendCORSHeaders();
    server.send_P(200, "application/javascript", SCRIPT_JS);
  });

  // Catch for unresolved Flask Jinja tags
  server.on("/%7B%7B%20url_for('static',%20filename='style.css')%20%7D%7D", HTTP_GET, []() {
    Serial.println("[GET] Jinja Tag Catch -> serving styles.css");
    sendCORSHeaders();
    server.send_P(200, "text/css", STYLES_CSS);
  });

  // --- API Endpoints ---

  // 1. GET (JSON): Iterate through map, package into single JSON, and send.
  server.on("/api/state", HTTP_GET, []() {
    Serial.println("[GET] /api/state");
    sendCORSHeaders();

    JsonDocument doc;

    // Deserialize strings from the map and add to the master JSON
    for (const auto& pair : appState) {
      JsonDocument tempDoc;
      deserializeJson(tempDoc, pair.second);
      doc[pair.first] = tempDoc;
    }

    String response;
    serializeJson(doc, response);
    server.send(200, "application/json", response);
  });

  server.on("/fan/data", HTTP_GET, []() {
    Serial.println("[GET] /fan/data");
    sendCORSHeaders();
    server.send(200, "application/json", appState["fan_data"]);
  });

  server.on("/argb/data", HTTP_GET, []() {
    Serial.println("[GET] /argb/data");
    sendCORSHeaders();
    server.send(200, "application/json", appState["argb_data"]);
  });

  server.on("/mlx90614/data", HTTP_GET, []() {
    Serial.println("[GET] /mlx90614/data");
    sendCORSHeaders();
    server.send(200, "application/json", appState["sensor_data"]);
  });

  server.on("/ui/config", HTTP_GET, []() {
    Serial.println("[GET] /ui/config");
    sendCORSHeaders();
    server.send(200, "application/json", appState["ui_config"]);
  });

  // Emulated Flask Logic for UI Config (Writable Endpoint)
  server.on("/ui/config", HTTP_POST, []() {
    Serial.println("[POST] /ui/config");
    sendCORSHeaders();

    String payload = server.arg("plain");
    JsonDocument incoming;
    DeserializationError err = deserializeJson(incoming, payload);

    if (err) {
      server.send(400, "application/json", "{\"error\":\"Invalid JSON\"}");
      return;
    }

    JsonDocument currentConfig;
    deserializeJson(currentConfig, appState["ui_config"]);

    // Process temp_curve
    if (incoming.containsKey("temp_curve") && incoming["temp_curve"].is<JsonArray>()) {
      JsonArray incCurve = incoming["temp_curve"].as<JsonArray>();
      std::vector<TempPoint> points;

      for (JsonVariant v : incCurve) {
        if (v.containsKey("temp") && v.containsKey("speed")) {
          points.push_back({v["temp"].as<int>(), v["speed"].as<int>()});
        }
      }

      if (points.size() >= 2) {
        std::sort(points.begin(), points.end()); // Sort by temp

        JsonArray updatedCurve = currentConfig["temp_curve"].to<JsonArray>();
        updatedCurve.clear();
        for (const auto& p : points) {
          JsonObject obj = updatedCurve.add<JsonObject>();
          obj["temp"] = p.temp;
          obj["speed"] = p.speed;
        }
      }
    }

    // Process curve_edge_colors
    if (incoming.containsKey("curve_edge_colors") && incoming["curve_edge_colors"].is<JsonObject>()) {
      JsonObject incColors = incoming["curve_edge_colors"].as<JsonObject>();
      if (incColors.containsKey("start")) {
        currentConfig["curve_edge_colors"]["start"] = incColors["start"].as<String>();
      }
      if (incColors.containsKey("end")) {
        currentConfig["curve_edge_colors"]["end"] = incColors["end"].as<String>();
      }
    }

    String updatedJson;
    serializeJson(currentConfig, updatedJson);
    appState["ui_config"] = updatedJson; // Save back to state map

    // Send response exactly like Flask
    String response = "{\"ok\":true,\"ui_config\":" + updatedJson + "}";
    server.send(200, "application/json", response);
  });

  // --- STRICT RULE IMPLEMENTATION: POST (Set) and POST (Delete) via generic map ---
  // This fulfills the ID max/iteration and Map erase() rules from your prompt.
  server.on("/api/schedule", HTTP_POST, []() {
    Serial.println("[POST] /api/schedule (Set)");
    sendCORSHeaders();

    String payload = server.arg("plain");
    JsonDocument doc;
    deserializeJson(doc, payload);

    String id = doc["id"].as<String>();

    if (id == "null" || id == "0" || id.isEmpty()) {
      // Find maximum integer ID
      int maxId = 0;
      for (const auto& pair : SCHEDULE_DATA) {
        int currentId = pair.first.toInt();
        if (currentId > maxId) {
          maxId = currentId;
        }
      }

      String newId = String(maxId + 1);
      doc["id"] = newId;

      String serializedItem;
      serializeJson(doc, serializedItem);
      SCHEDULE_DATA[newId] = serializedItem; // Save to map

      server.send(200, "application/json", serializedItem);
    } else {
      // Existing item update
      String serializedItem;
      serializeJson(doc, serializedItem);
      SCHEDULE_DATA[id] = serializedItem;
      server.send(200, "application/json", serializedItem);
    }
  });

  server.on("/api/schedule", HTTP_DELETE, []() {
    Serial.println("[DELETE] /api/schedule");
    sendCORSHeaders();

    String payload = server.arg("plain");
    JsonDocument doc;
    deserializeJson(doc, payload);

    String id = doc["id"].as<String>();
    SCHEDULE_DATA.erase(id); // POST (Delete) Strict Rule

    server.send(200, "application/json", "{\"deleted\":true}");
  });

  // --- CORS Preflight and 404 Handling ---
  server.onNotFound([]() {
    if (server.method() == HTTP_OPTIONS) {
      Serial.println("[OPTIONS] Preflight request acknowledged");
      sendCORSHeaders();
      server.send(204); // No Content
    } else {
      Serial.print("[404] Route Missed: ");
      Serial.println(server.uri());
      sendCORSHeaders();
      server.send(404, "text/plain", "Not Found");
    }
  });
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  // Setup WiFi
  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected.");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());

  initData();
  setupRoutes();

  server.begin();
  Serial.println("Web server started.");
}

void loop() {
  server.handleClient();
}