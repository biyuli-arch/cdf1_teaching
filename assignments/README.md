# In Between
Biyu Li | 03836066  
Computational Design and Fabrication 1 - Assignment 1

This submission is based specifically on the user-selected GH file in ASS/1/1.2. The included binary is an unchanged, byte-for-byte copy of that file. The Python library was extracted directly from its five embedded Python script components; all five contain the same geometry functions. Images were regenerated from those extracted functions.

## Files
- `assignments/assignment-01.gh`: selected Grasshopper model, unchanged.
- `src/cdf/in_between.py`: matching extracted Python geometry functions.
- `renders/`: four Rhino captures and a comparison image.

## Usage
Open the GH file in Rhino 8 / Grasshopper. Python 3 scripting is required. Code is embedded in the definition, so the separate source file is provided for review and does not need an absolute import path. Run the separate source only in Rhino's Python environment (RhinoCommon, rhinoscriptsyntax and System.Drawing).

Use `frame_open` from -1 to +1. Images show -0.5, 0, +0.5 and +1. Units: mm.

## Relationships
The moving outer posts drive the red sphere/hole, growing red inlay, blue half-disc-to-quadrilateral profile, disappearing upper-left black corner, lower black polygon, elongated lower-left blue block, and yellow triangle-to-cone revolution. At full opening the blue block is 8 x 50 x 8 mm, and the yellow base radius is 20 mm. The upper red hole is coaxial in this selected version. The lower black polygon retains its diagonal cut; this selected file does not contain an added support groove under the yellow body.

The four captured states generated valid closed Breps: 12 solids at -0.5, 0 and +0.5, and 11 at +1 after the upper-left black corner disappears.

Prepared for local submission. No upload or GitHub push has been performed. Moodle presentation slides are separate.
