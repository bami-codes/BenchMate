#pragma once
// Instrument-maintenance comparison only. Original instrument is preserved.
// Mode 0: installed core analogRead (cumulative scan mask).
// Mode 1: explicitly selected single-channel conversion.
// Mode 2: same single-channel conversion, discard one then retain one.
uint8_t adcQaMode=0;
bool adcQaFailed=false;
const uint8_t QA_PINS[4]={A1,A2,A3,A4};
const uint8_t QA_CHANNELS[4]={0,1,2,21};

bool singleAdcQa(uint8_t channel,uint16_t &value) {
  if (adcQaFailed || R_ADC0->ADCSR_b.ADST || channel>=28) {adcQaFailed=true;return false;}
  const uint16_t low=channel<16?(1U<<channel):0;
  const uint16_t high=channel>=16?(1U<<(channel-16)):0;
  R_ADC0->ADANSA[0]=low;R_ADC0->ADANSA[1]=high;
  if (R_ADC0->ADANSA[0]!=low || R_ADC0->ADANSA[1]!=high) {adcQaFailed=true;return false;}
  uint32_t start=micros();
  R_ADC0->ADCSR_b.ADST=1;
  while (R_ADC0->ADCSR_b.ADST) {
    if ((uint32_t)(micros()-start)>1000) {adcQaFailed=true;return false;}
  }
  value=R_ADC0->ADDR[channel];
  if (value>=16384) {adcQaFailed=true;return false;}
  return true;
}

uint16_t readAdcQa(uint8_t logicalChannel) {
  if (adcQaFailed || logicalChannel>=4) {adcQaFailed=true;return 0;}
  if (adcQaMode==0) return analogRead(QA_PINS[logicalChannel]);
  uint16_t value=0;
  if (adcQaMode==2 && !singleAdcQa(QA_CHANNELS[logicalChannel],value)) return 0;
  if (!singleAdcQa(QA_CHANNELS[logicalChannel],value)) return 0;
  return value;
}

void printAdcQaMetadata() {
  Serial.print(",\"adc_qa_mode\":");Serial.print(adcQaMode);
  Serial.print(",\"adc_qa_failed\":");Serial.print(adcQaFailed?"true":"false");
  Serial.print(",\"adc_qa_single_channel\":");Serial.print(adcQaMode?"true":"false");
  Serial.print(",\"adc_qa_discard_per_channel\":");Serial.print(adcQaMode==2?1:0);
  Serial.print(",\"adc_scan_mask_registers\":[");Serial.print(R_ADC0->ADANSA[0]);
  Serial.print(',');Serial.print(R_ADC0->ADANSA[1]);Serial.print(']');
}
