#include <cassert>
#include <iostream>
#include "../../firmware/instrument/instrument.ino"

std::string rngMode;
extern "C" fsp_err_t HW_SCE_McuSpecificInit(void) {
  return rngMode=="init-fail"?1:FSP_SUCCESS;
}
extern "C" fsp_err_t HW_SCE_RNG_Read(uint32_t *words) {
  if (rngMode=="read-fail") return 1;
  for (int i=0;i<4;i++) words[i]=rngMode=="zero"?0:i+1;
  return FSP_SUCCESS;
}

void send(const std::string &line) {Serial.input=line+"\n";loop();}

int main(int argc,char **argv) {
  rngMode=argc>1?argv[1]:"ok";
  setup();assert(dacWrites.empty());
  // Only the three dedicated registers and shared AN016+ register belong
  // to this fixture. Reserved/unused zero readbacks must not poison its QA.
  for (int c=3;c<16;c++) assert(R_ADC0->ADSSTR[c]==0);
  assert(R_ADC0->ADSSTR[0]==255 && R_ADC0->ADSSTR[1]==255 &&
         R_ADC0->ADSSTR[2]==255 && R_ADC0->ADSSTRL==255);
  send("PING");assert(dacWrites.empty());
  const std::string wrong(32,'a');
  const std::string limits=" 1394 523 2265 871 1200 20 1742 9412";
  send("ARM "+wrong+limits);assert(dacWrites.empty());
  send("CAPTURE "+wrong+" HOLD 16 500 1394 0");assert(dacWrites.empty());
  send("STOP "+wrong);assert(dacWrites.empty());
  send("INVALID");assert(dacWrites.empty());
  if (rngMode=="ok") {
    assert(bootIdReady && strlen(bootId)==32);
    const std::string id(bootId);
    // A malformed command cannot silently truncate into a valid ARM.
    std::string malformed="ARM "+id+limits;
    malformed.push_back('\0');malformed+="ignored";
    send(malformed);assert(dacWrites.empty());
    send("ARM "+id+limits);assert(armed && !dacWrites.empty());
    auto writes=dacWrites.size();
    send("CAPTURE "+wrong+" HOLD 16 500 1394 0");assert(dacWrites.size()==writes);
    send("STOP "+wrong);assert(dacWrites.size()==writes);
    send("CAPTURE "+id+" HOLD 16 500 1394 0");assert(dacWrites.size()>writes);
    send("STOP "+id);
    send("PING");
  } else {
    assert(!bootIdReady && !armed && dacWrites.empty());
  }
  std::cout<<Serial.output.str();
}
