
#include <Wire.h>
#include "Adafruit_SHT31.h"

Adafruit_SHT31 sht31 = Adafruit_SHT31();

// --- 引脚定义 ---
#define UNO_SIGNAL_PIN 1  // 接 Uno Pin 13 的信号 (D1)
#define RELAY_PIN D2      // 继电器引脚
#define TEMP_THRESHOLD 25.0 // 加热阈值

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("=== 智能猫窝系统: ESP32 指挥官模式 ===");

  // 引脚配置
  pinMode(UNO_SIGNAL_PIN, INPUT);
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW); // 默认关闭加热

  // 初始化 I2C (XIAO S3 默认 SDA=4, SCL=5，如果没出数请改回 Wire.begin(4, 5))
  Wire.begin(); 

  if (!sht31.begin(0x44)) {
    Serial.println("❌ 未找到 SHT30 传感器，请检查 D4/D5 接线");
  } else {
    Serial.println("✔ SHT30 初始化成功");
  }
}

void loop() {
  // 1. 读取 Uno 的猫检测信号
  int hasCat = digitalRead(UNO_SIGNAL_PIN);

  // 2. 读取温湿度数据
  float temp = sht31.readTemperature();
  float hum  = sht31.readHumidity();

  // 3. 打印实时状态
  Serial.print("状态: ");
  if (hasCat == HIGH) {
    Serial.print("[检测到猫] | ");
  } else {
    Serial.print("[无猫状态] | ");
  }

  if (!isnan(temp)) {
    Serial.printf("温度: %.2f °C | 湿度: %.2f %%\n", temp, hum);
  } else {
    Serial.println("温湿度读取失败！");
  }

  // 4. 核心逻辑决策
  // 只有 (有猫) 且 (温度 < 阈值) 才加热
  if (hasCat == HIGH && temp < TEMP_THRESHOLD) {
    digitalWrite(RELAY_PIN, HIGH);
    Serial.println(">>> 正在加热：猫在窝里且天冷。");
  } 
  // 如果猫走了，或者温度够了，立刻关掉
  else {
    digitalWrite(RELAY_PIN, LOW);
    if (hasCat == HIGH && temp >= TEMP_THRESHOLD) {
      Serial.println(">>> 加热停止：温度已达标。");
    } else if (hasCat == LOW) {
      Serial.println(">>> 加热停止：猫不在窝里。");
    }
  }

  Serial.println("------------------------------------");
  delay(1000); // 每秒检查一次，反应迅速
}
