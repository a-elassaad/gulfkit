# Rhino 8 command GulfMashrabiya (GulfKit). Run: _-RunPythonScript "<this file>"  or add an alias (see README).
import os, sys
D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if D not in sys.path: sys.path.insert(0, D)
import gulfkit_tools; reload(gulfkit_tools); gulfkit_tools.run(4)
