# Episode 2 · Mobjects: the nouns

Published video: [Mobjects: The Nouns · Drawing with Code 2 (Manim)](https://www.youtube.com/watch?v=uNAZ8IUrWGg&list=PLXaiuWr3VAhk) · [series playlist](https://www.youtube.com/playlist?list=PLXaiuWr3VAhk)

| | |
|---|---|
| Track | Main |
| Target length | about 15 min (segment estimates; set final timing from the narration audio) |
| Builds on | Episode 1 |
| QR codes | q02-01 … q02-06 |

## Learning goals

- Place points with Manim's coordinate system and direction constants.
- Create common shapes and style their stroke, fill and opacity.
- Position objects absolutely, relatively and against the frame edge.
- Scale and rotate about chosen points, and query positions such as `get_top()`.
- Group objects, arrange them in rows and grids, and move groups as one.
- Recognise when two names refer to the same object, and when to `copy()`.
- Control drawing order with `z_index`.

## Script

### 2.1 Cold open: where is (3, −1)? · ≈ 0:50

**Visual.** [V2.1a] An empty black frame. A yellow dot appears somewhere right of
centre and slightly low. Text: "Where is this dot?" [V2.1b] A ruler slides in along
the bottom edge and a second ruler up the left edge, both unlabelled. [V2.1c] The
rulers dissolve into a full `NumberPlane` grid; the dot is revealed to sit at (3, −1),
and a label snaps next to it.

> Before you can animate something, you have to say where it is. So, quick question: where is this dot?
>
> You might say: a bit to the right, a little below the middle. That is how people describe positions. But a computer needs numbers, and numbers need a ruler.
>
> Manim's ruler is a grid laid over the frame. The centre of the screen is the origin. And this dot is three units to the right, and one unit down. Three, minus one.

### 2.2 Manim's coordinate plane · ≈ 1:50

**Visual.** [V2.2a] The grid stays. A double-headed arrow measures the frame height:
"8 units". Another measures the width: "about 14.2 units". [V2.2b] Four arrows of
length one grow out of the origin, labelled `UP`, `DOWN`, `LEFT`, `RIGHT`. Each label
expands to show its numbers, for example `RIGHT = [1, 0, 0]`. [V2.2c] Vector
arithmetic as motion: a dot starts at the origin, steps along `RIGHT` three times,
then along `DOWN` once; the expression `RIGHT * 3 + DOWN` builds up beside it.
[V2.2d] Diagonal constants `UR`, `UL`, `DR`, `DL` flash briefly at 45 degrees.
[V2.2e] Hint of depth: the plane tilts slightly to reveal a third axis coming toward
the viewer, labelled `OUT`, then tilts back flat.

> The frame is eight units tall. Its width depends on the shape of the video. For ordinary widescreen it works out to about fourteen point two units. So anything between minus seven and seven horizontally, and minus four and four vertically, is on screen.
>
> You could type coordinates as lists of numbers, but Manim gives you something friendlier: direction constants. UP is one unit up. RIGHT is one unit right. And because they are vectors, arrows with a length and a direction, you can do arithmetic with them.
>
> RIGHT times three is three units right. Add DOWN, and you arrive at three, minus one. Read it out loud and it sounds like directions to a friend's house: go right three, then down one. That is why Manim code so often reads like a description rather than a calculation.
>
> There are diagonal shortcuts too. U R means up and to the right, D L means down and to the left.
>
> You may have noticed each point actually has three numbers. The third is depth, pointing out of the screen. In flat scenes it is always zero, so you can ignore it until episode eight, where we will give it a job.

**QR q02-01** appears at the end of [V2.2c], 8 seconds. Caption: "q02-01 · Points on the coordinate plane".

> This code plots four points with labels written in exactly this style. Try adding a fifth.

### 2.3 A zoo of shapes · ≈ 1:20

**Visual.** [V2.3a] Shapes appear one by one in a loose grid, each with its
constructor call written underneath in small code type: `Circle()`, `Square()`,
`Rectangle(width=4, height=2)`, `Triangle()`, `RegularPolygon(6)`, `Star()`,
`Line(LEFT, RIGHT)`, `Arrow(LEFT, RIGHT)`, `Dot()`. [V2.3b] For `Circle()` and
`Square()`, a dimension line shows the defaults: radius 1, side length 2. [V2.3c] A
closing pan across the whole zoo.

> Manim comes with a whole zoo of shapes. Circles, squares, rectangles, triangles, regular polygons with as many sides as you like, stars, lines, arrows and dots.
>
> Every one of them has sensible defaults. A circle has radius one. A square has sides of length two. A dot is tiny. And all of them start out centred at the origin. Arguments let you override any of that: Circle with radius two, a square with side length three, a regular polygon with six sides.
>
> Under the hood, nearly every shape here is the same kind of thing: an outline made of curves. Episode four opens that box. For now, let's dress them up.

### 2.4 Stroke, fill and opacity · ≈ 1:40

**Visual.** [V2.4a] A large circle. Its outline is highlighted and labelled
"stroke"; its interior is highlighted and labelled "fill". [V2.4b] Four sliders
appear beside it: stroke colour, stroke width, fill colour, fill opacity. Each slider
moves and the circle responds. [V2.4c] The q02-02 row of four styled shapes draws in.
Code excerpts appear under each. [V2.4d] A chain diagram: `Square()` → `.set_fill(...)`
→ `.set_stroke(...)`, with a curved arrow showing that each call hands the same square
to the next.

**On screen**

```python
Circle().set_stroke(BLUE, width=8)                                  # outline only
Square().set_fill(GREEN, opacity=1).set_stroke(width=0)             # fill only
Triangle().set_fill(RED, opacity=0.4).set_stroke(YELLOW, width=4)   # both
```

**QR q02-02** appears at [V2.4c], 8 seconds. Caption: "q02-02 · Fill, stroke and opacity".

> Every shape has two separate layers of paint. The stroke is the outline: it has a colour and a width. The fill is the inside: it has a colour and an opacity, where zero is invisible and one is solid.
>
> By default, most shapes are outlines with an invisible fill. That is why the square in episode one was hollow until we gave it a fill opacity.
>
> Set fill paints the inside. Set stroke paints the outline. Set color paints both at once. You can use named colours like BLUE and YELLOW, or any hex code, like the orange in this example.
>
> And notice how these calls are chained, one after another: Square, dot set fill, dot set stroke. That works because each method changes the shape and then hands back the very same shape, so the next method can keep working on it. You will see this chaining style everywhere in Manim code.

### 2.5 Putting things in their place · ≈ 2:10

**Visual.** [V2.5a] The q02-03 scene plays in slow motion. For each step, the
method name appears large, with a one-word tag: `shift` "by", `move_to` "to",
`next_to` "beside", `to_corner` "edge", `align_to` "line up". [V2.5b] During `shift`,
a ghost of the old position remains and an arrow shows the offset. During `move_to`,
a crosshair marks the destination. [V2.5c] During `next_to`, dashed bounding boxes
appear around the square and the dot; the gap between them is measured and labelled
`buff=0.3`. [V2.5d] During `align_to`, a horizontal guide line extends from the dot's
top edge to the square's top edge.

**On screen**

```python
self.play(dot.animate.shift(RIGHT * 3))                # relative: move by an offset
self.play(dot.animate.move_to(UP * 2 + LEFT * 4))      # absolute: go to a point
self.play(dot.animate.next_to(box, DOWN, buff=0.3))    # beside another object
self.play(dot.animate.to_corner(UR))                   # against the edge of the frame
self.play(box.animate.align_to(dot, UP))               # line up one edge
```

**QR q02-03** appears at [V2.5a], 10 seconds. Caption: "q02-03 · shift, move_to, next_to, to_corner, align_to".

> Once you have a shape, you will spend a lot of time putting it somewhere. Manim gives you a handful of verbs for this, and choosing the right one makes code much easier to change later.
>
> Shift moves by an offset: wherever you are, go three units right. Move to goes to an absolute point: no matter where you started, end up here.
>
> Next to is the one you will use most. It places one object beside another, in a direction, with a small gap called the buffer. How does it know where "beside" is? Every mobject has an invisible bounding box, the smallest rectangle that contains it, and next to lines up those boxes. That is why labels stay neatly beside things no matter how big they are.
>
> To edge and to corner push an object against the frame, leaving a small margin. And align to lines up one edge of an object with the same edge of another.
>
> You will notice something new in these lines: dot animate. Putting animate in front of a method turns that change into an animation, so instead of jumping, the dot glides. It is so useful it gets a big part of next episode.
>
> A good rule of thumb: position things relative to each other whenever you can. If you place a label with next to, and later move the shape, the label's relationship to it is still written in your code.

### 2.6 Scale, rotate and measure · ≈ 1:40

**Visual.** [V2.6a] A blue square. `scale(2)` doubles it about its centre; a ghost
of the original stays inside. `rotate(PI / 4)` turns it into a diamond. [V2.6b] The
same square scales with `about_edge=DL`: its lower-left corner stays pinned (a red pin
icon) while the rest grows away from it. [V2.6c] Yellow dots pop onto the square at
`get_center()`, `get_top()`, `get_right()` and `get_corner(UR)`, each labelled with its
method name. A dimension line shows `width`. [V2.6d] A label uses those points:
`next_to` is shown as "a bounding-box point plus a buffer".

**On screen**

```python
square.scale(2)                      # twice as big, about its centre
square.rotate(PI / 4)                # angles are in radians: PI / 4 is 45 degrees
square.scale(0.5, about_edge=DL)     # keep the lower-left corner where it is
square.get_top()                     # the middle of the top edge, as a point
```

> Moving is only one kind of change. Scale makes an object bigger or smaller, and rotate turns it. Both happen around the object's centre unless you say otherwise, and you can pin a different spot with about point, or with about edge, which keeps one side or corner fixed while the rest grows away from it.
>
> Angles in Manim are measured in radians, so a full turn is two pi, and pi over four is forty five degrees. If you'd rather think in degrees, multiply by the constant DEGREES: forty five times DEGREES means exactly what it says.
>
> You can also ask an object where its parts are. Get center returns its middle. Get top, get bottom, get left and get right return the middle of each edge of its bounding box, and get corner returns a corner. And width and height tell you how big it is. These answers are ordinary points, so you can hand them to move to, or to a Line, or use them in arithmetic. In fact, next to is built from exactly these pieces: a point on one bounding box, a direction, and a buffer.

### 2.7 Groups · ≈ 1:50

**Visual.** [V2.7a] Twelve dots, coloured from blue to yellow, burst out from the
origin, all stacked in one spot. [V2.7b] They line up in a row (`arrange`), then
reflow into a three-row grid (`arrange_in_grid`). [V2.7c] The whole grid scales up and
tilts as one rigid piece. A dashed rectangle around the group shows that the group has
its own bounding box. [V2.7d] They snap into a vertical column against the left edge.
[V2.7e] Inset: the list comprehension that builds the dots, with `i / 11` highlighted
and a colour bar running from BLUE to YELLOW.

**QR q02-04** appears at [V2.7b], 8 seconds. Caption: "q02-04 · Groups, rows and grids".

> Often you want to treat several objects as one. That is what a V group is for. Put mobjects in a V group, and you can move, scale, rotate, colour and animate them all together.
>
> Groups can also organise their members. Arrange lines them up in a row, or a column, with even gaps. Arrange in grid lays them out in rows and columns.
>
> In this example, twelve dots are created with a single line of Python, a list comprehension, each with a colour a little further along the way from blue to yellow. They all start at the origin, stacked on top of each other, so at first you see only one. Then a single arrange spreads them out, and a single arrange in grid reflows them.
>
> And when we scale and rotate the group, every dot moves together, as if they were glued to a sheet of glass. The group is an object in its own right, with its own centre and its own bounding box.

### 2.8 The copy trap · ≈ 1:50

**Visual.** [V2.8a] A blue square on stage. Beside it, a sticky note with the
letter `a` written on it is attached to the square by a string. [V2.8b] The line
`b = a` appears; a second sticky note `b` attaches to the same square. [V2.8c] The
line `c = a.copy()` appears; a second square pops out of the first and slides right,
with sticky note `c` attached. [V2.8d] q02-05 plays: `c` moves right and turns green.
Then `b.animate.set_color(RED)` turns the original square red, and the `a` note
wiggles to emphasise that `a` changed too.

**On screen**

```python
b = a            # a second name for the same square
c = a.copy()     # a genuinely new square
```

**QR q02-05** appears at [V2.8d], 8 seconds. Caption: "q02-05 · The copy trap".

> Now, the trap I promised. Here is a square called a. Suppose we write b equals a. How many squares are there?
>
> <break time="0.8s" /> Just one. In Python, a name is like a sticky note attached to an object. Writing b equals a does not build a second square. It sticks a second note on the same one.
>
> So when we turn b red, a turns red too, because a and b are two labels for one square. This surprises almost everyone the first time, and it can cause some very confusing animations.
>
> When you really want a second, independent object, ask for one: a dot copy. Copy builds a brand new square with the same shape, position and style, and from then on the two are free to go their separate ways.

### 2.9 Who is on top? · ≈ 1:10

**Visual.** [V2.9a] q02-06: a blue circle, a green square and a red triangle overlap.
An exploded side view shows them as three stacked sheets in the order they were added.
[V2.9b] The circle's sheet rises to the top of the stack as its `z_index` becomes 1;
the front view now shows the circle covering the others. [V2.9c] The triangle's sheet
rises above it with `z_index` 2.

**QR q02-06** appears at [V2.9a], 8 seconds. Caption: "q02-06 · Drawing order and z_index".

> One last property. When shapes overlap, which one is in front?
>
> By default, the answer is the order they were added: later objects are painted on top of earlier ones, like layers of paper. When that is not what you want, set z index. Objects with a higher z index are drawn later, so they appear in front, regardless of when they were added. It can even be animated, so a shape can rise above its neighbours mid-scene.

### 2.10 Recap · ≈ 0:50

**Visual.** [V2.10a] A one-screen summary: the grid with direction arrows, the
stroke/fill circle, the five positioning verbs with icons, a group of dots, the two
sticky notes, the stacked layers. [V2.10b] QR wall: q02-01 to q02-06 for 10 seconds.
[V2.10c] Teaser: five dots racing across the screen at different speeds (episode 3).

> So here are the nouns of Manim. Positions are vectors, built from directions like UP and RIGHT. Shapes have a stroke and a fill. You place them by offset, by absolute point, or relative to each other. Groups let many objects act as one. Names are sticky notes, so copy when you mean copy. And z index decides who is on top.
>
> Next time: the verbs. How Manim moves from one moment to the next, why some motions feel natural and others feel robotic, and a strange thing that happens when you rotate a square the wrong way.
