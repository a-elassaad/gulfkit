# -*- coding: utf-8 -*-
# GulfSunHours: direct sun hours on any selected Rhino geometry, shaded by every visible object.
# Rhino 8, IronPython 2.7. MIT licence. Quick check: direct sun only, no diffuse sky, no reflections.
import math, os, time, base64
import Rhino, System, scriptcontext as sc, rhinoscriptsyntax as rs
from Rhino.Geometry import Point3d, Vector3d, Mesh, Ray3d, MeshingParameters
from Rhino.Geometry.Intersect import Intersection

CITIES = [("Doha", 25.29, 51.53, 3.0), ("Dubai", 25.20, 55.27, 4.0), ("AbuDhabi", 24.45, 54.38, 4.0),
          ("Riyadh", 24.71, 46.68, 3.0), ("Jeddah", 21.49, 39.19, 3.0), ("Kuwait", 29.38, 47.99, 3.0),
          ("Manama", 26.23, 50.59, 3.0), ("Muscat", 23.59, 58.41, 4.0)]
MDAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
RAMP = [(75, 107, 169), (115, 147, 202), (170, 200, 247), (193, 213, 208), (245, 239, 103), (252, 230, 74),
        (239, 156, 21), (234, 123, 0), (234, 74, 0), (234, 38, 0)]
SECTORS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
# Screen openness rule (GulfKit design rule of thumb, not a code requirement): direct sun hours on the face -> open area of the screen
SCREEN = [(1.0, "no screen needed", 1.00), (2.0, "light screen", 0.50), (3.0, "medium screen", 0.35), (99.0, "dense screen", 0.20)]   # kWh/m2/day direct

def color(t):
    t = max(0.0, min(1.0, t)) * (len(RAMP) - 1); i = min(len(RAMP) - 2, int(t)); f = t - i
    a, b = RAMP[i], RAMP[i + 1]; return System.Drawing.Color.FromArgb(*[int(a[k] + (b[k] - a[k]) * f) for k in range(3)])

def doy(month, day): return sum(MDAYS[:month - 1]) + day

def sunpos(day, hour, lat, lon, tz):
    """Solar altitude and azimuth (deg, azimuth from north clockwise). NOAA general solar position equations."""
    g = 2 * math.pi / 365 * (day - 1 + (hour - 12) / 24.0)
    eot = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g) - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    dec = 0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g) + 0.000907 * math.sin(2 * g) - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g)
    ha = math.radians((hour * 60 + eot + 4 * lon - 60 * tz) / 4.0 - 180); la = math.radians(lat)
    alt = math.asin(math.sin(la) * math.sin(dec) + math.cos(la) * math.cos(dec) * math.cos(ha))
    az = math.atan2(math.sin(ha), math.cos(ha) * math.sin(la) - math.tan(dec) * math.cos(la))
    return math.degrees(alt), (math.degrees(az) + 180) % 360

def sun_vectors(day, lat, lon, tz, step=0.5):
    out = []
    for k in range(int(24 / step)):
        h = (k + 0.5) * step                              # centre of each time step
        alt, az = sunpos(day, h, lat, lon, tz)
        if alt > 0.5:
            a, z = math.radians(alt), math.radians(az)
            am = 1.0 / (math.sin(a) + 0.50572 * (alt + 6.07995) ** -1.6364)         # Kasten-Young air mass
            dni = 1.353 * 0.7 ** (am ** 0.678)                                       # Meinel clear-sky direct normal, kW/m2
            out.append((Vector3d(math.sin(z) * math.cos(a), math.cos(z) * math.cos(a), math.sin(a)), dni))
    return out

def to_mesh(obj, mp):
    g = obj.Geometry
    if isinstance(g, Mesh): return g.DuplicateMesh()
    if isinstance(g, Rhino.Geometry.Extrusion): g = g.ToBrep()
    if isinstance(g, Rhino.Geometry.Surface): g = g.ToBrep()
    if isinstance(g, Rhino.Geometry.Brep):
        m = Mesh(); [m.Append(x) for x in (Mesh.CreateFromBrep(g, mp) or [])]; return m
    if isinstance(g, Rhino.Geometry.SubD): return Mesh.CreateFromSubD(g, 2)
    return None

def orientation(n, z, zmin):
    if n.Z > 0.7: return "Ground" if z < zmin + 0.3 else "Roof"
    if n.Z < -0.7: return "Soffit"
    a = (math.degrees(math.atan2(n.X, n.Y)) + 360) % 360
    return SECTORS[int(((a + 22.5) % 360) // 45)]

def screen_rule(h):
    for lim, name, open_ in SCREEN:
        if h < lim: return name, open_

def analyse(targets, context, day, lat, lon, tz, grid=2.0, step=0.5):
    """targets/context: lists of RhinoObjects. Returns cells [(centre, normal, area, hours, face mesh)], number of sun steps."""
    mp = MeshingParameters(); mp.MaximumEdgeLength = grid; mp.MinimumEdgeLength = grid * 0.25; mp.GridAspectRatio = 1.5
    mp.SimplePlanes = False; mp.RefineGrid = True; mp.JaggedSeams = False
    obs = Mesh()
    for o in context:
        m = to_mesh(o, MeshingParameters.FastRenderMesh)
        if m: obs.Append(m)
    sv = sun_vectors(day, lat, lon, tz, step); cells = []
    for o in targets:
        m = to_mesh(o, mp)
        if not m: continue
        m.Faces.ConvertQuadsToTriangles(); m.Normals.ComputeNormals(); m.FaceNormals.ComputeFaceNormals()
        for fi in range(m.Faces.Count):
            f = m.Faces[fi]; a, b, c = m.Vertices[f.A], m.Vertices[f.B], m.Vertices[f.C]
            pa, pb, pc = Point3d(a), Point3d(b), Point3d(c); cen = Point3d((pa.X + pb.X + pc.X) / 3, (pa.Y + pb.Y + pc.Y) / 3, (pa.Z + pb.Z + pc.Z) / 3)
            n = Vector3d(m.FaceNormals[fi]); area = Vector3d.CrossProduct(pb - pa, pc - pa).Length / 2.0
            if area < 1e-6 or (n.Z < -0.7 and cen.Z < 0.1): continue     # skip faces lying on the ground, facing down
            start = cen + n * 0.05; hrs = 0.0; kwh = 0.0
            for v, dni in sv:
                c = n * v
                if c <= 0: continue
                if Intersection.MeshRay(obs, Ray3d(start, v)) < 0: hrs += step; kwh += dni * c * step
            cells.append((cen, n, area, hrs, (pa, pb, pc), kwh))
    return cells, len(sv) * step

def stats(cells, threshold=4.0):
    zmin = min(c[0].Z for c in cells); rows = {}
    for cen, n, area, h, tri, e in cells:
        k = orientation(n, cen.Z, zmin); r = rows.setdefault(k, [0.0, 0.0, 0.0, 0.0, 0.0])
        r[0] += area; r[1] += area * h; r[2] += area if h >= threshold else 0.0; r[3] = max(r[3], h); r[4] += area * e
    order = SECTORS + ["Roof", "Ground", "Soffit"]
    return [(k, rows[k][0], rows[k][1] / rows[k][0], rows[k][2] / rows[k][0], rows[k][3], rows[k][4] / rows[k][0]) for k in order if k in rows]

def draw(cells, hmax, layer="GK_SunHours"):
    if not rs.IsLayer(layer): rs.AddLayer(layer)
    rs.DeleteObjects(rs.ObjectsByLayer(layer) or [])          # replace the previous result
    m = Mesh()
    for cen, n, area, h, (pa, pb, pc), e in cells:
        k = m.Vertices.Count; col = color(h / max(0.01, hmax))
        for p in (pa, pb, pc): m.Vertices.Add(p + n * 0.03); m.VertexColors.Add(col)
        m.Faces.AddFace(k, k + 1, k + 2)
    m.Normals.ComputeNormals()
    attr = Rhino.DocObjects.ObjectAttributes(); attr.LayerIndex = sc.doc.Layers.FindByFullPath(layer, -1)
    return sc.doc.Objects.AddMesh(m, attr)

def legend(cells, hmax, layer="GK_SunHours"):
    bb = Rhino.Geometry.BoundingBox([c[0] for c in cells]); s = max(bb.Diagonal.X, bb.Diagonal.Y) * 0.03
    x0, y0, z0 = bb.Max.X + 4 * s, bb.Min.Y, 0.0; ids = []; m = Mesh()
    for i in range(10):
        k = m.Vertices.Count; col = color((i + 0.5) / 10.0)
        for (dx, dy) in [(0, i), (1, i), (1, i + 1), (0, i + 1)]: m.Vertices.Add(x0 + dx * s, y0 + dy * s * 1.6, z0); m.VertexColors.Add(col)
        m.Faces.AddFace(k, k + 1, k + 2, k + 3)
    attr = Rhino.DocObjects.ObjectAttributes(); attr.LayerIndex = sc.doc.Layers.FindByFullPath(layer, -1)
    ids.append(sc.doc.Objects.AddMesh(m, attr)); prev = rs.CurrentLayer(); rs.CurrentLayer(layer)
    for i in (0, 5, 10): ids.append(rs.AddText("%.1f h" % (hmax * i / 10.0), (x0 + 1.4 * s, y0 + i * s * 1.6 - 0.3 * s, z0), s * 0.8))
    ids.append(rs.AddText("Direct sun hours", (x0, y0 + 17.2 * s, z0), s * 0.9)); rs.CurrentLayer(prev)
    return ids

def report(rows, meta, folder):
    """Writes an HTML facade report with the viewport image. Returns its path."""
    if not os.path.isdir(folder): os.makedirs(folder)
    stamp = time.strftime("%Y%m%d-%H%M%S"); png = os.path.join(folder, "GulfSunHours-%s.png" % stamp)
    vc = Rhino.Display.ViewCapture(); vc.Width, vc.Height = 1600, 1000; vc.ScaleScreenItems = False; vc.DrawAxes = False; vc.DrawGrid = False
    vc.CaptureToBitmap(sc.doc.Views.ActiveView).Save(png); img = base64.b64encode(open(png, "rb").read())
    tr = "".join("<tr><td>%s</td><td>%.0f</td><td>%.1f</td><td>%.0f%%</td><td>%.1f</td><td>%.2f</td><td>%s</td><td>%s</td></tr>" % (
        k, a, mean, share * 100, mx, e, screen_rule(e)[0] if k in SECTORS else "-", ("%.0f%%" % (screen_rule(e)[1] * 100)) if k in SECTORS else "-")
        for (k, a, mean, share, mx, e) in rows)
    html = u"""<!doctype html><meta charset="utf-8"><title>GulfSunHours report</title>
<style>body{font:15px/1.5 Segoe UI,Arial,sans-serif;max-width:980px;margin:32px auto;color:#1d1d22;padding:0 16px}
table{border-collapse:collapse;width:100%%}td,th{border-bottom:1px solid #ddd;padding:6px 8px;text-align:right}td:first-child,th:first-child{text-align:left}
th{background:#f3efe8}img{width:100%%;border:1px solid #ddd}.note{color:#666;font-size:13px}</style>
<h1>GulfSunHours facade report</h1>
<p><b>%(city)s</b> (lat %(lat).2f, lon %(lon).2f, UTC+%(tz)g) &middot; day %(day)d (%(date)s) &middot; %(cells)d analysis cells &middot; grid %(grid)g m &middot; %(step)g h steps &middot; %(sunh).1f h of sun above the horizon</p>
<img src="data:image/png;base64,%(img)s">
<h2>Direct sun hours per orientation</h2>
<table><tr><th>Orientation</th><th>Area m&sup2;</th><th>Mean h</th><th>Area &ge; %(thr)g h</th><th>Max h</th><th>Direct kWh/m&sup2;</th><th>Screen</th><th>Screen open area</th></tr>%(tr)s</table>
<p class="note">Direct kWh/m&sup2;: clear-sky direct energy on the surface for the day (Meinel clear-sky model, Kasten-Young air mass,
cosine of incidence). Real Gulf skies carry dust and haze, so real values are lower. Screen rule (GulfKit rule of thumb, adjust to
the project), on the mean direct energy of each orientation: under 1 kWh/m&sup2; no screen, 1-2 light screen 50%% open,
2-3 medium 35%% open, over 3 dense 20%% open.</p>
<p class="note">Quick check for early design: direct sun only, no diffuse sky, no reflections; kWh/m&sup2; is a clear-sky estimate.
Sun position: NOAA general solar position equations, validated in VALIDATION.md. Check results before relying on them.</p>
<p class="note">Made with GulfKit, github.com/a-elassaad/gulfkit</p>""" % dict(meta, img=img, tr=tr, thr=4.0)
    path = os.path.join(folder, "GulfSunHours-%s.html" % stamp)
    with open(path, "wb") as f: f.write(html.encode("utf-8"))
    return path

def command():
    go = Rhino.Input.Custom.GetObject(); go.SetCommandPrompt("Select buildings or surfaces to analyse")
    go.GeometryFilter = Rhino.DocObjects.ObjectType.Brep | Rhino.DocObjects.ObjectType.Mesh | Rhino.DocObjects.ObjectType.Extrusion | Rhino.DocObjects.ObjectType.Surface | Rhino.DocObjects.ObjectType.SubD
    names = [c[0] for c in CITIES]
    o_city = go.AddOptionList("City", names, 0); oi_m = Rhino.Input.Custom.OptionInteger(6, 1, 12); oi_d = Rhino.Input.Custom.OptionInteger(21, 1, 31)
    od_g = Rhino.Input.Custom.OptionDouble(2.0, 0.25, 20.0); ot_r = Rhino.Input.Custom.OptionToggle(True, "No", "Yes")
    go.AddOptionInteger("Month", oi_m); go.AddOptionInteger("Day", oi_d); go.AddOptionDouble("Grid", od_g); go.AddOptionToggle("Report", ot_r)
    city = 0; go.EnablePreSelect(True, True); go.GroupSelect = True
    while True:
        r = go.GetMultiple(1, 0)
        if r == Rhino.Input.GetResult.Option:
            if go.OptionIndex() == o_city: city = go.Option().CurrentListOptionIndex
            continue
        if r != Rhino.Input.GetResult.Object: return
        break
    targets = [go.Object(i).Object() for i in range(go.ObjectCount)]
    gp = Rhino.Input.Custom.GetOption(); gp.SetCommandPrompt("%d objects selected. Press Enter to analyse" % len(targets)); gp.AcceptNothing(True)
    while True:                                           # options can still be changed after selecting
        gp.ClearCommandOptions(); p_city = gp.AddOptionList("City", names, city)
        gp.AddOptionInteger("Month", oi_m); gp.AddOptionInteger("Day", oi_d); gp.AddOptionDouble("Grid", od_g); gp.AddOptionToggle("Report", ot_r)
        r = gp.Get()
        if r == Rhino.Input.GetResult.Option:
            if gp.OptionIndex() == p_city: city = gp.Option().CurrentListOptionIndex
            continue
        if r == Rhino.Input.GetResult.Nothing: break
        return
    ids = set(t.Id for t in targets)
    context = [o for o in sc.doc.Objects.GetObjectList(Rhino.DocObjects.ObjectEnumeratorSettings())
               if o.Visible and not o.Attributes.LayerIndex == sc.doc.Layers.FindByFullPath("GK_SunHours", -1)
               and o.ObjectType in (Rhino.DocObjects.ObjectType.Brep, Rhino.DocObjects.ObjectType.Mesh, Rhino.DocObjects.ObjectType.Extrusion, Rhino.DocObjects.ObjectType.SubD, Rhino.DocObjects.ObjectType.Surface)]
    name, lat, lon, tz = CITIES[city]; day = doy(oi_m.CurrentValue, min(oi_d.CurrentValue, MDAYS[oi_m.CurrentValue - 1]))
    t0 = time.time(); Rhino.RhinoApp.WriteLine("GulfSunHours: %s, %d/%d, %d objects analysed, %d in context..." % (name, oi_d.CurrentValue, oi_m.CurrentValue, len(targets), len(context)))
    cells, sunh = analyse(targets, context, day, lat, lon, tz, od_g.CurrentValue)
    if not cells: Rhino.RhinoApp.WriteLine("Nothing to analyse."); return
    hmax = max(c[3] for c in cells); draw(cells, hmax); legend(cells, hmax); rs.UnselectAllObjects()
    bb = Rhino.Geometry.BoundingBox([c[0] for c in cells]); bb.Inflate(bb.Diagonal.Length * 0.08); sc.doc.Views.ActiveView.ActiveViewport.ZoomBoundingBox(bb); sc.doc.Views.Redraw()
    rows = stats(cells)
    Rhino.RhinoApp.WriteLine("%-7s %9s %7s %9s %6s %8s" % ("Face", "Area m2", "Mean h", ">=4 h", "Max h", "kWh/m2"))
    for (k, a, mean, share, mx, e) in rows: Rhino.RhinoApp.WriteLine("%-7s %9.0f %7.1f %8.0f%% %6.1f %8.2f" % (k, a, mean, share * 100, mx, e))
    Rhino.RhinoApp.WriteLine("%d cells in %.1f s" % (len(cells), time.time() - t0))
    if ot_r.CurrentValue:
        folder = os.path.dirname(sc.doc.Path) if sc.doc.Path else os.path.join(System.IO.Path.GetTempPath(), "GulfKit")
        p = report(rows, dict(city=name, lat=lat, lon=lon, tz=tz, day=day, date="%d/%d" % (oi_d.CurrentValue, oi_m.CurrentValue), cells=len(cells),
                              grid=od_g.CurrentValue, step=0.5, sunh=sunh), folder)
        Rhino.RhinoApp.WriteLine("Report: " + p)
    return cells, rows
