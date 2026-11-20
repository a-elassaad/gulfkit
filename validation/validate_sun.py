# Validates GulfKit's sun position (NOAA general solar position equations) against the full NOAA Solar Calculator
# algorithm (Meeus-based, as in NOAA's spreadsheet). Plain Python 3, no Rhino. Run: python validate_sun.py
import math, sys, os, importlib.util

def noaa_full(year, month, day, hour, lat, lon, tz):
    """NOAA Solar Calculator spreadsheet equations. Returns (elevation without refraction, azimuth from north clockwise)."""
    if month <= 2: y, m = year - 1, month + 12
    else: y, m = year, month
    A = y // 100; B = 2 - A + A // 4
    jd = int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + day + B - 1524.5 + (hour - tz) / 24.0
    T = (jd - 2451545) / 36525.0
    L0 = (280.46646 + T * (36000.76983 + T * 0.0003032)) % 360
    M = 357.52911 + T * (35999.05029 - 0.0001537 * T)
    e = 0.016708634 - T * (0.000042037 + 0.0000001267 * T)
    C = math.sin(math.radians(M)) * (1.914602 - T * (0.004817 + 0.000014 * T)) + math.sin(math.radians(2 * M)) * (0.019993 - 0.000101 * T) + math.sin(math.radians(3 * M)) * 0.000289
    true_long = L0 + C; om = 125.04 - 1934.136 * T; app_long = true_long - 0.00569 - 0.00478 * math.sin(math.radians(om))
    eps0 = 23 + (26 + (21.448 - T * (46.815 + T * (0.00059 - T * 0.001813))) / 60) / 60; eps = eps0 + 0.00256 * math.cos(math.radians(om))
    dec = math.degrees(math.asin(math.sin(math.radians(eps)) * math.sin(math.radians(app_long))))
    yv = math.tan(math.radians(eps / 2)) ** 2
    eot = 4 * math.degrees(yv * math.sin(2 * math.radians(L0)) - 2 * e * math.sin(math.radians(M)) + 4 * e * yv * math.sin(math.radians(M)) * math.cos(2 * math.radians(L0))
                           - 0.5 * yv * yv * math.sin(4 * math.radians(L0)) - 1.25 * e * e * math.sin(2 * math.radians(M)))
    tst = (hour * 60 + eot + 4 * lon - 60 * tz) % 1440
    ha = tst / 4 - 180 if tst / 4 >= 0 else tst / 4 + 180
    la, d, h = math.radians(lat), math.radians(dec), math.radians(ha)
    zen = math.degrees(math.acos(max(-1, min(1, math.sin(la) * math.sin(d) + math.cos(la) * math.cos(d) * math.cos(h)))))
    az = math.degrees(math.atan2(math.sin(h), math.cos(h) * math.sin(la) - math.tan(d) * math.cos(la))) + 180
    return 90 - zen, az % 360

def gulfkit_sunpos():
    # same function as sunhours.sunpos, loaded without Rhino
    src = open(os.path.join(os.path.dirname(__file__), "..", "sunhours.py"), encoding="utf-8").read()
    start = src.index("def sunpos("); end = src.index("def sun_vectors(")
    ns = {"math": math}; exec(src[start:end], ns); return ns["sunpos"]

if __name__ == "__main__":
    sunpos = gulfkit_sunpos(); MD = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    cities = [("Doha", 25.29, 51.53, 3), ("Dubai", 25.20, 55.27, 4), ("Riyadh", 24.71, 46.68, 3), ("Kuwait", 29.38, 47.99, 3)]
    lines = ["| City | Samples (sun up, every 15 min, all 2026) | Max altitude error | Mean altitude error | Max sun-direction error (angle between vectors) |", "|---|---|---|---|---|"]
    worst = 0
    for name, lat, lon, tz in cities:
        ea, ez, n = [], [], 0
        for mo in range(1, 13):
            for dd in range(1, MD[mo - 1] + 1):
                doy = sum(MD[:mo - 1]) + dd
                for k in range(0, 24 * 4):
                    hr = k / 4.0; a1, z1 = noaa_full(2026, mo, dd, hr, lat, lon, tz)
                    if a1 < 0: continue
                    a2, z2 = sunpos(doy, hr, lat, lon, tz); n += 1; ea.append(abs(a1 - a2))
                    v1 = (math.cos(math.radians(a1)) * math.sin(math.radians(z1)), math.cos(math.radians(a1)) * math.cos(math.radians(z1)), math.sin(math.radians(a1)))
                    v2 = (math.cos(math.radians(a2)) * math.sin(math.radians(z2)), math.cos(math.radians(a2)) * math.cos(math.radians(z2)), math.sin(math.radians(a2)))
                    ez.append(math.degrees(math.acos(min(1.0, sum(p * q for p, q in zip(v1, v2))))))
        lines.append("| %s | %d | %.2f deg | %.3f deg | %.2f deg |" % (name, n, max(ea), sum(ea) / len(ea), max(ez))); worst = max(worst, max(ea))
    print("\n".join(lines))
    a, z = sunpos(172, 12 + 40 / 60.0, 25.29, 51.53, 3); print("Doha 21 June 12:40 -> altitude %.1f, azimuth %.1f" % (a, z))
    assert worst < 1.0, "altitude error above 1 degree"
    open(os.path.join(os.path.dirname(__file__), "sun_results.md"), "w").write("\n".join(lines) + "\n")
