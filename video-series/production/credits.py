"""The production credits card that render.py appends to every episode, after its closing teaser.

Keep it in step with "How this series was made" in ../README.md.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import *  # noqa: E402,F403

CREDITS = [
    ('Animation', 'Manim Community, from Python code in the series repository'),
    ('Scripts and code', 'Claude Opus 5.5, an AI model by Anthropic'),
    ('Direction', 'Curt Cox'),
    ('Narration', "ElevenLabs text-to-speech, from a model of Curt Cox's voice"),
    ('Source', 'github.com/curtcox/ManimOnline (video-series)'),
]
NOTE = ('Text-to-speech reads names from code and terms from math as ordinary English words, so the words\n'
        'you hear may be pronounced differently than programmers or mathematicians would say them.')
HOLD = 9.0


class Credits(Scene):
    def construct(self):
        title = Text('How this series was made', font_size=40).to_edge(UP, buff=1.0)
        roles = VGroup(*[Text(role, font_size=24, color=SCAFFOLD) for role, _ in CREDITS])
        credits = VGroup(*[Text(credit, font_size=26) for _, credit in CREDITS])
        credits.arrange(DOWN, buff=0.42, aligned_edge=LEFT)
        # roles in a column, credits lined up after the widest role
        start = credits.get_left()[0] - max(r.width for r in roles) - 0.4
        for role, credit in zip(roles, credits):
            role.move_to([start + role.width / 2, credit.get_y(), 0])
        table = VGroup(roles, credits).next_to(title, DOWN, buff=0.7).set_x(0)
        note = VGroup(*[Text(line, font_size=22, color=FOCUS) for line in NOTE.split('\n')])
        note.arrange(DOWN, buff=0.15).next_to(table, DOWN, buff=0.75).set_x(0)
        fit(note)
        self.play(FadeIn(title, shift=UP * 0.2), LaggedStart(*[FadeIn(r) for r in table], lag_ratio=0.15), run_time=1.5)
        self.play(FadeIn(note))
        self.wait(HOLD - 3.5)
        self.play(FadeOut(VGroup(title, table, note)))
        self.wait(0.5)
