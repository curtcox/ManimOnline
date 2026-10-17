# Episode 6 · Things that change

| | |
|---|---|
| Track | Main |
| Target length | about 16 min (segment estimates; set final timing from the narration audio) |
| Builds on | Episodes 1–5 |
| QR codes | q06-01 … q06-05 |

## Learning goals

- Attach updaters that run every frame, and remove them.
- Write time-based updaters with `dt` that are independent of frame rate.
- Drive several objects from one `ValueTracker`, and display it with `DecimalNumber`.
- Rebuild objects every frame with `always_redraw`, and trace paths with `TracedPath`.
- Avoid common updater surprises: updaters that override animations, and update order.
- Choose between updaters, trackers, `always_redraw`, `become` and plain animations.

## Script

### 6.1 Cold open: a circle unrolls into a wave · ≈ 0:50

**Visual.** [V6.1a] q06-05 at full screen: a dot circles a blue circle on the left.
A dashed line links it horizontally to a second dot on the right, which moves steadily
rightward and rises and falls with the first. Behind the second dot, a yellow sine wave
grows. [V6.1b] Freeze. Five elements glow in turn: the radius line, the circling dot,
the dashed link, the wave dot, the trail. A counter: "5 moving parts, 1 number".

> Here is one of the loveliest ideas in trigonometry: a point going round a circle, casting its height onto a wave.
>
> Count the moving parts. The radius. The dot on the circle. The dashed link. The dot on the wave. And the wave itself, growing behind it. Five things, all moving in perfect sync.
>
> You could try to animate each one separately and hope they line up. But there is a far better way, and it's the subject of this episode. Every one of those five parts is driven by a single number.

### 6.2 The problem with telling everything what to do · ≈ 1:20

**Visual.** [V6.2a] A dot with a text label above it. The dot moves right; the label
stays behind. Caption: "only the dot was animated". [V6.2b] Second attempt: code shows
two animations in one `play`, the dot's and the label's, and they move together.
[V6.2c] A third motion, a rotation of the dot about the origin, is added to the code;
the label, animated with a straight `shift`, cuts across the circle instead of following
the arc, and separates from the dot. A red "✗" appears.

> Let's start small. A dot, and a label above it. Move the dot, and the label stays behind, because nobody told it to move.
>
> We could animate the label too, with the same shift. That works, for this one motion. But now every time the dot moves, you have to remember to move the label as well, and work out exactly how. If the dot travels along an arc, a straight shift for the label won't keep up.
>
> What we really want to say is not "move the label to here". It is a relationship. "The label is always just above the dot." And Manim has a way to say exactly that.

### 6.3 Updaters · ≈ 2:00

**Visual.** [V6.3a] A film strip of frames moves left to right. Between frames, a
small gear icon labelled "updaters" turns, and an arrow shows it adjusting the label
before each frame is captured. [V6.3b] q06-01: the label follows the dot right, then
up, then all the way around a circle about the origin. [V6.3c] `label.clear_updaters()`
is highlighted; the dot drops to the bottom and the label stays where it was.
[V6.3d] Inset explaining `lambda m: m.next_to(dot, UP)`: "m" is circled, with an arrow
to the label: "the object being updated".

**On screen**

```python
label.add_updater(lambda m: m.next_to(dot, UP))   # runs once per frame
...
label.clear_updaters()
```

**QR q06-01** appears at [V6.3b], 8 seconds. Caption: "q06-01 · A label that follows".

> An updater is a function that you attach to a mobject. Then, every single frame, before the frame is captured, Manim calls it.
>
> Here, the updater says: put m next to the dot, above it. And m is whatever object the updater is attached to, in this case the label. The word lambda is just Python's way of writing a small function in one line: it takes m, and does this to it.
>
> Now we only animate the dot. It moves right, the label follows. It moves up, the label follows. It swings around a full circle, and every frame the updater puts the label back above it. We never mention the label in those animations at all.
>
> When you want the relationship to end, call clear updaters. The label stops following, and the next time the dot moves, the label stays put.
>
> This is a shift in how you think about a scene. Instead of scripting every object's motion, you script a few, and describe how the rest relate to them.

### 6.4 Updaters that know what time it is · ≈ 1:50

**Visual.** [V6.4a] q06-02: two wheels spin, the yellow one twice as fast as the blue.
After four seconds the yellow wheel stops; the blue keeps turning. [V6.4b] Diagram: a
timeline with frames at 15 per second on top, and at 60 per second below. Each frame
carries a small `dt` value: "1/15 s" above, "1/60 s" below. Both rows' wheels end at
the same angle after one second. [V6.4c] The formula `angle per frame = speed × dt`
with units shown.

**On screen**

```python
slow.add_updater(lambda m, dt: m.rotate(-dt * PI / 2))   # a quarter turn per second
fast.add_updater(lambda m, dt: m.rotate(-dt * PI))       # half a turn per second
```

**QR q06-02** appears at [V6.4a], 8 seconds. Caption: "q06-02 · Time-based updaters".

> Some things should change by themselves, as time passes. A spinning wheel. A ticking clock. For those, an updater can ask for a second argument, d t, the amount of time since the last frame.
>
> Here, each wheel rotates by its speed times d t every frame. So the slow one turns a quarter turn per second, and the fast one half a turn per second. And these wheels keep turning even during a plain wait, when no animation is playing at all.
>
> Why multiply by d t, instead of just rotating a fixed amount each frame? Because frame rates differ. ManimOnline previews at fifteen frames per second. A finished video might use sixty. With d t, each frame turns the wheel by the right amount for the time that has actually passed, and after one second, both versions have turned exactly as far. Your scene describes motion in seconds, not in frames, and looks the same at any frame rate.

### 6.5 A number you can animate · ≈ 2:10

**Visual.** [V6.5a] An empty frame; a small box labelled "ValueTracker: 0" floats
in the corner, faintly, as if invisible. [V6.5b] q06-03: a number line from 0 to 10;
a yellow pointer above it; a decimal readout above the pointer. As the tracker's box
counts to 7.5, the pointer glides and the readout counts in step. [V6.5c] Wires drawn
from the tracker's box to the pointer and to the readout, labelled with their updaters.
[V6.5d] The tracker goes back to 2, then `increment_value(5)` takes it to 7.

**On screen**

```python
x = ValueTracker(0)
pointer.add_updater(lambda m: m.next_to(line.n2p(x.get_value()), UP, buff=0.1))
readout.add_updater(lambda m: m.set_value(x.get_value()).next_to(pointer, UP))
self.play(x.animate.set_value(7.5), run_time=3)
```

**QR q06-03** appears at [V6.5b], 8 seconds. Caption: "q06-03 · ValueTracker and DecimalNumber".

> Now the key ingredient. A value tracker is a mobject that holds a single number, and is never drawn. That sounds useless, until you realise that because it is a mobject, you can animate it like anything else.
>
> x dot animate dot set value seven point five smoothly changes the number from zero to seven point five over three seconds, using every idea from episode three: alpha, interpolation and rate functions.
>
> Then other objects read the number in their updaters. The pointer asks the number line where seven point five lives, using n to p, short for number to point, and sits just above it. The decimal number readout sets its displayed value to the tracker's value every frame, and parks itself above the pointer.
>
> So one animation, of one invisible number, moves the pointer and the readout together. That's the pattern you'll use over and over: decide which numbers your scene is really about, store them in value trackers, and let everything else follow.

### 6.6 Redrawing from scratch · ≈ 1:50

**Visual.** [V6.6a] q06-04: a grey circle; a yellow right triangle inside it with
one corner at the centre, one on the horizontal axis, one on the circle. As the angle
grows, the triangle reshapes; the labels `cos θ` (blue, under the base) and `sin θ`
(green, beside the vertical side) follow their sides. [V6.6b] A film strip showing
three consecutive frames with three different triangles. A small trash can collects
each old triangle as a new one is built. Caption: "always_redraw: build a new one every
frame".

**On screen**

```python
triangle = always_redraw(lambda: Polygon(ORIGIN, foot(), tip(), color=YELLOW, fill_opacity=0.3))
cos_label = always_redraw(lambda: MathTex(r"\cos\theta", color=BLUE).next_to(Line(ORIGIN, foot()), DOWN))
```

**QR q06-04** appears at [V6.6a], 8 seconds. Caption: "q06-04 · always_redraw".

> Sometimes it's easier to rebuild an object than to adjust it. This triangle has a corner on the circle, and its shape depends on the angle in a way that no single shift or scale could describe.
>
> Always redraw takes a function that builds the object from scratch. Every frame, Manim calls that function again and swaps in the brand new result. So the triangle is rebuilt from the current angle, sixty times a second in a finished video, and the cosine and sine labels are rebuilt beside its sides.
>
> It's the most flexible tool in this episode, and also the most expensive, because it creates new objects every frame. For a handful of shapes that's no problem at all. If you find yourself redrawing hundreds of objects, look for an updater that adjusts them instead.

### 6.7 Putting it together · ≈ 1:40

**Visual.** [V6.7a] The q06-05 code in a panel on the left, the animation on the
right. As each `always_redraw` line is highlighted, the corresponding part glows.
[V6.7b] `TracedPath(on_wave, ...)` is highlighted; the yellow trail grows behind the
wave dot. [V6.7c] The single line `self.play(t.animate.set_value(TAU), run_time=6,
rate_func=linear)` is highlighted in yellow, and a bracket links it to every moving part.

**QR q06-05** appears at [V6.7a], 10 seconds. Caption: "q06-05 · From a circle to a sine wave".

> Now the opening scene makes sense. There is one value tracker, t, the angle. Two little functions turn t into positions: one on the circle, one on the wave. The radius, the dashed link and both dots are always redrawn from those positions.
>
> The wave is a traced path. It's given a function that says where the wave dot is, and every frame it adds that point to a growing curve. So the wave isn't calculated in advance. It's literally drawn by the moving point.
>
> And the whole scene is driven by one line: animate t from zero to two pi over six seconds, at a steady linear rate. One number changes, and five things move.

### 6.8 Two surprises worth knowing · ≈ 1:20

**Visual.** [V6.8a] A spinning wheel with a dt updater. `wheel.animate.shift(RIGHT * 4)`
is played; the wheel glides right and keeps spinning, and a gear icon beside it keeps
turning: "updaters keep running during animations". [V6.8b] The dot and its label from
q06-01. `label.animate.shift(DOWN * 2)` is played and the label doesn't budge; a red "✗".
`label.animate.set_color(RED)` turns it red; a green "✓". [V6.8c] Two objects with
updaters, A reading from B. A frame-by-frame diagram shows A using B's position from
before B's updater ran: A lags one frame behind. Caption: "order matters".

> Two things tend to surprise people.
>
> First: updaters keep running while an animation plays. Manim even applies them to the animation's starting and ending copies, so a spinning wheel keeps spinning while it glides across the screen. But if an updater decides where an object is, animating its position does nothing: the updater puts it back, every frame. Animating its colour works, because the updater never touches colour. To move a follower, move what it follows, or clear its updater first.
>
> Second: updaters run in order. If one object's updater reads another object that hasn't been updated yet this frame, it sees last frame's position, and lags one frame behind. Usually that's invisible. When it isn't, have both read the same value tracker directly, rather than reading each other.

### 6.9 Choosing the right tool · ≈ 2:00

**Visual.** [V6.9a] A decision tree drawn left to right. Root: "Something should
change over time". Branch 1: "It follows another object" → `add_updater` (gear icon).
Branch 2: "It changes at a steady rate by itself" → `add_updater` with `dt` (stopwatch).
Branch 3: "Several things depend on one quantity" → `ValueTracker` (invisible box).
Branch 4: "Its shape must be rebuilt from scratch" → `always_redraw` (recycling icon).
Branch 5: "It should leave a trail" → `TracedPath` (pen). [V6.9b] Under
`always_redraw`, a small diagram reveals that it is an updater calling `become` on the
same object every frame. [V6.9c] A final branch, "It changes once, at a known moment"
→ an ordinary `self.play(...)`, highlighted green as "the simplest option".

**On screen**

```python
triangle = Polygon(ORIGIN, foot(), tip())
triangle.add_updater(lambda m: m.become(Polygon(ORIGIN, foot(), tip())))   # what always_redraw does
```

> With this many tools, it helps to have a way to choose.
>
> If an object should follow another, attach an updater that places it relative to the leader. If it should change steadily by itself, like a spinning wheel, use an updater with d t. If several objects depend on the same quantity, put that quantity in a value tracker, and let each object read it. If an object's very shape depends on that quantity, so that it's easier to rebuild than to adjust, use always redraw. And if you want the history of a moving point, use a traced path.
>
> It's worth knowing that always redraw isn't magic. It's an updater that calls become every frame: become makes an object take on the shape and style of another one, while staying the same object, so it stays in the scene and keeps its name. You can write that updater yourself whenever you need a variation.
>
> And finally, the most important option: if something changes once, at a moment you know in advance, don't use an updater at all. A plain animation is simpler to read and easier to change. Updaters are for relationships that must hold all the time.

### 6.10 Recap · ≈ 0:50

**Visual.** [V6.10a] Summary board: a gear (updater), a stopwatch (dt), an invisible
box with wires (ValueTracker), a recycling icon (always_redraw), a pen trail
(TracedPath). [V6.10b] QR wall: q06-01 to q06-05 for 10 seconds. [V6.10c] Teaser:
Riemann rectangles narrowing under a curve (episode 7).

> Updaters describe relationships that hold every frame. With d t, they describe change over time, independent of frame rate. Value trackers hold the numbers that a scene is really about, so animating one number can move everything. Always redraw rebuilds objects whose shape depends on those numbers. And traced paths draw the history of a moving point.
>
> Next time, we bring all of this to the place it shines brightest: graphs, areas under curves, and the slope of a tangent line.
