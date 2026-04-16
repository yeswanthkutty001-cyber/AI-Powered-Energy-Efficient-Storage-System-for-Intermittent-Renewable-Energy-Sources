#include <max6675.h>
#include <Wire.h>
#include <Adafruit_INA219.h>

#define FAN_PIN A0
bool fanState=false;

Adafruit_INA219 ina219;

// MAX6675 sensors
int ktc1SO=2;  int ktc1CS=3;  int ktc1CLK=4;
int ktc2SO=5;  int ktc2CS=6;  int ktc2CLK=7;
int ktc3SO=8;  int ktc3CS=9;  int ktc3CLK=10;
int ktc4SO=11; int ktc4CS=12; int ktc4CLK=13;

MAX6675 ktc1(ktc1CLK,ktc1CS,ktc1SO);
MAX6675 ktc2(ktc2CLK,ktc2CS,ktc2SO);
MAX6675 ktc3(ktc3CLK,ktc3CS,ktc3SO);
MAX6675 ktc4(ktc4CLK,ktc4CS,ktc4SO);

// BQ76920
#define BQ76920_ADDR 0x08
#define NUM_CELLS 5
#define RSNS_MOHM 5.0

#define SYS_STAT 0x00
#define SYS_CTRL1 0x04
#define SYS_CTRL2 0x05
#define VC1_HI 0x0C
#define BAT_HI 0x2A
#define TS1_HI 0x2C
#define CC_HI 0x32
#define ADCGAIN1 0x50
#define ADCOFFSET 0x51
#define ADCGAIN2 0x59

float gain_uV=0;
int8_t offset_mV=0;

void setup()
{
Serial.begin(115200);

pinMode(FAN_PIN,OUTPUT);
digitalWrite(FAN_PIN,HIGH);

Wire.begin();

if(!ina219.begin())
Serial.println("INA219 not detected");

// ===== BQ76920 initialization =====

uint8_t gain1=readRegister(ADCGAIN1);
uint8_t gain2=readRegister(ADCGAIN2);
uint8_t offset_reg=readRegister(ADCOFFSET);

uint8_t adc_gain=((gain1 & 0x0C)<<1) | ((gain2 & 0xE0)>>5);

gain_uV=365.0+adc_gain;
offset_mV=(int8_t)offset_reg;

uint8_t sys_ctrl1=readRegister(SYS_CTRL1);
sys_ctrl1|=0x10;
writeRegister(SYS_CTRL1,sys_ctrl1);

uint8_t sys_ctrl2=readRegister(SYS_CTRL2);
sys_ctrl2|=0x40;
writeRegister(SYS_CTRL2,sys_ctrl2);

delay(500);
}

void loop()
{

float t1=ktc1.readCelsius();
float t2=ktc2.readCelsius();
float t3=ktc3.readCelsius();
float t4=ktc4.readCelsius();

float maxTemp=max(max(t1,t2),max(t3,t4));

if(maxTemp>40) fanState=true;
if(maxTemp<35) fanState=false;

digitalWrite(FAN_PIN,fanState?LOW:HIGH);

// INA219
float busVoltage=ina219.getBusVoltage_V();
float shuntVoltage=ina219.getShuntVoltage_mV();
float current_mA=ina219.getCurrent_mA();
float power_mW=ina219.getPower_mW();
float loadVoltage=busVoltage+(shuntVoltage/1000);

// BQ76920
float packVoltage=readPackVoltage();
float packCurrent=readCurrent();
float dieTemp=readBQTemp();

Serial.println("================================================");

// Thermocouples
Serial.println("THERMOCOUPLE TEMPERATURES");
Serial.print("S1: ");Serial.print(t1);Serial.println(" °C");
Serial.print("S2: ");Serial.print(t2);Serial.println(" °C");
Serial.print("S3: ");Serial.print(t3);Serial.println(" °C");
Serial.print("S4: ");Serial.print(t4);Serial.println(" °C");

char f1=(t1>35)?'X':'O';
char f2=(t2>35)?'X':'O';
char f3=(t3>35)?'X':'O';
char f4=(t4>35)?'X':'O';

Serial.println("THERMAL GRID");
Serial.print("GRID: ");
Serial.print(f1);Serial.print(",O,");Serial.print(f2);
Serial.print(" ; O,O,O ; ");
Serial.print(f3);Serial.print(",O,");Serial.println(f4);

// Cell voltages
Serial.println("CELL VOLTAGES");
for(int i=0;i<NUM_CELLS;i++)
{
uint16_t adc=readDoubleRegister(VC1_HI+(i*2));
adc &=0x3FFF;

float cell_mV=(adc*gain_uV)/1000.0 + offset_mV;
float cell_V=cell_mV/1000.0;

Serial.print("Cell ");Serial.print(i+1);
Serial.print(": ");Serial.print(cell_V,3);
Serial.println(" V");
}

// Pack
Serial.println("PACK STATUS");
Serial.print("Pack Voltage: ");Serial.print(packVoltage);Serial.println(" V");
Serial.print("Pack Current: ");Serial.print(packCurrent);Serial.println(" A");

// INA219
Serial.println("INA219 POWER MONITOR");
Serial.print("Bus Voltage: ");Serial.print(busVoltage);Serial.println(" V");
Serial.print("Load Voltage: ");Serial.print(loadVoltage);Serial.println(" V");
Serial.print("Shunt Voltage: ");Serial.print(shuntVoltage);Serial.println(" mV");
Serial.print("Current: ");Serial.print(current_mA);Serial.println(" mA");
Serial.print("Power: ");Serial.print(power_mW);Serial.println(" mW");

// BQ76920
Serial.println("BQ76920 DIE TEMPERATURE");
Serial.print("Die Temp: ");Serial.print(dieTemp);Serial.println(" °C");

Serial.println("SYSTEM STATUS");
readSystemStatus();

Serial.print("Cooling Fan: ");
Serial.println(fanState?"ON":"OFF");

Serial.println("================================================\n");

delay(2000);
}

void readSystemStatus()
{
uint8_t stat=readRegister(SYS_STAT);

Serial.print("SYS_STAT: 0x");
Serial.println(stat,HEX);

if(stat & 0x20) Serial.println("FAULT: DEVICE_XREADY");
if(stat & 0x10) Serial.println("FAULT: OVRD_ALERT");
if(stat & 0x08) Serial.println("FAULT: Under Voltage");
if(stat & 0x04) Serial.println("FAULT: Over Voltage");
if(stat & 0x02) Serial.println("FAULT: Short Circuit");
if(stat & 0x01) Serial.println("FAULT: Over Current");

if(stat!=0) writeRegister(SYS_STAT,stat);
}

float readBQTemp()
{
uint16_t ts=readDoubleRegister(TS1_HI);
ts &=0x3FFF;

float v=(ts*382.0)/1000000.0;
float temp=25.0-((v-1.200)/0.0042);

return temp;
}

uint8_t readRegister(uint8_t reg)
{
Wire.beginTransmission(BQ76920_ADDR);
Wire.write(reg);
Wire.endTransmission(false);

Wire.requestFrom(BQ76920_ADDR,1);

if(Wire.available())
return Wire.read();

return 0;
}

uint16_t readDoubleRegister(uint8_t reg)
{
Wire.beginTransmission(BQ76920_ADDR);
Wire.write(reg);
Wire.endTransmission(false);

Wire.requestFrom(BQ76920_ADDR,2);

if(Wire.available()==2)
{
uint8_t hi=Wire.read();
uint8_t lo=Wire.read();
return (hi<<8)|lo;
}

return 0;
}

void writeRegister(uint8_t reg,uint8_t val)
{
Wire.beginTransmission(BQ76920_ADDR);
Wire.write(reg);
Wire.write(val);
Wire.endTransmission();
} 

float readPackVoltage()
{
uint16_t bat=readDoubleRegister(BAT_HI);
float bat_mV=(4.0*gain_uV*bat)/1000.0+(NUM_CELLS*offset_mV);
return bat_mV/1000.0;
}

float readCurrent()
{
uint16_t cc=readDoubleRegister(CC_HI);
int16_t cc_val=(int16_t)cc;

float v_sense=cc_val*8.44;
float current=(v_sense/1000.0)/RSNS_MOHM;

return current;
}