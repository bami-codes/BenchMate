import re, json
from collections import Counter
# Positions from confirmed U1 record. Rails are abstract named nodes: no new rail holes used.
existing=[
('u1pin8','pin','E10',None),('u1pin7','pin','E11',None),('u1pin6','pin','E12',None),('u1pin5','pin','E13',None),
('u1pin1','pin','F10',None),('u1pin2','pin','F11',None),('u1pin3','pin','F12',None),('u1pin4','pin','F13',None),
('div1','R','A3','A6'),('div2','R','B6','B9'),('div3','R','C9','C16'),
('power1','wire','B3','RAIL:+5'),('power2','wire','A10','RAIL:+5'),('ground1','wire','A16','RAIL:GND'),('ground2','wire','J13','RAIL:GND'),
('refinput','wire','D9','H12'),('reffb','wire','G10','G11'),('refpull','R','I10','I16'),('refpullground','wire','H16','H13'),
('driverfb','wire','B11','B12'),('bypass1','C','D10','G13'),('driveinput','wire','ARD:A0','A13'),('drivepull','R','D11','D16'),
('probeinput','probe','B13',None),('probedrive','probe','A11',None),('proberef','probe','J10',None),('probediv','probe','J12',None),
('supply','wire','ARD:5V','RAIL:+5'),('ground','wire','ARD:GND','RAIL:GND')]
new=[
('u2pin8','pin','E20',None),('u2pin7','pin','E21',None),('u2pin6','pin','E22',None),('u2pin5','pin','E23',None),
('u2pin1','pin','F20',None),('u2pin2','pin','F21',None),('u2pin3','pin','F22',None),('u2pin4','pin','F23',None),
('U2 supply','wire','C10','A20'),('ground distribution','wire','B16','A27'),('U2 ground','wire','C27','J23'),
('U2 bypass','C','D20','G23'),('OUT feedback','wire','G20','G21'),('aux feedback','wire','B21','B22'),
('OUT 10k pull','R','I20','I27'),('OUT pull ground','wire','H27','H23'),('aux 10k pull','R','D21','D27'),
('driver distribution','wire','C11','A28'),('shunt bypass','wire','B28','B35'),('OUT input','wire','A30','H22'),
('REF distribution','wire','H10','A50'),('aux park','wire','B50','B23'),('calibration bridge','wire','C35','C30'),
('A1 1k series','R','D35','G35'),('A1 lead','wire','H35','ARD:A1'),
('A2 source','wire','J20','A40'),('A2 1k series','R','D40','G40'),('A2 lead','wire','H40','ARD:A2'),
('A3 source','wire','C28','A45'),('A3 1k series','R','D45','G45'),('A3 lead','wire','H45','ARD:A3'),
('A4 1k series','R','D50','G50'),('A4 lead','wire','H50','ARD:A4')]
# A-E and F-J are distinct connected five-hole groups. Rail split is irrelevant to new wiring.
def strip(h):
 m=re.fullmatch(r'([A-J])(\d+)',h)
 return (('TOP:' if m[1]<='E' else 'BOTTOM:')+m[2]) if m else h
occ=Counter(h for _,_,a,b in existing+new for h in (a,b) if h and re.fullmatch(r'[A-J]\d+',h))
assert all(c==1 for c in occ.values()), [h for h,c in occ.items() if c>1]
for h in ('A35','B30','C50'): assert not occ[h], ('reserved DUT terminal occupied',h)
def topology(excluded=()):
 parent={}
 def find(h):
  h=strip(h);parent.setdefault(h,h)
  while parent[h]!=h:
   parent[h]=parent[parent[h]];h=parent[h]
  return h
 def join(a,b):parent[find(a)]=find(b)
 for name,kind,a,b in existing+new:
  if kind=='wire' and name not in excluded:join(a,b)
 return find
f=topology()
def same(a,b): assert f(a)==f(b),(a,b)
def diff(a,b): assert f(a)!=f(b),(a,b)
same('E20','ARD:5V');same('F23','ARD:GND');diff('ARD:5V','ARD:GND')
same('F20','F21');same('E21','E22')
same('I27','ARD:GND');same('D27','ARD:GND')
same('F22','A35');same('F22','B30');same('F22','E11')
same('E23','F10');same('C50','F10')
for name,kind,a,b in existing+new:
 if kind in ('R','C'):diff(a,b)
outputs=['E11','F10','F20','E21']
for i,a in enumerate(outputs):
 for b in outputs[i+1:]:diff(a,b)
for i in range(1,5):
 h={1:'G35',2:'G40',3:'G45',4:'G50'}[i]
 same('ARD:A'+str(i),h)
 for o in outputs+['ARD:5V','ARD:GND']:diff('ARD:A'+str(i),o)
for a,b in [('D35','A35'),('D40','F20'),('D45','E11'),('D50','F10')]:same(a,b)
# Removing only the calibration jumper separates DUT IN and OUT without disconnecting either sense input.
f=topology(('calibration bridge',));diff('A35','B30');same('D35','A35');same('F22','B30')
# Replacing the shunt bypass must not leave a hidden parallel short around the future shunt.
f=topology(('calibration bridge','shunt bypass'));diff('A35','E11');same('D45','E11');same('D35','A35')
# Parked auxiliary input is distinct from both output nodes; future aux probe requires removing park wire.
f=topology(('aux park',));diff('E23','F10')
result={'status':'passed','checks':['no occupied-hole collisions','DUT terminals free','supply and GND distinct','both U2 feedbacks correct','pull-down returns correct','four ADC inputs each behind separate 1k','driver/REF/measurement-buffer outputs not hard-tied','calibration bridge removable','shunt position has no bypass after jumper removal','aux park removable'], 'additional_resistors':{'10k':2,'1k':4},'additional_capacitors':{'0.1uF':1},'additional_jumpers':sum(k=='wire' for _,k,_,_ in new),'scope':'Connectivity design check, not confirmation of physical assembly or electrical performance'}
print(json.dumps(result,indent=2))
