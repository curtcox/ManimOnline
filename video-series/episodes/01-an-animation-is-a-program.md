# Episode 1 · An animation is a program

Published video: [An Animation Is a Program · Drawing with Code 1 (Manim)](https://www.youtube.com/watch?v=oZYsQfNCl7U&list=PLXaiuWr3VAhk) · [series playlist](https://www.youtube.com/playlist?list=PLXaiuWr3VAhk)

| | |
|---|---|
| Track | Main |
| Target length | about 14 min (segment estimates; set final timing from the narration audio) |
| Builds on | Basic Python: variables, calling functions, a class header |
| QR codes | q01-01 … q01-05 |

## Learning goals

By the end, the viewer can:

- explain an animation as frames computed from a description of change;
- open ManimOnline, render a scene, play, pause and seek it;
- read a minimal scene: `Scene`, `construct`, objects, `self.play`, `self.wait`;
- change colours and shapes, and predict a scene's total duration;
- read an error message and fix the line it names.

## Script

### 1.1 Cold open · ≈ 0:50

**Visual.** [V1.1a] Black canvas. A blue square draws itself, edge by edge, then
melts into a yellow circle (exactly q01-01). It holds. [V1.1b] The animation rewinds
and replays slowly; a frame counter in the top-left ticks up: 1, 2, 3 … 46 (at the
15 fps preview rate the clip is 46 frames). [V1.1c] The frames fan out into a
flipbook strip across the screen, each one a slightly different shape between square
and circle.

> Here is a square turning into a circle. <break time="0.6s" /> It takes about three seconds, and it looks effortless. But a screen cannot show motion. It can only show still pictures, one after another, fast enough that your brain fills in the gaps.
>
> So this little clip is really a stack of still frames. Dozens of them at preview quality, close to two hundred at the smoothness of a finished video. And each frame is a slightly different shape: not quite a square, not yet a circle.
>
> Here is the question that this whole series grows out of. Who drew all of those in-between shapes?

### 1.2 Describing change instead of drawing it · ≈ 1:30

**Visual.** [V1.2a] The flipbook strip compresses back into one frame. On the left, a
cartoon timeline in the style of traditional animation software: a key frame
"square" at time 0, a key frame "circle" at time 3, and a question mark between them.
[V1.2b] The question mark is replaced by a slider labelled "t" running from 0 to 1.
As the slider moves, the shape on the right morphs; at t = 0.5 it is a rounded
square. [V1.2c] The slider fades and is replaced by four short lines of plain English:
"Make a square. Draw it. Turn it into a circle. Pause." Each line lights up as its
part of the animation plays.

> The traditional answer is: an artist did, or an artist drew the start and the end, and software guessed the middle. That is called key framing, and it works wonderfully for characters and logos.
>
> But think about what a mathematician wants to animate. A curve that is exactly the graph of a function. A triangle whose corners stay exactly on a circle. An equation whose terms slide to exactly the right places. Guessing the middle is not good enough when the middle is the whole point.
>
> So here is a different idea. Instead of drawing frames, describe the change. <break time="0.5s" /> Make a square. Draw it. Turn it into a circle. Pause for a moment.
>
> If those sentences are precise enough, a computer can work out every in-between frame for you. For any moment in time, it asks: how far along are we? A quarter of the way? Then compute the shape that is a quarter of the way from square to circle. Halfway? Compute that one.
>
> And a description precise enough for a computer to follow has another name. <break time="0.6s" /> It is a program.

### 1.3 Where Manim comes from · ≈ 1:10

**Visual.** [V1.3a] A simple horizontal timeline of years. A marker at 2015: "Manim:
written by Grant Sanderson for his math videos." [V1.3b] A branch at 2020: "Manim
Community Edition", drawn as a second line splitting off and continuing to the
present. The original line continues labelled "ManimGL". [V1.3c] Today's end of the
community line is labelled "this series: Community conventions". [V1.3d] A small
browser window icon appears below the timeline, joined by a dashed line:
"ManimOnline: a Manim-compatible engine in your browser".

> That is exactly the idea behind Manim. The name is short for math animation. It was written by Grant Sanderson, around 2015, to make the videos on his channel, and he shared the code so that anyone could use it.
>
> As more people began using it, a group of them formed Manim Community, a separately maintained edition focused on stability, documentation and new features. The two have drifted apart in places, so when this series says Manim, it means the Community edition and its conventions.
>
> Normally, using Manim means installing Python, the library, and a handful of supporting tools for drawing, video encoding and typesetting. That is a real hurdle on your first day.
>
> So in this series we will mostly work somewhere else: ManimOnline. It is a website, and it runs a Manim-compatible engine entirely inside your browser tab. Nothing to install. And as we will see much later, nothing running on a server either.

### 1.4 A tour of ManimOnline · ≈ 1:40

**Visual.** [V1.4a] Screen recording: the ManimOnline page loads. A soft yellow
outline highlights each region as it is named: the code editor on the left, the
preview on the right, the toolbar along the top. [V1.4b] The editor shows the
`SquareToCircle` code. The status line reads that Python is loading; then the preview
plays the square-to-circle animation. [V1.4c] Highlight the playback controls: play,
pause, and the seek bar. The cursor drags the seek bar back and forth, scrubbing the
morph. [V1.4d] Highlight the "Renderer: Auto" selector and the "Sample gallery" link
briefly.

**QR q01-01** appears at [V1.4b], 8 seconds. Caption: "q01-01 · Square to circle".

> Let's open it. On the left is a code editor. On the right is the preview. Along the top, a toolbar we will explore over the course of the series.
>
> The first time you visit, the page downloads a Python interpreter, so the very first render takes a little while. After that, things move quickly.
>
> If you would like to follow along, scan the code in the corner. It opens this exact scene in your browser.
>
> Once it renders, the preview behaves like a video player. You can play, pause, and drag the seek bar to scrub through time. That last part is more interesting than it looks. The page already computed every frame before it started playing, so jumping to any moment is instant.
>
> Two more things worth knowing. ManimOnline also understands two diagram languages, Graphviz and modl, and it guesses which language you are writing. The Renderer selector says Auto, and for Python scenes it will choose Manim on its own. And the Sample gallery link opens a collection of ready-made examples, which is a wonderful place to steal ideas from. We will come back to both in episode nine.

### 1.5 Reading the first scene · ≈ 2:30

**Visual.** [V1.5a] Full-frame code panel with the scene below. As each line is
discussed, it is highlighted and the matching element appears on the right half of
the screen.

**On screen**

```python
from manim import *


class SquareToCircle(Scene):
    def construct(self):
        square = Square(color=BLUE)
        circle = Circle(color=YELLOW)
        self.play(Create(square))
        self.play(Transform(square, circle))
        self.wait()
```

[V1.5b] Line 1 highlighted: a toolbox icon opens and dozens of names fly out
(Square, Circle, Create, BLUE, UP, …). [V1.5c] The class line: a film-clapper icon
labelled "Scene". [V1.5d] `construct`: the icon opens to reveal an empty stage.
[V1.5e] The two assignment lines: a square and a circle appear on the right, faded and
labelled "exists, but not on screen yet". [V1.5f] `self.play(Create(square))`: the
square draws itself on the stage. [V1.5g] `Transform`: the morph plays. [V1.5h]
`self.wait()`: a clock icon ticks for one second while nothing moves.

> Let's read this program one line at a time. It is short, but every line is doing something you will use in every scene you ever write.
>
> The first line says: from manim, import everything. That fills your toolbox with names. Shapes like Square and Circle, animations like Create, colours like BLUE, and directions like UP.
>
> Next, a class called SquareToCircle, which is a kind of Scene. If you have not written classes before, do not worry. For now, read it as a template: "Here is a scene, and this is its name." A single file can hold several scenes, and the name is how you choose between them.
>
> Inside the scene is a method called construct. When the scene is rendered, Manim calls construct, and everything inside it happens in order, from top to bottom. You can think of construct as the script for this little film.
>
> The first two lines inside make objects. A blue square and a yellow circle. And here is a subtle point. Creating an object does not put it on screen. Right now, both shapes exist in the computer's memory, waiting in the wings.
>
> Then: self dot play, Create, square. This is the first line that takes time. Play means: run this animation, and record the frames. Create is a particular animation, one that draws an object's outline as if a pen were tracing it. And when it finishes, the square is on stage.
>
> Next: self dot play, Transform, square into circle. The square smoothly becomes the shape of the circle. Keep an eye on the wording there. The square becomes circle-shaped; the circle object we made is used as a target, a picture of where to end up. We will find out in episode three why that distinction matters more than it seems.
>
> And finally, self dot wait. Nothing moves. The scene simply holds for a second, so the viewer has a moment to look at what just happened.

### 1.6 Three nouns, one verb · ≈ 1:10

**Visual.** [V1.6a] Three large labels arranged in a triangle: "Scene" (a stage),
"Mobject" (a square and a circle), "Animation" (a curved arrow between square and
circle). [V1.6b] A fourth label, "play", sits in the middle, with arrows from
"Animation" into "play" and from "play" out to a strip of frames. [V1.6c] Each label
gets a one-line definition underneath, appearing as it is read.

> If you squint, that program has a small grammar, and it is the grammar of all of Manim.
>
> There is the scene, the stage where everything happens. There are mobjects, short for mathematical objects: anything you can see, like shapes, text, graphs and arrows. And there are animations, which describe how mobjects change over time.
>
> Then there is the verb that ties them together: play. Play takes animations, works out every in-between moment, and turns them into frames.
>
> Episode two is all about mobjects. Episode three is all about animations. But you already know enough to start changing things.

### 1.7 Your first edits · ≈ 1:20

**Visual.** [V1.7a] Screen recording. The cursor adds `fill_opacity=0.5` to the
square; one second after typing stops the preview re-renders, and the square is
half-filled. [V1.7b] The cursor adds a third line,
`self.play(Transform(shape, Triangle(color=RED, fill_opacity=0.5)))`, and the preview
now ends with a red triangle. [V1.7c] Split screen: before and after code.

**QR q01-02** appears at [V1.7b], 8 seconds. Caption: "q01-02 · Three shapes in a row".

> The best way to learn this is to change things and see what breaks. Try giving the square a fill. Add fill opacity equals zero point five inside the parentheses. Stop typing, and after a short pause the preview renders again by itself.
>
> Now add another transform: turn the shape into a red triangle. The code in the corner has all three shapes, and a comment inviting you to add a fourth, a green star.
>
> Notice that the new version gave the shape a more general name, shape instead of square, because it is not going to stay a square for long. Names are for you, not for Manim. Choose the one that will still be true at the end of the scene.

### 1.8 Time is something you write down · ≈ 1:30

**Visual.** [V1.8a] A horizontal timeline from 0 to 6 seconds runs along the bottom
of the screen. Above it, a yellow dot slides from left to centre (1 s), waits (1 s),
slides to the right edge slowly (3 s), then waits (0.5 s). [V1.8b] As each line of the
q01-03 code is highlighted, a coloured block grows on the timeline with its length
labelled: "play: 1 s", "wait: 1 s", "play, run_time=3: 3 s", "wait: 0.5 s". [V1.8c]
The blocks total "5.5 s" at the end, and `self.add` appears as a zero-width tick at
the start. [V1.8d] For the closing note about the narration, "synthetic voice"
appears under the narration line.

**On screen**

```python
self.add(dot)                                        # 0 seconds: add is instant
self.play(dot.animate.shift(RIGHT * 4))              # 1 second (the default)
self.wait(1)                                         # 1 second of stillness
self.play(dot.animate.shift(RIGHT * 4), run_time=3)  # 3 slower seconds
self.wait(0.5)
```

**QR q01-03** appears at [V1.8c], 8 seconds. Caption: "q01-03 · How play and wait build a timeline".

> Here is something worth noticing. In a Manim scene, time does not pass on its own. It only passes when you say so.
>
> Self dot add puts an object on stage instantly, with no animation, and takes no time at all. Each call to play adds the length of its animation, which is one second unless you say otherwise. Wait adds however many seconds you ask for, and one if you do not say.
>
> To make an animation slower, pass run time. Run time equals three makes the second slide take three seconds. Add it all up and this scene lasts five and a half seconds, and you could have predicted that before it ever rendered.
>
> That is a surprisingly powerful habit. When a scene feels rushed, you know exactly which line to stretch. When it drags, you know which wait to shorten. And when you later add a voice-over, like the one you are listening to now, you can match every animation to the length of a sentence.
>
> This voice-over, by the way, is synthetic: text-to-speech built from a model of Curt Cox's voice. It reads names from code and terms from math as ordinary English words, so you may hear some of them, like construct, pronounced differently than programmers or mathematicians would say them.

### 1.9 When things go wrong · ≈ 1:30

**Visual.** [V1.9a] Screen recording: the q01-04 code, with `Circel` on line 7. The
preview area shows a traceback ending in `File "<scene>", line 7, in construct` and
`NameError: name 'Circel' is not defined. Did you mean: 'Circle'?`.
[V1.9b] Zoom on the message; underline the word "Circel" in both the message and the
code. [V1.9c] The cursor fixes the spelling. The preview renders successfully.

**QR q01-04** appears at [V1.9a], 8 seconds. Caption: "q01-04 · Fix the typo".

> Sooner or later, you will make a mistake. Everyone does, constantly, and that is fine. What matters is reading what the computer tells you.
>
> Scan this code and you will get an error instead of an animation. The last line says NameError: name C I R C E L is not defined. Did you mean Circle? Python is telling you it has never heard of anything called Circel, and it even suggests what you probably meant. The line just above it says where: line seven, inside construct.
>
> Find that word in the code, fix the spelling, and stop typing. The scene renders again, and this time it works.
>
> Most early errors are like this one: a misspelled name, a missing parenthesis, or forgetting to import something. Read the last line of the message first. It usually names the problem, and very often the exact spot.

### 1.10 Recap and challenge · ≈ 1:10

**Visual.** [V1.10a] The three-noun diagram from 1.6 returns, now with small icons
of today's examples attached. [V1.10b] The traffic-light scene (q01-05): a grey
housing with three dark lamps; the bottom lamp lights green. The other two stay dark,
with a dotted outline and a question mark on each. [V1.10c] QR wall: q01-01 to q01-05
for 10 seconds. [V1.10d] End card teaser: a row of shapes snapping into a grid
(episode 2).

**QR q01-05** appears at [V1.10b], 10 seconds. Caption: "q01-05 · Challenge: a traffic light".

> Let's take stock. An animation is a stack of frames. Instead of drawing them, you describe the change, and that description is a program. In Manim, a scene's construct method is that description. Mobjects are the things you see, animations are how they change, and play turns animations into frames, adding time only when you ask.
>
> Here is a small challenge. This last code builds a traffic light, and lights the green lamp. Your job is to finish the cycle: switch green off, light yellow, wait, then light red. There is a hint in the comments, and everything you need is something you have already seen today.
>
> Next time, we zoom in on the nouns: where things go on screen, how to style them, and how to group them, plus one trap that catches almost everyone in their first week.
