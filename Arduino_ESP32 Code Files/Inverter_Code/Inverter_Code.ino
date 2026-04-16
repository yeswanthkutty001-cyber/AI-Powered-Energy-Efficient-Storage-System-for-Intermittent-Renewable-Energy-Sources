#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <TimerOne.h>

/* ================= LCD ================= */
LiquidCrystal_I2C lcd(0x27, 16, 2);   // SDA=A4, SCL=A5

/* ============ OPTOCOUPLER PINS ============ */
const int phase1_high = 2;
const int phase1_low  = 3;
const int phase2_high = 4;
const int phase2_low  = 5;
const int phase3_high = 6;
const int phase3_low  = 7;

/* ============ BUTTONS ===================== */
const int btnForward = 8;
const int btnReverse = 9;
const int btnStop    = 10;

/* ============ BATTERY ===================== */
const int battPin = A0;
const float battDividerRatio = 10.0;
const float lowCutOff = 0;

/* ============ SYSTEM STATES =============== */
volatile bool inverterOn = false;
volatile bool reverseMode = false;
volatile int phaseStep = 0;

/* ============ DEBOUNCE ==================== */
bool lastForwardState = LOW;
bool lastReverseState = LOW;
bool lastStopState    = LOW;

unsigned long lastDebounceForward = 0;
unsigned long lastDebounceReverse = 0;
unsigned long lastDebounceStop    = 0;

const unsigned long debounceDelay = 200;

/* ============ 6-STEP SEQUENCE ============= */
bool seqForward[6][3] = {
  {1,0,0},
  {1,1,0},
  {0,1,0},
  {0,1,1},
  {0,0,1},
  {1,0,1}
};

/* ========================================== */
void setup() {
  /* --- Serial Debug --- */
  Serial.begin(9600);
  Serial.println();
  Serial.println("===== 3-PHASE INVERTER DEBUG START =====");

  /* --- Pin modes --- */
  pinMode(phase1_high, OUTPUT);
  pinMode(phase1_low,  OUTPUT);
  pinMode(phase2_high, OUTPUT);
  pinMode(phase2_low,  OUTPUT);
  pinMode(phase3_high, OUTPUT);
  pinMode(phase3_low,  OUTPUT);

  pinMode(btnForward, INPUT);
  pinMode(btnReverse, INPUT);
  pinMode(btnStop,    INPUT);

  Serial.println("Pins initialized");

  /* --- LCD --- */
  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0,0);
  lcd.print("3-Phase Inverter");
  lcd.setCursor(0,1);
  lcd.print("Initializing...");
  delay(1500);
  lcd.clear();

  Serial.println("LCD initialized");

  /* --- Timer1: 50Hz output --- */
  Timer1.initialize(3333);  // 300 steps/sec
  Timer1.attachInterrupt(stepPhases);

  Serial.println("Timer1 started @ 50Hz");
  Serial.println("System READY");
}

/* ========================================== */
void loop() {
  float battVoltage = readBatteryVoltage();

  /* --- LCD Line 1 --- */
  lcd.setCursor(0,0);
  lcd.print("Battery: ");
  lcd.print(battVoltage, 2);
  lcd.print("V  ");

  /* --- Serial battery log --- */
  static unsigned long lastBattPrint = 0;
  if (millis() - lastBattPrint > 1000) {
    Serial.print("Battery Voltage: ");
    Serial.print(battVoltage, 2);
    Serial.println(" V");
    lastBattPrint = millis();
  }

  /* --- Low battery protection --- */
  if (battVoltage < lowCutOff && inverterOn) {
    inverterOn = false;
    Serial.println("!!! LOW BATTERY - INVERTER SHUTDOWN !!!");
  }

  /* --- Forward Button --- */
  bool fwd = digitalRead(btnForward);
  if (fwd == HIGH && lastForwardState == LOW &&
      (millis() - lastDebounceForward > debounceDelay)) {

    inverterOn = true;
    reverseMode = false;

    Serial.println("Button: FORWARD pressed");
    Serial.println("Direction set to FORWARD");
    Serial.println("Inverter ON");

    lastDebounceForward = millis();
  }
  lastForwardState = fwd;

  /* --- Reverse Button --- */
  bool rev = digitalRead(btnReverse);
  if (rev == HIGH && lastReverseState == LOW &&
      (millis() - lastDebounceReverse > debounceDelay)) {

    inverterOn = true;
    reverseMode = true;

    Serial.println("Button: REVERSE pressed");
    Serial.println("Direction set to REVERSE");
    Serial.println("Inverter ON");

    lastDebounceReverse = millis();
  }
  lastReverseState = rev;

  /* --- Stop Button --- */
  bool stp = digitalRead(btnStop);
  if (stp == HIGH && lastStopState == LOW &&
      (millis() - lastDebounceStop > debounceDelay)) {

    inverterOn = false;

    Serial.println("Button: STOP pressed");
    Serial.println("Inverter OFF");

    lastDebounceStop = millis();
  }
  lastStopState = stp;

  /* --- LCD Line 2 --- */
  lcd.setCursor(0,1);
  if (battVoltage < lowCutOff) {
    lcd.print("Battery LOW     ");
  } else if (!inverterOn) {
    lcd.print("Motor Stopped   ");
  } else {
    if (reverseMode)
      lcd.print("Direction: REV  ");
    else
      lcd.print("Direction: FWD  ");
  }
}

/* ========================================== */
/* BATTERY VOLTAGE READING */
float readBatteryVoltage() {
  long sum = 0;
  for (int i = 0; i < 10; i++) {
    sum += analogRead(battPin);
    delay(2);
  }
  float adc = sum / 10.0;
  return (adc * 5.0 / 1023.0) * battDividerRatio;
}

/* ========================================== */
/* TIMER ISR: PHASE COMMUTATION */
void stepPhases() {
  if (!inverterOn) {
    digitalWrite(phase1_high, LOW);
    digitalWrite(phase1_low,  LOW);
    digitalWrite(phase2_high, LOW);
    digitalWrite(phase2_low,  LOW);
    digitalWrite(phase3_high, LOW);
    digitalWrite(phase3_low,  LOW);
    return;
  }

  bool A = seqForward[phaseStep][0];
  bool B = seqForward[phaseStep][1];
  bool C = seqForward[phaseStep][2];

  digitalWrite(phase1_high, A);
  digitalWrite(phase1_low,  !A);
  digitalWrite(phase2_high, B);
  digitalWrite(phase2_low,  !B);
  digitalWrite(phase3_high, C);
  digitalWrite(phase3_low,  !C);

  if (reverseMode) {
    phaseStep--;
    if (phaseStep < 0) phaseStep = 5;
  } else {
    phaseStep++;
    if (phaseStep > 5) phaseStep = 0;
  }
}