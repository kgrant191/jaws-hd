"""Harbor arrival, receiver acquisition and the receiver indicator."""
from PIL import Image, ImageDraw, ImageOps
from sprite_motion import trim

LANCZOS = Image.Resampling.LANCZOS


def receiver_icon(vector, pulse):
    # Move a single trace across the phosphor display with the NES signal.
    # The receiver sits inside the two lower HUD tiles below the label strip.
    points = []
    for column in range(35):
        relative = column - pulse
        wave = {-3: -.3, -2: -.9, -1: -1.55, 0: -1.9,
                1: 1.45, 2: .95, 3: .35}.get(relative, 0)
        points.append(f"{2.35 + column * .235:.2f},{4.45 + wave:.2f}")
    return vector(16, 8, f'''<path d="M2.2 2.7L.8.45" stroke="#d0dbcc" stroke-width=".55"/>
    <rect x=".7" y="1.4" width="14.9" height="6.3" rx=".8" fill="#48585a" stroke="#a1b8b2" stroke-width=".34"/>
    <rect x="1.7" y="2.05" width="9.4" height="4.6" rx=".5" fill="#102f31" stroke="#728d86" stroke-width=".32"/>
    <path d="M4 2.5v3.6m2.3-3.6v3.6m2.3-3.6v3.6M2.2 4.45h8.4" fill="none" stroke="#37605b" stroke-width=".22"/>
    <polyline points="{' '.join(points)}" fill="none" stroke="#a6f6c3" stroke-width=".45" stroke-linejoin="round"/>
    <path d="M12.1 4h2.3m-2.3.9h2.3m-2.3.9h2.3" stroke="#192f33" stroke-width=".4"/>
    <circle cx="13.25" cy="2.8" r=".48" fill="{'#ffbc6b' if pulse >= 0 else '#a08057'}"/>''')


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

    # The game leaves the lower pair in place and writes its oscilloscope
    # waveform to the two tiles directly above it. Match the actual signal,
    # including pauses between proximity pings and the unowned HUD state.
    phases = (
        (0x2f6f, 0x0d, 1), (0x2f6f, 0x1d, 5),
        (0x2f6f, 0x0e, 10), (0x2f6f, 0x1e, 15),
        (0x2f6f, 0x24, 20), (0x2f70, 0x27, 24),
        (0x2f70, 0x28, 28), (0x2f70, 0x29, 33),
    )
    for phase, (address, code, pulse) in enumerate(phases):
        condition = f'ReceiverPulse{phase}'
        rules.append(f'<condition>{condition},ppuMemoryCheckConstant,{address:04X},==,{code:02X}')
        icon = receiver_icon(vector, pulse)
        for col, tile in enumerate((0x11b, 0x11c)):
            index = slot(icon.crop((col*32, 0, col*32+32, 32)))
            rules.append(f'[HudS&HudJ&{condition}]<tile>0,{tile:X},0F201527,{index%16*32},{index//16*32},1,N')
    icon = receiver_icon(vector, -20)
    for col, tile in enumerate((0x11b, 0x11c)):
        register(tile, '0F201527', slot(icon.crop((col*32, 0, col*32+32, 32))), 'HudS&HudJ')
