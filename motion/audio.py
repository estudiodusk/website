"""Trilha + efeitos sonoros do DUSK (síntese procedural, sem samples de terceiros).
usage: python3 audio.py out.wav"""
import sys, json, os, numpy as np, wave
tl=json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'timeline.json')))  # tempos vêm do HTML (render.mjs --cues)
SR=44100; T=tl['end']; N=int(SR*T)
rng=np.random.default_rng(7)
t_=np.arange(N)/SR
L=np.zeros(N); R=np.zeros(N)       # dry bus
RL=np.zeros(N); RR=np.zeros(N)     # reverb send
ML=np.zeros(N); MR=np.zeros(N); MRL=np.zeros(N); MRR=np.zeros(N)   # barramento da trilha (recebe ducking)

def add(sig,at,pan=0.0,gain=1.0,rev=0.0,music=False):
    bl,br,bwl,bwr=(ML,MR,MRL,MRR) if music else (L,R,RL,RR)
    i=int(at*SR)
    if i>=N: return
    if i<0: sig=sig[-i:]; i=0
    s=sig[:N-i]*gain
    l=np.sqrt((1-pan)/2); r=np.sqrt((1+pan)/2)
    bl[i:i+len(s)]+=s*l; br[i:i+len(s)]+=s*r
    bwl[i:i+len(s)]+=s*l*rev; bwr[i:i+len(s)]+=s*r*rev

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

# =====================  MÚSICA (120 bpm, Lá menor) + SFX  =====================
class Layer:
    def __init__(s): s.L=np.zeros(N); s.R=np.zeros(N); s.RL=np.zeros(N); s.RR=np.zeros(N)
    def add(s,sig,at,pan=0.0,gain=1.0,rev=0.0):
        i=int(at*SR)
        if i>=N: return
        if i<0: sig=sig[-i:]; i=0
        x=sig[:N-i]*gain; l=np.sqrt((1-pan)/2); r=np.sqrt((1+pan)/2); n=len(x)
        s.L[i:i+n]+=x*l; s.R[i:i+n]+=x*r; s.RL[i:i+n]+=x*l*rev; s.RR[i:i+n]+=x*r*rev
    def to_music(s,env=None,g=1.0):
        e=1.0 if env is None else env
        ML[:]+=s.L*e*g; MR[:]+=s.R*e*g; MRL[:]+=s.RL*e*g; MRR[:]+=s.RR*e*g
    def to_fx(s,g=1.0):
        L[:]+=s.L*g; R[:]+=s.R*g; RL[:]+=s.RL*g; RR[:]+=s.RR*g

beat=60/tl['bpm']; bar=4*beat
T1=tl['t1'][0]; T2=tl['t2'][0]; T3=tl['t3'][0]; T4=tl['t4'][0]; G=tl['glyph']; END=T
def beats(a,b,step=1.0,off=0.0):
    out=[]; x=a+off*beat
    while x<b-1e-6: out.append(x); x+=step*beat
    return out

CH={'Am':([57,60,64],33),'F':([53,57,60],29),'C':([55,60,64],36),'G':([55,59,62],31)}
def chord_at(t):
    if t<T1: return 'Am'
    if t<T4: return ['Am','F','C','G'][int((t-T1)//bar)%4]
    if t<T4+beat*2: return 'Am'
    if t<T4+beat*4: return 'F'
    if t<G: return 'G'
    return 'Am'

# --- sidechain: tudo que é "colchão" abaixa a cada bumbo
kick_ranges=[(T1,T4)]
ph=(t_%beat); sc=np.ones(N)
for a_,b_ in kick_ranges:
    m=(t_>=a_)&(t_<b_); sc[m]=1-.78*np.exp(-ph[m]/.15)

# --- sons base
def kick(d=.42):
    h=tt(d); f=45+120*np.exp(-h*38)
    body=np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-h*9)
    clk=np.sin(2*np.pi*2200*h)*np.exp(-h*420)*.25
    return body+clk
def clap(d=.22):
    out=np.zeros(int(SR*d))
    for off,g in ((0,.7),(.011,.8),(.024,1.0)):
        n=rng.standard_normal(int(SR*.1)); n=n-onepole_sweep(n,900,900); n=onepole_sweep(n,5200,5200)
        i=int(off*SR); k=min(len(n),len(out)-i); out[i:i+k]+=(n*np.exp(-np.arange(len(n))/SR*45))[:k]*g
    return out
def hat(d=.05,hp=6500,dec=90):
    n=rng.standard_normal(int(SR*d)); n=n-onepole_sweep(n,hp,hp); return n*np.exp(-tt(d)*dec)
def saw_pluck(f,d=.45,dec=7.0,det=.004,bright=.9):
    x=tt(d); out=np.zeros(len(x))
    for dt in (-det,0,det):
        ph0=rng.uniform(0,6.28)
        for h in range(1,13):
            if f*h>9000: break
            out+=np.sin(2*np.pi*f*(1+dt)*h*x+ph0*h)/h*np.exp(-x*(dec+h*bright))
    return out*np.minimum(x/.003,1)/3
def bass_note(f,d=.2):
    x=tt(d); e=np.minimum(x/.004,1)*np.exp(-x*5)*np.clip((d-x)/.03,0,1)
    return (np.sin(2*np.pi*f*x)+.45*np.sin(2*np.pi*2*f*x)+.2*np.sin(2*np.pi*3*f*x))*e
def riser(d,lo=300,hi=9000,g=1.0):
    n=int(SR*d); x=rng.standard_normal(n); y=onepole_sweep(x,lo,hi); y=y-onepole_sweep(y,200,200)
    e=np.linspace(0,1,n)**2.2; return y*e*g*3
def downlifter(d,hi=7000,lo=200,g=1.0):
    n=int(SR*d); x=rng.standard_normal(n); y=onepole_sweep(x,hi,lo); y=y-onepole_sweep(y,200,200)
    e=np.exp(-np.linspace(0,1,n)*3.0); return y*e*g*3
def tone_riser(d,f0,f1):
    n=int(SR*d); f=np.linspace(f0,f1,n)**1.0; ph=np.cumsum(f)/SR*2*np.pi
    return np.sin(ph)*np.linspace(0,1,n)**2
def sub(d=1.8,f0=70,f1=38,k=5):
    h=tt(d); return np.sin(2*np.pi*np.cumsum(f1+(f0-f1)*np.exp(-h*k))/SR)*np.exp(-h*1.6)
def bell(f,d=1.4):
    x=tt(d); m=np.sin(2*np.pi*f*2.01*x)*np.exp(-x*6)*1.2
    return np.sin(2*np.pi*f*x+m)*np.exp(-x*3.2)*np.minimum(x/.004,1)

# --- baterias
dr=Layer()
for t0 in beats(T1,T4): dr.add(kick(),t0,0,1.0,.02)
for t0 in beats(T1,T4,2.0,1.0): dr.add(clap(),t0,0,.50,.28)                     # tempos 2 e 4
for t0 in beats(T1,T4,1.0,.5): dr.add(hat(.11,6000,38),t0,.2,.16,.1)              # contratempo (aberto)
for t0 in beats(T1,T4,.5,.25): dr.add(hat(.04,8000,140),t0,-.2,.05,.05)           # semicolcheias fantasma
for t0 in beats(T3,T4,.25,.0): dr.add(hat(.03,9000,200),t0,rng.uniform(-.5,.5),.04,.05)   # galeria: shaker 16ths
# build-up (2.0→4.0): hats crescendo + rufar de caixa na última batida
for t0 in beats(T1-1.5,T1,.5,.0): dr.add(hat(.04,8000,150),t0,0,.04+.08*(t0-(T1-1.5))/1.5,.1)
for k,t0 in enumerate(beats(T1-beat,T1,.25,.0)): dr.add(clap(.16),t0,0,.12+.06*k,.2)
# viradas curtas antes de T2 / T3 / T4
for k,t0 in enumerate(beats(T2-beat,T2,.25,.0)): dr.add(clap(.16),t0,0,.10+.04*k,.2)
for k,t0 in enumerate(beats(T3-beat,T3,.25,.0)): dr.add(clap(.16),t0,0,.12+.05*k,.2)
for k,t0 in enumerate(beats(T4-beat*2,T4,.25,.0)): dr.add(clap(.16),t0,0,.10+.025*k,.2)
# coração no breakdown
for k,t0 in enumerate(beats(T4+beat*2,G,2.0,.0)): dr.add(sub(.5,60,40,12),t0,0,.28+.05*k,.1)
dr.to_music(None,1.35)

# --- baixo (contratempos), acordes em stabs, pad e arpejo — tudo com sidechain
bs=Layer(); st=Layer(); pd=Layer(); ar=Layer()
for t0 in beats(T1,T4,1.0,.5):
    root=CH[chord_at(t0)][1]+(12 if int((t0-T1)/beat)%4==2 else 0)
    bs.add(bass_note(midi(root),.22),t0,0,1.0,.02)
bars_t=beats(T1,T4,4.0,.0)
for bt in bars_t:
    for pos in (0.75,1.5,2.75,3.5):
        t0=bt+pos*beat
        if t0>=T4: continue
        ch=CH[chord_at(t0)][0]; g=.11 if t0<T3 else .17
        for n in ch: st.add(saw_pluck(midi(n+12),.5,6.5),t0,rng.uniform(-.4,.4),g/1.6,.25)
# pad contínuo (todo o vídeo, troca de acorde por compasso)
segs=[(0,T1)]
t_c=T1
while t_c<T4: segs.append((t_c,min(t_c+bar,T4))); t_c+=bar
segs+= [(T4,T4+beat*2),(T4+beat*2,T4+beat*4),(T4+beat*4,G),(G,END)]
for a_,b_ in segs:
    ch=CH[chord_at(a_+.01)][0]; g=.16 if a_<T1 else (.30 if a_<T4 else (.40 if a_<G else .5))
    pd.add(pad([n for n in ch]+[ch[0]+12],b_-a_+1.2,g),a_-.3,0,1,.5)
    root=CH[chord_at(a_+.01)][1]
    if a_<T1 or a_>=T4: pd.add(sine(midi(root),b_-a_+.8,a=.5,r=b_-a_+.3,curve=1.1)*(.2 if a_<T1 else .35),a_-.2,0,1,.05)
# arpejo (S3 em diante) com eco "3/16"
for k,t0 in enumerate(beats(T2,T4,.25,.0)):
    ch=CH[chord_at(t0)][0]; notes=ch+[ch[0]+12,ch[1]+12,ch[2]+12,ch[1]+12]
    f=midi(notes[k%len(notes)]+12); p=-.5+(k%2)
    g=.06 if t0<T3 else .09
    sig=saw_pluck(f,.28,9.0,.003,1.2)
    ar.add(sig,t0,p,g,.35); ar.add(sig,t0+.75*beat*.5,-p,g*.4,.35)
# fecho: pluck suave sobre Lá menor
for k,t0 in enumerate(beats(G+beat,END-1.0,.5,.0)):
    ch=CH['Am'][0]; f=midi(([ch[0],ch[1],ch[2],ch[1]][k%4])+24)
    ar.add(bell(f,1.2),t0,-.4+(k%2)*.8,.05,.6)
bs.to_music(sc,1.0); st.to_music(sc,1.0); pd.to_music(sc,1.0); ar.to_music(sc,1.0)

# =====================  TRANSIÇÕES / IMPACTOS (musicais, sem "whoosh" genérico)  =====================
fx=Layer()
fx.add(riser(1.7,300,9000,1),T1-1.7,0,.16,.35)
fx.add(sub(1.4,66,38,6),T1,0,.55,.1)                     # drop
fx.add(downlifter(.9,6000,300,1),T1,0,.10,.3)
fx.add(riser(.6,500,6500,1),T2-.6,0,.10,.3)
fx.add(riser(1.0,300,8000,1),T3-1.0,0,.14,.3)
fx.add(sub(1.0,64,40,7),T3,0,.38,.1)
fx.add(downlifter(1.1,8000,250,1),T4,0,.12,.35)
fx.add(riser(G-(T4+.6),200,10000,1),T4+.6,0,.17,.4)       # sobe até a assinatura
fx.add(tone_riser(G-(T4+.6),160,1400),T4+.6,0,.05,.4)
fx.add(sub(2.6,70,34,4),G,0,.85,.25)                      # assinatura do logo (sub + sinos)
for j,n in enumerate((81,88,93,100)): fx.add(bell(midi(n),3.2),G+.02+j*.07,-.5+.33*j,.14,.9)
fx.to_fx(1.0)

# =====================  CLIQUE DE CÂMERA + DIGITAÇÃO  =====================
def burst(ms,lo,hi,dec):
    n=rng.standard_normal(int(SR*ms/1000)); n=n-onepole_sweep(n,lo,lo); n=onepole_sweep(n,hi,hi)
    return n*np.exp(-np.arange(len(n))/SR*dec)
def shutter(p=1.0):
    x=np.zeros(int(SR*.16)); a=burst(14,2400*p,7500,300); b=burst(24,1000*p,4200,170)
    th=sine(165*p,.04,a=.001,curve=3)
    x[:len(a)]+=a*1.0; i2=int(SR*.034); x[i2:i2+len(b)]+=b*.85; x[i2:i2+len(th)]+=th*.5
    return x
def click(f=2600,d=.03,gain=1.0):
    n=rng.standard_normal(int(SR*d)); n=n-onepole_sweep(n,1800,1800); e=np.exp(-tt(d)*150)
    return (n*e*.7+np.sin(2*np.pi*f*tt(d))*e*.55)*gain
def thock(f=190,d=.07): return np.sin(2*np.pi*f*tt(d))*np.exp(-tt(d)*52)
ty=Layer()
def key_snd(t0,heavy=False):
    f=rng.uniform(2200,3300)
    ty.add(click(f,.032,1.0),t0,rng.uniform(-.3,.3),.55,.15)
    ty.add(thock(rng.uniform(170,240),.09),t0,0,.50,.05)
    ty.add(burst(10,1500,6000,320),t0+.004,rng.uniform(-.3,.3),.30,.1)
for t0 in tl['keys']: key_snd(t0)
for t0 in tl['sp']:                                        # barra de espaço: mais grave e cheia
    ty.add(thock(110,.13),t0,0,.60,.05); ty.add(click(1500,.04,1.0),t0,0,.30,.1)
ty.to_fx(1.0)
cam=Layer()
cl=[(t0,1.0+.06*((i%3)-1)) for i,t0 in enumerate(tl['lines'])]
cl+=[(tl['title']+.12,1.1)]
for i,s0 in enumerate(tl['cards']): cl+=[(s0+.4,.95+.05*i),(s0+.68,1.15)]
cl+=[(tl['sj'][0]+.12,1.0),(tl['sj'][1]+.12,.95),(tl['ao']+.1,1.2)]
for t0,p in cl: cam.add(shutter(p),t0,rng.uniform(-.25,.25),.17,.12)
cam.to_fx(1.0)
pen=Layer()
pen.add(burst(520,1800,7000,5),tl['under'][0],0,.35,.15)
pen.add(burst(520,900,3200,6),tl['under'][0]+.05,.2,.18,.1)
pen.to_fx(1.0)
mi=Layer()
mi.add(click(1500,.05,1.0),tl['lock'][0]+.45,0,.12,.1)    # moldura trava
mi.add(click(2400,.03,1.0),tl['pill']+.15,0,.08,.2)
mi.to_fx(1.0)

# ---- reverb sintético (cauda ~2.4s) ----
irn=int(SR*2.6); x=np.arange(irn)/SR
def ir(): 
    n=rng.standard_normal(irn)*np.exp(-x*2.6); 
    n=n-onepole_sweep(n,150,150); n=onepole_sweep(n,6500,2500); return n*np.minimum(x/.02,1)
def conv(a,b):
    m=1<<int(np.ceil(np.log2(len(a)+len(b)))); return np.fft.irfft(np.fft.rfft(a,m)*np.fft.rfft(b,m),m)[:len(a)]
duck=np.ones(N); MG=1.25
wl=conv(RL+MRL*duck*MG,ir()); wr=conv(RR+MRR*duck*MG,ir())


# ---- master: fade, soft clip, normalização ----
mixL=L+ML*duck*MG+wl*.55; mixR=R+MR*duck*MG+wr*.55
fade=np.minimum(1,np.minimum(t_/.3,(T-t_)/1.6))
mixL*=fade; mixR*=fade
pk=max(np.abs(mixL).max(),np.abs(mixR).max()); mixL/=pk; mixR/=pk
mixL=np.tanh(mixL*1.4)/np.tanh(1.4)*.9; mixR=np.tanh(mixR*1.4)/np.tanh(1.4)*.9
st=np.stack([mixL,mixR],1); pcm=(st*32767).astype('<i2')
with wave.open(sys.argv[1],'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print('ok')
