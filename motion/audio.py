"""Trilha + efeitos sonoros do DUSK (síntese procedural, sem samples de terceiros).
usage: python3 audio.py out.wav"""
import sys, numpy as np, wave
SR=44100; T=15.6; N=int(SR*T)
rng=np.random.default_rng(7)
t_=np.arange(N)/SR
L=np.zeros(N); R=np.zeros(N)       # dry bus
RL=np.zeros(N); RR=np.zeros(N)     # reverb send

def add(sig,at,pan=0.0,gain=1.0,rev=0.0):
    i=int(at*SR)
    if i>=N: return
    if i<0: sig=sig[-i:]; i=0
    s=sig[:N-i]*gain
    l=np.sqrt((1-pan)/2); r=np.sqrt((1+pan)/2)
    L[i:i+len(s)]+=s*l; R[i:i+len(s)]+=s*r
    RL[i:i+len(s)]+=s*l*rev; RR[i:i+len(s)]+=s*r*rev

def tt(d): return np.arange(int(SR*d))/SR
def env(d,a=.01,r=None,curve=3):
    x=tt(d); r=r if r is not None else d-a
    e=np.minimum(x/a,1)*np.clip(1-(x-a)/max(r,1e-3),0,1)**curve
    return e
def sine(f,d,**k): return np.sin(2*np.pi*f*tt(d))*env(d,**k)
def midi(n): return 440*2**((n-69)/12)

def onepole_sweep(noise,f0,f1,kind='lp'):
    n=len(noise); f=np.linspace(f0,f1,n); a=1-np.exp(-2*np.pi*f/SR)
    y=np.zeros(n); z=0.0
    for i in range(n):
        z+=a[i]*(noise[i]-z); y[i]=z
    return y if kind=='lp' else noise-y

def whoosh(d,up=True,gain=1.0):
    n=int(SR*d); x=rng.standard_normal(n)
    f0,f1=(300,7000) if up else (7000,300)
    y=onepole_sweep(x,f0,f1); y=onepole_sweep(y,f0*.6,f1*.9,'hp') if False else y
    x_=np.linspace(0,1,n); e=np.sin(np.pi*x_**(1.6 if up else .6))**2
    return y*e*gain*3

def pad(notes,d,gain=.5):
    x=tt(d); out=np.zeros(len(x))
    for n in notes:
        f=midi(n)
        for det in (-.07,0,.07):     # 3 detuned voices
            ff=f*2**(det/12*.5)
            ph=rng.uniform(0,6.28)
            out+=np.sin(2*np.pi*ff*x+ph)+.35*np.sin(2*np.pi*2*ff*x+ph)+.12*np.sin(2*np.pi*3*ff*x+ph)
    e=np.minimum(x/1.4,1)*np.minimum((d-x)/1.6,1)
    lfo=.85+.15*np.sin(2*np.pi*.13*x)
    return out*e*lfo*gain/ (len(notes)*3)

# ---- harmonia: Am9 | Fmaj7 | Cmaj7 -> Em | Am (final) ----
chords=[(0,3.7,[57,60,64,67,71],33),(3.7,7.9,[53,57,60,64,67],29),(7.9,11.6,[55,60,64,67,71],36),(11.6,15.6,[57,60,64,69,72],33)]
for a,b,ns,root in chords:
    d=b-a+1.2
    p=pad(ns,d,.9); add(p,a-.3,0,1,.5)
    bs=sine(midi(root),d,a=.6,r=d-.6,curve=1.2)*.55; add(bs,a-.2,0,1,0.05)

# ---- pulso suave (entra no S2, some no final) ----
bpm=100; beat=60/bpm
tk=3.75
while tk<11.5:
    k=tt(.35); f=48+60*np.exp(-k*40)
    thump=np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-k*11)
    add(thump,tk,0,.42,.05)
    tk+=beat
tk=3.75+beat/2
while tk<11.5:
    n=rng.standard_normal(int(SR*.05)); n=n-onepole_sweep(n,3000,3000)
    add(n*np.exp(-tt(.05)*70),tk,rng.uniform(-.3,.3),.16,.1); tk+=beat

# ---- arpejo de "sinos" com eco ----
scale={0:[69,72,76,79,81,76,72,79],1:[65,69,72,76,77,72,69,76],2:[67,71,74,79,83,79,74,71],3:[69,72,76,81,84,81,76,72]}
def bell(f,d=1.4):
    x=tt(d); m=np.sin(2*np.pi*f*2.01*x)*np.exp(-x*6)*1.2
    return np.sin(2*np.pi*f*x+m)*np.exp(-x*3.2)*np.minimum(x/.004,1)
step=beat/2; k=0; tk=4.0
while tk<15.0:
    ci=0 if tk<3.7 else 1 if tk<7.9 else 2 if tk<11.6 else 3
    f=midi(scale[ci][k%8]); vol=.16 if tk<11.6 else .12
    p=-.5+((k%2)*1.0)
    add(bell(f),tk,p,vol,.45)
    add(bell(f),tk+step*1.5,-p,vol*.45,.45)   # eco ping-pong
    k+=1; tk+=step

# ---- SFX ----
add(whoosh(1.3,True,.5),.15,0,.9,.4)                        # linha de luz
for i in range(4):                                           # letras DUSK
    f=midi(81+i*3)
    add(sine(f*2,.9,a=.002,curve=9)*.7+sine(f,.9,a=.002,curve=4)*.3,1.45+i*.13,-.4+i*.27,.35,.6)
h=tt(2.2); boom=np.sin(2*np.pi*np.cumsum(38+70*np.exp(-h*7))/SR)*np.exp(-h*2.4); add(boom,1.95,0,.9,.25)
for tr in (3.05,7.65,11.05):                                 # transições
    add(whoosh(1.15,True,.6),tr,0,.9,.35)
    h=tt(1.6); hit=np.sin(2*np.pi*np.cumsum(46+50*np.exp(-h*9))/SR)*np.exp(-h*3.5); add(hit,tr+1.05,0,.7,.2)
for i in range(11):                                          # palavras do manifesto
    tw=4.05+i*.14
    n=rng.standard_normal(int(SR*.09)); n=n-onepole_sweep(n,5000,5000)
    add(n*np.exp(-tt(.09)*45),tw,rng.uniform(-.6,.6),.22,.3)
    add(sine(midi(93-(i%4)*2),.25,a=.002,curve=5),tw+.01,rng.uniform(-.5,.5),.08,.5)
for i in range(3):                                           # cards de vidro
    tc=8.75+i*.2
    for f,g in ((1760,.5),(2637,.3),(3520,.18)): add(sine(f,1.0,a=.001,curve=4),tc,-.5+i*.5,g*.4,.7)
    add(sine(midi(45+i*2),.8,a=.02,curve=2),tc,0,.5,.2)
add(whoosh(1.4,True,.55),11.0,0,.0,0)                        # (reservado)
for i,tw in enumerate((11.9,12.12)):                         # Seja / bem-vindo
    add(whoosh(.9,False,.35),tw-.1,0,.6,.5)
    add(bell(midi(81+i*7),2.2),tw+.3,-.3+i*.6,.28,.8)
for i in range(4):                                           # DUSK final
    add(sine(midi(81+i*3)*2,.5,a=.002,curve=5),13.0+i*.11,-.4+i*.27,.28,.6)
h=tt(3.2); boom=np.sin(2*np.pi*np.cumsum(36+80*np.exp(-h*6))/SR)*np.exp(-h*1.5); add(boom,13.0,0,1.0,.3)
for j,n in enumerate((81,84,88,93,96)): add(bell(midi(n),3.0),13.0+j*.05,-.6+j*.3,.2,.9)
for f,g in ((1760,.5),(2637,.3)): add(sine(f,1.0,a=.001,curve=4),14.0,0,g*.35,.7)

# ---- reverb sintético (cauda ~2.4s) ----
irn=int(SR*2.6); x=np.arange(irn)/SR
def ir(): 
    n=rng.standard_normal(irn)*np.exp(-x*2.6); 
    n=n-onepole_sweep(n,150,150); n=onepole_sweep(n,6500,2500); return n*np.minimum(x/.02,1)
def conv(a,b):
    m=1<<int(np.ceil(np.log2(len(a)+len(b)))); return np.fft.irfft(np.fft.rfft(a,m)*np.fft.rfft(b,m),m)[:len(a)]
wl=conv(RL,ir()); wr=conv(RR,ir())
mixL=L+wl*.55; mixR=R+wr*.55

# ---- master: fade, soft clip, normalização ----
fade=np.minimum(1,np.minimum(t_/.3,(T-t_)/1.2))
mixL*=fade; mixR*=fade
pk=max(np.abs(mixL).max(),np.abs(mixR).max()); mixL/=pk; mixR/=pk
mixL=np.tanh(mixL*1.4)/np.tanh(1.4)*.9; mixR=np.tanh(mixR*1.4)/np.tanh(1.4)*.9
st=np.stack([mixL,mixR],1); pcm=(st*32767).astype('<i2')
with wave.open(sys.argv[1],'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print('ok')
