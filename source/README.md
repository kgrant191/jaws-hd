# Jaws HD v0.5.1

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
- `sprite_motion.py` assembles the boat headings, diver's kick, hit and death poses, drops, stingray and jellyfish atlases. The south-facing idle boat uses the stock stopped-pose pointer at $0688–$0689 to select a clean stern.
- `build_pack.py` decodes the 32 by 24 metatile world chart from the supported ROM, follows horizontal and vertical camera movement and handles the signed western boundary. The two port layouts, encounter banners and live HUD share the game's own state.
- `data/` holds measured scene signatures, sprite identities, palettes and fin layouts from the recordings. The pack asks Mesen to lift the sprite-per-scanline limit so firing, sharks and schools can share a row without losing pieces.

## Mixed jellyfish

Mixed mode is the default. The low two bits of actor field $1E retain each newly spawned jellyfish's appearance. At the first spawn, `jelly_variation.py` seeds an independent cosmetic generator from the game RNG and object slot. It checks each participating original code sequence before assembling a checksum-gated IPS. The emulator applies it in memory.

The eight-bit XNOR Galois sequence has 255 states and excludes $D0. Low pair 00 is rejected. Each of the other three bit pairs occurs exactly 64 times per complete selection cycle. A replay from an identical game state reproduces the sequence. An untagged jellyfish already present in an old save renders as Moon until it leaves. The two existing collision-height routines share identical 32-byte tails. The second tail now forwards to the first, making room for the one-time seed logic. The two jelly AI routines also share their original hit and despawn handlers.

The builder emits a separate `hires.txt` under each folder in `Jellyfish Options/`. Copy one into the pack root and reopen the ROM to use a single style. Copy the Mixed definition back to restore equal variation.

## Replay checks

The 11,578-frame opening, 3,045-frame feedback and 5,628-frame Jaws encounter recordings were replayed in MesenCE. The HUD/nametable, palette, frame ID and gameplay RNG matched the original runs at all 1,835 common checkpoints. All 74 continuously tracked jellyfish sightings kept their individual style. Paired emulator frames also confirmed the diver and overlapping stingrays stay visible while the player fires. The v0.5.1 preview pairs frames from the new 4,279-frame shark and aircraft recording. It shows the hit pose, shell release, and both airplane headings. The v0.5.1 build matches v0.5.0 sprite data on every recorded frame and matches the prior frame ID, RAM, nametables and palettes at 715 checkpoints.
