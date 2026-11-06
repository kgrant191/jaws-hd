"""Reassemble native Jaws sprite layouts at four times their original size."""

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import map_coordinates

LANCZOS = Image.Resampling.LANCZOS
STYLES = ("Moon Jelly", "Amber Sea Nettle", "Electric Blue")


def trim(image):
    bounds = image.getchannel("A").point(lambda value: 255 if value >= 20 else 0).getbbox()
    return image.crop(bounds)


def plate(path, rectangles):
    with Image.open(path) as master:
        image = master.convert("RGBA")
    return [trim(image.crop(box)) for box in rectangles]


def place(image, extent, size, center):
    canvas = Image.new("RGBA", extent)
    sprite = image.resize(size, LANCZOS)
    canvas.alpha_composite(sprite, (round(center[0] - size[0] / 2), round(center[1] - size[1] / 2)))
    return canvas


def subtle_outline(image, color, radius=1):
    alpha = image.getchannel("A").filter(ImageFilter.MaxFilter(2 * radius + 1))
    edge = Image.new("RGBA", image.size, color)
    edge.putalpha(alpha.point(lambda value: value * color[3] // 255))
    return Image.alpha_composite(edge, image)


def deform(image, dx, dy):
    """Inverse-map RGBA in premultiplied space to retain clean sprite edges."""
    pixels = np.array(image.convert("RGBa"), dtype=np.uint8)
    y, x = np.indices(pixels.shape[:2], dtype=float)
    channels = [map_coordinates(pixels[:, :, c], (y - dy, x - dx), order=1, mode="constant")
                for c in range(4)]
    return Image.fromarray(np.stack(channels, axis=-1), "RGBa").convert("RGBA")


def register_tiles(store, canvas, layout, bank):
    for tile, x, y in layout:
        store[bank + tile] = canvas.crop((4*x, 4*y, 4*x+32, 4*y+32))


def rectangle_tiles(store, image, tiles, columns=2):
    layout = [(tile, i % columns * 8, i // columns * 8) for i, tile in enumerate(tiles)]
    register_tiles(store, image, layout, 0x400)


def swim_cycle(store, swimmer):
    # The hip, tanks, mask and both hands are locked. Each fin rotates around
    # its own knee, with opposite upstrokes to produce a real scissor kick.
    base = place(swimmer, (64,64), (63,34), (32,31))
    y,x = np.indices((64,64), dtype=float)
    leg = np.clip((29-x)/24, 0, 1)**1.3
    split = 35 - 0.28*x
    for sign, tiles in ((1,(10,11,26,27)),(-1,(12,13,28,29))):
        dy = sign * leg * 5.6 * np.tanh((y-split)/2.8)
        body = deform(base, np.zeros_like(x), dy)
        rectangle_tiles(store, subtle_outline(body, (7,41,52,76)), tiles)


def boat_heading(store, vector, overhead):
    # The map's north and south poses use different OAM fragments, including
    # separate aft cells for a stopped boat. The bow fits in their common core.
    idle_south = {}
    bare = Image.new("RGBA", (96, 96))
    bare.alpha_composite(overhead.resize((30, 72), LANCZOS), (33, 4))
    south_still = Image.new("RGBA", bare.size)
    # The southern stern has two OAM columns, while the northern one has
    # three. Center its wake and hull together within the available cells.
    south_still.alpha_composite(bare.transpose(Image.Transpose.ROTATE_180), (-2, 0))
    for phase in range(4):
        shift = (0, .42, -.35, .08)[phase]
        wake = "" if phase == 3 else f"""
        <path d="M9.2 16.5Q8.9 19.2 {6.4+shift} 21.1 M14.6 16.5Q15 19 {17.8-shift} 21.1"
              fill="none" stroke="#87c4c0" stroke-width=".65"/>
        <path d="M10.1 18.1Q11.9 {20.4+shift} 13.8 18.2 M10.9 21.2h2"
              fill="none" stroke="#d1e1ce" stroke-width=".48"/>"""
        north = vector(24,24,wake)
        # The 32px-wide center column is always present, even when the boat
        # stops and the game drops both outer wake cells.
        north.alpha_composite(overhead.resize((30,72), LANCZOS),(33,4))
        south = vector(24, 24, f'''<g fill="none" stroke-linecap="round">
            <path d="M8.45 7Q8.35 5.1 {7.55+shift*.5} 2.5 M14.55 7Q14.65 5.1 {15.45-shift*.5} 2.5"
                  stroke="#90cecf" stroke-width=".7"/>
            <path d="M9.6 5.7Q11.5 {3.4+shift} 13.4 5.7 M10.55 2.4h1.9"
                  stroke="#d1e5de" stroke-width=".48"/></g>''') if phase != 3 else Image.new("RGBA", bare.size)
        south.alpha_composite(south_still)
        north_patterns = [
            [0x34,0x43,0x44,0x53,0x54,0x55],
            [0x04,0x13,0x14,0x23,0x24,0x25],
            [0x35,0x46,0x45,0x03,0x15,0x05],
            [None,None,None,None,0x36,None],
        ]
        north_pos = [(8,0),(0,8),(8,8),(0,16),(8,16),(16,16)]
        layout = [(t,x,y) for t,(x,y) in zip(north_patterns[phase],north_pos) if t is not None]
        register_tiles(store, north, layout, 0x200)
        if phase == 3:
            register_tiles(store, south, [(0x56,8,16)],0x200)
        else:
            a,b,c = [(0x37,0x57,0x3d),(0x39,0x59,0x4d),(0x3b,0x5b,0x5d)][phase]
            layout = [(a,0,0),(a+1,8,0),(a+16,0,8),(a+17,8,8),
                      (b,0,16),(b+1,8,16),(c,16,16)]
            register_tiles(store, south, layout, 0x200)
            register_tiles(idle_south, south_still, layout, 0x200)
    return idle_south


def horizontal_boat(store, overhead, vector):
    # Keep the same deck and cabin when turning through ninety degrees. The
    # original shifts the entire sprite by one NES pixel to make it bob.
    still = Image.new('RGBA',(96,96))
    hull = overhead.resize((30,72),LANCZOS).transpose(Image.Transpose.ROTATE_270)
    still.alpha_composite(hull,(15,45))
    upper = [(0,0,0),(1,8,0),(0x10,0,8),(0x11,8,8),(0x12,16,8)]
    # The middle bottom cell of the last moving pose is $02, not $31.
    rows = [(0x50,0x21,0x22),(0x30,0x31,0x32),(0x40,0x41,0x52),
            (0x20,0x51,0x52),(0x30,0x02,0x42)]
    idle = {}
    for phase,bottom in enumerate(rows):
        sway = (0,.30,-.2,.20,-.30)[phase]
        wake = vector(24,24, f'''<g fill="none" stroke-linecap="round">
          <path d="M4.5 12.9 Q2.6 12.9 .65 11.65 M4.6 16.6 Q2.7 17.1 .8 {18.05+sway}"
             stroke="#9acdc9" stroke-width=".52"/>
          <path d="M3.5 14.3 Q2.4 14.7 1.6 14.3 M2.6 16.3l-.9 .4"
             stroke="#c9ded5" stroke-width=".36"/></g>''')
        wake.alpha_composite(still)
        lower = [(t,x*8,16) for x,t in enumerate(bottom)]
        register_tiles(store,wake,lower,0x200)
        register_tiles(idle,still,lower,0x200)
    # Upper/middle pieces are shared by all wave phases. Only the lower
    # wake tips vary. Every shared cell has the same painted hull.
    register_tiles(store,wake,upper,0x200)
    register_tiles(idle,still,upper,0x200)
    return idle


def collectible_cycles(store, crab, shell):
    y,x = np.indices((64,64), dtype=float)
    crab_body = place(crab, (64,64), (59,46), (32,35))
    for sign, tiles in zip((-1,0,1), ((0x34,0x35,0x28,0x29),(0x8c,0x8d,0x9c,0x9d),
                                        (0x8e,0x8f,0x9e,0x9f))):
        claws = np.clip((30-y)/17,0,1) * np.clip(abs(x-32)/18,0,1)
        dy = -2.6 * sign * claws
        dx = 1.8 * sign * np.sign(x-32) * claws
        rectangle_tiles(store, subtle_outline(deform(crab_body,dx,dy),(42,51,44,135)), tiles)
    # Six falling-shell frames share three tops. Each corresponding pair of
    # lower halves joins to exactly that top, including the final resting pose.
    for group, angle, width in [
        ((0x0e,0x1e,0xde),-13,52), ((0xae,0xbe,0xce),3,48), ((0xac,0xbc,0xcc),17,51)
    ]:
        top, lower1, lower2 = group
        turned = trim(shell.rotate(angle,Image.Resampling.BICUBIC,expand=True))
        pearl = subtle_outline(place(turned,(64,64),(width,47),(32,34)),(75,58,63,118))
        register_tiles(store,pearl,[(top,0,0),(top+1,8,0)],0x400)
        for j,lower in enumerate((lower1,lower2)):
            dx = j * .9 * np.clip((y-33)/22,0,1)
            art = deform(pearl,dx,np.zeros_like(x)) if j else pearl
            register_tiles(store,art,[(lower,0,8),(lower+1,8,8)],0x400)


def sea_star_cycle(store, assets):
    with Image.open(assets / "sea-star.png") as image:
        star = trim(image.convert("RGBA"))
    # The game mirrors the angled and edge-on cells for the return half of
    # the turn. The edge-on metasprite occupies a single column at x+3.
    for width, canvas, center, tiles in (
        (59, (64,64), (32,32), (0xdc,0xdd,0xec,0xed)),
        (41, (64,64), (32,32), (0xfc,0xfd,0xee,0xef)),
        (10, (32,64), (18,32), (0x9b,0xab)),
    ):
        body = place(star, canvas, (width,57), center)
        body = subtle_outline(body, (77,43,30,135))
        rectangle_tiles(store, body, tiles, columns=canvas[0]//32)


def ray_cycle(store, ray):
    # The ray is three tiles wide; the first two IDs alternate in the SAME
    # tail slot, while the following two IDs hold its body and nose.
    for i,start in enumerate((0x4c,0x5c,0x6c,0x7c)):
        image = place(ray,(96,32),(94,24+(i%2)*3),(48,16))
        y,x=np.indices((32,96),dtype=float)
        tail = deform(image,0*x,(i%2*2-1)*2*np.clip((40-x)/30,0,1))
        register_tiles(store, image, [(start,0,0),(start+2,8,0),(start+3,16,0)],0x400)
        register_tiles(store, tail, [(start+1,0,0)],0x400)


def reaction_cycle(store, impacts):
    recoil,sinker=impacts
    # The actual impact footprint is a four-cell diagonal with its top-left
    # and bottom-right corners absent. Keeping the figure central preserves it.
    recoiled=trim(recoil.rotate(-26,Image.Resampling.BICUBIC,expand=True))
    contact=place(recoiled,(96,64),(48,56),(49,32))
    impact_layers = []
    for i in range(3):
        pose = contact.rotate((0,-5,-11)[i],Image.Resampling.BICUBIC,center=(49,32))
        pen = ImageDraw.Draw(pose)
        # Exhaled air stays in the two active upper cells and peels away from
        # the mask over the native 32-frame recoil countdown.
        for j in range(4):
            x = 60 + 4*j + i*2
            y = 20 - j*4 - i*3
            radius = 1 + (j+i)%2
            pen.ellipse((x-radius,y-radius,x+radius,y+radius),
                        outline=(209,241,240,225),width=1)
        tiles = {}
        register_tiles(tiles,pose,[(0xb0,16,0),(0xb1,8,0),(0xc0,0,8),(0xc1,8,8)],0x400)
        impact_layers.append(tiles)

    store.update(impact_layers[-1])
    canvas=place(sinker,(64,96),(36,78),(32,49))
    # Six existing cell pairs represent a cyclic tumble. Constant source scale
    # preserves proportions. Tiny bubbles rotate independently of the figure.
    sequence=[0,6,10,2,4,8]
    for i,offset in enumerate(sequence):
        angle=(7,4,-3,-8,-5,2)[i]
        face=canvas.rotate(angle,Image.Resampling.BICUBIC,center=(32,47))
        pen=ImageDraw.Draw(face)
        for j in range(3):
            y=55-(i*3+j*14)%40
            x=48+(i+j*2)%6
            pen.ellipse((x,y,x+1+(j==0),y+1+(j==0)),outline=(199,232,231,165))
        ids=(0xd0+offset,0xd1+offset,0xe0+offset,0xe1+offset,0xf0+offset,0xf1+offset)
        rectangle_tiles(store,face,ids)
    return impact_layers


def jelly_atlas(jelly, style_index):
    # Keep the bell apex aligned. Water is expelled by the rim closing;
    # the tentacles follow with a small lateral wave of their own.
    sizes=[(53,48),(42,58),(53,47)]
    w,h=sizes[style_index]
    base=place(jelly,(64,64),(w,h),(32,31))
    y,x=np.indices((64,64),dtype=float)
    atlas=Image.new('RGBA',(192,64))
    for phase,contraction in enumerate((-.85,0,1)):
        bell=np.clip((y-4)/23,0,1)*np.clip((49-y)/14,0,1)
        tail=np.clip((y-25)/26,0,1)
        dx=(x-32)*-.12*contraction*bell+np.sin(y/8+phase)*2*tail
        dy=contraction*(1.8*bell+2.3*tail)
        body=deform(base,dx,dy)
        atlas.alpha_composite(subtle_outline(body,(20,54,68,85)),(64*phase,0))
    return atlas


def build(store, swimmer, shell, ray, vector, assets, output):
    with Image.open(assets/'marine-specimens.png') as f:
        w,h=f.size
    mid=w//2
    crab,moon,amber,blue=plate(assets/'marine-specimens.png',[
        (0,0,mid,585),(mid,0,w,585),(0,585,mid,h),(mid,585,w,h)])
    with Image.open(assets/'diver-reactions.png') as f:
        w,h=f.size
    impacts=plate(assets/'diver-reactions.png',[(0,0,w//2,h),(w//2,0,w,h)])
    swim_cycle(store,swimmer)
    with Image.open(assets/"map-boat.png") as original:
        overhead = trim(original.convert("RGBA"))
    idle_south = boat_heading(store,vector,overhead)
    idle_side = horizontal_boat(store,overhead,vector)
    collectible_cycles(store,crab,shell)
    sea_star_cycle(store, assets)
    impact_layers = reaction_cycle(store,impacts)
    ray_cycle(store,ray)
    for i,(name,art) in enumerate(zip(STYLES,(moon,amber,blue))):
        atlas=jelly_atlas(art,i)
        dest=output/'Jellyfish Options'/name
        dest.mkdir(parents=True,exist_ok=True)
        atlas.save(dest/'jellyfish.png')
        if i==0:
            atlas.save(output/'jellyfish.png')
    return impact_layers, idle_south, idle_side


def jelly_position(tile):
    for i,start in enumerate((0x42a,0x42c,0x42e)):
        for k,t in enumerate((start,start+1,start+16,start+17)):
            if tile==t:
                return i*64+k%2*32,k//2*32
    return None
