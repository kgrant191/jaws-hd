"""Shark poses and camera-registered water and coastline for the Jaws encounters."""
from PIL import Image, ImageDraw
import numpy as np
from scipy.ndimage import map_coordinates, minimum_filter1d, gaussian_filter1d, gaussian_filter, binary_fill_holes
from sprite_motion import trim, deform, subtle_outline, register_tiles

LANCZOS = Image.Resampling.LANCZOS


def adult_pose(master):
    # Only the first four columns have upper tiles. Place the unwarped
    # shoulder below row 32, letting the dorsal and tail fill the upper row.
    base = Image.new('RGBA', (192, 96))
    base.alpha_composite(trim(master).resize((189, 76), LANCZOS), (1, 18))
    return subtle_outline(base, (9, 33, 43, 100))


def juvenile_pose(master):
    width = 128
    height = 96
    shark = trim(master)
    base = Image.new('RGBA', (width, height))
    pose_size = (width-3, 55)
    base.alpha_composite(shark.resize(pose_size, LANCZOS), (1, 16))
    # The juvenile has only one lower-fin cell and two isolated upper cells.
    # Compress fin tips into those cells while keeping the eye and belly aligned.
    pixels = np.asarray(base.convert('RGBa'))
    yy, xx = np.indices((height, width), dtype=float)
    axis = 48
    top_scale = np.ones(width)
    bottom_scale = np.ones(width)
    for x in range(width):
        opaque = np.flatnonzero(pixels[:,x,3] > 16)
        if len(opaque) < 3:
            continue
        top, bottom = opaque[[0,-1]]
        top_room = np.interp(x,[0,23,31,32,56,60,64,78,87,88,127],
                                  [7,8,31,33,33,32,9,9,31,33,33])
        floor = np.interp(x,[0,51,52,58,76,83,84,127],[62,62,63,81,81,63,62,62])
        if top < axis:
            top_scale[x] = min(1,(axis-top_room)/(axis-top))
        if bottom > axis:
            bottom_scale[x] = min(1,(floor-axis)/(bottom-axis))
    # Ease each fin into its allotted region without shifting the body center.
    top_scale = gaussian_filter1d(minimum_filter1d(top_scale,7),1)
    bottom_scale = gaussian_filter1d(minimum_filter1d(bottom_scale,7),1)
    sy = axis + (yy-axis)/np.where(yy<axis,top_scale,bottom_scale)
    channels = [map_coordinates(pixels[:,:,c],(sy,xx),order=1,mode='constant') for c in range(4)]
    return subtle_outline(Image.fromarray(np.stack(channels,axis=-1),'RGBa').convert('RGBA'),(9,33,43,100))


def sharks(store, assets):
    with Image.open(assets/'sharks.png') as source:
        art = source.convert('RGBA')
    juvenile = juvenile_pose(art.crop((0,0,art.width,414)))
    adult = adult_pose(art.crop((0,414,art.width,art.height)))
    for phase,(tail,dorsal,fin,body) in enumerate(((0x64,0x66,0x67,0x68),
                                                  (0x65,0x76,0x77,0x78),
                                                  (0x64,0x86,0x87,0x88))):
        y,x = np.indices((96,128), dtype=float)
        bend = np.maximum(0,1-x/54)**1.7
        factor = (-1,1,-1)[phase]
        sprite = deform(juvenile, -factor*1.9*bend, factor*3.7*bend)
        cells = [(tail,0,0),(dorsal,14 if phase==1 else 15,0),(fin,13,16)]
        cells += [(body+i,i*8,8) for i in range(4)]
        register_tiles(store,sprite,cells,0x400)
    # On contact the game selects palette 1, a new snout and a fin column at
    # x=16 for both fins. Register the complete pose separately from swimming.
    y,x = np.indices((96,128),dtype=float)
    forefin = np.clip((y-54)/12,0,1)*np.exp(-((x-72)/22)**2)
    dorsal = np.clip((37-y)/13,0,1)*np.exp(-((x-73)/16)**2)
    bend = np.maximum(0,1-x/51)**1.65
    recoil = deform(juvenile,9*forefin+3*dorsal-2*bend,
                    4*bend-1.4*np.clip((x-88)/30,0,1))
    rgba = np.array(recoil)
    # Retain the painted contrast, with a short pearly highlight for the hit.
    rgba[:,:,:3] = np.rint(rgba[:,:,:3]*.88+np.array([235,227,204])*.12).astype('uint8')
    damaged = {}
    hit_cells = [(0x65,0,0),(0x76,16,0),(0x77,16,16),
                 (0x78,0,8),(0x79,8,8),(0x7a,16,8),(0xa8,24,8)]
    register_tiles(damaged,Image.fromarray(rgba),hit_cells,0x400)
    register_adult(store, adult)
    wounded = {}
    with Image.open(assets/'shark-wounded.png') as source:
        register_adult(wounded, adult_pose(source.convert('RGBA')))
    return damaged, wounded


def register_adult(store, adult):
    # Tail and body cycles are selected separately by the original renderer.
    # Lock their shared joint and animate the jaw in the second head pose.
    y,x = np.indices((96,192),dtype=float)
    for phase,offset in enumerate((0,6)):
        bend = np.maximum(0,1-x/65)**1.6
        jaw = np.clip((x-145)/40,0,1)*np.clip((y-49)/12,0,1)
        factor = -1 if phase==0 else 1
        sprite = deform(adult, -factor*2.8*bend, factor*5.3*bend+phase*2.3*jaw)
        cells = [(0x30+16*row+col+offset,col*8,row*8)
                 for row,count in enumerate((4,6,6)) for col in range(count)]
        register_tiles(store,sprite,cells,0x400)
    neutral_tail = [(0x60+16*row+col,col*8,row*8) for row in range(3) for col in range(2)]
    register_tiles(store,adult,neutral_tail,0x400)
    # The third swimming body has a closing jaw and can pair with any tail.
    # Hold its flank color constant through the cycle, including while firing.
    pectoral = np.exp(-((x-99)/23)**2)*np.clip((y-57)/24,0,1)
    closing = deform(adult,1.5*pectoral,-4.2*jaw+1.4*pectoral)
    cells = [(0x60+row*16+col,col*8,row*8)
             for row,count in enumerate((4,6,6)) for col in range(2,count)]
    register_tiles(store,closing,cells,0x400)



def shallows(assets, full, destination, save, bg):
    ocean = Image.new('RGB',full.size,'#145564')
    ocean.paste(full.crop((0,0,1024,494)),(0,64))
    ocean.paste(full.crop((0,0,1024,64)),(0,0))
    shoal = Image.open(assets/'shoal.png').convert('RGB').resize((1024,412),LANCZOS)
    # Darken the first meters to meet the storm-lit surface used in the deep dive.
    arr = np.asarray(shoal).astype(float)
    t = np.linspace(0,1,412)[:,None,None]
    arr *= .78+.22*np.sqrt(t)
    shoal = Image.fromarray(arr.astype('uint8'))
    ocean.paste(shoal,(0,490))
    alpha = Image.fromarray(np.uint8(np.clip((np.arange(64)-2)/62,0,1)*255)).resize((1024,64))
    ocean.paste(shoal.crop((0,0,1024,64)),(0,490),alpha)
    surface = full.crop((0,426,1024,490))
    ocean.paste(surface,(0,490),Image.fromarray(255-np.asarray(alpha)))
    save(ocean,'shoal.png')
    bg('ShallowA&ShallowB','shoal.png',10,1)
    # A transparent wave layer dissolves into the new water column.
    for phase in reversed(range(4)):
        wave = Image.open(destination/f'breakers-{phase}.png').convert('RGBA')
        arr = np.array(wave)
        arr[:,:,3] = np.rint(arr[:,:,3]*np.clip((493-np.arange(wave.height))/62,0,1)[:,None]).astype('uint8')
        layer = Image.new('RGBA',(1024,wave.height+64))
        layer.paste(Image.fromarray(arr),(0,64))
        path = f'shoal-breakers-{phase}.png'
        save(layer,path)
        bg('ShallowA&ShallowB'+(f'&tide{phase}' if phase else ''),path,11,1)


def coastline(assets, previous, save):
    extension = Image.open(assets/'full-coast.png').convert('RGB').resize((2048,1536),LANCZOS)
    west = previous.crop((0,128,1024,1664))
    # Preserve the painted western half and crossfade twelve native pixels
    # over the seam. Both halves are aligned to the same ROM metatile grid.
    alpha = np.clip((1024-np.arange(1024))/48,0,1)
    mask = Image.fromarray(np.tile(np.uint8(255*alpha),(2,1))).resize((1024,1536))
    extension.paste(west,(0,0),mask)
    out = Image.new('RGB',(2048,1920),'#08171c')
    out.paste(extension.crop((0,0,2048,128)).transpose(Image.Transpose.FLIP_TOP_BOTTOM),(0,0))
    out.paste(extension,(0,128))
    out.paste(extension.crop((0,1280,2048,1536)).transpose(Image.Transpose.FLIP_TOP_BOTTOM),(0,1664))
    save(out,'coast.png')


def map_fins(store, patterns, layouts):
    # Assemble the real surfacing and submerging poses before smoothing. Edges
    # across adjoining cells then share normals and keep the fin in one piece.
    for cells in layouts:
        w = max(x for _,x,_ in cells)+8
        h = max(y for _,_,y in cells)+8
        original = np.zeros((h,w),np.uint8)
        for tile,x,y in cells:
            original[y:y+8,x:x+8]=patterns[0x200+tile]
        fin = binary_fill_holes(original>=2)
        def mask(a):
            plane=np.asarray(Image.fromarray(np.uint8(a)*255).resize((w*4,h*4),Image.Resampling.BICUBIC))/255
            return gaussian_filter(plane,1.6)
        body, highlight, foam = (mask(a) for a in (fin, original==3, original==1))
        y,x=np.indices(body.shape)
        alpha=np.clip((body-.28)*2.5,0,1)
        shade=np.clip(.30+.32*highlight+.15*(1-y/(h*4))+.19*np.sin((x-y*.23)/(w*4)*np.pi)
                      +.06*np.cos(y*.41+x*.73),0,1)
        dark=np.array([16,42,51]);light=np.array([149,171,174])
        rgb=dark+(light-dark)*shade[:,:,None]
        rim=np.clip(foam*alpha,0,1)[:,:,None]
        rgb=rgb*(1-.58*rim)+np.array([209,218,206])*.58*rim
        fg=Image.fromarray(np.dstack((rgb,alpha*255)).astype('uint8'))
        froth=np.clip((foam-.19)*1.7,0,1)
        out=Image.new('RGBA',fg.size,(167,215,215,0))
        out.putalpha(Image.fromarray(np.uint8(froth*235)))
        out.alpha_composite(fg)
        register_tiles(store,out,cells,0x200)


def ordnance(store):
    # Round iron shot on the boat has the same center and diameter as tile $23.
    y,x=np.mgrid[:32,:32];dx=(x-17.5)/9.6;dy=(y-13.5)/9.6
    r=dx*dx+dy*dy; z=np.sqrt(np.maximum(0,1-r))
    light=np.clip(-.52*dx-.65*dy+.56*z,0,1)
    shine=np.exp(-((dx+.38)**2+(dy+.44)**2)/.045)
    color=np.array([20,30,33])+light[:,:,None]*np.array([73,82,80])+shine[:,:,None]*142
    alpha=np.clip((1.05-r)*8,0,1)
    store[0x423]=Image.fromarray(np.dstack((color,alpha*255)).clip(0,255).astype('uint8'))


def bonus_plane(store, assets, vector):
    # The engine changes only the lower nose cell, on both left and right
    # passes. Keep the propeller's entire moving area inside that one cell.
    with Image.open(assets/'bonus-plane.png') as source:
        airframe = trim(source.convert('RGBA')).resize((122,43),LANCZOS)
    hull = Image.new('RGBA',(128,64))
    hull.alpha_composite(airframe,(2,18))
    layout = [(t,8*col,8*row) for row,tiles in enumerate(((0,1,2,3),(16,17,18,19)))
              for col,t in enumerate(tiles)]
    for phase,tilt in enumerate((2.3,-1.8)):
        scale = 4
        overlay = Image.new('RGBA',(128*scale,64*scale))
        pen = ImageDraw.Draw(overlay)
        def points(*coords):
            return tuple(round(v*scale) for v in coords)
        cx,cy = 118.8,45.5
        reach = (13.2,10.2)[phase]
        pen.ellipse(points(cx-2.4,cy-13.4,cx+2.4,cy+14.3),fill=(190,211,209,39))
        for side in (-1,1):
            endx,endy = cx+tilt*side,cy+reach*side
            pen.polygon([points(cx-.7,cy),points(endx-1.3,endy),
                         points(endx+.7,endy),points(cx+1.5,cy)],fill=(43,58,66,235))
            pen.line([points(endx-.4,endy-side*1.5),points(endx-.4,endy)],
                     fill=(230,199,137,233),width=scale)
        sprite = overlay.resize(hull.size,LANCZOS)
        sprite.alpha_composite(hull)
        if phase==0:
            register_tiles(store,sprite,layout,0x400)
        else:
            register_tiles(store,sprite,[(7,24,8)],0x400)
    # The charge has a canopy in air and switches to the existing round shot
    # at the waterline. The cords and weight share this single native cell.
    store[0x422] = vector(8,8,'''
      <g fill="none" stroke="#42555a" stroke-width=".22"><path d="M.55 3.4L3.65 5.8M2.4 3.2l1.4 2.5M5.55 3.2L4.1 5.7M7.4 3.4L4.3 5.8"/></g>
      <path d="M.4 3.55Q.85.55 3.95.35Q7.05.5 7.6 3.55Q6.65 2.9 5.55 3.4Q4 2.9 2.45 3.4Q1.3 2.95.4 3.55Z"
       fill="#efe0c0" stroke="#657477" stroke-width=".19"/>
      <path d="M.63 3.27Q1.3 1 3.8.5Q2.19 1.55 1.74 3.06Z" fill="#d7b892"/>
      <path d="M4.13.51Q6.34.7 7.34 3.28Q6.63 2.9 5.56 3.22Q5.17 1.38 4.13.51Z" fill="#baa38d"/>
      <path d="M3.95.45Q2.65 1.1 2.45 3.37Q3.2 3.1 3.85 3.12Q3.55 1.85 3.95.45Z" fill="#c3754d"/>
      <path d="M4.05.5Q5.1 1.1 5.55 3.32" fill="none" stroke="#9c8e7d" stroke-width=".17"/>
      <rect x="3.35" y="5.23" width="1.22" height=".74" rx=".22" fill="#aa9367"/>
      <circle cx="4" cy="6.42" r="1.27" fill="#3d5056" stroke="#293c43" stroke-width=".2"/>
      <ellipse cx="3.63" cy="5.97" rx=".48" ry=".34" fill="#9aaca7"/>''')


def impact_bubbles(store, vector):
    # The NES effect grows from one centered 8x8 cell to four 8x8 cells.
    # Draw the three steps about one center so the shell can spawn in its place.
    for extent,tiles,bubbles in (
        (8,[0xa4],[(4,4,1.1)]),
        (8,[0x98],[(3.9,2.2,.8),(5.6,3.8,.65),(2.4,4,.75),(4.4,5.7,.63)]),
        (16,[0x99,0x9a,0xa9,0xaa],[(6.4,2.3,1.15),(11.5,4.4,.88),
             (13.2,8.5,1.05),(10.9,11.8,.70),(6.6,13.1,.77),(3.1,9.9,.90),(2.2,5.8,.63)])):
        paths=[]
        for x,y,r in bubbles:
            paths.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#52919c" fill-opacity=".52" stroke="#c4e2df" stroke-width=".28"/>')
            paths.append(f'<circle cx="{x-.27*r}" cy="{y-.36*r}" r="{r*.27}" fill="#eef8e8"/>')
        image=vector(extent,extent,''.join(paths))
        cols=extent//8
        register_tiles(store,image,[(t,j%cols*8,j//cols*8) for j,t in enumerate(tiles)],0x400)
