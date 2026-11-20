# Exact reference for unobstructed surfaces: direct sun hours at 1-minute resolution with the full NOAA algorithm.
# Compared in Rhino with GulfSunHours on the same five surfaces (see VALIDATION.md). Run: python validate_wall.py
import math
from validate_sun import noaa_full

def exact_hours(normal, month=6, day=21, lat=25.29, lon=51.53, tz=3):
    t = 0
    for k in range(24 * 60):
        a, z = noaa_full(2026, month, day, k / 60.0, lat, lon, tz)
        if a <= 0: continue
        v = (math.cos(math.radians(a)) * math.sin(math.radians(z)), math.cos(math.radians(a)) * math.cos(math.radians(z)), math.sin(math.radians(a)))
        if sum(p * q for p, q in zip(normal, v)) > 0: t += 1
    return t / 60.0

if __name__ == "__main__":
    for date in [(6, 21), (12, 21)]:
        print(date, {k: round(exact_hours(n, *date), 2) for k, n in [("N", (0, 1, 0)), ("E", (1, 0, 0)), ("S", (0, -1, 0)), ("W", (-1, 0, 0)), ("Roof", (0, 0, 1))]})
