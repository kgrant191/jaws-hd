"""Build the final encounter from its native sprites, camera and title cue."""
import json
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import map_coordinates

from sprite_motion import trim

LANCZOS = Image.Resampling.LANCZOS
BATTLE = 'FinalSky&StrobeStrip'
FLIGHT = 'FinalSky&SunsetBluff'
SINK = 'FinishHit&DiveA&DiveB&!HudS&SinkWater'
BATTLE_COLORS = ('FF20170F','FF200F00','FF20260F','FF16260F')


def silhouette(cells, patterns, bank):
    width = max(x for _,x,_,_ in cells)+8
    height = max(y for _,_,y,_ in cells)+8
    result = np.zeros((height,width),np.uint8)
    for tile,x,y,attr in cells:
        pattern = patterns[bank+tile]
        if attr&64:
            pattern = np.fliplr(pattern)
        if attr&128:
            pattern = np.flipud(pattern)
        result[y:y+8,x:x+8] = pattern
    return result


def add_tiles(output, canvas, cells, bank, colors):
    for tile,x,y,attr in cells:
        image = canvas.crop((4*x,4*y,4*x+32,4*y+32))
        if attr&64:
            image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if attr&128:
            image = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        output.setdefault((bank+tile,colors[attr&3]),image)


def final_ocean(art, save, rules):
    source = art('battle-ocean').convert('RGB')
    # Align the painted horizon with the farthest fin and build a wrap for
    # both nametables. The underlying PPU scroll is tracked on each scanline.
    horizon = round(source.height*.350)
    plate = Image.new('RGB',(1024,832))
    plate.paste(source.crop((0,0,source.width,horizon)).resize((1024,320),LANCZOS))
    plate.paste(source.crop((0,horizon,source.width,source.height)).resize((1024,512),LANCZOS),(0,320))
    # Crossfade two ends of the same open-water view into one period.
    tile = plate.resize((1152,832),LANCZOS)
    plate = tile.crop((64,0,1088,832))
    blend = Image.fromarray(np.uint8(np.linspace(0,255,128))[None,:]).resize((128,832))
    seam = Image.composite(tile.crop((0,0,128,832)),tile.crop((1024,0,1152,832)),blend)
    plate.paste(seam.crop((0,0,64,832)),(960,0))
    plate.paste(seam.crop((64,0,128,832)),(0,0))

    def repeat(im):
        strip=Image.new(im.mode,(im.width*3,im.height))
        for repeat_index in range(3):
            strip.paste(im,(im.width*repeat_index,0))
        return strip

    save(repeat(plate.crop((0,0,1024,320))),'final-sky.png')
    rules.append(f'[{BATTLE}]<background>final-sky.png,1,1,0,20')
    sea=np.array(plate.crop((0,320,1024,832)))
    y,x=np.indices(sea.shape[:2],dtype=float)
    for phase in (3,2,1,0):
        position=phase*math.pi/2
        depth=y/(sea.shape[0]-1)
        sx=x+depth*2.3*np.sin(y/43+position+2*math.pi*x/1024)
        sy=np.clip(y+depth*2.2*np.sin(4*math.pi*x/1024+y/39+position),0,511)
        # Pad one periodic column on each side for subpixel interpolation.
        padded=np.pad(sea,((0,0),(1,1),(0,0)),mode='wrap')
        rgb=np.stack([map_coordinates(padded[:,:,k],(sy,sx%1024+1),order=1) for k in range(3)],axis=-1)
        layer=Image.new('RGBA',(1024,832))
        layer.paste(Image.fromarray(rgb),(0,320))
        name=f'final-water-{phase}.png'
        save(repeat(layer),name)
        gate=f'&tide{phase}' if phase else ''
        rules.append(f'[{BATTLE}{gate}]<background>{name},1,1,0,21')


def paint_fin(cells, dorsal, vector):
    width=max(x for _,x,_,_ in cells)+8
    height=max(y for _,_,y,_ in cells)+8
    center=width/2
    # Use the adult shark's painted dorsal. The advancing fin is nearly
    # edge-on, and its upper two cells are shared with the retreat animation.
    fin_height={8:21,16:46,24:79}[height]
    fin_width={8:15,16:23,24:29}[height]
    canvas=Image.new('RGBA',(width*4,height*4))
    fin=dorsal.resize((fin_width,fin_height),LANCZOS)
    x=round(center*4-fin_width/2)
    base=height*4-8
    canvas.alpha_composite(fin,(x,base-fin_height))
    # Different native splash IDs give the two curls alternating lengths.
    phase=sum(tile for tile,_,_,_ in cells)%3
    y=height-2.1
    if width>8:
        reach=width*(.34+.025*phase)
    else:
        reach=3.0
    if len(cells)==1 and cells[0][0]==0xcf:
        reach=1.5
    wake=vector(width,height,f'''<g fill="none" stroke-linecap="round">
      <path d="M{center-reach} {y+.2} Q{center-reach*.7} {y-1.2} {center-1.4} {y-.1}
               Q{center} {y+.75} {center+1.5} {y-.2} Q{center+reach*.72} {y-1.3} {center+reach} {y+.45}"
            stroke="#447e85" stroke-width="1.15"/>
      <path d="M{center-reach} {y+.4} Q{center-reach*.62} {y-1.35} {center-1.35} {y+.05}
               M{center+1} {y+.25} Q{center+reach*.6} {y-1.45} {center+reach} {y+.15}"
            stroke="#deeee3" stroke-width=".52"/>
      <path d="M{center-2.2} {y+1} Q{center-.3} {y+1.4} {center+2.6} {y+.95}"
            stroke="#a8d8d4" stroke-width=".4"/></g>''')
    canvas.alpha_composite(wake)
    return canvas


def paint_breaches(master, poses, output):
    # The game raises the animal one row at a time. The first four poses
    # reuse the top of the first full pose at different screen positions.
    for phase,cells in enumerate(poses):
        width=max(x for _,x,_,_ in cells)+8
        height=max(y for _,_,y,_ in cells)+8
        canvas=Image.new('RGBA',(4*width,4*height))
        positions={t:(x,y) for t,x,y,_ in cells}
        anchor=next((positions[t][0] for t in (0x55,0x58,0x5b) if t in positions),0)
        # Roll slightly from the open-mouth breach to the struck pose.
        sprite=master.rotate((0,3,-4)[max(0,phase-4)],Image.Resampling.BICUBIC,expand=True)
        sprite=trim(sprite).resize((88,156),LANCZOS)
        canvas.alpha_composite(sprite,(anchor*4+1,2))
        if height<40:
            foam=master.crop((0,int(master.height*.946),master.width,master.height))
            foam=foam.resize((min(width*4-2,100),min(13,height*2)),LANCZOS)
            canvas.alpha_composite(foam,((canvas.width-foam.width)//2,canvas.height-foam.height))
        add_tiles(output,canvas,cells,0x600,BATTLE_COLORS)


def flight_art(master, cells, angle, patterns):
    # Scale the banked aircraft to its native wing span, then align its
    # silhouette with the original footprint. This preserves moving wingtips
    # even when the NES uses sparse diagonal cells rather than a rectangle.
    mask=silhouette(cells,patterns,0x700)>0
    ys,xs=np.where(mask)
    size=((xs.max()-xs.min()+1)*4,(ys.max()-ys.min()+1)*4)
    rotated=trim(master.rotate(angle,Image.Resampling.BICUBIC,expand=True))
    plane=rotated.resize(size,LANCZOS)
    frame=Image.new('RGBA',(mask.shape[1]*4,mask.shape[0]*4))
    frame.alpha_composite(plane,(int(xs.min()*4),int(ys.min()*4)))
    return frame


def banked_flyby(frame, cells, rules, save, output):
    # The first flyby advances four NES pixels left and one up per frame.
    # Its Y coordinate therefore identifies the whole position. The emulator
    # displays the previous sprite DMA while the actor updates the next one.
    # Rendering this bank as one plane lets both wingtips cross otherwise
    # empty sprite cells. Later, smaller poses use native sprites directly.
    sheet=Image.new('RGBA',(1312,960))
    sheet.alpha_composite(frame,(1024,640))
    save(sheet,'banked-flight.png')
    rules.append('<condition>FirstFlyby,memoryCheckConstant,0688,==,85')
    for actor_y in range(56,139):
        name=f'FlybyY{actor_y:02X}'
        x=4*actor_y-300
        y=actor_y-46
        rules.append(f'<condition>{name},memoryCheckConstant,0684,==,{actor_y:02X}')
        rules.append(f'[{FLIGHT}&FirstFlyby&{name}]<background>banked-flight.png,1,0,0,24,{256-x},{160-y}')
    for tile,_,_,_ in cells:
        output[(0x700+tile,'FF252005')]=Image.new('RGBA',(32,32))


def sparkle(cells, patterns):
    mask=silhouette(cells,patterns,0x700)>0
    w,h=mask.shape[1]*4,mask.shape[0]*4
    core=Image.fromarray(np.uint8(mask)*255).resize((w,h),LANCZOS)
    glow=Image.new('RGBA',(w,h),(244,170,112,0))
    glow.putalpha(core.filter(ImageFilter.GaussianBlur(4)))
    light=Image.new('RGBA',(w,h),(255,236,198,0))
    light.putalpha(core.filter(ImageFilter.GaussianBlur(.8)))
    glow.alpha_composite(light)
    return glow


def build_finale(assets, poses_file, patterns, save, rules, register, slot, font, vector):
    poses=json.loads(poses_file.read_text())
    def art(name):
        with Image.open(assets/'finale'/(name+'.png')) as source:
            return source.copy()
    rules.extend((
        '<condition>FinalSky,tileAtPosition,19,3,702,00000000,Y',
        '<condition>StrobeStrip,tileAtPosition,19,233,700,00000000,Y',
        '<condition>SunsetBluff,tileAtPosition,19,233,73C,00000000,Y',
        '<condition>EndCaption,tileAtPosition,179,211,7E8,00000000,Y',
        '<condition>FinishHit,memoryCheckConstant,0306,==,80,80',
        '<condition>SinkWater,tileAtPosition,203,185,501,00000000,Y'))
    final_ocean(art,save,rules)
    rules.append(f'[{SINK}]<background>atlantic.png,1,0,1,20')
    sunset=art('ending-coast').convert('RGB').resize((1024,960),LANCZOS)
    save(sunset,'sunset-flight.png')
    rules.append(f'[{FLIGHT}]<background>sunset-flight.png,1,0,0,20')
    ending=Image.new('RGBA',(1024,960))
    pen=ImageDraw.Draw(ending)
    # The painted closing card follows the PPU title, after the last glint.
    pen.text((927,872),'THE END',font=font(59,True),anchor='rs',fill='#f9ead2',
             stroke_width=2,stroke_fill='#463934')
    pen.line((701,888,926,888),fill='#dbac72',width=2)
    save(ending,'the-end.png')
    rules.append(f'[{FLIGHT}&EndCaption]<background>the-end.png,1,0,0,23')

    surface={}
    bow=trim(art('bow').convert('RGBA')).resize((236,224),LANCZOS)
    for phase,cells in enumerate(poses['bow']):
        deck=Image.new('RGBA',(256,224))
        deck.alpha_composite(bow,(10,0))
        if phase:
            pen=ImageDraw.Draw(deck)
            pen.polygon([(125,2),(129,0),(132,31),(129,47),(125,27)],fill='#92382e')
            pen.line((128,3,129,28),fill='#e2a08b',width=2)
        add_tiles(surface,deck,cells,0x600,BATTLE_COLORS)
    with Image.open(assets/'sharks.png') as source:
        dorsal=trim(source.convert('RGBA').crop((650,419,980,560)))
    for cells in poses['fin']:
        add_tiles(surface,paint_fin(cells,dorsal,vector),cells,0x600,BATTLE_COLORS)
    paint_breaches(trim(art('breach-shark').convert('RGBA')),poses['breach'],surface)

    # The STROBE letters and number are sprites and remain separately live.
    strip=Image.new('RGBA',(1024,960))
    pen=ImageDraw.Draw(strip)
    pen.rectangle((0,832,1023,959),fill='#0b1b21')
    pen.line((0,833,1023,833),fill='#81938b',width=2)
    save(strip,'strobe-panel.png')
    rules.append(f'[{BATTLE}]<background>strobe-panel.png,1,0,0,22')
    letters=Image.new('RGBA',(192,32))
    ImageDraw.Draw(letters).text((96,26),'STROBE',font=font(27,True),anchor='ms',fill='#b5d5ce')
    for index,tile in enumerate((0x30,0x31,0x32,0x40,0x41,0x42)):
        surface[(0x600+tile,BATTLE_COLORS[0])]=letters.crop((index*32,0,index*32+32,32))
    for value in range(4):
        image=Image.new('RGBA',(32,32))
        ImageDraw.Draw(image).text((16,27),str(value),font=font(29,True),anchor='ms',fill='#f4d59d')
        surface[(0x606+value,BATTLE_COLORS[0])]=image

    sinking={}
    dead=Image.new('RGBA',(96,192))
    shark=trim(art('sinking-shark').convert('RGBA')).resize((91,169),LANCZOS)
    # The bottom two rows have no right-hand tile. Aim the snout down the
    # middle of the second column and keep the broad fins above that gap.
    dead.alpha_composite(shark,(0,0))
    add_tiles(sinking,dead,poses['sink'][0],0x400,('','','FF200300',''))

    flying={}
    plane=trim(art('plane-front').convert('RGBA'))
    for cells,angle in zip(poses['plane'],(46,-47,0,0,0,0)):
        frame=flight_art(plane,cells,angle,patterns)
        if angle==46:
            banked_flyby(frame,cells,rules,save,flying)
        else:
            add_tiles(flying,frame,cells,0x700,('FF252005',))
    for cells in poses['glint']:
        add_tiles(flying,sparkle(cells,patterns),cells,0x700,('FF252005',))
    for guard,images in ((BATTLE,surface),(SINK,sinking),(FLIGHT,flying)):
        for (tile,palette),image in images.items():
            register(tile,palette,slot(image),guard)
