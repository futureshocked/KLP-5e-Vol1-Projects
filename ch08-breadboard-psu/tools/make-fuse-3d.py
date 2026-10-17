#!/usr/bin/env python3
"""Build the 3D model KiCad's own library never shipped for F1.

Chapter 8's fuse uses the stock footprint Fuse:Fuse_Bourns_MF-RHT050. That footprint
carries a (model ...) line pointing at

    ${KICAD10_3DMODEL_DIR}/Fuse.3dshapes/Fuse_Bourns_MF-RHT050.step

and that file does not exist. It is not a broken local install: kicad-packages3D has
29 files in Fuse.3dshapes and not one Bourns MF-R model among them, so all 17 MF-RHT
and 10 MF-RG footprints reference 3D models that were never published. Bourns gives a
datasheet but no STEP, and the third-party libraries that have one want an account
login and attach terms that do not belong in a book repo. So the model gets built here
instead, from dimensions rather than from a guess.

Every number in the DIMENSIONS block below is sourced, not invented. The body and the
lead geometry come from the footprint's own F.Fab outline and pad positions, which is
what makes the model land on its pads; the heights come from the DigiKey MF-RHT050-2
spec table (0.291" dia, 0.118" thick, 0.201" pitch, 0.500" max seated height).

Three things here are easy to get wrong and are worth stating plainly:

1.  **The Y axis is negated.** A .kicad_mod measures Y downward, a 3D model measures
    it upward, so a model authored straight off the footprint's numbers comes out
    mirrored. Confirmed empirically rather than assumed: the stock
    PinHeader_1x02_P2.54mm_Vertical footprint spans Y -1.27..3.81, and its shipped
    STEP spans Y -3.81..1.27. Every footprint coordinate is therefore negated in Y on
    its way in here, which is what MODEL_Y() is for.

2.  **The 1.2 mm lead stagger is real geometry, not a tolerance.** The footprint puts
    pad 1 at (0, 0) and pad 2 at (5.1, 1.2), and that 1.2 mm offset is constant across
    the whole MF-RHT and MF-RG family. A PPTC disc is polymer between two foil
    electrodes and each lead welds to one face, so the two leads sit 0.6 mm either side
    of the disc's mid-plane. Straightening them onto one centreline would put both pads
    in the wrong place.

3.  **Leads run to 2 mm below the board.** Not cosmetic: it is the convention the stock
    radial THT models follow (C_Disc and CP_Radial both stop at Z -2.00), so matching it
    keeps this part consistent with its neighbours when the board is rendered with a
    translucent substrate.

Needs build123d, which is not a repo dependency. The committed .step is the deliverable
and this script rarely needs re-running, so install it somewhere throwaway:

    python3 -m venv /tmp/b123d && /tmp/b123d/bin/pip install build123d
    /tmp/b123d/bin/python tools/make-fuse-3d.py --install

Run from the project root. --install additionally drops a copy into the shared
kicad-packages3D tree, which is the path the stock footprint already looks in, so no
.kicad_pcb, .kicad_mod or .kicad_sch is touched by any of this.

Unlike the Chapter 8 generators over in Volume 2, this one is *not* byte-idempotent: a
STEP file records its own export timestamp in the FILE_NAME header, so a second run
rewrites the file and shows up as a diff even when the geometry is identical. The
committed .step is the artefact. Re-run this only when a dimension above actually
changes, not to check that it still works.
"""
import argparse
import os
import shutil
import sys

from build123d import (
    Color,
    Compound,
    Cylinder,
    GeomType,
    Location,
    Rotation,
    export_step,
    fillet,
)

# ---------------------------------------------------------------------------
# DIMENSIONS -- Bourns MF-RHT050, all millimetres.
#
# Sourced from, in order of precedence:
#   footprint  /usr/share/kicad/footprints/Fuse.pretty/Fuse_Bourns_MF-RHT050.kicad_mod
#   datasheet  DigiKey MF-RHT050-2 mechanical spec table
# ---------------------------------------------------------------------------
PITCH_X = 5.10      # footprint: pad 2 X offset.  datasheet: 0.201" lead spacing
STAGGER_Y = 1.20    # footprint: pad 2 Y offset.  the electrode-face offset, see (2)
BODY_DIA = 7.40     # footprint: F.Fab X span.    datasheet: 0.291" dia
BODY_THICK = 3.00   # footprint: F.Fab Y span.    datasheet: 0.118" T
LEAD_DIA = 0.50     # footprint: 0.71 mm drill less the library's standard clearance
STANDOFF = 5.10     # board surface to the disc's lowest point; Bourns 0.200" min lead
LEAD_BELOW = 2.00   # lead stub below the board, matching C_Disc and CP_Radial
RIM_FILLET = 0.50   # the epoxy coat is moulded, not a sharp-edged puck

# Colours. The MF-RHT coat is a pale blue; the leads are tinned copper.
BODY_COLOUR = Color(0.44, 0.62, 0.78)
LEAD_COLOUR = Color(0.78, 0.79, 0.81)

NAME = "Fuse_Bourns_MF-RHT050"
REPO_OUT = os.path.join("Libraries", "3D-models", NAME + ".step")
SHARED_LIB = os.path.expanduser(
    "~/KiCad_shared/kicad-packages3D-master/Fuse.3dshapes"
)


def MODEL_Y(footprint_y):
    """Footprint Y (down-positive) to model Y (up-positive). See docstring note (1)."""
    return -footprint_y


# Derived geometry, in model space.
BODY_CX = PITCH_X / 2                   # 2.55, midway between the two leads
BODY_CY = MODEL_Y(STAGGER_Y / 2)        # -0.60, the disc's mid-plane
BODY_CZ = STANDOFF + BODY_DIA / 2       # 8.80, the disc's centre height
LEADS = ((0.0, MODEL_Y(0.0)), (PITCH_X, MODEL_Y(STAGGER_Y)))

# What the finished model must measure, checked after export. Derived from the
# footprint's F.Fab rect (-1.15,-0.9)..(6.25,2.1) with Y negated, so a mirrored or
# mis-scaled build fails here instead of looking subtly wrong in a render.
EXPECT_BBOX = {
    "X": (BODY_CX - BODY_DIA / 2, BODY_CX + BODY_DIA / 2),        # -1.15 .. 6.25
    "Y": (BODY_CY - BODY_THICK / 2, BODY_CY + BODY_THICK / 2),    # -2.10 .. 0.90
    "Z": (-LEAD_BELOW, STANDOFF + BODY_DIA),                      # -2.00 .. 12.50
}
TOLERANCE = 0.01


def build():
    """The disc and its two staggered leads, as a two-colour compound."""
    # A disc on its edge: build the cylinder on Z, round its two rim edges, then lay
    # the axis over onto Y so the 3.00 mm dimension runs front-to-back.
    disc = Cylinder(radius=BODY_DIA / 2, height=BODY_THICK)
    disc = fillet(disc.edges().filter_by(GeomType.CIRCLE), RIM_FILLET)
    disc = Location((BODY_CX, BODY_CY, BODY_CZ)) * Rotation(90, 0, 0) * disc

    # Each lead runs from LEAD_BELOW under the board up to the disc's centre, then gets
    # cut back to the disc's surface. Cutting rather than leaving the two solids
    # interpenetrating matters because they carry different colours: coincident faces
    # inside the body would otherwise z-fight in the viewer.
    span = BODY_CZ + LEAD_BELOW
    leads = None
    for x, y in LEADS:
        wire = Location((x, y, (BODY_CZ - LEAD_BELOW) / 2)) * Cylinder(
            radius=LEAD_DIA / 2, height=span
        )
        leads = wire if leads is None else leads + wire
    leads -= disc

    disc.color = BODY_COLOUR
    disc.label = "body"
    leads.color = LEAD_COLOUR
    leads.label = "leads"

    part = Compound(children=[disc, leads])
    part.label = NAME
    return part


def check(path):
    """Re-import the exported file and hold it to EXPECT_BBOX. Returns True on pass."""
    from build123d import import_step

    box = import_step(path).bounding_box()
    got = {
        "X": (box.min.X, box.max.X),
        "Y": (box.min.Y, box.max.Y),
        "Z": (box.min.Z, box.max.Z),
    }
    ok = True
    for axis, (want_lo, want_hi) in EXPECT_BBOX.items():
        lo, hi = got[axis]
        good = abs(lo - want_lo) < TOLERANCE and abs(hi - want_hi) < TOLERANCE
        ok = ok and good
        print(
            f"  {axis}  [{lo:7.3f}, {hi:7.3f}]  expected "
            f"[{want_lo:7.3f}, {want_hi:7.3f}]  {'ok' if good else 'MISMATCH'}"
        )
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "-o", "--out", default=REPO_OUT, help=f"output .step (default: {REPO_OUT})"
    )
    ap.add_argument(
        "--install",
        action="store_true",
        help="also copy into the shared kicad-packages3D Fuse.3dshapes tree",
    )
    args = ap.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    export_step(build(), args.out)
    print(f"wrote {args.out}  ({os.path.getsize(args.out):,} bytes)")

    print("bounding box:")
    if not check(args.out):
        sys.exit("bounding box check failed; model not installed")

    with open(args.out, "rb") as fh:
        blob = fh.read()
    print(f"colour: {blob.count(b'COLOUR_RGB')} COLOUR_RGB entries")

    if args.install:
        if not os.path.isdir(SHARED_LIB):
            sys.exit(f"shared library not found: {SHARED_LIB}")
        dest = os.path.join(SHARED_LIB, NAME + ".step")
        shutil.copy2(args.out, dest)
        print(f"installed {dest}")


if __name__ == "__main__":
    main()
