# Jaws HD

A 4× graphics pack for the NES game *Jaws*, tested with MesenCE 2.2.1. It includes a painted coastal map, surface and underwater encounters, animated sharks and a mixed jellyfish school.

## Install

1. Close the game in MesenCE.
2. Copy the `Jaws (USA)` folder inside `HdPacks/` into MesenCE's own `HdPacks` directory. Replace the previous Jaws HD folder. The resulting path should be `HdPacks/Jaws (USA)/hires.txt`.
3. If your ROM has a different filename, rename the pack folder to match its name without the `.nes` extension.
4. Enable NES HD packs and open your original USA ROM. The supported file has SHA-1 `C102DA80B2DED9364EBD707DF14CBC3BD40BD65A`.

## Current build

**v0.9.0.** Pick up the orange mini-sub on the overworld to pilot it underwater. Its painted cockpit and hull carry across both views. The propeller turns underwater, and the torpedoes follow the sub’s heading. This build also includes the recent fin, sea star, transceiver, boat wake and map fixes.

The install ZIP includes the three jellyfish appearances used by the default mixed mode. The optional single-style configurations are available in the repository and source build.

## Rebuild

The `source/` directory contains the editable artwork, builder and instructions. [Build from source](source/README.md).

Unofficial fan project. Jaws and the original NES game belong to their respective rights holders. Supply your own ROM.
