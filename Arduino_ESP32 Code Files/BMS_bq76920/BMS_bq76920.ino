#include <Arduino.h>
#include <Wire.h>
#include "bq769x0.h"

// number of cells = 3, I2C address = 0x08
bq769x0 bms(1, 0x08);

#define ALERT_PIN 27   // change to your actual pin

void setup() {
    Serial.begin(115200);
    Wire.begin(21, 22);   // ESP32 I2C pins

    // Initialize BMS
    bms.begin(ALERT_PIN);   // TS1 handled by hardware RC

    bms.setTemperatureLimits(-10, 45, 0, 45);
    bms.setShuntResistorValue(1); // 1 mOhm
}

void loop() {
    bms.update();

    Serial.print("Cell 1: ");
    Serial.print(bms.getCellVoltage(1));
    Serial.println(" mV");

    Serial.print("Cell 2: ");
    Serial.print(bms.getCellVoltage(2));
    Serial.println(" mV");

    Serial.print("Cell 3: ");
    Serial.print(bms.getCellVoltage(3));
    Serial.println(" mV");

    Serial.print("Pack Voltage: ");
    Serial.print(bms.getBatteryVoltage());
    Serial.println(" mV");

    int status = bms.checkStatus();
    if (status == 0) {
        Serial.println("Status: OK");
    } else {
        Serial.print("Status: Fault! Error Code: 0x");
        Serial.println(status, HEX);
    }

    delay(2000);
}
