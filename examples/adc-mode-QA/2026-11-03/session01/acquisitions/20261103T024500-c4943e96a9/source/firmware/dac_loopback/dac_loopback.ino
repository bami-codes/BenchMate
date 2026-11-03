// Bare-board DC loopback only. A0 -> four separate 1k resistors -> A1..A4.
// No DUT, buffer, external resistor to GND, or calibrated-voltage claim.
// Boot/PING never drives A0. HOLD selects one nominal point and keeps it there
// for a manual DMM reading; unplug USB before rewiring or leaving the bench.
#include <Arduino.h>

constexpr uint16_t NOMINAL_SUPPLY_MV = 4900; // Earlier operator reading; not calibration.
constexpr uint16_t LEVELS_MV[] = {600,1100,1600,2100,2600};
constexpr uint16_t CODES[] = {501,919,1337,1755,2173};
constexpr uint16_t MAX_INCREMENT = 372; // <=0.5 V even at a 5.5 V supply.
constexpr uint8_t CHANNEL_COUNT=4, SAMPLE_COUNT=64;
const uint8_t CHANNELS[] = {A1,A2,A3,A4};
uint16_t samples[SAMPLE_COUNT][CHANNEL_COUNT];
uint32_t timestamps[SAMPLE_COUNT][CHANNEL_COUNT];
uint16_t currentCode=0;
int8_t selected=-1;
char command[32];
uint8_t commandLength=0;
bool overflowed=false;

void error(const char *message) {
  Serial.print("{\"type\":\"error\",\"message\":\"");Serial.print(message);Serial.println("\"}");
}

void state() {
  Serial.print("\"dac_enabled\":");Serial.print(selected>=0?"true":"false");
  Serial.print(",\"dac_code\":");Serial.print(currentCode);
  Serial.print(",\"nominal_level_mv\":");Serial.print(selected>=0?LEVELS_MV[selected]:0);
  Serial.print(",\"nominal_supply_mv\":");Serial.print(NOMINAL_SUPPLY_MV);
  Serial.print(",\"calibrated\":false");
}

void ping() {
  Serial.print("{\"protocol\":\"benchmate-dac-loopback-v1\",\"type\":\"pong\",\"adc_bits\":14,\"dac_bits\":12,");
  state();Serial.println("}");
}

void hold(uint8_t index) {
  if (selected<0) analogWrite(A0,0);
  const uint16_t target=CODES[index];
  while (currentCode!=target) {
    int32_t delta=(int32_t)target-currentCode;
    delta=constrain(delta,-(int32_t)MAX_INCREMENT,(int32_t)MAX_INCREMENT);
    currentCode+=delta;analogWrite(A0,currentCode);delay(50);
  }
  selected=index;
  delay(250); // Fixed dwell only: not evidence of measured settling.
  Serial.print("{\"protocol\":\"benchmate-dac-loopback-v1\",\"type\":\"holding\",");
  state();Serial.println("}");
}

void capture() {
  if (selected<0) {error("Select a DC level with HOLD first");return;}
  const uint32_t start=micros();
  for (uint8_t n=0;n<SAMPLE_COUNT;n++) {
    for (uint8_t c=0;c<CHANNEL_COUNT;c++) {
      samples[n][c]=analogRead(CHANNELS[c]);timestamps[n][c]=micros()-start;
    }
    if (n+1<SAMPLE_COUNT) delayMicroseconds(500);
  }
  Serial.print("{\"protocol\":\"benchmate-dac-loopback-v1\",\"type\":\"capture\",\"source\":\"hardware_uncalibrated\",\"adc_bits\":14,\"dac_bits\":12,\"channels\":[\"A1\",\"A2\",\"A3\",\"A4\"],\"timestamp_semantics\":\"analogRead_completion_us\",");
  state();Serial.print(",\"samples\":[");
  for (uint8_t n=0;n<SAMPLE_COUNT;n++) {
    if (n) Serial.print(',');Serial.print("{\"t_us\":[");
    for (uint8_t c=0;c<CHANNEL_COUNT;c++) {if (c) Serial.print(',');Serial.print(timestamps[n][c]);}
    Serial.print("],\"raw\":[");
    for (uint8_t c=0;c<CHANNEL_COUNT;c++) {if (c) Serial.print(',');Serial.print(samples[n][c]);}
    Serial.print("]}");
  }
  Serial.println("]}"); // A0 stays at the selected code for the DMM.
}

void dispatch() {
  if (!strcmp(command,"PING")) {ping();return;}
  if (!strcmp(command,"CAPTURE")) {capture();return;}
  // Exact strings only: malformed/suffixed commands cannot start the DAC.
  const char *holds[]={"HOLD 600","HOLD 1100","HOLD 1600","HOLD 2100","HOLD 2600"};
  for (uint8_t i=0;i<5;i++) if (!strcmp(command,holds[i])) {hold(i);return;}
  error("Expected PING, CAPTURE, or HOLD 600/1100/1600/2100/2600");
}

void setup() {
  Serial.begin(115200);analogReadResolution(14);analogWriteResolution(12);
  // No analogWrite, pinMode OUTPUT, or stimulus on boot.
  // Keep the same default ADC sampling configuration as bringup.
}

void loop() {
  while (Serial.available()) {
    char ch=(char)Serial.read();if (ch=='\r') continue;
    if (ch=='\n') {
      command[commandLength]='\0';
      if (overflowed) error("command too long");else dispatch();
      commandLength=0;overflowed=false;
    } else if (!overflowed) {
      if (ch=='\0') overflowed=true;
      else if (commandLength<sizeof(command)-1) command[commandLength++]=ch;
      else overflowed=true;
    }
  }
}
