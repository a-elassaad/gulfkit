# GulfKit: six climate tools for Gulf design, as Rhino 8 commands

Quick climate checks for early design in the Gulf, written in Python for Rhino 8. They are set up for Doha
(lat 25.29, lon 51.53, UTC+3) and run on a generic city block, so every tool works the moment it is installed.

| Command | What it does |
|---|---|
| `GulfSunPath` | Solar geometry for the site: 21 June, March and December day arcs, hour analemmas, live sun and shadow |
| `GulfSunHours` | Direct sun hours on every facade, roof and street on 21 June, shaded by every building (about 10,000 cells) |
| `GulfShamal` | Facade exposure to the Shamal, the prevailing north-west wind (315°), with a moving arrow field |
| `GulfMassing` | 12 tower and podium options at a fixed FAR of 6.0, with setbacks applied |
| `GulfMashrabiya` | Star-pattern screen panels on the south and west faces, perforation sized by the sun hours on each panel |
| `GulfCanopy` | Courtyard canopy from 09:00 to 17:00: apertures close where the solar ray reaches the occupied floor |
| `GulfSetup` | Rebuilds the generic Doha block (runs by itself the first time) |

## Install
1. Download or clone this folder anywhere. Keep the folder structure as it is.
2. In Rhino 8 run `_-RunPythonScript` and pick a file in `commands/`, for example `commands/GulfSunHours.py`.
3. Optional, to type the tools like normal commands: Options > Aliases > New, name `GulfSunHours`, macro
   `! _-RunPythonScript "C:\path\to\GulfKit\commands\GulfSunHours.py"`. Repeat for the others.

The tools draw on their own `GK_` layers. They do not delete anything outside those layers.
Results print in the command line, for example the mean sun hours or the FAR of each option.
Most tools finish in seconds. GulfMashrabiya builds 495 panel surfaces and takes a few minutes.

## Test your own massing
The block is defined in `gulfkit.py` as `BLOCKS`: one line per box, `(x0, y0, x1, y1, height)` in metres, north = +Y.
Edit the list, run `GulfSetup`, then run any tool. Change `LAT, LON, TZ` for another Gulf city.

## The science
- Solar position: NOAA-style formulas (declination, equation of time, hour angle). Checked against Rhino's own sun.
- Sun hours: one ray per half hour from each cell towards the sun, blocked by any building (06:00 to 18:30, 21 June).
- Shamal: cosine between the facade normal and the wind direction. Direction only.
- Canopy: each aperture closes in proportion to how far inside the courtyard its sun ray lands.

## Limits
Quick checks for early design, not full simulations. Direct sun only (no diffuse sky, no reflections, no radiation in kWh).
Wind is direction only (no speed, no CFD). The block is generic. Check results before relying on them.

## Licence
MIT. Free to use, change and share. Made by Ahmad ELAssaad, Architect · PhD at HBKU · Design technologist.
