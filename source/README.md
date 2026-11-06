# Jaws HD v0.8.1

Editable source for the MesenCE 2.2.1 4× graphics pack.

## Rebuild

Use Python 3.12, the packages in requirements.txt, and the original USA ROM. Run from this directory.

```sh
python3 -m pip install -r requirements.txt
python3 build_pack.py --rom "/path/to/Jaws (USA).nes" --output pack
```

The supported source ROM SHA-1 is `c102da80b2ded9364ebd707df14cbc3bd40bd65a`. The builder reads the ROM and writes the deployable pack to the output folder. For the original typography, supply the directory containing the URW Base 35 Nimbus Sans fonts with `--font-dir`. The default searches the Debian system font directory. macOS has an Arial fallback.

## Artwork and registration

- `art/` contains the paintings and isolated sprites, including separate juvenile and adult great white masters, the shoal, the full coastal chart and the existing animated title.
- `encounters.py` fits both sharks to their native frame layouts. The adult uses three swimming body poses and three independent tail positions. The juvenile has a separate hit layout using palette FF200F27, snout tile $4A8 and the hit pose’s fin positions. The bonus plane uses a dedicated side-profile master and interchanges the bottom nose cells $413 and $407. Its parachuted charge and the three impact-bubble stages are assembled here as well. This module also builds the overhead fin, iron boat shot and shallow-water surface layers.
- `sprite_motion.py` assembles the boat headings, diver's kick, hit and death poses, drops, stingray and jellyfish atlases. The map's four headings use the same overhead boat painting. Horizontal travel follows the game's five moving frames, with its own clean idle hull. The stopped-pose pointer at $0688–$0689 and the port dialog select the appropriate stern.
- `build_pack.py` covers the chart’s dedicated background CHR page across all four map palettes, follows horizontal and vertical camera movement and handles the signed western boundary. The two port layouts, encounter banners and live HUD share the game's own state.
- `data/` holds measured scene signatures, sprite identities and palettes from the recordings, plus the full set of map-fin layouts from the ROM. The pack asks Mesen to lift the sprite-per-scanline limit so firing, sharks and schools can share a row without losing pieces.

## Mixed jellyfish

Mixed mode is the default. The low two bits of actor field $1E retain each newly spawned jellyfish's appearance. At the first spawn, `jelly_variation.py` seeds an independent cosmetic generator from the game RNG and object slot. It checks each participating original code sequence before assembling a checksum-gated IPS. The emulator applies it in memory.

The eight-bit XNOR Galois sequence has 255 states and excludes $D0. Low pair 00 is rejected. Each of the other three bit pairs occurs exactly 64 times per complete selection cycle. A replay from an identical game state reproduces the sequence. An untagged jellyfish already present in an old save renders as Moon until it leaves. The two existing collision-height routines share identical 32-byte tails. The second tail now forwards to the first, making room for the one-time seed logic. The two jelly AI routines also share their original hit and despawn handlers.

The builder emits a separate `hires.txt` under each folder in `Jellyfish Options/`. Copy one into the pack root and reopen the ROM to use a single style. Copy the Mixed definition back to restore equal variation.

## Replay checks

The 11,578-frame opening, 3,045-frame feedback and 5,628-frame Jaws encounter recordings were replayed in MesenCE. The HUD/nametable, palette, frame ID and gameplay RNG matched the original runs at all 1,835 common checkpoints. All 74 continuously tracked jellyfish sightings kept their individual style. Paired emulator frames also confirmed the diver and overlapping stingrays stay visible while the player fires. The v0.5.1 preview pairs frames from the new 4,279-frame shark and aircraft recording. It shows the hit pose, shell release, and both airplane headings. The v0.5.1 build matches v0.5.0 sprite data on every recorded frame and matches the prior frame ID, RAM, nametables and palettes at 715 checkpoints.

## Map replay in v0.5.2

The native map scroll byte wraps from $FF to $00 while the boat crosses the western edge. CPU position and rendered scroll can refer to different frames. A second coastal texture covers both sides of the wrap. Near zero it uses a 17/16 horizontal ratio, for which Mesen adds exactly 15 native pixels to scroll values $F8–$FF and zero to $00–$07. Both texture windows display the same western coastline.

The harbor banner follows the visible PPU text row. The queued text selects the new message on the frame before the nametable catches up. The 1,110-frame port movie covers the western boundary, east/west turns, shell shortage and transition to a shallow Jaws encounter. A supplemental steering check crosses the boundary in reverse.


## Harbor and adult Jaws in v0.6.0

The navigation recording covers the receiver purchase, scrolling in both directions and two harbor upgrades. The incoming map column and its attribute byte can be updated on different frames. The four map palettes share transparent terrain replacements so the painted chart stays visible throughout the update. The receiver and harbor match the tiles actually displayed, including the first and last frames of each visit.

Jaws starts at $1400 health. The hit routine subtracts damage from the little-endian value at $0388–$0389. The coarse HUD meter reads only $0389. The adult shark uses the wounded atlas when the full value is at or below $0A00. Both appearances use the same head and fin layout, three body poses, independent tail and native mirroring. A combat replay initialized just above half health crosses the threshold on an in-game hit. Additional boundary checks use $0A01, $0A00 and $09FF.

## Final encounter in v0.7.0

The game sets bit $20 in $0306 when the underwater encounter ends. It pulses the power meter between full and empty while the defeated actor is still on screen. This flag takes precedence over the normal half-health check for adult shark sprites. HUD counters use the original live digits with a smaller cap and extra headroom inside each 32-pixel HD cell.

`finale.py` uses the bow, fin, sinking and flyby sprite registrations in `data/finale-poses.json`. Each cell records the CHR tile index, X and Y in NES pixels, and original sprite attributes. The surface vista follows the PPU camera. The strobe number, bow movement, hit effect and flyby all follow native sprite changes. The first banked pass uses one painted aircraft anchored to the plane’s flight path so both wings stay continuous. The closing title appears when the game draws its title tiles.

The 3,604-frame ending recording covers the last underwater hit, all six meter pulses, both strobe uses, the successful bow strike, the descent and the sunset flyby.


## Final strike in v0.7.1

`strike.py` reads the four strobe animation sequences from the supported ROM. The scene compositor follows Jaws’s signed X coordinate, waterline, current pose and facing direction. The closest full breach is 280 × 400 HD pixels. The visible body rises out of a separate line of foam on the early frames.

The game accepts the fatal thrust while Jaws is in the eight-by-eight contact window. The finishing artwork uses both the native success flag and the rendered impact tile at the bow tip. It stays aligned to the spike in either facing direction. The underwater descent uses a separate wounded dorsal view. Earlier underwater encounters follow the existing half-health and defeat rules.

The ending recording includes a missed strobe attack and a successful strike. Supplementary input replays fire earlier to exercise the three farther strobe distances.

## Map and pickups in v0.8.0

The overworld camera reaches x=264, but the horizontal scroll sent to the PPU wraps at 256. Near the eastern boundary, `coast-east.png` supplies two continuous 256-pixel viewports into the eastern part of the chart. The lower scroll bytes 0–8 and upper bytes 244–255 use separate sections of that texture. The original 1,723-frame playthrough crosses the boundary heading east and west. A second steering check crosses it three times at the northern camera limit.

The transceiver uses the original idle oscilloscope line and eight pulse positions written to $2F6F–$2F70. Its lower HUD cells display the corresponding HD waveform. The sea star uses the game's face-on, angled and edge-on poses and mirrors the latter two during its rotation. The southbound hull and both wake tips fit within the stern's two native sprite columns.

## Overworld fin in v0.8.1

The supported ROM stores 34 map-fin poses at $B34D–$B56A. The HD layouts cover all 104 distinct cells, including shared tiles and the partial surfacing or diving poses. Each layout supplies both the painting and its map-sprite registration. The game controls timing, heading and mirroring.
