# `voiceovers/plugin`

Add narration with timing hooks inside code.

Docs: [Add voiceovers](https://docs.manim.community/en/stable/guides/add_voiceovers.html)

```py
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService

class VoiceoverExample(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GTTSService())
        with self.voiceover(text="Hello voiceover"):
            self.play(Write(Text("Narrated")))
```
