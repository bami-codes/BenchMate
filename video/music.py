"""Procedurally generated ambient bed (no third-party audio): warm pad + soft arpeggio + sub, ducked under narration."""
import os
V=os.path.dirname(os.path.abspath(__file__)); ROOT=os.environ.get('BENCHMATE_ROOT',os.path.dirname(V))
import json, numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt
SR=48000
tl=json.load(open(f'{V}/timeline.json')); total=tl['total']+0.5
n=int(total*SR); t=np.arange(n)/SR
def midi(m):return 440*2**((m-69)/12)
bpm=84; beat=60/bpm; bar=4*beat
# Am9 - Fmaj7 - Cadd9 - G6 (voicings around A3)
chords=[[57,60,64,67,71],[53,57,60,64,69],[48,55,60,62,67],[55,59,62,64,71]]
pad=np.zeros(n); arp=np.zeros(n); sub=np.zeros(n)
nb=int(np.ceil(total/bar))
rng=np.random.default_rng(7)
for b in range(nb):
    ch=chords[b%4]; s0=int(b*bar*SR); s1=min(n,int((b+1)*bar*SR)+int(0.9*SR))
    tt=np.arange(s1-s0)/SR; env=np.minimum(1,tt/0.9)*np.exp(-np.maximum(0,tt-bar)/0.35)
    seg=np.zeros(s1-s0)
    for m in ch:
        for det in (-0.07,0.07):
            f=midi(m+det); ph=rng.uniform(0,2*np.pi)
            seg+=(np.sin(2*np.pi*f*tt+ph)+0.25*np.sin(4*np.pi*f*tt+ph)+0.08*np.sin(6*np.pi*f*tt))
    pad[s0:s1]+=seg*env/len(ch)
    f0=midi(ch[0]-12); sub[s0:s1]+=np.sin(2*np.pi*f0*tt)*env*0.6
    # eighth-note arpeggio
    for k in range(8):
        m=ch[[0,2,4,2,3,1,4,2][k]]+12; st=s0+int(k*beat/2*SR)
        L=int(0.6*SR); st2=min(n,st+L); tt2=np.arange(st2-st)/SR
        arp[st:st2]+=np.sin(2*np.pi*midi(m)*tt2)*np.exp(-tt2/0.22)*(0.55 if k%2==0 else 0.4)
sos=butter(2,1800,fs=SR,output='sos'); pad=sosfilt(sos,pad)
sos2=butter(2,3500,fs=SR,output='sos'); arp=sosfilt(sos2,arp)
mix=0.55*pad/np.abs(pad).max()+0.22*arp/np.abs(arp).max()+0.30*sub/np.abs(sub).max()
# stereo width via short delay on arp
left=mix; right=np.roll(mix,int(0.012*SR))
# fades: in 2.5 s, out 4 s
fade=np.minimum(1,t/2.5)*np.minimum(1,(total-t)/4.0); fade=np.clip(fade,0,1)
# ducking from narration envelope
sr_n,nar=wavfile.read(f'{V}/out/narration.wav'); nar=nar.astype(np.float32)
if nar.ndim>1:nar=nar.mean(1)
env=np.abs(nar); win=int(0.25*sr_n); env=np.convolve(env,np.ones(win)/win,mode='same')
env=np.interp(t,np.arange(len(env))/sr_n,env,right=0); active=np.clip(env/0.02,0,1)
duck=1-0.55*active
gain=10**(-17/20)
st=np.stack([left,right],1)*(fade*duck*gain)[:,None]
wavfile.write(f'{V}/out/music.wav',SR,(st*32767).astype(np.int16)); print('music',round(total,1),'s')
