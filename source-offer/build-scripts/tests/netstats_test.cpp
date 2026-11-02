// Test für netstats.h (Patch uxplay-1.73.7-stats-line). Bauen im UxPlay-Quellordner (MSYS2 UCRT64): g++ -std=c++17 -o netstats_test.exe netstats_test.cpp
#include "netstats.h"
#include <cassert>
#include <cstring>
int main(){
  NetStats n;
  assert(n.line(1.0,0,0,0,0,0,0).empty());               // nichts los, keine Verbindung
  for(int i=0;i<60;i++) n.video(10000, 50000000 - i*1000000);  // 60 Bilder, Reserve 50..-9 ms
  for(int i=0;i<125;i++) n.audio(400, 200000000);
  std::string l=n.line(1.0,3,2,1,0,4,1); puts(l.c_str());
  assert(l.find("vf=60.0")!=std::string::npos);
  assert(l.find("vk=4800")!=std::string::npos);
  assert(l.find("vmin=-9")!=std::string::npos);
  assert(l.find("af=125.0")!=std::string::npos);
  assert(l.find("aavg=200")!=std::string::npos);
  assert(l.find("rs=3 re=2 gp=1 ds=0 dd=4")!=std::string::npos);
  l=n.line(1.0,3,2,1,0,4,1); puts(l.c_str());            // Stillstand: nur Delta 0, aber verbunden
  assert(l.find("vf=0.0")!=std::string::npos && l.find("vmin=na")!=std::string::npos && l.find("rs=0")!=std::string::npos);
  l=n.line(1.0,5,2,1,0,4,0); assert(l.find("rs=2")!=std::string::npos);
  assert(n.line(1.0,5,2,1,0,4,0).empty());
  puts("OK");
}
