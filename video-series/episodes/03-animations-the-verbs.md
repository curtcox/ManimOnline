# Episode 3 · Animations: the verbs

Published video: [Animations: The Verbs · Drawing with Code 3 (Manim)](https://www.youtube.com/watch?v=2gHw0OI5Ewg&list=PLXaiuWr3VAhk) · [series playlist](https://www.youtube.com/playlist?list=PLXaiuWr3VAhk)

| | |
|---|---|
| Track | Main |
| Target length | about 16 min (segment estimates; set final timing from the narration audio) |
| Builds on | Episodes 1–2 |
| QR codes | q03-01 … q03-06 |

## Learning goals

- Describe an animation as interpolation driven by a progress value from 0 to 1.
- Choose rate functions, and recognise linear, smooth and there-and-back motion.
- Use the common built-in animations, including entrances, emphasis and exits.
- Use `.animate`, and explain why `.animate.rotate` and `Rotate` differ.
- Combine animations with `AnimationGroup`, `LaggedStart` and `Succession`.
- Predict which object is on screen after `Transform` and `ReplacementTransform`.
- Choose run times and pauses that give viewers time to follow.

## Script

### 3.1 Cold open: two rotations · ≈ 0:50

**Visual.** [V3.1a] Two identical squares side by side: blue on the left, yellow on
the right. Both rotate a quarter turn at the same time. The yellow one turns like a
rigid tile. The blue one also ends a quarter turn round, but halfway through it is
visibly smaller, as if it breathed in. [V3.1b] Both rotate again, this time half a
turn. The yellow square spins. The blue square collapses to a point in the middle and
re-expands. Freeze on the collapsed frame. Text: "Same instruction?"

> Here are two squares, each told to rotate by a quarter turn. They both end up in the same place. But watch the blue one again. <break time="0.6s" /> Halfway through, it shrinks.
>
> Now let's ask both for half a turn. The yellow square spins around. The blue one does something much stranger: it collapses to a single point and turns itself inside out.
>
> Same ending, completely different journey. By the end of this episode, you will know exactly why, and the explanation reveals how every animation in Manim actually works.

### 3.2 What play really does · ≈ 2:00

**Visual.** [V3.2a] A dot on the left labelled "start", a ghost dot on the right
labelled "end". Below, a slider labelled "alpha" from 0 to 1. As alpha moves, the dot
moves proportionally. [V3.2b] The formula `point = start + alpha · (end − start)`
appears, with each symbol coloured to match the picture. [V3.2c] The dot becomes a
square, then a circle as the target. Each of the square's outline points gets its own
little dashed track to its partner on the circle; alpha drives all of them at once.
[V3.2d] A clock beside the slider: time from 0 to 1 second on top, alpha below, with
ticks every fifteenth of a second showing the frames that get sampled.

> Every animation in Manim, from a simple fade to a full morph, is built on one idea. You have a starting state, an ending state, and a number called alpha that runs from zero to one.
>
> When alpha is zero, you see the start. When alpha is one, you see the end. And for any alpha in between, Manim computes the state that far along the way.
>
> For a single point, "that far along" is simple. Take the start, and move a fraction alpha of the way toward the end. At one half, you are exactly in the middle. Mathematicians call this linear interpolation, and you will often hear it shortened to lerp.
>
> A shape is just many points, so to morph a square into a circle, Manim pairs every point on the square with a point on the circle, and moves each one a fraction alpha of the way along its own little path. All of them, at the same time, driven by the same alpha.
>
> And where does alpha come from? From the clock. A one-second animation sampled fifteen times a second, the rate ManimOnline uses for previews, takes fifteen snapshots, each with alpha a little larger. That is the whole engine. Starts, ends, and alpha.

### 3.3 Rate functions · ≈ 2:10

**Visual.** [V3.3a] Axes: horizontal "time, 0 to 1", vertical "alpha, 0 to 1". The
diagonal line `linear` draws itself. A dot rides along a track below, its position
read off the graph. [V3.3b] The S-shaped curve `smooth` draws; the dot now eases out,
cruises, and eases in. [V3.3c] `rush_into` (slow start, fast finish) and `rush_from`
(fast start, slow finish) draw, each with its own track dot. [V3.3d] `there_and_back`
draws as a hill: up to 1 at the midpoint and back to 0. Its dot goes out and returns.
[V3.3e] The q03-01 race: five labelled lanes, five dots, all reaching the far end at
the same moment except `there_and_back`, which returns home.

**On screen**

```python
animations.append(dot.animate(rate_func=rate).shift(RIGHT * 7))
...
self.play(*animations, run_time=3)
```

**QR q03-01** appears at [V3.3e], 8 seconds. Caption: "q03-01 · Rate function race".

> There is a small twist. Alpha does not have to grow steadily. Between the clock and alpha sits a rate function, which can bend time.
>
> If alpha simply equals time, that is the linear rate function. Steady speed from start to finish. It looks mechanical, like a conveyor belt, because nothing in the real world starts and stops instantly.
>
> Manim's default is called smooth. Its graph is an S-shaped curve: flat at the start, steep in the middle, flat again at the end. So objects ease out of rest, cruise, and ease into place. That gentle acceleration is a large part of why Manim animations feel calm.
>
> There are many more. Rush into starts slowly and finishes fast. Rush from does the opposite. And there and back is not even a one-way trip: alpha climbs to one at the halfway mark, and then returns to zero, so the motion undoes itself.
>
> This code races five dots, one per rate function, and they all start and finish together, except the one that comes home. You choose a rate function per animation by passing rate func. Try adding your own: any Python function that takes a number from zero to one and returns a number will do.

### 3.4 A tour of built-in animations · ≈ 1:50

**Visual.** [V3.4a] The q03-02 scene plays at normal speed, with each animation's
name appearing as a caption as it runs: Write, Create, GrowFromCenter,
FadeIn with shift, Indicate, Circumscribe, Rotate, FadeOut with shift. [V3.4b] A
two-column sorting animation: animation names fly into bins labelled "brings in",
"draws attention", "changes", "takes away".

**QR q03-02** appears at [V3.4a], 8 seconds. Caption: "q03-02 · Entrances, emphasis and exits".

> Manim comes with dozens of ready-made animations, and they fall into a few families.
>
> Some bring objects in. Create traces an outline. Write is designed for text, drawing strokes and then filling them. Grow from center expands an object from nothing. Fade in materialises it, and you can pass a shift so it drifts in from a direction.
>
> Some draw attention. Indicate briefly enlarges and recolours an object, then returns it to normal. Circumscribe traces a shape around it, like a teacher circling something on the board.
>
> Some change an object: Rotate, Transform, and many more.
>
> And some take objects away. Fade out and Uncreate remove the object from the scene when they finish, so you do not have to. Not every exit works that way, though: Shrink to center leaves a zero-sized object behind, still in the scene, invisible but present.
>
> Scan this one and read the code alongside the animation. It is almost a dictionary: one line, one effect.

### 3.5 The animate builder, and the shrinking square · ≈ 2:30

**Visual.** [V3.5a] Code: `square.animate.shift(RIGHT * 2).scale(0.5)`. Diagram:
the live square on the left; a ghost "target" copy on the right produced by applying
`shift` and `scale` instantly; then an animation interpolating from one to the other.
[V3.5b] Back to the cold-open blue square. Its four corners are marked with dots. The
target, a quarter turn round, appears as a ghost. Dashed straight lines connect each
corner to where it must end up. [V3.5c] Alpha runs. Each corner slides along its
straight dashed line; at alpha = 0.5 the corners are at the midpoints of the dashed
lines, which form a smaller square; a measurement shows it is about 71 percent of the
original width. [V3.5d] The half turn: each corner's target is the opposite corner,
and every dashed line passes through the centre. At alpha = 0.5 all four corners
meet at the centre. [V3.5e] The yellow square with `Rotate`: its corners travel
around circular arcs instead.

**On screen**

```python
self.play(left.animate.rotate(PI / 2), Rotate(right, PI / 2), run_time=3)
self.play(left.animate.rotate(PI), Rotate(right, PI), run_time=3)
```

**QR q03-03** appears at [V3.5d], 8 seconds. Caption: "q03-03 · Two kinds of rotation".

> You have already met the most flexible animation of all: the word animate. Write square dot animate, followed by any chain of methods, and Manim does something clever.
>
> It makes a copy of the square, applies those methods to the copy instantly, and uses the result as the target. Then it builds an animation from the current square to that target. Any method that changes a mobject can become an animation this way, which is why animate is everywhere.
>
> Now we can solve the mystery. The blue square was rotated with animate. So Manim worked out the target, the square turned a quarter turn, and then did what every animation does: it moved each point in a straight line from where it starts to where it ends.
>
> Follow one corner. It does not travel around a circle. It cuts straight across, like a shortcut. Do that with all four corners, and halfway through they form a smaller square, about seventy one percent of the size.
>
> For a half turn it gets more dramatic. Every corner's destination is the opposite corner, and the straight line between opposite corners goes right through the centre. So at the halfway point, all four corners meet in the middle, and the square vanishes for an instant.
>
> The yellow square used Rotate, an animation that knows it is a rotation. It doesn't interpolate between a start and an end; at every moment it turns the original by a fraction of the angle. Every corner travels on a circle, and the square stays rigid.
>
> So the rule is: animate is perfect for moving, scaling and recolouring. When you mean "spin", reach for Rotate.

### 3.6 Many things at once · ≈ 2:20

**Visual.** [V3.6a] A single `self.play(a, b, c)` call; three timeline bars start
and end together. [V3.6b] The q03-04 scene: three balls grow together under the label
`AnimationGroup`; the label morphs to `LaggedStart` and the balls hop up one after
another, overlapping; it morphs to `Succession` and the balls drop one at a time with
no overlap. [V3.6c] Under each segment, a timeline diagram: three bars stacked
together; three bars offset by half a bar (labelled `lag_ratio=0.5`); three bars end
to end. [V3.6d] The q03-05 wave: sixteen bars rise and fall in sequence with
`there_and_back`, then drop away one after another.

**QR q03-04** appears at [V3.6b], 8 seconds. Caption: "q03-04 · AnimationGroup, LaggedStart, Succession".
**QR q03-05** appears at [V3.6d], 8 seconds. Caption: "q03-05 · A lagged wave".

> Give play several animations, and they run at the same time. That covers most needs. But sometimes you want more control over timing, and there are three tools for that.
>
> Animation group bundles animations together so they can be treated as one, and by default they all start together.
>
> Lagged start begins each animation a little after the previous one. How much later is controlled by lag ratio. A lag ratio of zero point five means each one starts when the previous one is halfway done, so they overlap, like a ripple.
>
> Succession plays them strictly one after another. Each waits for the previous one to finish.
>
> Lagged starts are behind a lot of the most satisfying motion in math animations. In this second example, sixteen bars each stretch up and back down with the there-and-back rate function, and a small lag turns sixteen identical motions into a wave.

### 3.7 Who is on screen after a Transform? · ≈ 2:00

**Visual.** [V3.7a] q03-06, left half: square `a` with its sticky note; circle `b`
offstage with its note. `Transform(a, b)`: the square becomes circle-shaped, but the
note on the visible circle still says `a`; `b` stays offstage. [V3.7b] Right half:
square `c` and circle `d`. `ReplacementTransform(c, d)`: the square becomes the
circle, and at the end the visible circle carries the note `d`; `c` is gone from the
stage. [V3.7c] Both visible circles slide down: on the left this is `a.animate`, on the
right `d.animate`. Code lines light up as they play.

**On screen**

```python
self.play(Transform(a, b), ReplacementTransform(c, d))
# On the left, the circle on screen is still named a. On the right, it is d.
self.play(a.animate.shift(DOWN * 1.5), d.animate.shift(DOWN * 1.5))
```

**QR q03-06** appears at [V3.7c], 8 seconds. Caption: "q03-06 · Transform or ReplacementTransform?".

> In episode one, I said that Transform makes the square circle-shaped, and that the circle is only used as a target. Here is why that matters.
>
> After Transform a into b, the thing on screen looks like b, but it is still the object named a. The object named b was never added to the scene. So if you later want to move what you see, you must animate a.
>
> That can feel backwards, so Manim offers Replacement transform. After Replacement transform c into d, the object c is removed from the scene, and d takes its place. The circle on screen really is d.
>
> Neither is right or wrong. Use Transform when you want to keep talking about the same object as it changes shape. Use Replacement transform when you would rather keep using the name of the new thing. The trouble only starts when you forget which one you used, and animate an object that is not on screen.

### 3.8 Choosing how long things take · ≈ 1:50

**Visual.** [V3.8a] The same reveal of a formula played three times: at 0.3 seconds
(too fast; a stopwatch flashes red), at 1 second, and at 4 seconds (too slow; the
stopwatch yawns). [V3.8b] A timeline of a short explanation: animation blocks in blue,
narration sentences in grey above them, and `wait` gaps in white. Blocks stretch and
gaps grow until each animation sits under its sentence. [V3.8c] A checklist: "big
changes: slower", "small changes: faster", "new text: time to read", "after a reveal:
a pause".

> Knowing how to animate is one thing. Knowing how long an animation should take is a craft, and it's worth a minute.
>
> The default of one second is a good starting point, but a viewer needs more time for a big change than a small one. A dot sliding a short distance can be quick. A whole equation rearranging itself, or a grid bending into a new shape, deserves two or three seconds, because the viewer is trying to follow several things at once.
>
> New text needs time to be read, and the time grows with its length. If something appears and vanishes before it can be read, it might as well not have appeared.
>
> And pauses are not wasted time. A short wait after an important reveal gives the viewer a moment to think, "oh, I see". The most common mistake in first animations isn't anything technical. It's simply going too fast.
>
> If you plan to add narration, write the words first, and time the animations to them. That's how this series is made: every play and wait is matched to a sentence.

### 3.9 Recap · ≈ 0:50

**Visual.** [V3.9a] Summary board: the alpha slider; the five rate-function curves
as small icons; the four families of animations; the corner tracks of the shrinking
square next to the arcs of `Rotate`; the three timing diagrams. [V3.9b] QR wall:
q03-01 to q03-06 for 10 seconds. [V3.9c] Teaser: the corner dots of the square from
segment 3.5 multiply into many dots around a circle, with little handles sprouting
from them (episode 4).

> Every animation is a start, an end, and alpha running from zero to one, bent by a rate function. Animate turns any change into an animation, by moving every point in a straight line toward the target. That is perfect for most changes, and exactly wrong for rotations, which is what Rotate is for. And groups, lagged starts and successions arrange animations in time.
>
> But there was a phrase we used casually today: "every point on the shape". What points? How many? And how does a square, with four corners, morph into a circle, which has none? That is next time, and it is one of my favourite ideas in all of computer graphics.
