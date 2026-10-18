# Episode 4 · What is a shape, really?

Published video: [What Is a Shape, Really? Bézier Curves · Drawing with Code 4 (Manim)](https://www.youtube.com/watch?v=wLi02QRgJ3k&list=PLXaiuWr3VAhk) · [series playlist](https://www.youtube.com/playlist?list=PLXaiuWr3VAhk)

| | |
|---|---|
| Track | Main |
| Target length | about 16 min (segment estimates; set final timing from the narration audio) |
| Builds on | Episodes 1–3 (interpolation and alpha from episode 3) |
| QR codes | q04-01 … q04-05 |

## Learning goals

- Build a cubic Bézier curve from repeated linear interpolation (de Casteljau).
- Explain anchors and handles, and how curves join smoothly.
- Explain why cubic curves are the standard choice.
- Describe a Manim VMobject as a list of points in groups of four.
- Explain why morphs need matching point counts, and how subdivision provides them.
- Use `path_arc`, `CubicBezier` and `set_points_smoothly`.

## Script

### 4.1 Cold open: how do you store a circle? · ≈ 1:00

**Visual.** [V4.1a] A perfect-looking circle. The camera zooms in on its edge, ten
times, a hundred times, a thousand times. It stays perfectly smooth. [V4.1b] Beside
it, a "circle" made of 24 straight segments. The same zoom reveals corners almost
immediately. [V4.1c] Text: "A computer has finite memory. A circle has infinitely
many points." [V4.1d] Back on the smooth circle, eight small yellow dots appear evenly
around it.

> Here is a circle. Let's zoom in on its edge. Ten times. A hundred times. A thousand. It stays perfectly smooth.
>
> That should be a little puzzling. A circle contains infinitely many points, and a computer has finite memory. If you approximate the circle with straight segments, zooming in gives the game away almost immediately.
>
> So how is this circle stored? The answer is: as eight pieces of a special kind of curve, each described by just four points. And those same curves are behind every outline you have seen in this series, behind the letters in most fonts, and behind almost every drawing tool on your computer.

### 4.2 Lerp, then lerp again · ≈ 2:30

**Visual.** [V4.2a] Two grey points, `P0` and `P1`. A yellow dot moves between them
as `t` goes from 0 to 1, leaving a straight yellow trail. Label: "one lerp: a line".
[V4.2b] Three points, `P0`, `P1`, `P2`. Two blue dots ride the two grey segments, both
at fraction `t`. A blue segment joins them. A green dot rides the blue segment, also
at `t`. The green dot leaves a curved trail: a parabola-like arc. Label: "lerp of
lerps: a quadratic curve". [V4.2c] Four points: the full q04-01 construction. Three
blue dots, two green dots, one yellow dot, which traces the cubic. [V4.2d] The curve
completes; the scaffolding fades, leaving the curve and its four grey control points.

**QR q04-01** appears at [V4.2c], 10 seconds. Caption: "q04-01 · Building a cubic Bezier curve".

> To build that kind of curve, we need only one tool, and you met it last episode: linear interpolation. Lerp.
>
> Take two points. Lerp between them, letting t run from zero to one, and you trace a straight line. Nothing surprising yet.
>
> Now take three points. Lerp along the first segment, and along the second segment, both with the same t. That gives two moving points. Now lerp between those two, again with the same t. This final point traces something new: a smooth curve that starts at the first point, ends at the last, and bends toward the middle point without ever touching it.
>
> Do it once more, with four points. Three lerps on the first level, two on the second, and one at the top. The single point that survives traces a cubic Bézier curve.
>
> This construction is named after Paul de Casteljau, who worked it out at the car maker Citroën in the late nineteen fifties. Pierre Bézier, at Renault, popularised the same curves for designing car bodies, and his name is the one that stuck.
>
> Scan this code to play with the construction yourself. The four control points are in a list called p at the top of the scene. Drag them around by editing the numbers, and watch the curve follow.

### 4.3 Anchors and handles · ≈ 2:00

**Visual.** [V4.3a] A single cubic curve with its four points labelled: two
**anchors** (the curve's ends, drawn as larger dots) and two **handles** (smaller
dots joined to their anchors by thin lines). [V4.3b] One handle moves outward; the
curve bulges more in that direction. It swings around; the curve's starting direction
swings with it. [V4.3c] Two curves meet at a shared anchor. When their handles are
not in a straight line, there is a visible corner. The handles rotate into alignment,
and the corner disappears. [V4.3d] The circle from the cold open, now with all its
anchors and handles shown, exactly as q04-02 draws them; caption "8 cubic curves, 32
points".

**QR q04-02** appears at [V4.3d], 8 seconds. Caption: "q04-02 · The control points inside a circle".

> The four points have different jobs. The first and last are anchors: the curve really passes through them. The middle two are handles. The curve never touches them, but it leaves the first anchor heading straight toward the first handle, and arrives at the last anchor coming from the direction of the second handle. Pull a handle further away, and the curve leans harder in that direction.
>
> That is what makes these curves so useful for drawing. You can chain them, end to end, so that one curve's last anchor is the next one's first. And if the handles on either side of that shared anchor line up, the join is smooth: no corner at all.
>
> Now we can look inside the circle. Manim builds it from eight cubic pieces, joined smoothly at eight anchors. That is thirty two points in total, counting each piece's four. The pieces are not exactly circular. But their error is far smaller than a pixel, which is why the zoom in the opening never revealed them.

### 4.4 Why cubic? · ≈ 1:50

**Visual.** [V4.4a] A quadratic curve with its single handle. The handle moves; both
ends of the curve swing together, because one handle sets both end directions. An
attempt to make an S shape fails: the curve can only bend one way. [V4.4b] A cubic
with two handles: each end's direction changes independently, and an S curve forms
easily. [V4.4c] A fifth-degree curve with six control points; moving one point ripples
the whole curve. Caption: "more points, less local control". [V4.4d] A chain of cubics
with one handle moved: only the neighbouring piece changes. [V4.4e] A small sidebar:
a font glyph made of quadratic pieces (TrueType) is converted into cubic pieces; the
outline does not change.

> Why four points? Why not three, or ten?
>
> With three points, the quadratic curve, there's only one handle, and it controls the direction at both ends at once. You can't choose them separately, and you can't make an S shape: a quadratic curve only ever bends one way.
>
> Four points, the cubic, is the smallest number that lets you set each end's direction independently. That's exactly what you need to join curves smoothly, and it's enough to make S shapes within a single piece.
>
> You could go higher. Five, six, ten control points. But higher-degree curves are harder to control: move one point, and the whole curve shifts. It's far easier to chain many cubic pieces, where moving a handle only changes its own piece and its neighbour.
>
> That's why cubic curves became the standard of design software. Some font formats use quadratic pieces instead, but every quadratic curve can be rewritten exactly as a cubic, so when Manim meets one, it converts it and carries on.

### 4.5 Every outline is a list of points · ≈ 1:40

**Visual.** [V4.5a] A Python list of points printed vertically beside a square,
grouped in fours with brackets: anchor, handle, handle, anchor. As each group is
highlighted, its edge of the square lights up. Label: "Square: 4 curves, 16 points".
[V4.5b] The handles of a straight edge sit on the edge itself, a third and two thirds
of the way along. [V4.5c] Other shapes flash by with their counts: triangle (3
curves), star (10 curves), the letter "S" from a font (many curves). [V4.5d] Text:
"VMobject = vectorised mobject = list of cubic curves".

> In Manim, a shape made of outlines is called a V mobject, short for vectorised mobject. And under the hood, every V mobject is just a list of points, read in groups of four: anchor, handle, handle, anchor.
>
> Even a straight line is stored this way. Put both handles on the line itself, and the cubic curve is perfectly straight. So a square is four cubic curves, sixteen points, which happen to be straight.
>
> This is a wonderfully simple representation. Squares, circles, stars, arrows, graphs of functions and every letter of every formula are all the same kind of thing: a list of cubic curves. And that uniformity is what makes the next trick possible.

### 4.6 How a square becomes a circle · ≈ 2:40

**Visual.** [V4.6a] q04-03, first beat: a blue square with 4 anchor dots on the
left, a yellow circle with 8 anchor dots on the right. A counter under each: "16
points", "32 points". [V4.6b] An attempt to pair them: lines from square points to
circle points, but half of the circle's points have no partner; they flash red.
[V4.6c] Each straight edge of the square is split at its midpoint. Zoom into one edge:
de Casteljau at t = 0.5 splits the one cubic into two, each with its own handles.
New anchor dots pop in at the midpoints. Counter: "32 points". [V4.6d] Now every point
has a partner. Dashed straight tracks join each square anchor to its circle anchor,
and the transform plays along them. The anchor dots travel along their tracks.

**On screen**

```python
# Four curves cannot pair up with eight, so the square's curves are split in half.
square.align_points(circle)
```

**QR q04-03** appears at [V4.6d], 10 seconds. Caption: "q04-03 · Matching points before a morph".

> Let's return to the question from last episode. To morph one shape into another, Manim pairs up their points and moves each one in a straight line. But a square has sixteen points and the circle has thirty two. Half of the circle's points would have no partner.
>
> The fix is beautiful. Remember the de Casteljau construction? Stop it at t equals one half, and look at the scaffolding. The points along the way are exactly the control points of two smaller cubic curves, which together trace the original curve perfectly. So you can split any cubic curve into two without changing its shape at all.
>
> Manim splits the square's four curves into eight. The square looks exactly the same, but it now has thirty two points, and every point has a partner on the circle.
>
> Then the morph is exactly what we saw in episode three: each point travels in a straight line, driven by alpha. The anchors at the square's corners glide inward, and the new anchors at the middle of each edge bow outward, and the whole outline relaxes into a circle.
>
> This example calls align points directly so you can see the new dots appear. Normally you never need to. Every transform does this matching automatically before it starts.

### 4.7 Not every path is straight · ≈ 1:40

**Visual.** [V4.7a] Two shapes far apart. A straight-path transform between them:
dashed straight tracks. [V4.7b] The same transform with `path_arc=PI / 2`: the tracks
bend into arcs and the shape swings across. [V4.7c] q04-04: square → circle →
triangle → star, each swinging along an arc; finally the star swings back along a
half-circle arc (`path_arc=-PI`) to become the square. [V4.7d] Small inset: the same
corner pairing done badly, where a shape is paired starting from the "wrong" point;
the outline twists through itself. Caption: "pairing order matters".

**QR q04-04** appears at [V4.7c], 8 seconds. Caption: "q04-04 · Morphing along arcs".

> Straight lines are only the default. Pass path arc to a transform, and every point travels along an arc instead, turning by that angle as it goes. A quarter turn gives a gentle swing. A negative angle swings the other way.
>
> This also tells you something about the morphs that look odd. Because the pairing goes in order around the outline, two shapes that start their outlines in different places, or travel in opposite directions, can make points cross over each other mid-morph. The outline appears to twist. When you see that, the fix is usually to rotate or reverse one of the shapes so their starting points line up.

### 4.8 Drawing a curve a piece at a time · ≈ 1:40

**Visual.** [V4.8a] q04-05: grey guide lines to two handles; the yellow cubic draws
from left to right. [V4.8b] A magnified view of the moving pen tip: at each frame the
drawn part is exactly the curve cut at some t, again by de Casteljau. [V4.8c] The blue
smooth path through five dots draws itself. Its anchors and handles are revealed
briefly: four cubic pieces, joined smoothly.

**On screen**

```python
curve = CubicBezier(start, handle1, handle2, end, color=YELLOW, stroke_width=8)
...
path.set_points_smoothly([LEFT * 5 + DOWN * 2, LEFT * 2.5 + DOWN, DOWN * 3, RIGHT * 2.5 + DOWN, RIGHT * 5 + DOWN * 2])
```

**QR q04-05** appears at [V4.8a], 10 seconds. Caption: "q04-05 · Draw your own curve".

> One more payoff. How does Create draw a curve, gradually, as if with a pen?
>
> At every frame, it shows only the first part of the outline: the curve cut off at some fraction of the way along. And cutting a cubic curve at any fraction is, once again, de Casteljau's construction. The same lerps that built the curve also let Manim draw it one sliver at a time.
>
> You can build curves yourself. Cubic Bézier takes exactly four points: anchor, handle, handle, anchor. And if you would rather just say "go through these points smoothly", a V mobject's set points smoothly method works out handles for you, so that the joins have no corners.
>
> The same machinery answers another question: where is the point halfway along this outline? Point from proportion measures along the curves and returns that point, and Move along path uses it to slide an object along any outline, a circle, a polygon, or a curve you drew yourself.
>
> Scan this code, move the handles around, and you will build your intuition for Bézier curves faster than any explanation can.

### 4.9 Recap · ≈ 1:00

**Visual.** [V4.9a] The lerp-of-lerps pyramid shrinks into a small icon. Around it,
icons for what it enables: a smooth circle (storage), aligned dots (morphing), a pen
tip (Create). [V4.9b] QR wall: q04-01 to q04-05 for 10 seconds. [V4.9c] Teaser:
the letters of "MANIM" revealed as outlines with anchors and handles, then filled
(episode 5).

> Let's put it together. A cubic Bézier curve is what you get when you lerp, and lerp again, and lerp once more. Anchors are where it goes; handles are how it leans. Chain these curves, and you can draw anything, so Manim stores every outline as a list of cubic curves in groups of four points. To morph two shapes, it splits curves until the counts match, then pairs points and moves them. And the very same construction lets Create draw a curve one sliver at a time.
>
> Next time, we put this to work on the most intricate outlines of all: letters, numbers and equations.
