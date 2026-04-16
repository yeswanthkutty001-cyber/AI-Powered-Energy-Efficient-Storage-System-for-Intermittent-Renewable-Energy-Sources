#include <max6675.h>

// --------- Pin setup ---------
// Sensor 1
int ktc1SO = 2;
int ktc1CS = 3;
int ktc1CLK = 4;

// Sensor 2
int ktc2SO = 5;
int ktc2CS = 6;
int ktc2CLK = 7;

// Sensor 3
int ktc3SO = 8;
int ktc3CS = 9;
int ktc3CLK = 10;

// Sensor 4
int ktc4SO = 11;
int ktc4CS = 12;
int ktc4CLK = 13;

// Create sensor objects
MAX6675 ktc1(ktc1CLK, ktc1CS, ktc1SO);
MAX6675 ktc2(ktc2CLK, ktc2CS, ktc2SO);
MAX6675 ktc3(ktc3CLK, ktc3CS, ktc3SO);
MAX6675 ktc4(ktc4CLK, ktc4CS, ktc4SO);

void setup() {
  Serial.begin(9600);
  delay(500);  // Allow sensors to stabilize
  Serial.println("4 Thermocouple Temperature Readings (Celsius)");
}

void loop() {

  float t1 = ktc1.readCelsius();
  float t2 = ktc2.readCelsius();
  float t3 = ktc3.readCelsius();
  float t4 = ktc4.readCelsius();

  Serial.print("Sensor 1: ");
  Serial.print(t1);
  Serial.println(" °C");

  Serial.print("Sensor 2: ");
  Serial.print(t2);
  Serial.println(" °C");

  Serial.print("Sensor 3: ");
  Serial.print(t3);
  Serial.println(" °C");

  Serial.print("Sensor 4: ");
  Serial.print(t4);
  Serial.println(" °C");

  Serial.println("---------------------------");

  delay(2000);   // 2 second delay
}