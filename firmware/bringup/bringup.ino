// BenchMate bring-up only. No DAC drive, no stimulus, no calibration claim.
// Commands: PING, READ, CAPTURE. Samples stay in RAM until acquisition finishes.
#include <Arduino.h>

constexpr uint16_t SAMPLE_COUNT = 64;
constexpr uint8_t CHANNEL_COUNT = 4;
const uint8_t CHANNELS[CHANNEL_COUNT] = {A1, A2, A3, A4};
uint16_t samples[SAMPLE_COUNT][CHANNEL_COUNT];
uint32_t timestamps[SAMPLE_COUNT][CHANNEL_COUNT];
char command[32];
uint8_t commandLength = 0;
bool overflowed = false;

void ping() {
  Serial.println("{\"protocol\":\"benchmate-bringup-v1\",\"type\":\"pong\",\"adc_bits\":14,\"dac_enabled\":false,\"calibrated\":false}");
}

void capture(uint16_t count) {
  const uint32_t start = micros();
  for (uint16_t n=0; n<count; n++) {
    for (uint8_t c=0; c<CHANNEL_COUNT; c++) {
      // Timestamp is analogRead completion time, not a calibrated sample aperture.
      samples[n][c] = analogRead(CHANNELS[c]);
      timestamps[n][c] = micros()-start;
    }
    if (n+1<count) delayMicroseconds(500);
  }
  Serial.print("{\"protocol\":\"benchmate-bringup-v1\",\"type\":\"capture\",\"source\":\"hardware_uncalibrated\",\"adc_bits\":14,\"channels\":[\"A1\",\"A2\",\"A3\",\"A4\"],\"timestamp_semantics\":\"analogRead_completion_us\",\"samples\":[");
  for (uint16_t n=0; n<count; n++) {
    if (n) Serial.print(',');
    Serial.print("{\"t_us\":[");
    for (uint8_t c=0; c<CHANNEL_COUNT; c++) {
      if (c) Serial.print(',');
      Serial.print(timestamps[n][c]);
    }
    Serial.print("],\"raw\":[");
    for (uint8_t c=0; c<CHANNEL_COUNT; c++) {
      if (c) Serial.print(',');
      Serial.print(samples[n][c]);
    }
    Serial.print("]}");
  }
  Serial.println("]}");
}

void setup() {
  Serial.begin(115200);
  analogReadResolution(14);
  // Do not enable DAC or drive external circuits during bring-up.
}

void loop() {
  while (Serial.available()) {
    char ch = (char)Serial.read();
    if (ch=='\r') continue;
    if (ch=='\n') {
      command[commandLength]='\0';
      if (overflowed) Serial.println("{\"type\":\"error\",\"message\":\"command too long\"}");
      else if (!strcmp(command,"PING")) ping();
      else if (!strcmp(command,"READ")) capture(1);
      else if (!strcmp(command,"CAPTURE")) capture(SAMPLE_COUNT);
      else Serial.println("{\"type\":\"error\",\"message\":\"unknown command\"}");
      commandLength=0; overflowed=false;
    } else if (!overflowed) {
      if (commandLength<sizeof(command)-1) command[commandLength++]=ch;
      else overflowed=true;
    }
  }
}
