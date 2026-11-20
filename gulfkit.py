# -*- coding: utf-8 -*-
# GulfKit: climate tools for Gulf design, for Rhino 8 (IronPython). Generic Doha site, metres.
# Library: solar position, demo block, analysis grid and the rules behind the six commands (see gulfkit_tools.py).
import math, os, json
import Rhino, System, scriptcontext as sc, rhinoscriptsyntax as rs
from Rhino.Geometry import Point3d, Vector3d, Mesh, Ray3d
from Rhino.Geometry.Intersect import Intersection

LAT, LON, TZ = 25.29, 51.53, 3.0
C = System.Drawing.Color.FromArgb

# ---------------- solar position (NOAA-style) ----------------
def sunpos(day, hour, lat=LAT, lon=LON, tz=TZ):
    g = 2 * math.pi / 365 * (day - 1 + (hour - 12) / 24.0)
    eot = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g) - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    dec = 0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g) + 0.000907 * math.sin(2 * g) - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g)
    tst = hour * 60 + eot + 4 * lon - 60 * tz
    ha = math.radians(tst / 4.0 - 180); la = math.radians(lat)
    alt = math.asin(math.sin(la) * math.sin(dec) + math.cos(la) * math.cos(dec) * math.cos(ha))
    az = math.atan2(math.sin(ha), math.cos(ha) * math.sin(la) - math.tan(dec) * math.cos(la))
    return math.degrees(alt), (math.degrees(az) + 180) % 360

def sunvec(day, hour):
    alt, az = sunpos(day, hour); a, z = math.radians(alt), math.radians(az)
    return Vector3d(math.sin(z) * math.cos(a), math.cos(z) * math.cos(a), math.sin(a)), alt

# ---------------- colour ramp (blue -> yellow -> red) ----------------
RAMP = [(75, 107, 169), (115, 147, 202), (170, 200, 247), (193, 213, 208), (245, 239, 103), (252, 230, 74), (239, 156, 21), (234, 123, 0), (234, 74, 0), (234, 38, 0)]
def ramp(t):
    t = max(0.0, min(1.0, t)) * (len(RAMP) - 1); i = min(len(RAMP) - 2, int(t)); f = t - i
    a, b = RAMP[i], RAMP[i + 1]; return C(*[int(a[k] + (b[k] - a[k]) * f) for k in range(3)])

def layer(name, rgb=(200, 200, 200)):
    if not rs.IsLayer(name): rs.AddLayer(name, C(*rgb))
    rs.CurrentLayer(name); return name

# ---------------- generic Doha block ----------------
# (x0, y0, x1, y1, h): towers, a podium, a courtyard block, villas. North = +Y.
BLOCKS = [(-70, 20, -46, 44, 72), (-38, 26, -20, 56, 48), (-70, -10, -20, 14, 9),          # towers + podium (north-west)
          (10, 10, 22, 50, 14), (48, 10, 60, 50, 14), (22, 10, 48, 22, 14), (22, 38, 48, 50, 14),  # courtyard block (north-east)
          (-66, -66, -48, -48, 8), (-40, -66, -22, -48, 8), (-66, -40, -48, -22, 8),          # villas (south-west)
          (12, -66, 60, -24, 22)]                                                               # mid-rise (south-east), mashrabiya target
SITE = (-90, -90, 80, 80)

def boxmesh(x0, y0, x1, y1, h):
    m = Mesh(); p = [(x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0), (x0, y0, h), (x1, y0, h), (x1, y1, h), (x0, y1, h)]
    for q in p: m.Vertices.Add(*q)
    for f in [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]: m.Faces.AddFace(*f)
    m.Normals.ComputeNormals(); return m

def obstacles(extra=None):
    m = Mesh()
    for b in BLOCKS: m.Append(boxmesh(*b))
    for e in (extra or []): m.Append(e)
    return m

def massing():
    layer("GK_Massing", (235, 235, 235)); ids = []
    for (x0, y0, x1, y1, h) in BLOCKS:
        ids.append(rs.AddBox([(x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0), (x0, y0, h), (x1, y0, h), (x1, y1, h), (x0, y1, h)]))
    layer("GK_Ground", (245, 245, 245)); x0, y0, x1, y1 = SITE
    ids.append(rs.AddSrfPt([(x0, y0, -0.05), (x1, y0, -0.05), (x1, y1, -0.05), (x0, y1, -0.05)]))
    return ids

# ---------------- analysis grid: cells on every exposed face + ground ----------------
def cells(size=2.0, ground=True, roofs=True):
    out = []                                         # (centre, normal, half-u vector, half-v vector)
    def face(o, u, v, n):
        nu, nv = max(1, int(round(u.Length / size))), max(1, int(round(v.Length / size)))
        du, dv = u / nu, v / nv
        for i in range(nu):
            for j in range(nv):
                c = o + du * (i + 0.5) + dv * (j + 0.5); out.append((c + n * 0.05, n, du * 0.5, dv * 0.5))
    for (x0, y0, x1, y1, h) in BLOCKS:
        face(Point3d(x0, y0, 0), Vector3d(x1 - x0, 0, 0), Vector3d(0, 0, h), Vector3d(0, -1, 0))
        face(Point3d(x1, y1, 0), Vector3d(x0 - x1, 0, 0), Vector3d(0, 0, h), Vector3d(0, 1, 0))
        face(Point3d(x1, y0, 0), Vector3d(0, y1 - y0, 0), Vector3d(0, 0, h), Vector3d(1, 0, 0))
        face(Point3d(x0, y1, 0), Vector3d(0, y0 - y1, 0), Vector3d(0, 0, h), Vector3d(-1, 0, 0))
        if roofs: face(Point3d(x0, y0, h), Vector3d(x1 - x0, 0, 0), Vector3d(0, y1 - y0, 0), Vector3d(0, 0, 1))
    if ground:
        x0, y0, x1, y1 = SITE; g = 3.0
        for i in range(int((x1 - x0) / g)):
            for j in range(int((y1 - y0) / g)):
                cx, cy = x0 + g * (i + 0.5), y0 + g * (j + 0.5)
                if any(b[0] < cx < b[2] and b[1] < cy < b[3] for b in BLOCKS): continue
                out.append((Point3d(cx, cy, 0.05), Vector3d(0, 0, 1), Vector3d(g / 2, 0, 0), Vector3d(0, g / 2, 0)))
    return out

def quadmesh(items):                                 # items: (cell, colour)
    m = Mesh()
    for (c, n, hu, hv), col in items:
        k = m.Vertices.Count
        for p in (c - hu - hv, c + hu - hv, c + hu + hv, c - hu + hv): m.Vertices.Add(p); m.VertexColors.Add(col)
        m.Faces.AddFace(k, k + 1, k + 2, k + 3)
    m.Normals.ComputeNormals(); return m

# ---------------- 1. SunHours: direct sun hours, 21 June, with shading by every building ----------------
def sun_hours(day=172, h0=6.0, h1=18.5, step=0.5, size=2.0):
    obs = obstacles(); cs = cells(size); sv = [sunvec(day, h0 + step * k) for k in range(int((h1 - h0) / step) + 1)]
    sv = [(v, a) for (v, a) in sv if a > 1.0]; res = []
    for (c, n, hu, hv) in cs:
        hrs = 0.0
        for (v, a) in sv:
            if n * v <= 0: continue
            if Intersection.MeshRay(obs, Ray3d(c + n * 0.02, v)) < 0: hrs += step
        res.append(hrs)
    return cs, res, len(sv) * step

# ---------------- 2. Shamal: facade exposure to the north-west wind (direction only) ----------------
def shamal(deg=315.0):
    w = Vector3d(math.sin(math.radians(deg)), math.cos(math.radians(deg)), 0)   # direction the wind comes FROM
    cs = cells(2.0, ground=False, roofs=False); return cs, [max(0.0, n * w) for (c, n, hu, hv) in cs], w

# ---------------- 3. Setback envelope: plot, setbacks, height, GFA, FAR ----------------
def envelope(plot=(-90, -90, -10, -10), front=6.0, side=3.0, far=3.0, floor=3.6):
    x0, y0, x1, y1 = plot; bx0, by0, bx1, by1 = x0 + side, y0 + front, x1 - side, y1 - side
    area = (x1 - x0) * (y1 - y0); fp = (bx1 - bx0) * (by1 - by0); floors = int(far * area / fp); gfa = fp * floors
    return dict(plot=plot, box=(bx0, by0, bx1, by1), area=area, footprint=fp, floors=floors, height=floors * floor, gfa=gfa, far=gfa / area)

# ---------------- 4. Mashrabiya: perforation scaled by facade sun hours ----------------
def star(cx, cz, r, y, k=8, inner=0.55):
    pts = []
    for i in range(2 * k + 1):
        a = math.pi * i / k; rr = r if i % 2 == 0 else r * inner
        pts.append((cx + rr * math.cos(a), y, cz + rr * math.sin(a)))
    return pts

# ---------------- 5. Solar fins: vertical fins rotated to the hottest afternoon sun ----------------
def fin_angle(day=172, hours=(13, 14, 15, 16)):
    az = [sunpos(day, h)[1] for h in hours]; return sum(az) / len(az)

# ---------------- 6. Adaptive canopy: close where the solar ray reaches the occupied floor ----------------
def canopy_rule(cx, cy, cz, v, court=(22, 22, 48, 38)):
    if v.Z <= 0.02: return 0.0
    px, py = cx - v.X * cz / v.Z, cy - v.Y * cz / v.Z
    m = min(px - court[0], court[2] - px, py - court[1], court[3] - py); return max(0.0, min(1.0, 0.5 + m / 3.0))

if __name__ == "__main__":
    a, z = sunpos(172, 15); print("sun 21 Jun 15:00", round(a, 1), round(z, 1)); assert 40 < a < 50
