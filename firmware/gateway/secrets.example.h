// Copy this file to secrets.h (same folder) and fill in your values.
// secrets.h is gitignored: never commit real passwords.
#pragma once

#define WIFI_SSID      "your-wifi-name"
#define WIFI_PASSWORD  "your-wifi-password"

// HiveMQ Cloud: Cluster "Overview" tab -> URL; "Access Management" -> credentials.
#define MQTT_HOST      "xxxxxxxx.s1.eu.hivemq.cloud"
#define MQTT_PORT      8883
#define MQTT_USER      "farmlink-gateway"
#define MQTT_PASSWORD  "your-hivemq-password"

// Used in the topic: farmlink/v2/<DEVICE_ID>/readings
#define DEVICE_ID      "field-unit-1"
