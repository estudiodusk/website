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

# =====================  TRILHA  =====================
def bell(f,d=1.4):
    x=tt(d); m=np.sin(2*np.pi*f*2.01*x)*np.exp(-x*6)*1.2
    return np.sin(2*np.pi*f*x+m)*np.exp(-x*3.2)*np.minimum(x/.004,1)
bd=[0,tl['t1'][1],tl['t2'][1],tl['t3'][1],tl['t4'][1],T]
# Am9 | Fmaj7 | Cmaj9 | Em7 | Dm9 | Am(add9)
chords=[(bd[0],bd[1],[57,60,64,67,71],33,.55),(bd[1],bd[2],[53,57,60,64,67],29,.8),(bd[2],bd[3]-.0,[55,60,64,67,71],36,.85),
        (bd[3],bd[4],[52,55,59,64,67],28,.8),(bd[4],T,[57,60,64,69,72],33,.8)]
# S3 é longa: divide em duas harmonias
chords=[(bd[0],bd[1],[57,60,64,67,71],33,.55),(bd[1],bd[2],[53,57,60,64,67],29,.8),
        (bd[2],bd[2]+4.2,[55,60,64,67,71],36,.85),(bd[2]+4.2,bd[3]+.6,[52,55,59,64,67],28,.8),
        (bd[3]+.6,bd[4],[50,53,57,60,64],26,.75),(bd[4],T,[57,60,64,69,72],33,.8)]
for a,b,ns,root,g in chords:
    d=b-a+1.4
    add(pad(ns,d,.9*g),a-.3,0,1,.5,music=True)
    add(sine(midi(root),d,a=.6,r=d-.6,curve=1.2)*.5*g,a-.2,0,1,.05,music=True)

beat=60/100
# pulso grave + "hat" suave: entra com o manifesto, sai antes do fechamento
tk=tl['t1'][1]+.1; pe=tl['t4'][0]
while tk<pe:
    k=tt(.35); f=48+60*np.exp(-k*40)
    add(np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-k*11),tk,0,.30,.05,music=True); tk+=beat
tk=tl['t1'][1]+.1+beat/2
while tk<pe:
    n=rng.standard_normal(int(SR*.05)); n=n-onepole_sweep(n,3000,3000)
    add(n*np.exp(-tt(.05)*70),tk,rng.uniform(-.3,.3),.10,.1,music=True); tk+=beat
# arpejo de sinos com eco (S2 em diante; some no fechamento)
scales=[[69,72,76,79,81,76,72,79],[65,69,72,76,77,72,69,76],[67,71,74,79,83,79,74,71],[64,67,71,76,79,76,71,67],[62,65,69,72,76,72,69,65]]
step=beat/2; k=0; tk=tl['lines'][0]-.1
def which(t):
    for i,(a,b,*_ ) in enumerate(chords):
        if a<=t<b: return min(i-1,4) if i>0 else 0
    return 4
while tk<tl['t4'][0]+.2:
    sc=scales[max(0,min(which(tk),4))]
    f=midi(sc[k%8]); vol=.12; p=-.5+((k%2)*1.0)
    add(bell(f),tk,p,vol,.45,music=True); add(bell(f),tk+step*1.5,-p,vol*.45,.45,music=True)
    k+=1; tk+=step
# final: pad abre; arpejo de 4 notas assina o logotipo
duck=np.ones(N)
def duck_to(a,b,c,d,lvl):   # desce em a→b, segura, volta em c→d
    global duck
    x=t_; env_=np.clip((x-a)/(b-a),0,1)*(1-np.clip((x-c)/(d-c),0,1)); duck*=1-(1-lvl)*env_
duck_to(tl['line'][0]-.5,tl['line'][0]+.2,tl['glyph']+.4,tl['glyph']+1.6,.30)        # respiro antes do logo
duck_to(tl['t4'][0]+.3,tl['t4'][1]+.2,tl['sj'][1]+.2,tl['sj'][1]+1.4,.55)             # abre espaço no colapso da galeria
duck_to(.0,.3,tl['keys'][-1]+.3,tl['keys'][-1]+1.0,.45)                                # abertura mais seca, digitação em primeiro plano

# =====================  EFEITOS  =====================
def click(f=2600,d=.03,gain=1.0):
    n=rng.standard_normal(int(SR*d)); n=n-onepole_sweep(n,1800,1800); e=np.exp(-tt(d)*150)
    return (n*e*.7+np.sin(2*np.pi*f*tt(d))*e*.55)*gain
def thock(f=190,d=.07): return np.sin(2*np.pi*f*tt(d))*np.exp(-tt(d)*52)
def tink(f=1760,d=.8): return (sine(f,d,a=.001,curve=4)*.6+sine(f*1.5,d,a=.001,curve=5)*.3+sine(f*2.0,d,a=.001,curve=6)*.15)
def swell(d,lo,hi,gain=1.0):  # textura eletrônica: ruído filtrado em varredura
    n=int(SR*d); x=rng.standard_normal(n); y=onepole_sweep(x,lo,hi); y=y-onepole_sweep(y,120,120)
    e=np.sin(np.pi*np.linspace(0,1,n))**2; return y*e*gain*3
def sub(d=1.8,f0=70,f1=38,k=5): 
    h=tt(d); return np.sin(2*np.pi*np.cumsum(f1+(f0-f1)*np.exp(-h*k))/SR)*np.exp(-h*2.0)

# --- S1: digitação (cada tecla com variação de timbre; "Dusk" um pouco mais grave e cheia)
for i,t0 in enumerate(tl['keys']):
    big=i>=8
    f=rng.uniform(2300,3300) if not big else rng.uniform(1700,2300)
    add(click(f,.03,1.0),t0,rng.uniform(-.35,.35),.10 if not big else .13,.12)
    add(thock(rng.uniform(150,210) if not big else rng.uniform(110,150),.08),t0,0,.09 if not big else .13,.05)
add(swell(.6,1200,5200,1),tl['rule1'][0],0,.10,.3)                         # régua nasce
# --- T1: régua → máscara branca
add(swell(.9,200,2600,1),tl['t1'][0]+.05,0,.12,.3)
add(sub(.9,62,44,9),tl['t1'][0]+.35,0,.14,.1)
# --- S2: uma batida por linha, timbres alternados (seco / médio / grave)
kinds=[('tick',3000),('tap',1400),('tick',2500),('tap',900),('tick',2800),('tap',700)]
for i,t0 in enumerate(tl['lines']):
    kind,f=kinds[i]
    if kind=='tick': add(click(f,.035,1.0),t0+.12,rng.uniform(-.4,.4),.11,.2)
    else: add(click(f,.05,.8),t0+.12,rng.uniform(-.4,.4),.10,.2); add(thock(f/6,.12),t0+.12,0,.12,.1)
add(click(3600,.02,1.0),tl['que']+.12,.3,.07,.2)
add(swell(.8,900,4200,1),tl['rule2'][0],0,.07,.3)
# --- T2: corte seco sincronizado + sopro curto
add(swell(.7,300,5000,1),tl['t2'][0]+.05,0,.10,.25)
add(click(1200,.05,1.2),tl['t2'][0]+.32,0,.16,.1); add(thock(95,.14),tl['t2'][0]+.32,0,.20,.05)
# --- S3: título, cards (vidro), palavras-chave, traço dos ícones
add(click(2800,.03,1.0),tl['title']+.15,0,.08,.2)
kw=[2,4,6]
for i,s0 in enumerate(tl['cards']):
    pan=[-.2,-.5,.5][i]
    add(tink(1760+i*220,.9),s0+.2,pan,.06,.7); add(sine(midi(45+i*2),.7,a=.02,curve=2),s0+.15,0,.10,.2)
    add(swell(1.0,500,3500,1),s0+.3,pan,.05,.4)                              # linhas se desenhando
    add(click(2400,.03,1.0),s0+.45,pan,.07,.2)                               # título do card
    add(tink(2637,.7),s0+.85+kw[i]*.1,pan,.05,.8)                            # palavra-chave
# --- T3: câmera avança (sopro limpo, sem impacto)
add(swell(1.1,250,4800,1),tl['t3'][0]+.05,0,.11,.35)
# --- S4: cada fileira entra com um toque leve
for j,t0 in enumerate(tl['rows']):
    add(swell(.8,400,3800,1),t0,-.4+.4*j,.06,.4); add(click(1900,.04,1.0),t0+.55,-.4+.4*j,.07,.3)
# --- T4: fileiras caem na linha (varredura descendente) → ping fino
add(swell(.9,5200,300,1),tl['t4'][0]+.05,0,.09,.3)
add(click(2200,.03,1.2),tl['t4'][0]+.78,0,.09,.2)
add(tink(2637,1.4),tl['ruleIn'][0],0,.05,.9)
# --- S5: "Seja" / "bem-vindo" / "ao"
for i,t0 in enumerate(tl['sj']): add(click(2200-i*300,.04,1.0),t0+.12,0,.09,.3); add(thock(130,.1),t0+.12,0,.09,.1)
add(click(3200,.025,1.0),tl['ao']+.1,0,.06,.2)
# silêncio relativo (música abaixa) → linha desce até a base do logo
add(swell(.7,6000,500,1),tl['line'][0],0,.07,.3)
# --- ASSINATURA: letras sobem da linha (4 toques ascendentes), sub-grave suave, trava da moldura, acorde de sinos
for i in range(4):
    t0=tl['glyph']+i*.09+.12
    add(click(2200+i*420,.04,1.0),t0,-.4+.27*i,.12,.4); add(thock(160-i*10,.09),t0,0,.12,.1)
add(sub(2.2,64,36,5),tl['glyph']+.05,0,.34,.25)
add(click(1500,.05,1.0),tl['lock'][0]+.45,0,.10,.1)                           # moldura trava
for j,n in enumerate((81,88,93)): add(bell(midi(n),3.2),tl['lock'][0]+.1+j*.11,-.4+.4*j,.13,.9)
add(tink(2093,1.6),tl['lock'][1]-.05,0,.07,.9)
add(click(2400,.03,1.0),tl['pill']+.15,0,.06,.2); add(tink(2637,.9),tl['pill']+.2,0,.04,.8)

# ---- reverb sintético (cauda ~2.4s) ----
irn=int(SR*2.6); x=np.arange(irn)/SR
def ir(): 
    n=rng.standard_normal(irn)*np.exp(-x*2.6); 
    n=n-onepole_sweep(n,150,150); n=onepole_sweep(n,6500,2500); return n*np.minimum(x/.02,1)
def conv(a,b):
    m=1<<int(np.ceil(np.log2(len(a)+len(b)))); return np.fft.irfft(np.fft.rfft(a,m)*np.fft.rfft(b,m),m)[:len(a)]
MG=.85
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
