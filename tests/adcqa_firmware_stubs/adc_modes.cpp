#include <cassert>
#include <iostream>
#include "../../firmware/instrument_adcqa/instrument_adcqa.ino"
extern "C" fsp_err_t HW_SCE_McuSpecificInit(void) {return FSP_SUCCESS;}
extern "C" fsp_err_t HW_SCE_RNG_Read(uint32_t *w) {for(int i=0;i<4;i++)w[i]=i+1;return FSP_SUCCESS;}
void send(const std::string &s) {Serial.input=s+"\n";loop();}
int main() {
  setup();assert(dacWrites.empty());
  const std::string id(bootId),wrong(32,'a');
  send("QA_MODE "+id+" 1");assert(adcQaMode==0 && dacWrites.empty());
  send("ARM "+id+" 1394 523 2265 871 1200 20 1742 9412");
  auto writes=dacWrites.size();
  send("QA_MODE "+wrong+" 1");assert(adcQaMode==0 && dacWrites.size()==writes);
  send("QA_MODE "+id+" 3");assert(adcQaMode==0);
  send("DC "+id+" 2265");
  send("QA_MODE "+id+" 1");assert(adcQaMode==0);
  send("STOP "+id);
  send("QA_MODE "+id+" 1");assert(adcQaMode==1);
  scannedChannels.clear();assert(readAdcQa(3)==adcValue);
  assert(scannedChannels==std::vector<int>{21});
  assert(R_ADC0->ADANSA[0]==0 && R_ADC0->ADANSA[1]==32);
  scannedChannels.clear();assert(readAdcQa(0)==adcValue);
  assert(scannedChannels==std::vector<int>{0});
  assert(R_ADC0->ADANSA[0]==1 && R_ADC0->ADANSA[1]==0);
  send("CAPTURE "+id+" HOLD 16 500 1394 0");
  assert(!adcQaFailed && currentCode==1394);
  send("QA_MODE "+id+" 2");assert(adcQaMode==2);
  scannedChannels.clear();assert(readAdcQa(2)==adcValue);
  assert(scannedChannels==std::vector<int>({2,2}));
  send("CAPTURE "+id+" HOLD 16 500 1394 0");
  assert(!adcQaFailed && currentCode==1394);
  adcFreeze=true;readAdcQa(0);assert(adcQaFailed);
  send("QA_MODE "+id+" 0");assert(adcQaMode==2); // cannot clear a failed ADC
  std::cout<<Serial.output.str();
}
