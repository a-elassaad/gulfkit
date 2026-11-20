# -*- coding: utf-8 -*-
# GulfKit tools for Rhino 8 (IronPython). Each command file in commands/ calls run(n). MIT licence, see LICENSE.
# Quick checks on a generic Doha block: direct sun only, wind direction only. Not a full simulation.
import sys, os, math, time
P = os.path.dirname(os.path.abspath(__file__))
if P not in sys.path: sys.path.append(P)
import gulfkit; reload(gulfkit); from gulfkit import *

def view():
    v = sc.doc.Views.Find("Perspective", False) or sc.doc.Views.ActiveView; sc.doc.Views.ActiveView = v; return v
def cam(az, el, dist, tgt, lens=35):
    a, e = math.radians(az), math.radians(el); t = Point3d(*tgt)
    loc = Point3d(t.X + dist * math.cos(e) * math.sin(a), t.Y - dist * math.cos(e) * math.cos(a), t.Z + dist * math.sin(e))
    vp = view().ActiveViewport; vp.ChangeToPerspectiveProjection(True, lens); vp.SetCameraLocations(t, loc); vp.CameraUp = Vector3d.ZAxis
def cap(tool, info=None): sc.doc.Views.Redraw()     # the video version saved a frame here

def clear(prefix="GK_T"):
    for L in rs.LayerNames():
        if L.startswith(prefix): rs.DeleteObjects(rs.ObjectsByLayer(L) or [])
def hide_blocks(idx, hide=True):
    for o in rs.ObjectsByLayer("GK_Massing") or []:
        bb = rs.BoundingBox(o); c = ((bb[0].X + bb[6].X) / 2, (bb[0].Y + bb[6].Y) / 2)
        for i in idx:
            b = BLOCKS[i]
            if b[0] < c[0] < b[2] and b[1] < c[1] < b[3]: (rs.HideObject if hide else rs.ShowObject)(o)
def orbit(k, n, a0, a1, el, dist, tgt, lens=35):
    if k > 0: return                        # set the view once
    cam(a0 + (a1 - a0) * k / max(1, n - 1), el, dist, tgt, lens)
def ease(t): t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)

def setup():                                # build the generic Doha block on GK_ layers (never touches other layers)
    rs.UnitSystem(4, False); clear("GK_")
    for L in ("GK_Massing", "GK_Ground"):
        if rs.IsLayer(L): rs.DeleteObjects(rs.ObjectsByLayer(L) or [])
    massing(); rs.CurrentLayer("Default") if rs.IsLayer("Default") else None

def t1():                                   # GulfSunHours
    cs, res, tot = sun_hours(step=0.5); mx = max(res); order = sorted(range(len(cs)), key=lambda i: (cs[i][0].Z > 0.1, cs[i][0].X + cs[i][0].Y))
    gr = [res[i] for i in range(len(cs)) if cs[i][1].Z > 0.9 and cs[i][0].Z < 0.2]
    info = dict(cells=len(cs), avg_ground=sum(gr) / len(gr), share_ground_8h=sum(1 for g in gr if g >= 8) / float(len(gr)), max=mx)
    layer("GK_T1"); N, HOLD = 80, 25; done = 0
    for k in range(N + HOLD):
        upto = int(len(order) * ease((k + 1) / float(N)))
        if upto > done:
            sc.doc.Objects.AddMesh(quadmesh([(cs[i], ramp(res[i] / mx)) for i in order[done:upto]])); done = upto
        orbit(k, N + HOLD, 198, 226, 38, 300, (-5, -5, 8)); cap("sunhours", dict(info, done=done / float(len(cs))))
    print("GulfKit sunhours:", info)

def arrow(p, d, L=15.0, r=1.0):
    tip = p + d * L; line = Rhino.Geometry.Line(p, tip)
    cyl = Rhino.Geometry.Cylinder(Rhino.Geometry.Circle(Rhino.Geometry.Plane(p, d), r * 0.45), L * 0.72)
    cone = Rhino.Geometry.Cone(Rhino.Geometry.Plane(tip, -d), L * 0.28, r * 1.3)
    m = Mesh.CreateFromCylinder(cyl, 1, 10); m.Append(Mesh.CreateFromCone(cone, 1, 10)); return m

def t2():                                   # GulfShamal
    clear(); cs, ex, w = shamal(315.0); flow = -w
    windward = sum(1 for e in ex if e > 0.5) / float(len(ex))
    layer("GK_T2"); N = 105; faces = None; arrows = []
    for k in range(N):
        if faces is None and k >= 8: faces = sc.doc.Objects.AddMesh(quadmesh([(c, ramp(e)) for c, e in zip(cs, ex)]))
        if arrows: rs.DeleteObjects(arrows)
        arrows = []; ph = (k * 1.6) % 20.0
        for i in range(-4, 5):
            for j in range(-4, 5):
                base = Point3d(i * 24.0, j * 24.0, 0) + flow * (ph - 60) * 1.0
                for z in (24.0, 60.0):
                    p = Point3d(base.X, base.Y, z) + flow * (ph * 3)
                    if SITE[0] - 20 < p.X < SITE[2] + 20 and SITE[1] - 20 < p.Y < SITE[3] + 20:
                        m = arrow(p, flow); m.VertexColors.CreateMonotoneMesh(C(30, 150, 190)); arrows.append(sc.doc.Objects.AddMesh(m))
        orbit(k, N, 318, 296, 30, 290, (-5, -5, 12)); cap("shamal", dict(windward=windward, deg=315))
    rs.DeleteObjects(arrows)
    print("GulfKit shamal:", dict(windward=windward, deg=315))

def t3():                                   # GulfMassing: tower + podium options at a fixed FAR, setbacks applied
    clear(); hide_blocks([7, 8, 9]); e = envelope(plot=(-88, -88, -16, -16), front=6.0, side=3.0, far=6.0, floor=3.6)
    x0, y0, x1, y1 = e["plot"]; bx0, by0, bx1, by1 = e["box"]; target = 6.0 * e["area"]
    layer("GK_T3"); pl = rs.AddPolyline([(x0, y0, 0.1), (x1, y0, 0.1), (x1, y1, 0.1), (x0, y1, 0.1), (x0, y0, 0.1)])
    sb = rs.AddPolyline([(bx0, by0, 0.15), (bx1, by0, 0.15), (bx1, by1, 0.15), (bx0, by1, 0.15), (bx0, by0, 0.15)])
    opts = []
    for pf in (2, 3, 4):
        for tw in (22.0, 28.0):
            for corner in ("NE", "NW", "SE"):
                pod = (bx1 - bx0) * (by1 - by0) * pf; tf = int(math.ceil((target - pod) / (tw * tw)))
                tx0 = bx1 - tw if "E" in corner else bx0; ty0 = by1 - tw if "N" in corner else by0
                opts.append(dict(pf=pf, tw=tw, corner=corner, tf=tf, tx=(tx0, ty0), gfa=pod + tf * tw * tw, h=(pf + tf) * 3.6))
    opts = opts[:12]; ids = []; N_PER = 9
    for oi, o in enumerate(opts):
        if ids: rs.DeleteObjects(ids)
        ids = []; mm = Mesh()
        for f in range(o["pf"]):
            m = boxmesh(bx0, by0, bx1, by1, 3.3); m.Translate(0, 0, f * 3.6); m.VertexColors.CreateMonotoneMesh(ramp(0.12)); mm.Append(m)
        for f in range(o["tf"]):
            m = boxmesh(o["tx"][0], o["tx"][1], o["tx"][0] + o["tw"], o["tx"][1] + o["tw"], 3.3); m.Translate(0, 0, (o["pf"] + f) * 3.6)
            m.VertexColors.CreateMonotoneMesh(ramp(0.25 + 0.75 * f / float(max(1, o["tf"] - 1)))); mm.Append(m)
        ids.append(sc.doc.Objects.AddMesh(mm))
        for k in range(N_PER):
            g = oi * N_PER + k; orbit(g, 12 * N_PER, 322, 350, 22, 360, (-52, -52, 62))
            cap("massing", dict(option=oi + 1, of=len(opts), gfa=o["gfa"], far=o["gfa"] / e["area"], height=o["h"], podium=o["pf"], tower=o["tf"]))
    print("GulfKit massing:", dict(options=len(opts), area=e["area"], far_target=6.0))

def t4():                                   # GulfMashrabiya on the south and west faces of the mid-rise
    clear(); hide_blocks([7, 8, 9], False); x0, y0, x1, y1, h = BLOCKS[10]; obs = obstacles()
    sv = [sunvec(172, 6 + 0.5 * k) for k in range(26)]; sv = [(v, a) for v, a in sv if a > 1]
    panels = []
    for (face, n) in [("S", Vector3d(0, -1, 0)), ("W", Vector3d(-1, 0, 0))]:
        L = (x1 - x0) if face == "S" else (y1 - y0); nu, nv = int(L / 2.0), int(h / 2.0)
        for i in range(nu):
            for j in range(nv):
                u = 2.0 * (i + 0.5); z = 2.0 * (j + 0.5)
                c = Point3d(x0 + u, y0, z) if face == "S" else Point3d(x0, y1 - u, z)
                hrs = sum(0.5 for v, a in sv if n * v > 0 and Intersection.MeshRay(obs, Ray3d(c + n * 0.3, v)) < 0)
                panels.append((face, c, n, hrs))
    mx = max(p[3] for p in panels); mn = min(p[3] for p in panels); layer("GK_T4"); N = 110; done = 0
    order = sorted(range(len(panels)), key=lambda i: (panels[i][1].Z, panels[i][0]))
    for k in range(N):
        upto = int(len(panels) * ease((k + 1) / 85.0))
        for i in order[done:upto]:
            face, c, n, hrs = panels[i]; t = (hrs - mn) / max(0.01, mx - mn); r = 0.92 - 0.5 * t          # more sun -> smaller opening
            off = n * 0.35; cc = c + off
            if face == "S":
                outer = [(cc.X - 1, cc.Y, cc.Z - 1), (cc.X + 1, cc.Y, cc.Z - 1), (cc.X + 1, cc.Y, cc.Z + 1), (cc.X - 1, cc.Y, cc.Z + 1), (cc.X - 1, cc.Y, cc.Z - 1)]
                st = star(cc.X, cc.Z, r, cc.Y)
            else:
                outer = [(cc.X, cc.Y - 1, cc.Z - 1), (cc.X, cc.Y + 1, cc.Z - 1), (cc.X, cc.Y + 1, cc.Z + 1), (cc.X, cc.Y - 1, cc.Z + 1), (cc.X, cc.Y - 1, cc.Z - 1)]
                st = [(cc.X, cc.Y + (p[0] - cc.X), p[2]) for p in star(cc.X, cc.Z, r, cc.Y)]
            co, cs_ = rs.AddPolyline(outer), rs.AddPolyline(st); s = rs.AddPlanarSrf([co, cs_]); rs.DeleteObjects([co, cs_])
            if s:
                br = rs.coercebrep(s[0]); ms = Mesh.CreateFromBrep(br, Rhino.Geometry.MeshingParameters.Minimal); rs.DeleteObject(s[0])
                for mm in ms: mm.VertexColors.CreateMonotoneMesh(ramp(t)); sc.doc.Objects.AddMesh(mm)
        done = upto
        orbit(k, N, 318, 338, 14, 105, (30, -50, 9), 32); cap("mashrabiya", dict(panels=len(panels), done=done))
    print("GulfKit mashrabiya:", dict(panels=len(panels), max_hours=mx, min_hours=mn))

def t5():                                   # GulfSunPath: 3D sun-path diagram for Doha, live sun and shadows
    clear(); R = 115.0; O = Point3d(-5, -5, 0)
    def sp(day, hour):
        alt, az = sunpos(day, hour); a, z = math.radians(alt), math.radians(az)
        return Point3d(O.X + R * math.cos(a) * math.sin(z), O.Y + R * math.cos(a) * math.cos(z), O.Z + R * math.sin(a)), alt, az
    layer("GK_T5"); ids = []
    def tube(cid, r, col):
        crv = rs.coercecurve(cid); m = Mesh.CreateFromCurvePipe(crv, r, 8, 0, Rhino.Geometry.MeshPipeCapStyle.Dome, False, None)
        m.VertexColors.CreateMonotoneMesh(col); sc.doc.Objects.AddMesh(m)
    ring = rs.AddCircle(rs.PlaneFromNormal((O.X, O.Y, 0.2), (0, 0, 1)), R); ids.append(ring)
    for k, lab in enumerate(["N", "E", "S", "W"]):
        a = math.radians(90 * k); ids.append(rs.AddText(lab, (O.X + (R + 9) * math.sin(a) - 2.5, O.Y + (R + 9) * math.cos(a) - 3, 0.2), 7.0))
        ids.append(rs.AddLine((O.X + (R - 4) * math.sin(a), O.Y + (R - 4) * math.cos(a), 0.2), (O.X + (R + 4) * math.sin(a), O.Y + (R + 4) * math.cos(a), 0.2)))
    arcs = {}
    for day, col in [(172, (234, 74, 0)), (80, (245, 200, 60)), (355, (75, 107, 169))]:
        pts = [sp(day, 4 + i / 12.0)[0] for i in range(16 * 12) if sp(day, 4 + i / 12.0)[1] > 0]
        c = rs.AddInterpCurve(pts); tube(c, 0.9, C(*col)); rs.DeleteObject(c); arcs[day] = pts
    for hr in range(6, 19):
        pts = [sp(d, hr)[0] for d in range(1, 366, 7) if sp(d, hr)[1] > 0]
        if len(pts) > 3: c = rs.AddInterpCurve(pts); tube(c, 0.35, C(120, 120, 128)); rs.DeleteObject(c)
    for o in ids: rs.ObjectColorSource(o, 1)
    rs.ViewDisplayMode("Perspective", "Rendered"); s = sc.doc.Lights.Sun; s.Enabled = True; s.ManualControl = False
    s.Latitude, s.Longitude, s.TimeZone, s.DaylightSaving = LAT, LON, TZ, False
    N = 110; ball = None
    for k in range(N):
        hour = 5.4 + 13.2 * k / (N - 1); p, alt, az = sp(172, hour)
        mins = int(round(hour * 60)); s.SetDateTime(System.DateTime(2026, 6, 21, mins // 60, mins % 60, 0), System.DateTimeKind.Local)
        if ball: rs.DeleteObject(ball)
        ball = None
        if alt > 0:
            sm = Mesh.CreateFromSphere(Rhino.Geometry.Sphere(p, 5.0), 24, 16); sm.VertexColors.CreateMonotoneMesh(C(255, 176, 0)); ball = sc.doc.Objects.AddMesh(sm)
        orbit(k, N, 336, 360, 24, 330, (-5, -5, 25)); cap("sunpath", dict(hour=hour, alt=alt, az=az))
    if ball: rs.DeleteObject(ball)
    rs.ViewDisplayMode("Perspective", "Arctic")
    print("GulfKit sunpath:", dict(june_noon_alt=max(sp(172, 9 + i / 12.0)[1] for i in range(72))))

def t6():                                   # GulfCanopy over the courtyard (22..48 x 22..38), 09:00 -> 17:00
    clear(); court = (22, 22, 48, 38); cz = 15.5; s = 1.3; cells_ = []
    nx, ny = int((court[2] - court[0]) / s), int((court[3] - court[1]) / s)
    for i in range(nx):
        for j in range(ny): cells_.append((court[0] + s * (i + 0.5), court[1] + s * (j + 0.5)))
    floor = [(court[0] + 0.5 + 1.0 * i, court[1] + 0.5 + 1.0 * j) for i in range(int(court[2] - court[0])) for j in range(int(court[3] - court[1]))]
    layer("GK_T6"); N = 120; ids = []; frame = Mesh()
    for (x, y) in cells_:
        for (a, b, c_, d) in [(-s / 2, -s / 2, s / 2, -s / 2 + 0.06), (-s / 2, s / 2 - 0.06, s / 2, s / 2), (-s / 2, -s / 2, -s / 2 + 0.06, s / 2), (s / 2 - 0.06, -s / 2, s / 2, s / 2)]:
            fm = boxmesh(x + a, y + b, x + c_, y + d, 0.12); fm.Translate(0, 0, cz); frame.Append(fm)
    frame.VertexColors.CreateMonotoneMesh(C(240, 240, 240)); sc.doc.Objects.AddMesh(frame)
    for k in range(N):
        hour = 9.0 + 8.0 * k / (N - 1); v, alt = sunvec(172, hour)
        if ids: rs.DeleteObjects(ids)
        ids = []; pm = Mesh(); closed = 0.0
        for (x, y) in cells_:
            cl = canopy_rule(x, y, cz, v, court); closed += cl; hw = (s / 2 - 0.06) * (1 - 0.92 * cl)   # aperture shrinks to 8% when closed
            k0 = pm.Vertices.Count
            for (px, py) in [(x - s / 2 + 0.06, y - s / 2 + 0.06), (x + s / 2 - 0.06, y - s / 2 + 0.06), (x + s / 2 - 0.06, y + s / 2 - 0.06), (x - s / 2 + 0.06, y + s / 2 - 0.06)]:
                pm.Vertices.Add(px, py, cz + 0.06); pm.VertexColors.Add(ramp(0.2 + 0.8 * cl))
            for (px, py) in [(x - hw, y - hw), (x + hw, y - hw), (x + hw, y + hw), (x - hw, y + hw)]:
                pm.Vertices.Add(px, py, cz + 0.06); pm.VertexColors.Add(ramp(0.2 + 0.8 * cl))
            for q in range(4): pm.Faces.AddFace(k0 + q, k0 + (q + 1) % 4, k0 + 4 + (q + 1) % 4, k0 + 4 + q)
        pm.Normals.ComputeNormals(); ids.append(sc.doc.Objects.AddMesh(pm))
        obs = obstacles([pm]); lit = 0; fm = Mesh()
        for (x, y) in floor:
            p = Point3d(x, y, 0.06); hit = v.Z > 0.02 and Intersection.MeshRay(obs, Ray3d(p, v)) >= 0
            if not hit and v.Z > 0.02: lit += 1
            q0 = fm.Vertices.Count
            for (px, py) in [(x - 0.5, y - 0.5), (x + 0.5, y - 0.5), (x + 0.5, y + 0.5), (x - 0.5, y + 0.5)]:
                fm.Vertices.Add(px, py, 0.08); fm.VertexColors.Add(C(250, 190, 60) if not hit else C(70, 90, 140))
            fm.Faces.AddFace(q0, q0 + 1, q0 + 2, q0 + 3)
        fm.Normals.ComputeNormals(); ids.append(sc.doc.Objects.AddMesh(fm))
        orbit(k, N, 196, 226, 52, 66, (35, 30, 6), 32)
        cap("canopy", dict(hour=hour, floor_sun=lit / float(len(floor)), closed=closed / len(cells_), cells=len(cells_)))
    print("GulfKit canopy:", dict(cells=len(cells_)))


NAMES = {1: "GulfSunHours", 2: "GulfShamal", 3: "GulfMassing", 4: "GulfMashrabiya", 5: "GulfSunPath", 6: "GulfCanopy"}
def run(n):
    t = time.time(); rs.EnableRedraw(True)
    if not rs.IsLayer("GK_Massing") or not rs.ObjectsByLayer("GK_Massing"): setup()
    if rs.ViewDisplayMode("Perspective") is not None and n != 5: rs.ViewDisplayMode("Perspective", "Arctic")
    {0: setup, 1: t1, 2: t2, 3: t3, 4: t4, 5: t5, 6: t6}[n]()
    print("%s done in %.1f s" % (NAMES.get(n, "GulfSetup"), time.time() - t))
