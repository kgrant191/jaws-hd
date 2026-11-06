"""Mini-submarine pickup, piloted craft and torpedo in their native sprite cells."""
from PIL import Image

from sprite_motion import LANCZOS, subtle_outline


def mini_sub(assets, vector, register, slot, rules):
    # In both metasprites the upper row uses sprite palette 1 and the
    # lower row palette 3. The PPU mirrors the whole craft when it turns.
    row_palettes = ('FF200F27', 'FF0F2717')
    with Image.open(assets / 'mini-sub-map.png') as source:
        pickup = source.transpose(Image.Transpose.FLIP_LEFT_RIGHT).resize((88, 42), LANCZOS)
    chart = Image.new('RGBA', (96, 64))
    chart.alpha_composite(subtle_outline(pickup, (28, 42, 41, 115)), (0, 13))
    for row, palette in enumerate(row_palettes):
        for col in range(3):
            x, y = col*32, row*32
            tile = 0x260 + row*16 + col
            register(tile, palette, slot(chart.crop((x,y,x+32,y+32))), 'MapA&MapB')

    with Image.open(assets / 'mini-sub-side.png') as source:
        side = source.convert('RGBA')
    # Foreshorten the two propeller blades around their shaft for the
    # second pose. The housing and cockpit stay fixed through the cycle.
    blade_x = round(side.width * .946)
    blades = side.crop((blade_x, 0, side.width, side.height))
    short = blades.resize((blades.width, round(blades.height*.32)), LANCZOS)
    turned = side.copy()
    turned.paste((0,0,0,0), (blade_x,0,side.width,side.height))
    turned.alpha_composite(short, (blade_x, round((side.height-short.height)*.52)))

    rules.append('<condition>SubPropTurn,frameRange,10,5')
    for phase, master in enumerate((side, turned)):
        hull = master.transpose(Image.Transpose.FLIP_LEFT_RIGHT).resize((64,28), LANCZOS)
        pose = Image.new('RGBA', (64,64))
        pose.alpha_composite(hull, (0,20))
        for row, palette in enumerate(row_palettes):
            for col in range(2):
                # Only the stern column changes at the half-turn.
                if phase and col:
                    continue
                guard = 'DiveA&DiveB'
                if col == 0:
                    guard += '&SubPropTurn' if phase else '&!SubPropTurn'
                x, y = col*32, row*32
                register(0x408+16*row+col, palette, slot(pose.crop((x,y,x+32,y+32))), guard)

    torpedo = vector(8, 8, '''
        <path d="M1 2.5l1.6.7h2.6q1.15 0 1.8.85-.7.9-1.8.9H2.6L1 5.65 1.4 4Z"
              fill="#adc5c4" stroke="#264751" stroke-width=".35"/>
        <path d="M5.1 3.32q1-.03 1.69.73-.7.73-1.69.75Z" fill="#e9a14d"/>
        <path d="M2.4 3.6H4.9" stroke="#e6efdc" stroke-width=".34"/>''')
    register(0x421, 'FF201610', slot(torpedo), 'DiveA&DiveB')
