"""Harbor arrival, receiver acquisition and the receiver indicator."""
from PIL import Image, ImageDraw, ImageOps
from sprite_motion import trim

LANCZOS = Image.Resampling.LANCZOS


def receiver_icon(vector):
    return vector(16, 8, '''
    <path d="M2 3L.7.6" fill="none" stroke="#d1d9d2" stroke-width=".55"/>
    <rect x="1.2" y="2" width="14.2" height="5.7" rx="1" fill="#354d50" stroke="#8bafad" stroke-width=".35"/>
    <rect x="2.3" y="3.1" width="5.2" height="2.5" rx=".3" fill="#d9bd82"/>
    <path d="M3 4.6h3.6M5.4 3.5v1.6" fill="none" stroke="#805732" stroke-width=".35"/>
    <path d="M9 3.4h4.1M9 4.3h4.1M9 5.2h4.1M9 6.1h4.1" fill="none" stroke="#111f25" stroke-width=".42"/>
    <circle cx="3" cy="6.5" r=".45" fill="#d5a55e"/>''')


def build_harbor(assets, boat, vector, text, save, rules, register, slot):
    # These pairs identify the two different nametables before and after the
    # purchase, independently of the HUD variant and the sprite palette.
    receiver = 'ReceiverTitle&ReceiverWord'
    port = 'HarborCloud&HarborTree'
    rules.extend(('<condition>ReceiverWord,tileAtPosition,83,59,154,00000000,Y',
                  '<condition>ReceiverTitle,tileAtPosition,43,43,159,00000000,Y',
                  '<condition>HarborCloud,tileAtPosition,43,43,38,00000000,Y',
                  '<condition>HarborTree,tileAtPosition,43,83,4A,00000000,Y'))
    with Image.open(assets/'harbor.png') as image:
        harbor = ImageOps.fit(image.convert('RGB'), (1024, 800), method=LANCZOS)
    save(harbor.crop((0,0,1024,736)), 'harbor.png')
    strip = Image.new('RGBA',(1024,800))
    strip.paste(harbor.crop((0,736,1024,800)),(0,736))
    save(strip,'harbor-water.png')
    # Priority 30 covers the original composite (dock and oversized boat).
    # Reserve the dialogue area whenever the game opens the text split.
    rules.append(f'[{port}]<background>harbor.png,1,0,0,30')
    rules.append(f'[{port}&!MapMessageRow]<background>harbor-water.png,1,0,0,29')
    with Image.open(assets/'sharks.png') as image:
        shark = trim(image.convert('RGBA').crop((0,414,image.width,image.height)))
    with Image.open(assets/'underwater.png') as image:
        water = ImageOps.fit(image.convert('RGB'), (1024, 800), method=LANCZOS)
    card = Image.blend(water, Image.new('RGB',water.size,'#082832'), .38).convert('RGBA')
    glass = Image.new('RGBA',card.size)
    draw = ImageDraw.Draw(glass)
    cx,cy=530,441
    for radius in (145,221,298):
        draw.ellipse((cx-radius,cy-radius,cx+radius,cy+radius),outline=(173,221,196,74),width=2)
    draw.line((80,cy,948,cy), fill=(173,221,196,54),width=2)
    draw.line((cx,224,cx,706), fill=(173,221,196,54),width=2)
    card.alpha_composite(glass)
    card.alpha_composite(shark.resize((696,267),LANCZOS),(164,330))
    draw = ImageDraw.Draw(card)
    draw.rectangle((0,0,1023,193), fill='#0c222a')
    draw.line((64,192,960,192), fill='#c99d62', width=3)
    text(card,(512,80),'YOU CAN NOW TRACK JAWS',50,'#f7ead5','ms',True)
    text(card,(512,141),'WITH THE RECEIVER.',40,'#b1cfcc','ms',True)
    save(card,'receiver.png')
    rules.append(f'[{receiver}]<background>receiver.png,1,0,0,30')
    # During the split transition the game briefly displays the same scene
    # with an uninitialized HUD. Mask only that uninitialized footer.
    footer = Image.new('RGBA',(1024,960))
    ImageDraw.Draw(footer).rectangle((0,800,1023,959),fill='#0b1b21')
    save(footer,'port-footer.png')
    for scene in (receiver,port):
        rules.append(f'[{scene}&!HudS]<background>port-footer.png,1,0,0,34')
    # The boat actor advances one native pixel at a time from outside the
    # left edge. Pin the painting to its signed world X during this shot.
    surface = Image.new('RGBA',(1280,800))
    surface.alpha_composite(boat.resize((249,172),LANCZOS),(252,422))
    save(surface,'harbor-boat.png')
    for x in range(-63,9):
        name = f'HarborX{x & 255:02X}'
        rules.append(f'<condition>{name},memoryCheckConstant,0682,==,{x & 255:02X}')
        rules.append(f'[{port}&{name}]<background>harbor-boat.png,1,0,0,31,{64-x},0')
    rules.extend(('<condition>PowerReply,tileAtPosition,59,194,150,00000000,Y',
                  '<condition>PowerReplyWord,tileAtPosition,107,194,14C,00000000,Y'))
    banner = Image.new('RGBA',(1024,800))
    pen = ImageDraw.Draw(banner)
    pen.rectangle((0,736,1023,799),fill='#102831')
    pen.line((0,737,1023,737),fill='#d29d60',width=2)
    text(banner,(512,780),'POWER LEVEL RAISED.',28,'#ffe5ac','ms',True)
    save(banner,'port-power.png')
    rules.append(f'[{port}&MapMessageRow&PowerReply&PowerReplyWord]<background>port-power.png,1,0,0,32')

    # The receiver indicator replaces the two original HUD icon tiles once
    # acquired. Cover only the native glyphs so shell and power counts stay live.
    icon = receiver_icon(vector)
    for index, tile in enumerate((0x11b,0x11c)):
        image = icon.crop((index*32,0,index*32+32,32))
        register(tile,'0F201527',slot(image),'HudS&HudJ')
