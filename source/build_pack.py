from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageFilter
import numpy as np, math, shutil
import argparse, hashlib, json
parser=argparse.ArgumentParser(description="Rebuild the 4× Jaws HD pack.")
parser.add_argument("--rom",required=True,type=Path)
parser.add_argument("--output",type=Path,default=Path("pack"))
parser.add_argument("--font-dir",type=Path,default=Path("/usr/share/fonts/opentype/urw-base35"))
args=parser.parse_args()
project_dir=Path(__file__).resolve().parent
rom=args.rom.read_bytes()
if hashlib.sha1(rom).hexdigest()!="c102da80b2ded9364ebd707df14cbc3bd40bd65a":
 raise SystemExit("Expected the Jaws (USA) NES 2.0 ROM used by the recording.")
planes=np.unpackbits(np.frombuffer(rom[32784:],np.uint8).reshape(-1,2,8,1),axis=-1)
chrtiles=planes[:,0]+2*planes[:,1]
from scipy.ndimage import map_coordinates
from encounters import sharks, shallows, coastline, map_fins, ordnance, bonus_plane, impact_bubbles
P=args.output; P.mkdir(parents=True,exist_ok=True)
for f in (project_dir/'art/title-pack').glob('*.png'):shutil.copyfile(f,P/f.name)
R={int(n):{k:bytes.fromhex(v) for k,v in fields.items()} for n,fields in json.loads((project_dir/'data/scenes.json').read_text()).items()}
G=project_dir/'art'
def asset(name):return Image.open(G/(name+'.png'))
size=(1024,960); blank=(0,0,0,0); rules=[]
def cond(tag,addr,v):rules.append(f'<condition>{tag},ppuMemoryCheckConstant,{addr:04X},==,{v:02X}')
def bg(cond,filename,order,vs=0,hs=0):
 if cond.startswith(('MapA&MapB','DiveA&DiveB','ShallowA&ShallowB')):cond+='&HudS&HudJ'
 rules.append(f'[{cond}]<background>{filename},1,{hs},{vs},{order}')
def font(sz,bold=False):
 path=args.font_dir/('NimbusSans-Bold.otf' if bold else 'NimbusSans-Regular.otf')
 if not path.is_file():
  path=Path('/System/Library/Fonts/Supplemental')/('Arial Bold.ttf' if bold else 'Arial.ttf')
 return ImageFont.truetype(str(path),sz)
def text(im,xy,txt,sz,fill,anchor='la',bold=False):
 ImageDraw.Draw(im).text(xy,txt,font=font(sz,bold),fill=fill,anchor=anchor)
def marker(name,tx,ty,tile):
 rules.append(f'<condition>{name},tileAtPosition,{tx},{ty},{tile:X},00000000,Y')
def artfile(im, name):
 from io import BytesIO
 encoded = BytesIO()
 im.save(encoded, format='PNG', compress_level=6)
 dest = P / name
 temp = dest.with_suffix('.png.tmp')
 temp.write_bytes(encoded.getvalue())
 temp.replace(dest)
# Scene markers use the saved world data, leaving the game's other screens independent.
for name,addr,n in [('DiveA',0x21c0,1200),('DiveB',0x2200,1200)]:
 cond(name,addr,R[n]['nt'][addr-0x2000])
cond('MapA',0x3f05,0x20);cond('MapB',0x3f0f,0x1A)
cond('ShallowA',0x2200,0x6C);cond('ShallowB',0x21c0,0x02)
rules.append('<options>disableSpriteLimit')
marker('Ready',91,43,0x576);marker('ReadyBoat',115,92,0x5a4)
marker('HudS',11,209,0x153);marker('HudJ',163,209,0x14a)
cond('PowerHud',0x2f6f,0x18);cond('HitsHud',0x2f6f,0x48)
marker('Bonus',83,99,0x142);marker('BonusWord',147,99,0x145)
marker('Results',51,67,0x142);marker('ResultsWord',131,67,0x145)
# Bright lands, navigable water and the harbor stay registered to the map camera.
m=Image.new('RGB',(1024,1920),'#08171c'); m.paste(asset('coast').convert('RGB').resize((1024,1536),Image.Resampling.LANCZOS),(0,128));coastline(G,m,artfile)
bg('MapA&MapB','coast.png',10,1,1)
# At the western stop the NES scroll register wraps from $FF to $00,
# sometimes a frame after the signed CPU position changes. Give both visible
# windows their own space on one texture and use it on either side of zero.
# Mesen takes floor(scrollX * 17/16) before applying the 4x pack scale.
# That adds 15 pixels for $F8..$FF and zero for $00..$07.
coast = Image.open(P/'coast.png').convert('RGB')
westedge = Image.new('RGB', (527*4,1920), '#08171c')
westedge.paste(coast.crop((0,0,263*4,1920)),(0,0))
westedge.paste(coast.crop((0,0,8*4,1920)).transpose(Image.Transpose.FLIP_LEFT_RIGHT),(263*4,0))
westedge.paste(coast.crop((0,0,256*4,1920)),(271*4,0))
artfile(westedge,'coast-west.png')
rules.extend(('<condition>WestEdge,memoryCheckConstant,0339,==,FF',
              '<condition>MapPageZero,memoryCheckConstant,0339,==,00',
              '<condition>NearWestEdge,memoryCheckConstant,0338,<,05'))
for edge_guard in ('WestEdge','MapPageZero&NearWestEdge'):
 bg('MapA&MapB&'+edge_guard,'coast-west.png',11,1,1.0625)
# The game clamps the camera to x=264 but only sends its low byte to
# the PPU. At the eastern edge $FF -> $00 means 255 -> 256 in the chart.
# With 21/256 extra scroll, PPU 244..255 receives a fixed +20 offset
# and 0..8 receives zero. Their full 256-pixel viewports fit side by side.
east = coast.crop((256*4, 0, 512*4, coast.height))
edge = Image.new('RGB', (532*4, coast.height))
edge.paste(east, (0, 0))
edge.paste(east.crop((248*4, 0, 256*4, east.height)).transpose(Image.Transpose.FLIP_LEFT_RIGHT), (256*4, 0))
edge.paste(coast.crop((244*4, 0, 512*4, coast.height)), (264*4, 0))
artfile(edge, 'coast-east.png')
rules.extend(('<condition>MapPageOne,memoryCheckConstant,0339,==,01',
              '<condition>NearEastEdge,memoryCheckConstant,0338,>,F7'))
for edge_guard in ('MapPageOne', 'MapPageZero&NearEastEdge'):
 bg('MapA&MapB&'+edge_guard, 'coast-east.png', 11, 1, 1+21/256)
# Surface water and the underwater plate share the original world waterline.
full=Image.new('RGB',(1024,1920),'#052c39'); cap=asset('title-master').convert('RGB')
sky=cap.crop((270,0,cap.width,468)).resize((1024,426),Image.Resampling.LANCZOS);full.paste(sky)
sea=asset('underwater').convert('RGB').resize((1024,868),Image.Resampling.LANCZOS)
full.paste(sea,(0,422))
surf=cap.crop((270,467,cap.width,552)).resize((1024,76),Image.Resampling.LANCZOS)
# Blend wave bottoms into the sunbeams, then register the crest to the NES boat.
a=np.asarray(surf).copy();dest=np.asarray(full.crop((0,419,1024,495)));yy=np.arange(76)[:,None,None]; blend=np.clip((76-yy)/26,0,1)
stripe=Image.fromarray(np.rint(a*blend+dest*(1-blend)).astype(np.uint8))
full.paste(stripe,(0,419));artfile(full,'atlantic.png');bg('DiveA&DiveB','atlantic.png',10,1)
# The four wave states follow the same world scroll and remain below sprites.
for phase in range(1,4):rules.append(f'<condition>tide{phase},frameRange,40,{phase*10}')
for phase in reversed(range(4)):
 y0,y1=404,500;y,x=np.mgrid[y0:y1,:1024].astype(float);env=np.sin(math.pi*(y-y0)/(y1-y0))**2
 p=phase*math.pi/2; sy=y+env*np.sin(x/46-p)*1.5;sx=x+env*np.sin(x/76+y/13+p)*2.6; im=np.asarray(full)
 ar=np.stack([map_coordinates(im[:,:,c],[sy,sx],order=1,mode='nearest')for c in range(3)],axis=-1)
 strip=Image.new('RGBA',(1024,y1));strip.paste(Image.fromarray(ar),(0,y0)); name=f'breakers-{phase}.png';artfile(strip,name)
 bg('DiveA&DiveB'+(f'&tide{phase}' if phase else ''),name,11,1)
shallows(G,full,P,artfile,bg)
# Older title build is preserved in its own folder. Start this pack from its rules.
# The native tile layer remains active everywhere. Only terrain tiles present in
# the captured world receive transparent replacements that reveal the artwork.
arena=[]
def slot(im):
 arena.append(im.convert('RGBA'));return len(arena)-1
zero=slot(Image.new('RGBA',(32,32)))
mappings={}
def register(tile,pal,ind,guard=''):
 mappings[(guard,tile,pal)]=ind
for start,n,guard in [(0x500,1200,'DiveA&DiveB'),(0x500,4656,'ShallowA&ShallowB')]:
 r=R[n]
 samples={n}
 if n==1200:samples.update([840,1080,8400])
 if n==4656:samples.update([5016,5502])
 for sn in samples:
  rr=R[sn];nt=rr['nt'];pal=rr['pa']
  for ry in range(4,52 if start==0x300 else 40):
   base=(ry//30)*1024;y=ry%30
   for x in range(32):
    idx=nt[base+y*32+x]; a=nt[base+960+y//4*8+x//4];p=((a>>((y%4//2)*4+(x%4//2)*2))&3)*4
    palstr=bytes([pal[0],*pal[p+1:p+4]]).hex().upper()
    register(start+idx,palstr,zero,guard)
 # Surface animation has four different CHR rows, all using the same palette.
 if start==0x500:
  for i in [0xcc,0xdc,0xec,0xfc]:
   for off in range(4):
    for pp in range(4):
     palstr=bytes([r['pa'][0],*r['pa'][pp*4+1:pp*4+4]]).hex().upper()
     register(start+i+off,palstr,zero,guard)
# A scrolling column is uploaded before its attribute byte. For one frame a
# terrain tile can have its neighbor's palette. The chart has its own CHR
# page, distinct from the boat sprites and the shared HUD font.
map_colors = R[600]['pa']
for index in range(0, 16, 4):
 key = bytes([map_colors[0], *map_colors[index+1:index+4]]).hex().upper()
 for tile in range(0x300, 0x400):
  register(tile, key, zero, 'MapA&MapB')
# A compact marine instrument strip. Values and Jaws' meter continue to be
# drawn from the game's live nametable and remain directly over this background.
body=Image.new('RGBA',size);d=ImageDraw.Draw(body);d.rectangle((0,800,1023,959),fill='#0b1b21');d.rectangle((0,800,1023,802),fill='#81938b')
for x in (264,454,608):d.line((x,823,x,899),fill='#385054',width=1)
artfile(body,'hud-base.png');bg('HudS&HudJ','hud-base.png',16)
for variant,gate in [('plain',''),('power','&PowerHud'),('hits','&HitsHud')]:
 panel=Image.new('RGBA',size)
 d=ImageDraw.Draw(panel);d.rectangle((0,800,1023,862),fill='#0b1b21');d.rectangle((0,800,1023,802),fill='#81938b')
 for x in (264,454,608):d.line((x,823,x,862),fill='#385054',width=1)
 for x,label,col in [(34,'SCORE','#b5d5ce'),(289,'SHELLS','#f6cb85'),(640,'JAWS’ POWER','#e9b08a')]:
  text(panel,(x,848),label,24,col,'ls',True)
 if variant!='plain':text(panel,(480,848),variant.upper(),24,'#b5d5ce','ls',True)
 d.rectangle((0,948,1023,959),fill='#0b1b21')
 artfile(panel,f'hud-{variant}.png')
# Higher priority header paint for the two live variants, with base header below.
bg('HudS&HudJ','hud-plain.png',21);bg('HudS&HudJ&PowerHud','hud-power.png',22);bg('HudS&HudJ&HitsHud','hud-hits.png',22)
# The map changes scroll origin just above its HUD during encounter messages.
# A banner covers the split only when the matching native message is visible.
marker('MapMessageRow',11,194,0x120)
cond('ContactY',0x2f26,0x59);cond('ContactS',0x2f31,0x53)
notice=Image.new('RGBA',size);nd=ImageDraw.Draw(notice)
nd.rectangle((0,736,1023,800),fill='#102831');nd.line((0,737,1023,737),fill='#d29d60',width=2)
text(notice,(512,780),'YOU’VE HIT SOMETHING!',28,'#ffe5ac','ms',True)
artfile(notice,'contact.png');bg('ContactY&ContactS&MapMessageRow&HudS&HudJ','contact.png',25)
cond('ContactJ',0x2f33,0x4A);cond('ContactW',0x2f35,0x57)
jaws_notice=Image.new('RGBA',size)
jaws_notice.paste(notice.crop((0,736,1024,743)),(0,736))
ImageDraw.Draw(jaws_notice).rectangle((0,743,1023,800),fill='#102831')
text(jaws_notice,(512,780),'YOU’VE HIT JAWS!',28,'#ffe5ac','ms',True)
artfile(jaws_notice,'contact-jaws.png');bg('ContactJ&ContactW&MapMessageRow&HudS&HudJ','contact-jaws.png',25)
# The port message remains in nametable RAM after the game closes it.
# Match the Y and C that the PPU actually drew in the message strip.
marker('PortY',27,194,0x159)
marker('PortC',139,194,0x143)
port_notice = jaws_notice.copy()
ImageDraw.Draw(port_notice).rectangle((0,743,1023,800),fill='#102831')
text(port_notice,(512,780),'YOU NEED MORE CONCH SHELLS.',28,'#ffe5ac','ms',True)
artfile(port_notice,'port-shells.png')
bg('MapA&MapB&PortY&PortC','port-shells.png',25)
# The first split scanline can show an empty or stale nametable before the
# queued text is copied. At that point the upload buffer already holds the
# next message. Select it only while the PPU is displaying the dialogue row.
rules.append('<condition>MessageUpload,memoryCheckConstant,0102,==,AB')
for name,filename,first,last in (
    ('Shell','port-shells.png',(0x0108,'Y'),(0x0116,'C')),
    ('Jaws','contact-jaws.png',(0x0118,'J'),(0x011A,'W')),
    ('Encounter','contact.png',(0x010B,'Y'),(0x0116,'S'))):
 for suffix,(address,char) in (('First',first),('Word',last)):
  rules.append(f'<condition>{name}{suffix},memoryCheckConstant,{address:04X},==,{ord(char):02X}')
 bg(f'MapA&MapB&MapMessageRow&MessageUpload&{name}First&{name}Word',filename,26)
# Artwork and labels sit around native counters.
offwhite='#f5ecda';teal='#abcac5'
ready=Image.new('RGBA',(1024,800),'#08161a');boat=asset('boat').convert('RGB').resize((1024,500),Image.Resampling.LANCZOS)
ready.paste(boat,(0,56));d=ImageDraw.Draw(ready);d.rectangle((0,0,1024,91),fill='#0c2026');text(ready,(48,64),'GET READY!',49,offwhite,'ls',True);d.line((48,85,976,85),fill='#d0a679',width=2)
text(ready,(543,630),'LIVES',25,teal,'rs',True);text(ready,(583,694),'HI-SCORE',25,teal,'rs',True)
# Slightly larger than the NES glyph cells so surrounding text stays covered.
d.rectangle((576,608,607,639),fill=blank);d.rectangle((608,672,767,703),fill=blank)
# Match the counter background to the panel via the layer behind native digits.
readybase=Image.new('RGBA',(1024,800),'#08161a');artfile(readybase,'ready-base.png');bg('Ready&ReadyBoat','ready-base.png',10)
artfile(ready,'ready.png');bg('Ready&ReadyBoat','ready.png',20)
bonus=Image.new('RGBA',(1024,800),'#0a1c23');bt=full.crop((0,0,1024,800)).convert('RGB')
t=np.array(bt).astype(float); y=np.linspace(0,1,800)[:,None,None];t*=.26+.17*(1-y);bonus.paste(Image.fromarray(t.astype('uint8')))
def ruleline(im,y,x=86):ImageDraw.Draw(im).line((x,y,1024-x,y),fill='#c79c65',width=2)
bonus1=bonus.copy();ruleline(bonus1,299);ruleline(bonus1,468);text(bonus1,(512,414),'BONUS SCENE!',65,offwhite,'ms',True);artfile(bonus1,'bonus.png');bg('Bonus&BonusWord','bonus.png',20)
results=Image.new('RGBA',(1024,800),'#0a1c23');results.paste(bonus.crop((0,0,1024,300)),(0,0));ruleline(results,298)
text(results,(84,249),'BONUS SCENE RESULTS',52,offwhite,'ls',True)
text(results,(86,379),'Number of hits',32,offwhite,'ls');text(results,(86,475),'Bonus shells collected',32,offwhite,'ls')
ImageDraw.Draw(results).line((86,411,938,411),fill='#2e494e',width=2)
for y in [352,448]:ImageDraw.Draw(results).rectangle((864,y,927,y+31),fill=blank)
resultbase=Image.new('RGBA',(1024,800),'#0a1c23');artfile(resultbase,'results-base.png');bg('Results&ResultsWord','results-base.png',10);artfile(results,'results.png');bg('Results&ResultsWord','results.png',20)
# Live sprite tile keys are paired with each observed sprite palette.
from collections import defaultdict
import fitz
def vector(w,h,paths,k=4):
 svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{paths}</svg>'
 with fitz.open(stream=svg.encode(),filetype='svg') as doc:
  pm=doc[0].get_pixmap(matrix=fitz.Matrix(k,k),alpha=True)
  from io import BytesIO
  return Image.open(BytesIO(pm.tobytes('png'))).convert('RGBA')
observed={(scope,t):pals for scope,t,pals in json.loads((project_dir/'data/sprites.json').read_text())}
custom={}
def assign(im,slots,bank):
 for t,x,y in slots:
  custom[bank+t]=im.crop((x*4,y*4,(x+8)*4,(y+8)*4))
def grid(im,ts,cols,bank=0x400):
 assign(im,[(t,i%cols*8,i//cols*8) for i,t in enumerate(ts) if t is not None],bank)
sheet=asset('sprites').convert('RGBA')
def clean(col,row):
 # Unmix the soft matte supplied with the cutouts, retaining antialiased edges.
 im=sheet.crop((512*col,512*row,512*(col+1),512*(row+1)))
 a=np.asarray(im.getchannel('A'),dtype=float); a=np.clip((a-194)*255/35,0,255)
 im.putalpha(Image.fromarray(a.astype('uint8')));return im.crop(im.getbbox())
diver,boatobj,ray,shell=[clean(i%3,i//3) for i in (0,1,4,5)]
def fitted(obj,canvas,rect):
 im=Image.new('RGBA',canvas);x,y,w,h=rect;im.alpha_composite(obj.resize((w,h),Image.Resampling.LANCZOS),(x,y));return im
from harbor import build_harbor
build_harbor(G, boatobj, vector, text, artfile, rules, register, slot)

# Surface boat and bonus plane each follow the game's own sprite coordinates.
grid(fitted(boatobj,(128,96),(0,5,124,86)),[4,5,6,None,0x14,0x15,0x16,0x17,0x24,0x25,0x26,0x27],4)
bonus_plane(custom,G,vector)
shark_hit, wounded_jaws = sharks(custom,G)
impact_bubbles(custom,vector)
fin_layouts = json.loads((project_dir/'data/fin-poses.json').read_text())
map_fins(custom, chrtiles, fin_layouts)
ordnance(custom)
harpoon=vector(8,8,'<path d="M.4 3.5L5.5 3.5 5.5 2.25 7.9 4 5.5 5.45 5.5 4.5 .4 4.5Z" fill="#e1efce" stroke="#225163" stroke-width=".28"/>')
custom[0x420]=harpoon
# Conventional 4x treatment for remaining live effects and transitions; map
# the exact observed tile/palette identities instead of a palette-wide fallback.
nes={0x0f:'#102832',0x00:'#a0b1ae',0x10:'#9bafbc',0x20:'#f2e6ca',0x06:'#8a4936',0x03:'#395c73',0x27:'#e6bb68',0x17:'#995c35',0x16:'#b64f3e',0x25:'#c59cbe',0x12:'#355b88'}
def basic(t,p):
 col=['#000000']+[nes.get(int(p[i:i+2],16),'#7d9c99') for i in (2,4,6)]
 arr=np.array([tuple(bytes.fromhex(c[1:]))+(0 if i==0 else 255,) for i,c in enumerate(col)],np.uint8)
 return Image.fromarray(arr[chrtiles[t]],'RGBA').resize((32,32),Image.Resampling.LANCZOS)
from sprite_motion import build as build_motion, jelly_position
impact_layers, idle_south, idle_side = build_motion(custom, diver, shell, ray, vector, G, P)
rules.extend(['<condition>HitEarly,memoryCheckConstant,0695,>,14',
              '<condition>HitMiddle,memoryCheckConstant,0695,>,09'])
# Mesen selects the first matching rule. Test the early threshold before
# the middle one and both before the normal (late-recoil) tile rule.
for window, layer in zip(('HitEarly','HitMiddle'),impact_layers[:2]):
 for tile, image in layer.items():
  idx = slot(image)
  for palette in observed.get(('DiveA&DiveB',tile),[]):
   rules.append(f'[DiveA&DiveB&{window}]<tile>0,{tile:X},{palette},{idx%16*32},{idx//16*32},1,N')
# Jaws starts at $1400. The hit routine subtracts a 16-bit amount at
# $0388-$0389. The HUD only displays the integer part of that quantity.
rules.extend(('<condition>JawsDefeated,memoryCheckConstant,0306,==,20,20',
              '<condition>BelowHalf,memoryCheckConstant,0389,<,0A',
              '<condition>HalfHigh,memoryCheckConstant,0389,==,0A',
              '<condition>HalfLow,memoryCheckConstant,0388,==,00'))
for tile, image in wounded_jaws.items():
 index = slot(image)
 for hp_guard in ('JawsDefeated', 'BelowHalf', 'HalfHigh&HalfLow'):
  rules.append(f'[DiveA&DiveB&{hp_guard}]<tile>0,{tile:X},FF200300,{index%16*32},{index//16*32},1,N')

# The south-facing idle pose reuses upper pieces from its moving animation.
# Resolve these tiles using the boat's own stopped-pose pointer.
rules.append('<condition>SouthIdleLo,memoryCheckConstant,0688,==,78')
rules.append('<condition>MapBoatAnimPage,memoryCheckConstant,0689,==,AE')
for tile, image in idle_south.items():
    index = slot(image)
    for palette in observed.get(('MapA&MapB', tile), []):
        rules.append(f'[MapA&MapB&SouthIdleLo&MapBoatAnimPage]<tile>0,{tile:X},{palette},{index%16*32},{index//16*32},1,N')

# Both headings share the same horizontal metasprite; Mesen mirrors the cells.
# Port dialogs freeze the last moving pose, including its wake cells.
rules.append('<condition>SideIdleLo,memoryCheckConstant,0688,==,72')
rules.append('<condition>MapDialog,memoryCheckConstant,0305,>,7F')
for tile, image in idle_side.items():
    index = slot(image)
    for palette in observed.get(('MapA&MapB',tile),[]):
        for state in ('SideIdleLo&MapBoatAnimPage','MapDialog'):
            rules.append(f'[MapA&MapB&{state}]<tile>0,{tile:X},{palette},{index%16*32},{index//16*32},1,N')

jelly_rules = []
for (scope,t),pals in observed.items():
 for pal in pals:
  jelly_cell = jelly_position(t)
  if jelly_cell is not None and scope == 'DiveA&DiveB':
   x, y = jelly_cell
   jelly_rules.append(f'[{scope}]<tile>1,{t:X},{pal},{x},{y},1,N')
   continue
  if scope=='DiveA&DiveB' and pal=='FF200F27' and t in shark_hit:
   im=shark_hit[t]
  else:
   im=custom[t] if t in custom else basic(t,pal)
  register(t,pal,slot(im),scope)
# Native HUD variable values use the game's font cell and the original meter
# segment patterns, so scoring, hits, shell purchases and damage remain live.
for t in range(0x130,0x13a):
 im=Image.new('RGBA',(32,32)); mask=Image.new('L',(50,55)); d=ImageDraw.Draw(mask)
 d.text((5,4),str(t-0x130),font=font(39,True),fill=255,anchor='lt')
 mask=mask.crop(mask.getbbox()).resize((17 if t==0x131 else 25,27),Image.Resampling.LANCZOS)
 im.paste('#f6ead0',((32-mask.width)//2,2,(32+mask.width)//2,29),mask);idx=slot(im)
 for j in range(4):
  pa=R[360]['pa'];register(0x560+t-0x130,bytes([pa[0],*pa[4*j+1:4*j+4]]).hex().upper(),idx,'Ready&ReadyBoat')
 # The lower HUD split can start a scanline early. Leave room above
 # the full cap and below the baseline in the native 8x8 number slot.
 hud_digit = Image.new('RGBA',(32,32))
 ImageDraw.Draw(hud_digit).text((16,28),str(t-0x130),font=font(29,True),
                               fill='#f6ead0',anchor='ms')
 idx = slot(hud_digit)
 for rr in [R[n] for n in (360,600,1200,8160,8400,11520,4656)]:
  for j in range(4):
   pa=rr['pa'];register(t,bytes([pa[0],*pa[4*j+1:4*j+4]]).hex().upper(),idx,'HudS&HudJ')
# Two live segments occupy each 8px bar tile. Preserve exact native cut-outs.
for t in [0x108,0x109,0x10a]:
 im=Image.new('RGBA',(32,32));dr=ImageDraw.Draw(im)
 for half in range(2):
  x=half*16
  # A filled segment uses three native columns; an empty one is a tick.
  filled=np.count_nonzero(chrtiles[t,0,x//4:x//4+4])==3
  if filled:
   dr.rounded_rectangle((x,6,x+13,25),radius=2,fill='#d79056',outline='#76523b')
   dr.line((x+2,8,x+11,8),fill='#f7bc7c')
  else:
   dr.rounded_rectangle((x+5,8,x+7,24),radius=1,fill='#526469')
 ix=slot(im)
 for rr in [R[n] for n in (360,600,1200,8160,8400,11520,4656)]:
  for j in range(4):
   pa=rr['pa'];register(t,bytes([pa[0],*pa[j*4+1:j*4+4]]).hex().upper(),ix,'HudS&HudJ')
from finale import build_finale
build_finale(G, project_dir/'data/finale-poses.json', rom, chrtiles, artfile, rules, register, slot, font, vector)
# Fill gaps in the recordings from the complete map-fin layouts. Append
# these cells so that existing atlas slots keep their original coordinates.
fin_palette = 'FF' + map_colors[25:28].hex().upper()  # NES sprite palette 2
for layout in fin_layouts:
 for tile, _, _ in layout:
  index = 0x200 + tile
  if ('MapA&MapB', index, fin_palette) not in mappings:
   register(index, fin_palette, slot(custom[index]), 'MapA&MapB')
# Emit a single indexed tile atlas and a readable Mesen definition file.
atlas=Image.new('RGBA',(512,((len(arena)+15)//16)*32))
for i,im in enumerate(arena):atlas.paste(im,((i%16)*32,(i//16)*32))
artfile(atlas,'entities.png')
head=(project_dir/'art/title-pack/hires.txt').read_text().rstrip()
for (guard,t,pal),i in sorted(mappings.items()):
 pre='['+guard+']' if guard else ''
 rules.append(f'{pre}<tile>0,{t:X},{pal},{i%16*32},{i//16*32},1,N')
from jelly_variation import cosmetic_patch

# Resolve each appearance through the live NES palette indices. An existing
# untagged save or object naturally uses Moon, the original sprite palette.
image_files = ('jellyfish.png', 'jelly-amber.png', 'jelly-blue.png')
styles = ('Moon Jelly', 'Amber Sea Nettle', 'Electric Blue')
for style, filename in zip(styles[1:], image_files[1:]):
    shutil.copyfile(P/'Jellyfish Options'/style/'jellyfish.png', P/filename)
base_rules = head + '\n<img>entities.png\n'
definitions = ''.join(f'<img>{name}\n' for name in image_files)
# Actor keys and pose thresholds are shared across the two depths.
for group in (rules,jelly_rules):
    group += [line.replace('DiveA&DiveB','ShallowA&ShallowB') for line in group
              if '[DiveA&DiveB' in line and '<tile>' in line and ',FF' in line]
common = base_rules + definitions + '\n'.join(rules) + '\n'
tagged_rules = list(jelly_rules)
palettes = ('FF201610','FF200F27','FF200300','FF0F2717')
for line in jelly_rules:
    for palette_index, image_index in [(1,2),(2,3),(3,1)]:
        tagged_rules.append(line.replace('<tile>1,',f'<tile>{image_index},').replace(palettes[0],palettes[palette_index]))
mixed = common + '<patch>jelly-appearance.ips,' + hashlib.sha1(rom).hexdigest() + '\n' + '\n'.join(tagged_rules) + '\n'
(P/'jelly-appearance.ips').write_bytes(cosmetic_patch(rom))
(P/'hires.txt').write_text(mixed)
mixed_dir = P/'Jellyfish Options'/'Mixed'
mixed_dir.mkdir(exist_ok=True)
(mixed_dir/'hires.txt').write_text(mixed)
for i,style in enumerate(styles):
    fixed = [row.replace('<tile>1,',f'<tile>{i+1},') for row in jelly_rules]
    (P/'Jellyfish Options'/style/'hires.txt').write_text(common + '\n'.join(fixed) + '\n')
print('Built mixed and fixed jellyfish modes.')
