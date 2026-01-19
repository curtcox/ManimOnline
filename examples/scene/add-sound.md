# `scene/add-sound`

Add audio clips aligned to animation time.

Docs: [Scene.add_sound](https://docs.manim.community/en/stable/reference/manim.scene.scene.Scene.html?highlight=add_sound)

```py
from manim import *

class AddSoundExample(Scene):
    def construct(self):
        self.add_sound("click.wav", time_offset=0)
        self.play(Write(Text("Sound cue")))
```
