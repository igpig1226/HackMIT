# Smart Cat Box: ESP32-S3 to Server Data Protocol

## 1. Overview
This document defines how the **ESP32-S3 (Sensor Node)** sends data to the **Central Server (Unoq's Receiver)** via Local Network (WLAN).

## 2. Network Configuration
- **Protocol**: HTTP / 1.1
- **Method**: `POST`
- **Content-Type**: `application/json`
- **Target Endpoint**: `http://<YOUR_IP>:<PORT>/data`

## 3. Data Structure (JSON)
The ESP32 will send a JSON payload every interval (e.g., 5 seconds) or when motion is detected.

### Sample Payload
```json
{
  "device_id": "ESP32_S3_CAT_01",
  "timestamp": 1711612800,
  "sensors": {
    "temperature": 24.5,
    "humidity": 55.2,
    "motion_detected": true
  },
  "camera": {
    "has_image": true,
    "image_data": "/9j/4AAQSkZJRg...", 
    "format": "jpeg"
  }
}
