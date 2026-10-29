#pragma once
// Native protocol tests only: this stub makes no hardware/timing accuracy claim.
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <sstream>
#include <string>
#include <vector>
using std::abs;
constexpr int A0=0,A1=1,A2=2,A3=3,A4=4;
constexpr double PI=3.141592653589793;
inline uint64_t clockUs=0;
inline std::vector<int> dacWrites;
inline uint32_t millis() {return clockUs/1000;}
inline uint32_t micros() {return ++clockUs;}
inline void delay(uint32_t ms) {clockUs+=(uint64_t)ms*1000;}
inline void analogReadResolution(int) {}
inline void analogWriteResolution(int) {}
inline uint16_t adcValue=5000;
inline uint16_t analogRead(int) {clockUs+=25;return adcValue;}
inline void analogWrite(int,int value) {dacWrites.push_back(value);}
struct FakeAdc {uint8_t ADSSTR[16]={0};uint8_t ADSSTRL=0;};
inline FakeAdc adcRegisters;
inline FakeAdc *R_ADC0=&adcRegisters;
struct FakeSerial {
  std::string input;
  std::ostringstream output;
  void begin(int) {}
  int available() {return input.size();}
  int read() {unsigned char c=input.front();input.erase(0,1);return c;}
  template<class T> void print(T value) {output<<value;}
  void print(uint8_t value) {output<<(unsigned int)value;}
  template<class T> void println(T value) {print(value);output<<'\n';}
};
inline FakeSerial Serial;
#define min(a,b) ((a)<(b)?(a):(b))
#define max(a,b) ((a)>(b)?(a):(b))
#define constrain(x,a,b) ((x)<(a)?(a):((x)>(b)?(b):(x)))
