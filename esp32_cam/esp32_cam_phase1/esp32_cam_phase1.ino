#include "esp_camera.h"
#include <ArduinoJson.h>
#include <WebServer.h>
#include <WiFi.h>

// AI Thinker ESP32-CAM pin map.
#define PWDN_GPIO_NUM 32
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 0
#define SIOD_GPIO_NUM 26
#define SIOC_GPIO_NUM 27

#define Y9_GPIO_NUM 35
#define Y8_GPIO_NUM 34
#define Y7_GPIO_NUM 39
#define Y6_GPIO_NUM 36
#define Y5_GPIO_NUM 21
#define Y4_GPIO_NUM 19
#define Y3_GPIO_NUM 18
#define Y2_GPIO_NUM 5
#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM 23
#define PCLK_GPIO_NUM 22

const char *WIFI_SSID = "WIGGLEGRAM_AP";
const char *WIFI_PASSWORD = "Wigglegram2026";

IPAddress localIp(192, 168, 50, 11);
IPAddress gateway(192, 168, 50, 1);
IPAddress subnet(255, 255, 255, 0);
IPAddress dns(192, 168, 50, 1);

WebServer server(80);

String wifiStatusName(wl_status_t status) {
  switch (status) {
    case WL_IDLE_STATUS: return "IDLE";
    case WL_NO_SSID_AVAIL: return "NO_SSID";
    case WL_SCAN_COMPLETED: return "SCAN_COMPLETED";
    case WL_CONNECTED: return "CONNECTED";
    case WL_CONNECT_FAILED: return "CONNECT_FAILED";
    case WL_CONNECTION_LOST: return "CONNECTION_LOST";
    case WL_DISCONNECTED: return "DISCONNECTED";
    default: return "UNKNOWN";
  }
}

framesize_t parseFrameSize(const String &value) {
  if (value == "QQVGA") return FRAMESIZE_QQVGA;
  if (value == "QVGA") return FRAMESIZE_QVGA;
  if (value == "CIF") return FRAMESIZE_CIF;
  if (value == "VGA") return FRAMESIZE_VGA;
  if (value == "SVGA") return FRAMESIZE_SVGA;
  if (value == "XGA") return FRAMESIZE_XGA;
  if (value == "SXGA") return FRAMESIZE_SXGA;
  if (value == "UXGA") return FRAMESIZE_UXGA;
  return FRAMESIZE_SVGA;
}

bool initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  if (psramFound()) {
    config.frame_size = FRAMESIZE_SVGA;
    config.jpeg_quality = 12;
    config.fb_count = 2;
    config.grab_mode = CAMERA_GRAB_LATEST;
  } else {
    config.frame_size = FRAMESIZE_VGA;
    config.jpeg_quality = 14;
    config.fb_count = 1;
    config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  }

  esp_err_t err = esp_camera_init(&config);
  return err == ESP_OK;
}

void sendJson(int code, const String &body) {
  server.send(code, "application/json", body);
}

void handleStatus() {
  sensor_t *sensor = esp_camera_sensor_get();
  StaticJsonDocument<384> doc;
  doc["ok"] = sensor != nullptr;
  doc["ip"] = WiFi.localIP().toString();
  doc["rssi"] = WiFi.RSSI();
  doc["free_heap"] = ESP.getFreeHeap();

  String body;
  serializeJson(doc, body);
  sendJson(200, body);
}

void handleConfig() {
  if (!server.hasArg("plain")) {
    sendJson(400, "{\"ok\":false,\"error\":\"missing JSON body\"}");
    return;
  }

  StaticJsonDocument<512> doc;
  DeserializationError error = deserializeJson(doc, server.arg("plain"));
  if (error) {
    sendJson(400, "{\"ok\":false,\"error\":\"invalid JSON\"}");
    return;
  }

  sensor_t *sensor = esp_camera_sensor_get();
  if (!sensor) {
    sendJson(500, "{\"ok\":false,\"error\":\"camera sensor unavailable\"}");
    return;
  }

  if (doc.containsKey("framesize")) {
    sensor->set_framesize(sensor, parseFrameSize(doc["framesize"].as<String>()));
  }
  if (doc.containsKey("quality")) {
    sensor->set_quality(sensor, doc["quality"].as<int>());
  }
  if (doc.containsKey("brightness")) {
    sensor->set_brightness(sensor, doc["brightness"].as<int>());
  }
  if (doc.containsKey("contrast")) {
    sensor->set_contrast(sensor, doc["contrast"].as<int>());
  }
  if (doc.containsKey("saturation")) {
    sensor->set_saturation(sensor, doc["saturation"].as<int>());
  }
  if (doc.containsKey("aec")) {
    sensor->set_exposure_ctrl(sensor, doc["aec"].as<bool>() ? 1 : 0);
  }
  if (doc.containsKey("agc")) {
    sensor->set_gain_ctrl(sensor, doc["agc"].as<bool>() ? 1 : 0);
  }

  sendJson(200, "{\"ok\":true}");
}

void handleCapture() {
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    server.send(500, "text/plain", "camera capture failed");
    return;
  }

  WiFiClient client = server.client();
  server.setContentLength(fb->len);
  server.sendHeader("Content-Disposition", "inline; filename=capture.jpg");
  server.send(200, "image/jpeg", "");
  client.write(fb->buf, fb->len);
  esp_camera_fb_return(fb);
}

void handleSleep() {
  sendJson(200, "{\"ok\":true,\"message\":\"entering light sleep for 5 seconds\"}");
  delay(100);
  esp_sleep_enable_timer_wakeup(5ULL * 1000ULL * 1000ULL);
  esp_light_sleep_start();
}

void connectWiFi() {
  WiFi.disconnect(true, true);
  delay(300);
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.config(localIp, gateway, subnet, dns);

  Serial.println("Scanning for Wi-Fi networks");
  int networkCount = WiFi.scanNetworks();
  bool foundTarget = false;
  for (int i = 0; i < networkCount; i++) {
    String ssid = WiFi.SSID(i);
    Serial.print("  ");
    Serial.print(ssid);
    Serial.print(" RSSI=");
    Serial.print(WiFi.RSSI(i));
    Serial.print(" channel=");
    Serial.println(WiFi.channel(i));
    if (ssid == WIFI_SSID) {
      foundTarget = true;
    }
  }
  if (!foundTarget) {
    Serial.print("Target SSID not found: ");
    Serial.println(WIFI_SSID);
  }

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.print("Connecting to Wi-Fi");
  unsigned long startedAt = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - startedAt < 30000) {
    delay(500);
    wl_status_t status = WiFi.status();
    Serial.print(".");
    Serial.print(static_cast<int>(status));
    Serial.print("(");
    Serial.print(wifiStatusName(status));
    Serial.print(")");
  }
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println();
    Serial.print("Wi-Fi connection failed. Final status: ");
    Serial.println(wifiStatusName(WiFi.status()));
    delay(5000);
    ESP.restart();
  }
  Serial.println();
  Serial.print("ESP32-CAM IP: ");
  Serial.println(WiFi.localIP());
}

void setup() {
  Serial.begin(115200);
  Serial.setDebugOutput(false);

  if (!initCamera()) {
    Serial.println("Camera init failed");
    delay(5000);
    ESP.restart();
  }

  connectWiFi();

  server.on("/status", HTTP_GET, handleStatus);
  server.on("/config", HTTP_POST, handleConfig);
  server.on("/capture", HTTP_GET, handleCapture);
  server.on("/sleep", HTTP_POST, handleSleep);
  server.begin();

  Serial.println("HTTP camera API started");
}

void loop() {
  server.handleClient();
}
