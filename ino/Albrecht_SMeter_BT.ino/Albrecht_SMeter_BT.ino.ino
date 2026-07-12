#include "BluetoothSerial.h"

const int sMeterPin = 36; 

BluetoothSerial SerialBT;

void setup() {
  Serial.begin(115200);
  
  SerialBT.begin("AE5900_SMETER_BT"); 
  Serial.println("=== Bluetooth S-Meter ready! ===");
  Serial.println("Pair your Pi/Host with 'AE5900_SMETER_BT'");

  analogSetAttenuation(ADC_11db);
}

void loop() {

  int rawValue = analogRead(sMeterPin);
  
  int minRaw = 62;
  int maxRaw = 3720;
  
  int percent = map(rawValue, minRaw, maxRaw, 0, 100);
  
  percent = constrain(percent, 0, 100);
  
  if (SerialBT.hasClient()) {
    SerialBT.println(percent);
    
    Serial.print("Raw ADC: "); Serial.print(rawValue);
    Serial.print(" -> S-Meter: "); Serial.print(percent); Serial.println("%");
  } else {
    Serial.println("Waiting for connection...");
  }
  
  delay(100);
}