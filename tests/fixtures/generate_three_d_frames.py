"""Regenerate three_d_frames.json: world-space ThreeDScene frames for the JS projector.

Usage: python tests/fixtures/generate_three_d_frames.py
The renderer tests project these frames and compare with Manim 0.22 measurements;
tests/test_manim_lite.py checks that the fixture matches the current Python output.
"""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATH = Path(__file__).with_name('three_d_frames.json')

CASES = {
    'square_projection': """self.set_camera_orientation(phi=75 * DEGREES, theta=-45 * DEGREES)
self.add(Square())""",
    'depth_shading': """self.add(Square(fill_color=BLUE, shade_in_3d=True).shift(OUT),
         Square(shade_in_3d=True).shift(IN))""",
    'depth_flipped': """self.set_camera_orientation(phi=180 * DEGREES)
self.add(Square(fill_color=BLUE, shade_in_3d=True).shift(OUT),
         Square(shade_in_3d=True).shift(IN))""",
    'fixed_members': """text = Text('hi')
self.add_fixed_in_frame_mobjects(text)
dot = Dot().shift(RIGHT)
self.add_fixed_orientation_mobjects(dot)
self.set_camera_orientation(phi=75 * DEGREES)""",
    'cube': """self.set_camera_orientation(phi=75 * DEGREES, theta=-30 * DEGREES)
self.add(Cube())""",
    'rotated_square': """s = Square()
s.rotate(PI / 3, axis=UP)
self.add(s)
self.set_camera_orientation(phi=60 * DEGREES, theta=-45 * DEGREES)""",
}


def load_lite():
    spec = importlib.util.spec_from_file_location('manim_lite', ROOT / 'src' / 'manim-lite.py')
    lite = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lite)
    return lite


def frames(lite=None):
    lite = lite or load_lite()
    result = {}
    for name, body in CASES.items():
        source = 'from manim import *\nclass Demo(ThreeDScene):\n    def construct(self):\n'
        source += '\n'.join('        ' + line for line in body.splitlines())
        # The final seekable frame holds the configured camera.
        result[name] = json.loads(lite.render_scene(source))['frames'][-1]
    return result


if __name__ == '__main__':
    PATH.write_text(json.dumps(frames(), indent=None, separators=(',', ':')) + '\n')
