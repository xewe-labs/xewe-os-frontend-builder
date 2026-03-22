#include <WiFi.h>
#include <WebServer.h>

WebServer server(80);

// --- Auto-Generated Web Files ---
#include "templates/index_html.h"
#include "static/styles_css.h"
#include "static/script_js.h"
// --------------------------------

void setupRoutes() {
  // --- Auto-Generated Routes ---
  server.on("/", HTTP_GET, []() {
    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.send_P(200, "text/html", INDEX_HTML);
  });
  server.on("/static/styles.css", HTTP_GET, []() {
    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.send_P(200, "text/css", STYLES_CSS);
  });
  server.on("/static/script.js", HTTP_GET, []() {
    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.send_P(200, "application/javascript", SCRIPT_JS);
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
