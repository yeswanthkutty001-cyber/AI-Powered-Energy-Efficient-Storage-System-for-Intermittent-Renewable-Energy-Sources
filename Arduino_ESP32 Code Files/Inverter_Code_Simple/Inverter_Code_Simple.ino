#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <TimerOne.h>

/* ===== LCD ===== */
LiquidCrystal_I2C lcd(0x27, 16, 2);

/* ===== Pins ===== */
const int phaseHigh[] = {2, 4, 6};
const int phaseLow[]  = {3, 5, 7};
const int btnForward = 8;
const int btnReverse = 9;
const int btnStop    = 10;

/* ===== Battery ===== */
const int battPin = A0;
const float battDividerRatio = 10.0;
const float lowCutOff = 0;

/* ===== System State ===== */
volatile bool inverterOn = false;
volatile bool reverseMode = false;
volatile int phaseStep = 0;

/* ===== Debounce ===== */
bool lastBtnState[3] = {LOW, LOW, LOW};
unsigned long lastDebounce[3] = {0, 0, 0};
const unsigned long debounceDelay = 200;

/* ===== 6-step sequence ===== */
const bool seqForward[6][3] = {
  {1,0,0}, {1,1,0}, {0,1,0},
  {0,1,1}, {0,0,1}, {1,0,1}
};

/* ===== Function Prototypes ===== */
float readBatteryVoltage();
void stepPhases();
void handleButton(int pin, int index, bool isReverse, bool isStop=false);

void setup() {
  Serial.begin(9600);
  Serial.println("\n===== 3-PHASE INVERTER DEBUG START =====");

  // Initialize pins
  for (int i = 0; i < 3; i++) {
    pinMode(phaseHigh[i], OUTPUT);
    pinMode(phaseLow[i], OUTPUT);
  }
  pinMode(btnForward, INPUT);
  pinMode(btnReverse, INPUT);
  pinMode(btnStop, INPUT);
  Serial.println("Pins initialized");

  // Initialize LCD
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0,0);
  lcd.print("3-Phase Inverter");
  lcd.setCursor(0,1);
  lcd.print("Initializing...");
  delay(1500);
  lcd.clear();
  Serial.println("LCD initialized");

  // Initialize Timer1 for 300 steps/sec (~50Hz)
  Timer1.initialize(3333);
  Timer1.attachInterrupt(stepPhases);
  Serial.println("Timer1 started @ 50Hz");
  Serial.println("System READY");
}

void loop() {
  float battVoltage = readBatteryVoltage();

  // LCD Line 1: Battery voltage
  lcd.setCursor(0,0);
  lcd.print("Battery: ");
  lcd.print(battVoltage, 2);
  lcd.print("V  ");

  // Low battery protection
  if (battVoltage < lowCutOff && inverterOn) {
    inverterOn = false;
    Serial.println("!!! LOW BATTERY - INVERTER SHUTDOWN !!!");
  }

  // Handle buttons
  handleButton(btnForward, 0, false);
  handleButton(btnReverse, 1, true);
  handleButton(btnStop, 2, false, true);

  // LCD Line 2: Status
  lcd.setCursor(0,1);
  if (battVoltage < lowCutOff) lcd.print("Battery LOW     ");
  else if (!inverterOn) lcd.print("Motor Stopped   ");
  else lcd.print(reverseMode ? "Direction: REV  " : "Direction: FWD  ");
}

/* ===== Battery Reading ===== */
float readBatteryVoltage() {
  long sum = 0;
  for (int i = 0; i < 10; i++) {
    sum += analogRead(battPin);
    delay(2);
  }
  return (sum / 10.0 * 5.0 / 1023.0) * battDividerRatio;
}

/* ===== Timer ISR for Phase Commutation ===== */
void stepPhases() {
  if (!inverterOn) {
    for (int i = 0; i < 3; i++) {
      digitalWrite(phaseHigh[i], LOW);
      digitalWrite(phaseLow[i], LOW);
    }
    return;
  }

  for (int i = 0; i < 3; i++) {
    digitalWrite(phaseHigh[i], seqForward[phaseStep][i]);
    digitalWrite(phaseLow[i], !seqForward[phaseStep][i]);
  }

  // Update phase step
  phaseStep = reverseMode ? (phaseStep + 5) % 6 : (phaseStep + 1) % 6;
}

/* ===== Button Handling ===== */
void handleButton(int pin, int index, bool isReverse, bool isStop) {
  bool state = digitalRead(pin);
  if (state == HIGH && lastBtnState[index] == LOW &&
      (millis() - lastDebounce[index] > debounceDelay)) {

    inverterOn = !isStop;
    reverseMode = isReverse && !isStop;

    Serial.print("Button: ");
    Serial.print(isStop ? "STOP" : (isReverse ? "REVERSE" : "FORWARD"));
    Serial.println(" pressed");

    if (inverterOn) Serial.println("Inverter ON");
    else Serial.println("Inverter OFF");

    lastDebounce[index] = millis();
  }
  lastBtnState[index] = state;
}