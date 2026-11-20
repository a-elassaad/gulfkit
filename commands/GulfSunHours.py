# Rhino 8 command GulfSunHours (GulfKit). Run: _-RunPythonScript "<this file>"  or add an alias (see README).
# Select your buildings or surfaces; every other visible object casts shadow. Options: City, Month, Day, Grid, Report.
import os, sys
D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if D not in sys.path: sys.path.insert(0, D)
import sunhours; reload(sunhours); sunhours.command()
