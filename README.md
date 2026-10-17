# KiCad Like a Pro, 5th Edition: Volume 1 project files

These are the finished KiCad projects from **Volume 1, Getting Started: Your First PCBs**, part of
*KiCad Like a Pro, 5th Edition* by Peter Dalmaris. The book teaches by building, and this repository
holds the result of each build, so you can open a working project, compare it against your own, or
pick up where you got stuck.

Book page and table of contents: <https://techexplorations.com/kicad/book/>

## Projects

| Folder | Project | Book chapter | Board |
|---|---|---|---|
| [`ch02-blinky/`](ch02-blinky/) | A 555 LED blinker, the project from the hands-on tour | Chapters 2 and 3 | 2-layer through-hole |
| [`ch08-breadboard-psu/`](ch08-breadboard-psu/) | Breadboard power supply with a USB-C input | Chapter 8 | 2-layer, through-hole and SMD |
| [`ch09-solar-psu/`](ch09-solar-psu/) | Tiny solar power supply (a rebuild of the Elektor design by Clemens Valens) | Chapter 9 | 2-layer, through-hole and SMD |

## How to use them

1. Install KiCad 10 from <https://www.kicad.org/download/>. The projects were made with KiCad 10, and
   older versions may not open them.
2. Clone this repository, or download it as a ZIP with the green **Code** button.
3. In KiCad's project manager choose **File, Open Project**, and open the `.kicad_pro` file inside
   the project folder you want.

Each project folder is self-contained. The `ch08` and `ch09` projects keep their imported parts in a
local `Libraries/` folder, and their library tables point at it with `${KIPRJMOD}`, so nothing
needs installing.

### What each folder holds

```
chNN-<project>/
├── <project>.kicad_pro / .kicad_sch / .kicad_pcb   the project, schematic and board
├── Gerbers/        manufacturing files: Gerber layers, one Excellon drill file, and the job file
├── BOM/            the bill of materials exported from the schematic
└── Libraries/      imported symbols, footprints and 3D models (ch08 and ch09)
```

The files in `Gerbers/` are ready to upload to a PCB manufacturer. The drill file is a single Excellon
file in millimetres with decimal coordinates, a format that fabricators such as NextPCB accept.
Chapter 10 of the book explains how it was produced and why that format matters.

### 3D models in the blinker

The blinker board refers to KiCad's standard 3D models through the `${KICAD10_3DMODEL_DIR}`
variable, which KiCad 10 sets for you. If the 3D viewer shows a bare board, open
**Preferences, Configure Paths** and check that the variable points at KiCad's `3dmodels` folder.

## If your result differs from the book

The projects here are the author's finished versions. Your own may look a little different, and
that is normal. Differences in placement and routing are fine as long as the design rules check
(DRC and ERC) passes. If a project does not open, or something does not match the chapter, please
open an issue on this repository.

## Licence and credits

The project files written for the book are released under the [MIT licence](LICENSE).

1. The solar power supply is a rebuild of the **Tiny Solar Supply** by Clemens Valens, published by
   Elektor. Credit for the circuit belongs to its author.
2. The files in `ch08-breadboard-psu/Libraries/` and `ch09-solar-psu/Libraries/` (symbols,
   footprints and 3D models for the USB-C receptacle, slide switch, AP3015A, SS14 diode, inductor and
   fuse) come from the parts' manufacturers and from SnapMagic, and they stay under their own terms.
   The MIT licence does not cover them.

## The rest of the series

Volume 2 of the book has its own project repository. See the book page above for the other volumes
and for the video courses.
