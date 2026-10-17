# Episode 7 · Graphs, areas and slopes

| | |
|---|---|
| Track | Main |
| Target length | about 16 min (segment estimates; set final timing from the narration audio) |
| Builds on | Episodes 1–6 (ValueTracker and always_redraw from episode 6) |
| QR codes | q07-01 … q07-05 |

## Learning goals

- Convert numbers to points on a `NumberLine`.
- Build `Axes`, convert between graph coordinates and screen points with `c2p`.
- Plot parametric curves and label axes.
- Plot functions and label graphs; understand that plots are sampled curves.
- Animate Riemann sums converging to an area, and areas with a moving bound.
- Animate a secant line becoming a tangent with a shrinking `dx`.
- Use `LinearTransformationScene` to show what a matrix does to the plane.

## Script

### 7.1 Cold open: how much is under the curve? · ≈ 1:00

**Visual.** [V7.1a] A yellow curve rises across a set of axes. The region beneath it
is shaded with a question mark. [V7.1b] Four wide rectangles fill the region, with a
staircase edge poking above and below the curve. [V7.1c] They split into eight,
sixteen, forty, eighty, each time hugging the curve more tightly, until the staircase
can no longer be seen. [V7.1d] The rectangles melt into a smooth shaded area and the
value 22/3 appears.

> How much space is under this curve? <break time="0.6s" /> There is no formula for "area" that works on a wiggly shape directly. But there is a formula for the area of a rectangle.
>
> So: fill the region with rectangles. Four of them get the rough idea, with obvious gaps and overhangs. Eight are better. Sixteen, forty, eighty. The errors shrink, and the total settles towards one particular number.
>
> That is the whole idea of an integral, and it is a perfect thing to animate, because the important part is not the answer. It's the motion of getting there.

### 7.2 Number lines · ≈ 1:30

**Visual.** [V7.2a] A `NumberLine` from −5 to 5 with numbers draws itself. [V7.2b] A
dot is placed with `number_to_point(2.5)`; a second dot is dropped at a screen
position and `point_to_number` reads back 1.0. [V7.2c] The line is rotated and moved;
the dot at 2.5 stays at 2.5 on the line. [V7.2d] Two number lines, one horizontal and
one vertical, slide together and cross at zero; a caption appears: "two number lines
= Axes".

**On screen**

```python
line = NumberLine(x_range=[-5, 5, 1], length=10, include_numbers=True)
dot = Dot(line.number_to_point(2.5))     # n2p for short
```

> Before graphs, the simplest coordinate system of all: a number line. You give it a range, a step between ticks and a length on screen, and it can label its own ticks.
>
> A number line converts in both directions. Number to point, n two p for short, tells you where a number lives on screen. Point to number does the reverse. And these conversions follow the line wherever it goes: rotate it, move it, shrink it, and two point five is still exactly where two point five should be. We used n two p last episode to park the pointer above a value.
>
> Now put two number lines together, one across and one up, crossing at zero. That, give or take some styling, is exactly what Axes are.

### 7.3 Axes: a ruler inside the scene · ≈ 2:00

**Visual.** [V7.3a] q07-01: axes create themselves with numbered ticks; x from −3 to 3,
y from −2 to 9. [V7.3b] A side-by-side: the point (2, 4) on the graph's own ruler,
and the same location in Manim's screen coordinates, about (2.33, 0.27). An arrow
between them labelled `axes.c2p(2, 4)`. [V7.3c] The parabola draws, with its label
`x²`; the line draws with its label `2x+1`. [V7.3d] Two red dots pop in where they
cross; the values `1 − √2` and `1 + √2` appear beneath them.

**On screen**

```python
axes = Axes(x_range=[-3, 3, 1], y_range=[-2, 9, 1], x_length=7, y_length=6, tips=False).add_coordinates()
parabola = axes.plot(lambda x: x ** 2, color=YELLOW)
dots = VGroup(*[Dot(axes.c2p(x, x ** 2), color=RED) for x in crossings])
```

**QR q07-01** appears at [V7.3c], 8 seconds. Caption: "q07-01 · Axes and plots".

> To draw graphs, we need a second kind of coordinate system, one that belongs to the graph rather than the screen. That is what Axes are.
>
> You tell Axes the range of numbers each axis should cover, and how long it should be on screen. This one runs from minus three to three across, and from minus two to nine upwards, squeezed into a box seven units wide and six units tall. Add coordinates puts numbers on the ticks.
>
> Now there are two ways to describe a position: in graph numbers, or in screen units. The method c to p, short for coordinates to point, converts from one to the other. Ask for the point two, four on this graph, and you get back the screen location where that point is drawn.
>
> This matters because it means you can think in the graph's own numbers. To put dots where the line crosses the parabola, we solve x squared equals two x plus one, which gives one minus root two and one plus root two, and let c to p work out where those points are on screen. If you resize the axes later, the dots still land in the right place.

### 7.4 What a plot really is · ≈ 1:20

**Visual.** [V7.4a] The parabola's outline is shown as sample points: a row of
dots along the curve at evenly spaced x values. [V7.4b] Smooth cubic pieces join the
dots, with handles briefly shown (callback to episode 4). [V7.4c] Inset: a function
with a jump, `1/x` near zero, plotted naively: a steep false line connects the two
sides. Caption: "split the range, or declare a gap".

> What does plot actually do? It can't draw a function exactly, any more than a computer can store a perfect circle. Instead, it evaluates your function at many x values across the range, and threads a smooth chain of cubic curves through the results. Episode four in action.
>
> That works beautifully for smooth functions. But it means plot doesn't know about jumps. Plot one over x straight through zero, and the curve may join the two sides with a steep line that isn't really there. The fix is to plot each side separately, or to tell plot where the discontinuities are.

### 7.5 Rectangles become area · ≈ 2:00

**Visual.** [V7.5a] q07-02 in full: axes with the curve `x²/4 + 1/2`; four Riemann
rectangles draw in. [V7.5b] Each refinement step labelled with its width: `dx = 1`,
`0.5`, `0.25`, `0.1`, `0.05`. A running total of rectangle areas is shown in a small
box, approaching 7.33. [V7.5c] The rectangles fade into the smooth blue area. The
integral writes in the top-left corner.

**On screen**

```python
rectangles = axes.get_riemann_rectangles(graph, x_range=[0, 4], dx=1, fill_opacity=0.6)
for dx in [0.5, 0.25, 0.1, 0.05]:
    self.play(Transform(rectangles, axes.get_riemann_rectangles(graph, x_range=[0, 4], dx=dx, fill_opacity=0.6)))
area = axes.get_area(graph, x_range=[0, 4], color=BLUE, opacity=0.6)
```

**QR q07-02** appears at [V7.5a], 10 seconds. Caption: "q07-02 · Riemann rectangles".

> Here is the opening scene. Axes have a method called get Riemann rectangles, which builds the rectangles for you: give it a graph, a range, and a width d x. Each rectangle's height is the function's value at its left edge, and its colour shifts gradually from one end to the other, so you can still tell them apart when there are dozens.
>
> To refine, we build a new set with a smaller d x and transform the old set into it. Transform pairs up rectangles, and because the new set has more of them, the extra ones grow out of the old, which gives that lovely splitting motion.
>
> Finally, get area shades the exact region under the curve, and we write down the exact answer: twenty two thirds, or about seven point three three, which is the number the rectangles were closing in on all along.

### 7.6 Area as a running total · ≈ 2:00

**Visual.** [V7.6a] q07-04: axes with `sin x` from 0 to 2π. A vertical white line at
`b` sweeps to the right; the area between 0 and `b` fills behind it with a blue-to-green
gradient. The readout "∫₀ᵇ sin x dx =" counts up. [V7.6b] At b = π, freeze briefly:
readout 2.00. [V7.6c] As b passes π, the new area appears below the axis, and the
readout counts back down, reaching 0.00 at 2π. [V7.6d] Inset: the area above the axis
glows "+2", the area below glows "−2".

**On screen**

```python
b = ValueTracker(0.01)
area = always_redraw(lambda: axes.get_area(graph, x_range=[0, b.get_value()], color=[BLUE, GREEN], opacity=0.5))
value.add_updater(lambda m: m.set_value(1 - math.cos(b.get_value())))
```

**QR q07-04** appears at [V7.6a], 10 seconds. Caption: "q07-04 · Area with a moving bound".

> Now let's make the boundary move. Store the right-hand edge of the area in a value tracker, b, and always redraw the area from zero to b. Then animate b, and the area sweeps out behind it.
>
> The readout shows the integral of sine from zero to b, which works out to one minus cosine of b. As b grows to pi, the area grows to exactly two. Then something interesting happens. Past pi, the curve dips below the axis, and area below the axis counts as negative. So the total starts falling, and by two pi it is back to zero: the part below cancels the part above exactly.
>
> This is the idea of an integral as a running total, an accumulation. It's one thing to be told that, and quite another to watch it happen.

### 7.7 The slope of a curve · ≈ 2:10

**Visual.** [V7.7a] q07-03: a curve and a green secant line through two points on it,
the first at x = 1.5 and the second at x = 1.5 + dx. A small right triangle beneath
shows `dx` along the bottom and `dy` up the side. A readout in the corner:
`dy/dx = 1.375`. [V7.7b] As dx shrinks toward zero, the second point slides along the
curve toward the first, the triangle shrinks, and the secant swings until it just
grazes the curve. The readout settles towards 0.750. [V7.7c] The final line glows and
is labelled "tangent".

**On screen**

```python
dx = ValueTracker(2.5)
secant = always_redraw(lambda: axes.get_secant_slope_group(
    x=1.5, graph=graph, dx=dx.get_value(), dx_label="dx", dy_label="dy",
    secant_line_color=GREEN, secant_line_length=6))
self.play(dx.animate.set_value(0.01), run_time=5)
```

**QR q07-03** appears at [V7.7a], 10 seconds. Caption: "q07-03 · From secant to tangent".

> Area was the first big idea of calculus. Here is the second: the slope of a curve at a single point.
>
> A straight line has a slope: how far it rises for each step across. A curve doesn't, because it keeps changing direction. But we can pick two points on the curve, draw the line through them, called a secant, and measure its slope: the rise, d y, divided by the run, d x.
>
> Now put d x in a value tracker, and always redraw the secant, its little triangle and its labels. As d x shrinks, the second point slides toward the first, and the secant pivots. The slope readout changes, and then settles. For this curve, x squared over four plus one, at x equals one point five, it settles at zero point seven five.
>
> The line it settles into touches the curve at just that one point. It's the tangent line, and its slope is the derivative. Again, the animation shows you the limit happening, instead of asking you to imagine it.

### 7.8 Curves that aren't functions · ≈ 1:40

**Visual.** [V7.8a] On a set of axes, a circle traced by `plot_parametric_curve`
with `t` from 0 to 2π; a small `t` readout and a dot show the parameter driving the
point. [V7.8b] The same with `(cos 3t, sin 2t)`: a Lissajous figure draws itself.
[V7.8c] Axis labels `x` and `y` appear at the ends of the axes via `get_axis_labels`.
[V7.8d] A vertical line test: a vertical line sweeps across the circle and crosses it
twice; caption "not a function of x, but a perfectly good curve".

**On screen**

```python
curve = axes.plot_parametric_curve(lambda t: (math.cos(3 * t), math.sin(2 * t)), t_range=[0, TAU])
labels = axes.get_axis_labels(x_label="x", y_label="y")
```

> Plot draws graphs of functions: one height for each x. But many curves aren't like that. A circle has two heights for most x values, above and below.
>
> For those, describe the curve with a parameter instead. Plot parametric curve takes a function of t that returns both coordinates, x and y, and traces the point as t runs through a range. Cosine t and sine t give a circle. Cosine of three t and sine of two t give this looping figure, called a Lissajous curve, which you may have seen on an old oscilloscope.
>
> And to finish a graph, get axis labels puts names at the ends of the axes. It's a small touch, but a graph without axis labels is a picture without a caption.

### 7.9 Grids that bend · ≈ 2:00

**Visual.** [V7.9a] q07-05: a full-screen coordinate grid with a green arrow
`î` (one unit right), a red arrow `ĵ` (one unit up), and a yellow vector (1, 2).
[V7.9b] The matrix `[[1, 1], [0, 1]]` appears in the corner. The whole grid shears:
vertical lines lean right; `î` stays put, `ĵ` lands at (1, 1), and the yellow vector
lands at (3, 2). Faded "ghost" copies of the old arrows remain. [V7.9c] The columns of
the matrix are highlighted, one green, one red, and each slides onto the arrow it
describes. [V7.9d] A second matrix, a quarter turn, rotates the whole sheared grid.

**On screen**

```python
class BendTheGrid(LinearTransformationScene):
    ...
    def construct(self):
        self.add_vector([1, 2], color=YELLOW)
        self.apply_matrix([[1, 1], [0, 1]])     # a shear: i-hat stays, j-hat leans right
```

**QR q07-05** appears at [V7.9b], 10 seconds. Caption: "q07-05 · Bend the grid".

> Graphs aren't the only thing worth drawing on a grid. Sometimes the grid itself is the star.
>
> A linear transformation moves every point of the plane in a way that keeps grid lines straight, parallel and evenly spaced. And a two by two matrix describes one completely. Its first column says where the arrow one-to-the-right ends up. Its second column says where the arrow one-upward ends up. Everything else follows along.
>
> Manim has a scene type built for exactly this: linear transformation scene. It draws the grid and those two basis arrows for you. Call apply matrix, and the whole plane moves. This shear leaves the first arrow alone and tips the second over to one, one. The yellow vector, one, two, rides along to three, two. Then a quarter-turn rotation spins everything.
>
> If this way of seeing matrices is new to you, it's worth slowing down for. Pause the video, scan the code, and try your own matrices.

### 7.10 Recap · ≈ 0:50

**Visual.** [V7.10a] Summary board: the `c2p` arrow between two rulers; sample dots
on a curve; rectangles merging into an area; the sweeping bound; the secant becoming a
tangent; a sheared grid. [V7.10b] QR wall: q07-01 to q07-05 for 10 seconds. [V7.10c]
Teaser: the camera dives into a single dot in a grid of dots (episode 8).

> Axes give a scene its own ruler, and c to p converts graph numbers into screen points. Plots are sampled curves. Riemann rectangles and get area show integrals; a moving bound shows accumulation; a shrinking d x shows a derivative being born. And linear transformation scene shows what matrices do to space.
>
> So far, the camera has stayed perfectly still. Next time, we move it: zoom into tiny details, open a magnifying inset, and then tilt the whole world into three dimensions.
