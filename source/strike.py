"""Oversized final-battle shark art, anchored to the native encounter."""
from PIL import Image
import numpy as np

from sprite_motion import trim

LANCZOS = Image.Resampling.LANCZOS


def breach_sequences(rom):
    # Four camera distances use separate strobe animations. Each entry has
    # duration/flip flags and a pointer to signed XY/CHR triples. Receding
    # poses reuse the same pictures in reverse.
    prg = memoryview(rom)[16:16+32768]
    def word(address):
        index = address-0x8000
        return int.from_bytes(prg[index:index+2], 'little')
    for tier in range(4):
        sequence = word(0xded3+2*tier)
        offset = sequence-0x8000
        frames = {}
        while prg[offset]:
            pose = word(0x8000+offset+1)
            if pose not in frames:
                index = pose-0x8000
                tiles = []
                while prg[index] != 0x80:
                    tiles.append(prg[index+2])
                    index += 3
                frames[pose] = tiles
            offset += 3
        yield sequence, frames


def emerging(master, width, height, fraction, angle):
    shark = trim(master.rotate(angle, Image.Resampling.BICUBIC, expand=True))
    shark = shark.resize((width,height), LANCZOS)
    if fraction >= 1:
        return shark
    visible = round(height*fraction)
    head = shark.crop((0,0,width,visible))
    # Use the painted water splash at the current waterline, with a gradual
    # edge on the body where it disappears into the water.
    pixels = np.array(head)
    fade = max(3,round(height*.045))
    pixels[-fade:,:,3] = np.rint(pixels[-fade:,:,3]*np.linspace(1,0,fade)[:,None])
    head = Image.fromarray(pixels)
    water = master.crop((0,int(master.height*.942),master.width,master.height))
    visible_body = head.getchannel('A').point(lambda a: 255 if a>80 else 0).getbbox()
    if visible_body:
        left,_,right,_ = visible_body
        spread = min(width,right-left+round(width*.19))
        water = water.resize((spread,max(4,round(height*.055))),LANCZOS)
        head.alpha_composite(water,(max(0,min(width-spread,(left+right-spread)//2)),visible-water.height))
    return head


def placements(width, y_min, y_max, check):
    """A leap holds its world position throughout the rise and fall."""
    margin = ((width//8+15)//8)*8
    result = []
    for xb in range(-margin,256+margin,8):
        page = check(f'SharkPage{(xb>>8)&255:02X}',0x0023,(xb>>8)&255)
        coarse_x = check(f'SharkX{xb&255:02X}',0x0022,xb&255,0xf8)
        for yb in range(y_min//8*8,y_max+1,8):
            coarse_y = check(f'SharkY{yb:02X}',0x0024,yb,0xf8)
            # Use exact positions in the game's small bow-strike window.
            if yb==168 and xb in (120,128):
                for x in range(xb,xb+8):
                    x_check = check(f'BowX{x:02X}',0x0022,x)
                    for y in range(yb,yb+8):
                        y_check = check(f'BowY{y:02X}',0x0024,y)
                        result.append((x,y,f'{x_check}&{y_check}&{page}'))
            else:
                result.append((xb+4,yb+4,f'{coarse_x}&{coarse_y}&{page}'))
    return result


def build_strike(art, rom, rules, save, battle_guard, surface, palette):
    conditions = {}
    def check(name, address, value, mask=255):
        conditions[name] = f'<condition>{name},memoryCheckConstant,{address:04X},==,{value:02X},{mask:02X}'
        return name

    impact_rules = []
    rise_rules = []
    empty = Image.new('RGBA',(32,32))
    clean = trim(art('breach-shark').convert('RGBA'))
    impaled = trim(art('impaled-shark').convert('RGBA'))
    right = check('BreachRight',0x02ba,0,64)
    left = check('BreachLeft',0x02ba,64,64)
    rules.append('<condition>PiercedTip,spriteAtPosition,123,156,61C,FF16260F,Y')
    sizes = ((60,88),(99,144),(175,248),(280,400))
    distances = ((80,95),(96,111),(112,135),(136,184))
    for tier,(seq,frames) in enumerate(breach_sequences(rom)):
        width,height = sizes[tier]
        y_min,y_max = distances[tier]
        points = placements(width,y_min,y_max,check)
        animation = check(f'Leap{tier}',0x0028,seq&255)
        page = check(f'LeapPage{seq>>8:X}',0x0029,seq>>8)
        num_rising = len(frames)-2
        for phase,(pose,tiles) in enumerate(frames.items()):
            for tile in tiles:
                surface[(0x600+tile,palette)] = empty
            phase_check = check(f'Rise{pose:04X}',0x0026,pose&255)
            gate = f'{phase_check}&{animation}&{page}&{battle_guard}'
            fraction = min(1,(phase+1)/num_rising)
            roll = max(0,phase-num_rising+1)
            angle = (0,4,-6)[roll]
            shark = emerging(clean,width,height,fraction,angle)
            for facing,mirrored in ((right,False),(left,True)):
                sprite = shark.transpose(Image.Transpose.FLIP_LEFT_RIGHT) if mirrored else shark
                # Padding lets an intact picture follow the shark, including
                # the moments when a fin or splash crosses a screen edge.
                pad_y = y_max+8
                sheet = Image.new('RGBA',(1024+width,4*pad_y+sprite.height))
                sheet.alpha_composite(sprite,(1024,4*pad_y))
                suffix = 'l' if mirrored else 'r'
                name = f'leap-{tier}-{phase}-{suffix}.png'
                save(sheet,name)
                # Match the belly's anatomical center over the spike during
                # the clean approach; small distant encounters retain scale.
                center_x = width//8
                base_y = 3
                if tier==3:
                    center_x = (35,31,34)[roll]
                    if mirrored:
                        center_x = width//4-center_x
                    base_y = 7
                for x,y,location in points:
                    origin_x = 256-x+center_x
                    origin_y = pad_y-y-base_y+round(sprite.height/4)
                    rise_rules.append(f'[{location}&{facing}&{gate}]<background>{name},1,0,0,23,{origin_x},{origin_y}')

                if tier==3 and phase>=num_rising:
                    # The successful thrust is always on the centerline.
                    # Register the actual puncture to the painted steel tip.
                    hurt = emerging(impaled,width,height,1,angle)
                    pivot_x,pivot_y = ((31,76),(34,75))[roll-1]
                    if mirrored:
                        hurt = hurt.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                        pivot_x = width//4-pivot_x
                    wound = Image.new('RGBA',(1024,832))
                    wound.alpha_composite(hurt,(4*(128-pivot_x),4*(154-pivot_y)))
                    hit_name = f'impaled-{roll}-{suffix}.png'
                    save(wound,hit_name)
                    # On the last partial frame the PPU has already blanked
                    # the bow and footer, while the upper sea is still live.
                    for contact in ('PiercedTip','!StrobeStrip'):
                        impact_rules.append(f'[FinishHit&{contact}&{facing}&{gate}]<background>{hit_name},1,0,0,23')

    rules.extend(conditions.values())
    # The renderer chooses the first active background at a given priority.
    rules.extend(impact_rules)
    rules.extend(rise_rules)


def build_descent(master, cells, rules, save, sink_guard, output):
    # A wider underwater view follows the dead shark all the way down. The
    # descent routine starts at (128,160), adds half a pixel per frame to Y
    # and drifts one pixel to the right for each eight pixels of descent.
    image=trim(master.convert('RGBA')).resize((208,332),LANCZOS)
    sheet=Image.new('RGBA',(1024,1280))
    sheet.alpha_composite(image,(768,944))
    save(sheet,'shark-descent.png')
    for depth in range(97):
        y=(160+depth)&255
        condition=f'SinkDepth{depth}'
        rules.append(f'<condition>{condition},memoryCheckConstant,0684,==,{y:02X}')
        x=128+depth//8
        top=85+round(1.57*depth)
        rules.append(f'[{sink_guard}&{condition}]<background>shark-descent.png,1,0,0,23,{192-x+26},{236-top}')
    empty=Image.new('RGBA',(32,32))
    for tile,_,_,_ in cells:
        output[(0x400+tile,'FF200300')]=empty
