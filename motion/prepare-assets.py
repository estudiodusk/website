"""Redimensiona imagens novas de assets/apps/original/*.webp|png|jpg para assets/apps/app-N.jpg (800px).
Depois acrescente o número em APPS no dusk-intro.html."""
import glob,os,re
from PIL import Image
files=sorted(sum([glob.glob(f'assets/apps/original/*.{e}') for e in ('webp','png','jpg','jpeg')],[]),key=lambda f:[int(x) if x.isdigit() else x for x in re.split(r'(\d+)',f)])
for n,f in enumerate(files,1):
    im=Image.open(f).convert('RGB'); im=im.resize((800,int(800*im.height/im.width)),Image.LANCZOS)
    im.save(f'assets/apps/app-{n}.jpg',quality=88)
print(len(files),'imagens')
