#include <WiFi.h>
#include <WebServer.h>

WebServer server(80);

// --- Auto-Generated Web Files ---
#include "templates/schedule_html.h"
#include "static/schedule_core_js.h"
#include "static/schedule_style_css.h"
#include "static/schedule_actions_js.h"
#include "static/schedule_interactions_js.h"
#include "static/schedule_utils_js.h"
#include "static/schedule_ui_js.h"
// --------------------------------

void setupRoutes() {
  // --- Auto-Generated Routes ---
  server.on("/templates/schedule.html", HTTP_GET, []() {
    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.send_P(200, "text/html", SCHEDULE_HTML);
  });
  server.on("/static/schedule-core.js", HTTP_GET, []() {
    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.send_P(200, "application/javascript", SCHEDULE_CORE_JS);
  });
  server.on("/static/schedule-style.css", HTTP_GET, []() {
    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.send_P(200, "text/css", SCHEDULE_STYLE_CSS);
  });
  server.on("/static/schedule-actions.js", HTTP_GET, []() {
    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.send_P(200, "application/javascript", SCHEDULE_ACTIONS_JS);
  });
  server.on("/static/schedule-interactions.js", HTTP_GET, []() {
    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.send_P(200, "application/javascript", SCHEDULE_INTERACTIONS_JS);
  });
  server.on("/static/schedule-utils.js", HTTP_GET, []() {
    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.send_P(200, "application/javascript", SCHEDULE_UTILS_JS);
  });
  server.on("/static/schedule-ui.js", HTTP_GET, []() {
    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.send_P(200, "application/javascript", SCHEDULE_UI_JS);
  });
}

void setup() {
  Serial.begin(115200);
  // TODO: Setup WiFi here

  setupRoutes();
  server.begin();
}

void loop() {
  server.handleClient();
}
