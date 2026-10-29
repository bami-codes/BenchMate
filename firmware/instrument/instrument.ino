// BenchMate D2 instrument preparation. No accuracy/rate claim before hardware QA.
// Raw DAC codes, raw ADC counts, actual read-completion timestamps.
#include <Arduino.h>
#include <math.h>
#include "boot_identity.h"

// Full per-sample timing is retained in D2 mode. 512 fits both boards including
// the core's reserved heap/stack; a later compressed mode needs measured jitter.
constexpr uint16_t MAX_SAMPLES = 512;
constexpr uint8_t NCH = 4;
const uint8_t PINS[NCH] = {A1,A2,A3,A4};
// UNO R4 Minima/WiFi core 1.6.0 pin maps: A1/A2/A3=AN000/001/002,
// A4=AN021 (shared ADSSTRL). Other register slots are not our channels;
// in particular ADSSTR[15] is reserved and may read zero.
const uint8_t ADC_CHANNELS[NCH] = {0,1,2,21};
uint8_t adcSampleState(uint8_t channel) {
  return channel<16 ? R_ADC0->ADSSTR[channel] : R_ADC0->ADSSTRL;
}
void printAdcStates(const uint8_t *states) {
  Serial.print('[');
  for (uint8_t c=0;c<NCH;c++) {if(c) Serial.print(',');Serial.print(states[c]);}
  Serial.print(']');
}
uint16_t values[MAX_SAMPLES][NCH];
uint16_t offsets[MAX_SAMPLES][NCH];
uint16_t dacCodes[MAX_SAMPLES];
uint32_t frameTimes[MAX_SAMPLES];
char line[160];
uint16_t lineSize = 0;
bool overflowed = false, armed = false;
uint16_t currentCode=0, refCode=0, minCode=0, maxCode=0, maxJump=0;
uint16_t settleMs=1200, stableDelta=20, clipLow=16, clipHigh=16367;
char bootId[33]={0};
bool bootIdReady=false;

void beginResponse(const char *type) {
  Serial.print("{\"protocol\":\"benchmate-instrument-v2\",\"type\":\"");Serial.print(type);
  Serial.print("\",\"boot_id\":");
  if (bootIdReady) {Serial.print('"');Serial.print(bootId);Serial.print('"');}
  else Serial.print("null");
  Serial.print(",\"boot_id_ready\":");Serial.print(bootIdReady?"true":"false");
  Serial.print(",\"uptime_ms\":");Serial.print((uint32_t)millis());
}

void error(const char *message) {
  beginResponse("error");Serial.print(",\"message\":\""); Serial.print(message); Serial.println("\"}");
}

void writeCode(uint16_t code) { analogWrite(A0,code); currentCode=code; }

bool cancelled() {
  // Any new serial input during a blocking acquisition cancels it; no command
  // can be pipelined into an active stimulus. Pending bytes are discarded.
  if (!Serial.available()) return false;
  while (Serial.available()) Serial.read();
  return true;
}

void park() {
  if (!armed) return;
  while (currentCode != refCode) {
    int32_t delta = (int32_t)refCode-currentCode;
    delta = constrain(delta,-(int32_t)maxJump,(int32_t)maxJump);
    writeCode(currentCode+delta);
    delay(settleMs);
  }
}

bool stable() {
  uint32_t start=millis();
  uint16_t lo=16383, hi=0, n=0;
  while (millis()-start < (uint32_t)settleMs+5000) {
    if (cancelled()) return false;
    uint16_t v=analogRead(A2);
    if (millis()-start >= settleMs) {
      lo=min(lo,v);hi=max(hi,v);n++;
      if (n>=20) {
        if (lo>clipLow && hi<clipHigh && hi-lo<=stableDelta) return true;
        lo=16383;hi=0;n=0;
      }
    }
    delay(1);
  }
  return false;
}

bool moveSettled(uint16_t target) {
  while (currentCode != target) {
    int32_t delta=(int32_t)target-currentCode;
    delta=constrain(delta,-(int32_t)maxJump,(int32_t)maxJump);
    writeCode(currentCode+delta);
    if (!stable()) return false;
  }
  return stable();
}

void ping() {
  beginResponse("pong");
  Serial.print(",\"adc_bits\":14,\"dac_bits\":12,\"calibrated\":false,\"max_samples\":512,\"armed\":");
  Serial.print(armed?"true":"false");Serial.print(",\"ref_code\":");Serial.print(refCode);
  Serial.print(",\"max_jump_code\":");Serial.print(maxJump);
  Serial.print(",\"dc_hold_supported\":true,\"current_code\":");Serial.print(currentCode);
  uint8_t states[NCH];
  for (uint8_t c=0;c<NCH;c++) states[c]=adcSampleState(ADC_CHANNELS[c]);
  Serial.print(",\"adc_sample_state_channels\":");printAdcStates(ADC_CHANNELS);
  Serial.print(",\"adc_sample_states_readback\":");printAdcStates(states);
  Serial.println("}");
}

bool number(const char *text,uint32_t &value) {
  if (!text || !*text) return false;
  value=0;
  for (const char *p=text;*p;p++) {
    if (*p<'0'||*p>'9'||value>1000000) return false;
    value=value*10+(*p-'0');
  }
  return value<=10000000;
}

void capture(const char *kind,uint32_t count,uint32_t period,uint32_t amplitude,uint32_t frequencyMilliHz) {
  bool sine=!strcmp(kind,"SINE"), step=!strcmp(kind,"STEP"), hold=!strcmp(kind,"HOLD");
  if (!armed || (!sine&&!step&&!hold) || count<16 || count>MAX_SAMPLES || period<100 || period>20000) {
    error("invalid capture or instrument not armed");return;
  }
  if (hold) {
    // For HOLD the amplitude field is the absolute target DAC code.
    if (amplitude<minCode||amplitude>maxCode||frequencyMilliHz) { error("invalid hold code");return; }
  } else if (!amplitude || amplitude>maxJump || amplitude>refCode-minCode || amplitude>maxCode-refCode ||
             (step && (2*amplitude>maxJump||frequencyMilliHz)) ||
             (sine && (frequencyMilliHz<1000||frequencyMilliHz>500000||(uint64_t)period*frequencyMilliHz>50000000UL))) {
    error("stimulus exceeds configured envelope or samples per cycle");return;
  }
  uint16_t startCode = hold?amplitude:(step?refCode-amplitude:refCode);
  if (!moveSettled(startCode)) { park();error("settling failed or cancelled");return; }
  uint8_t statesBefore[NCH];
  for (uint8_t c=0;c<NCH;c++) statesBefore[c]=adcSampleState(ADC_CHANNELS[c]);
  uint32_t warmup = sine ? (uint32_t)ceil(max((double)settleMs*1000,2e9/frequencyMilliHz)/period) : 0;
  uint32_t origin=micros(), capturedOrigin=0, overruns=0, maxLate=0;
  bool aborted=false, offsetOverflow=false;
  uint16_t stored=0;
  for (uint32_t n=0;n<warmup+count;n++) {
    uint32_t deadline=origin+n*period;
    while ((int32_t)(micros()-deadline)<0) { if (cancelled()) { aborted=true;break; } }
    if (aborted||cancelled()) { aborted=true;break; }
    uint32_t now=micros(),late=now-deadline;
    if (late>=period) { overruns++;aborted=true;break; }
    maxLate=max(maxLate,late);
    uint16_t code=startCode;
    if (sine) code=refCode+(int32_t)lround(amplitude*sin(2*PI*(double)frequencyMilliHz*n*period/1e9));
    else if (step && n>=count/10) code=refCode+amplitude;
    if (abs((int32_t)code-currentCode)>maxJump) { aborted=true;break; }
    writeCode(code);
    uint32_t frame=micros();
    if (n==warmup) capturedOrigin=frame;
    uint16_t temporary[NCH],dt[NCH];
    for (uint8_t c=0;c<NCH;c++) {
      temporary[c]=analogRead(PINS[c]);
      uint32_t offset=micros()-frame;
      if (offset>65535) offsetOverflow=true;
      dt[c]=min(offset,(uint32_t)65535);
    }
    if (n>=warmup) {
      frameTimes[stored]=frame-capturedOrigin;dacCodes[stored]=code;
      for (uint8_t c=0;c<NCH;c++) { values[stored][c]=temporary[c];offsets[stored][c]=dt[c]; }
      stored++;
    }
  }
  // Final scan may also exceed its allocated period.
  if (!aborted && (uint32_t)(micros()-origin)>(warmup+count)*period) overruns++;
  park();
  uint8_t minState=255, statesAfter[NCH];
  for (uint8_t c=0;c<NCH;c++) {
    statesAfter[c]=adcSampleState(ADC_CHANNELS[c]);
    minState=min(minState,min(statesBefore[c],statesAfter[c]));
  }
  beginResponse("capture");
  Serial.print(",\"source\":\"hardware_uncalibrated\",\"adc_bits\":14,\"dac_bits\":12,\"channels\":[\"A1\",\"A2\",\"A3\",\"A4\"],\"timestamp_semantics\":\"analogRead_completion_us\",\"kind\":\"");
  Serial.print(kind);Serial.print("\",\"requested_samples\":");Serial.print(count);
  Serial.print(",\"period_us\":");Serial.print(period);
  Serial.print(",\"amplitude_or_hold_code\":");Serial.print(amplitude);
  Serial.print(",\"frequency_millihz\":");Serial.print(frequencyMilliHz);
  Serial.print(",\"step_index\":");Serial.print(count/10);
  Serial.print(",\"adc_sample_states_requested\":255,\"adc_sample_states_readback_min\":");Serial.print(minState);
  Serial.print(",\"adc_sample_state_channels\":");printAdcStates(ADC_CHANNELS);
  Serial.print(",\"adc_sample_states_readback_before\":");printAdcStates(statesBefore);
  Serial.print(",\"adc_sample_states_readback_after\":");printAdcStates(statesAfter);
  Serial.print(",\"timing_valid\":");Serial.print(!aborted&&!overruns&&!offsetOverflow?"true":"false");
  Serial.print(",\"overruns\":");Serial.print(overruns);
  Serial.print(",\"max_start_lateness_us\":");Serial.print(maxLate);
  Serial.print(",\"parked_ref_code\":");Serial.print(currentCode);
  Serial.print(",\"rows\":[");
  for (uint16_t i=0;i<stored;i++) {
    if (i) Serial.print(',');Serial.print('[');Serial.print(frameTimes[i]);Serial.print(',');Serial.print(dacCodes[i]);
    for (uint8_t c=0;c<NCH;c++) { Serial.print(',');Serial.print(values[i][c]); }
    for (uint8_t c=0;c<NCH;c++) { Serial.print(',');Serial.print(offsets[i][c]); }
    Serial.print(']');
  }
  Serial.println("]}");
}

void command() {
  char *tokens[11];uint8_t n=0;
  char *token=strtok(line," ");
  while (token && n<11) {tokens[n++]=token;token=strtok(nullptr," ");}
  if (token||!n) {error("invalid command");return;}
  if (!strcmp(tokens[0],"PING")&&n==1) {ping();return;}
  if ((!strcmp(tokens[0],"ARM")||!strcmp(tokens[0],"CAPTURE")||!strcmp(tokens[0],"STOP")||!strcmp(tokens[0],"DC")) &&
      (n<2||!bootIdReady||strcmp(tokens[1],bootId))) {
    error("boot identity mismatch or unavailable; output not changed");return;
  }
  if (!strcmp(tokens[0],"STOP")&&n==2) {park();beginResponse("parked");Serial.println("}");return;}
  // Calibration-only persistent level for a human DMM reading. CAPTURE keeps
  // its existing behavior: return to REF after acquisition, including HOLD.
  if (!strcmp(tokens[0],"DC")&&n==3) {
    uint32_t target;
    if (!armed||!number(tokens[2],target)||target<minCode||target>maxCode) {
      error("invalid DC level or instrument not armed");return;
    }
    if (!moveSettled(target)) {park();error("DC settling failed or cancelled; parked at REF");return;}
    beginResponse("dc_held");Serial.print(",\"held_code\":");Serial.print(currentCode);
    Serial.println(",\"calibrated\":false}");return;
  }
  if (!strcmp(tokens[0],"ARM")&&n==10) {
    uint32_t v[8];
    for (uint8_t i=0;i<8;i++) if (!number(tokens[i+2],v[i])) {error("invalid ARM number");return;}
    if (v[1]>=v[0]||v[0]>=v[2]||v[2]>4095||v[3]<1||v[3]>1023||
        v[0]-v[1]>v[3]||v[2]-v[0]>v[3]||v[4]<50||v[4]>5000||v[5]<1||v[5]>1000||v[6]>=v[7]||v[7]>=16384) {
      error("invalid ARM limits");return;
    }
    if (armed) park();
    refCode=v[0];minCode=v[1];maxCode=v[2];maxJump=v[3];settleMs=v[4];stableDelta=v[5];clipLow=v[6];clipHigh=v[7];
    if (!armed) {writeCode(0);armed=true;}
    // Initial ramp is performed before attaching a DUT. No settling claim here.
    park();beginResponse("armed");Serial.println(",\"calibrated\":false}");return;
  }
  if (!strcmp(tokens[0],"CAPTURE")&&n==7) {
    uint32_t v[4];
    for (uint8_t i=0;i<4;i++) if (!number(tokens[i+3],v[i])) {error("invalid capture number");return;}
    capture(tokens[2],v[0],v[1],v[2],v[3]);return;
  }
  error("unknown command");
}

void setup() {
  Serial.begin(115200);analogReadResolution(14);analogWriteResolution(12);
  bootIdReady=makeBootIdentity(bootId);
  for (uint8_t c=0;c<NCH;c++) analogRead(PINS[c]);
  // RA4M1 sampling state registers, based on the installed Renesas core header.
  // Report readback in every packet so D2 can detect an overridden setting.
  for (uint8_t c=0;c<NCH;c++) {
    uint8_t channel=ADC_CHANNELS[c];
    if (channel<16) R_ADC0->ADSSTR[channel]=255;
    else R_ADC0->ADSSTRL=255;
  }
  // A0 remains undriven until the explicit ARM command.
}

void loop() {
  while (Serial.available()) {
    char ch=Serial.read();if (ch=='\r') continue;
    if (ch=='\n') {
      line[lineSize]='\0';if (overflowed) error("command too long");else command();
      lineSize=0;overflowed=false;
    } else if (!overflowed) {
      if (ch=='\0') overflowed=true;
      else if (lineSize<sizeof(line)-1) line[lineSize++]=ch;else overflowed=true;
    }
  }
}
