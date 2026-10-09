"""Regenerate community_reference.json with a local Manim Community install.

Usage: python generate_community_reference.py  (requires `pip install manim`)
Bodies are read from the existing fixture; only the measured bounds change.
"""
import json
from pathlib import Path

from manim import DL, UR, Scene, config, tempconfig  # noqa: F401

PATH = Path(__file__).with_name('community_reference.json')
data = json.loads(PATH.read_text())
config.verbosity = 'ERROR'
for name, case in data['cases'].items():
    source = 'from manim import *\nclass S(Scene):\n    def construct(self):\n'
    source += '\n'.join('        ' + line for line in case['body'].splitlines())
    namespace = {}
    exec(source, namespace)
    with tempconfig({'dry_run': True, 'disable_caching': True, 'quality': 'low_quality'}):
        scene = namespace['S']()
        scene.render()
    case['mobjects'] = [dict(cls=type(m).__name__, dl=[float(v) for v in m.get_critical_point(DL)[:2]],
                             ur=[float(v) for v in m.get_critical_point(UR)[:2]],
                             c=[float(v) for v in m.get_center()[:2]], w=float(m.width), h=float(m.height))
                        for m in scene.mobjects]
PATH.write_text(json.dumps(data, indent=1))
