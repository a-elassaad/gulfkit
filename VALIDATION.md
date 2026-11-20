# Validation of GulfSunHours

Two checks, both reproducible with the scripts in `validation/`.

## 1. Sun position against the full NOAA Solar Calculator algorithm
GulfKit uses the NOAA general solar position equations (short form). They were compared with the full NOAA Solar
Calculator algorithm (Meeus-based, as in NOAA's spreadsheet) every 15 minutes for every day of 2026, sun above the horizon.
Script: `validation/validate_sun.py`.

| City | Samples | Max altitude error | Mean altitude error | Max sun-direction error |
|---|---|---|---|---|
| Doha | 17,545 | 0.41° | 0.158° | 0.41° |
| Dubai | 17,546 | 0.39° | 0.151° | 0.39° |
| Riyadh | 17,572 | 0.41° | 0.156° | 0.41° |
| Kuwait | 17,579 | 0.41° | 0.171° | 0.41° |

The sun direction is within half a degree of the reference all year in all four cities.

## 2. Sun hours on unobstructed surfaces against an exact count
Five 10 x 10 m surfaces facing N, E, S, W and up, with nothing around them, Doha. Exact reference: full NOAA algorithm at
1-minute resolution (`validation/validate_wall.py`). GulfSunHours: default 2 m grid, 0.5 h steps, run in Rhino 8.

| Surface | 21 June exact | 21 June GulfSunHours | 21 Dec exact | 21 Dec GulfSunHours |
|---|---|---|---|---|
| North wall | 10.45 h | 10.5 h | 0.00 h | 0.0 h |
| East wall | 6.78 h | 6.5 h | 5.20 h | 5.0 h |
| South wall | 3.13 h | 3.0 h | 10.42 h | 10.0 h |
| West wall | 6.80 h | 7.0 h | 5.22 h | 5.0 h |
| Roof | 13.58 h | 13.5 h | 10.42 h | 10.0 h |

Largest difference 0.42 h, inside the 0.5 h time step. Results are reported to the nearest half hour.

## 3. Clear-sky direct energy on the same surfaces (model output, for orientation only)
Direct beam from the Meinel clear-sky model (DNI = 1.353 x 0.7^(AM^0.678) kW/m²) with the Kasten-Young air mass,
multiplied by the cosine of incidence and the time step. Doha, unobstructed, kWh/m² per day:

| Surface | 21 June | 21 Dec |
|---|---|---|
| North wall | 1.10 | 0.00 |
| East wall | 2.87 | 1.58 |
| South wall | 0.06 | 4.59 |
| West wall | 2.88 | 1.57 |
| Roof | 7.35 | 3.35 |

In June the south wall sees 3 h of sun but almost no energy, because the sun stands almost overhead at noon and grazes it.
Clear sky is an upper bound: Gulf dust and haze lower real values. This is why the screen rule uses energy, not hours.

## What is not validated
Shading by other buildings uses exact ray casts against the meshed model, so its accuracy follows the mesh of the
context. Diffuse sky, reflections and radiation (kWh/m²) are not computed. This is a quick check for early design,
not a replacement for a full daylight or energy simulation.
