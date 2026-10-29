#pragma once
#include <Arduino.h>
#include <stdio.h>
extern "C" {
#include "common_data.h"
fsp_err_t HW_SCE_McuSpecificInit(void);
fsp_err_t HW_SCE_RNG_Read(uint32_t *words);
}

// Same RA4M1 hardware RNG entry points as Renesas core 1.6.0 WMath.cpp.
// Check both status returns; never fall back to deterministic randomSeed/analogRead.
// This nonce identifies one boot, not a device or an authentication credential.
bool makeBootIdentity(char (&id)[33]) {
  uint32_t words[4]={0,0,0,0};
  if (HW_SCE_McuSpecificInit()!=FSP_SUCCESS || HW_SCE_RNG_Read(words)!=FSP_SUCCESS ||
      !(words[0]|words[1]|words[2]|words[3])) return false;
  snprintf(id,sizeof(id),"%08lx%08lx%08lx%08lx",(unsigned long)words[0],
           (unsigned long)words[1],(unsigned long)words[2],(unsigned long)words[3]);
  return true;
}
