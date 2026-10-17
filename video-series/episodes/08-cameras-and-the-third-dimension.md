# Episode 8 · Cameras and the third dimension

| | |
|---|---|
| Track | Main |
| Target length | about 16 min (segment estimates; set final timing from the narration audio) |
| Builds on | Episodes 1–7 (updaters from episode 6, helix/sine link from episode 6) |
| QR codes | q08-01 … q08-05 |

## Learning goals

- Move and zoom the camera with `MovingCameraScene`, and restore a saved view.
- Show a magnified inset with `ZoomedScene`.
- Place a 3D camera with `phi` and `theta`, and animate it with `move_camera`.
- Place points with `ThreeDAxes` and the `OUT`/`IN` directions.
- Plot surfaces, add solids, and keep text flat with `add_fixed_in_frame_mobjects`.
- Choose camera angles and motion that keep a 3D scene readable.
- Explain, at a high level, how a 3D frame becomes a flat picture.

## Script

### 8.1 Cold open: a secret in the middle · ≈ 0:50

**Visual.** [V8.1a] q08-01: a five-by-five grid of dots, coloured from blue to yellow.
Nothing else seems to be there. [V8.1b] The camera dives toward the centre dot.
Something tiny below it grows into legible text: "hello from the middle". [V8.1c] The
camera drifts to the next dot, then pulls back out to the full grid.

> Here's a grid of twenty five dots. Nothing special. But there's something hidden here, too small to see from this distance.
>
> Let's go and look. <break time="0.6s" /> There it is: a message, tucked under the middle dot, about the size of a grain of sand on this screen.
>
> In every scene so far, the camera has been bolted down, and we moved the objects. This episode, the camera gets to move, first across the flat plane, and then into the third dimension.

### 8.2 The camera is a rectangle · ≈ 2:00

**Visual.** [V8.2a] Pull far back from the grid scene to show the scene "world"
extending beyond the frame. The camera frame appears as a white rectangle, 8 units
tall. [V8.2b] The rectangle shrinks and slides toward the centre dot; a picture-in-
picture shows what the camera sees, which fills the screen. [V8.2c] Code beats
highlighted in sequence: `save_state()`, `frame.animate.scale(0.15).move_to(dots[12])`,
`Restore(frame)`. [V8.2d] Close-up comparison: a line drawn at normal zoom, then at
6.7× zoom, where it looks proportionally thicker. Caption: "stroke widths are in
scene units".

**On screen**

```python
class ZoomToDetail(MovingCameraScene):
    def construct(self):
        frame = self.camera.frame
        ...
        frame.save_state()
        self.play(frame.animate.scale(0.15).move_to(dots[12]), run_time=3)
        ...
        self.play(Restore(frame), run_time=2)
```

**QR q08-01** appears at [V8.2b], 8 seconds. Caption: "q08-01 · Zooming the camera".

> In a moving camera scene, the camera's view is itself a mobject: a rectangle called the frame. Whatever is inside the rectangle fills the screen.
>
> And because the frame is a mobject, everything you already know works on it. Scale it down by a factor of zero point one five, and you zoom in by almost seven times. Move it to a dot, and the view glides there. Animate those changes, and you get a smooth camera move, with rate functions and everything.
>
> Save state before you go wandering, and restore takes you smoothly back to where you started. That pattern, save, zoom in, explain, restore, is one you'll use constantly.
>
> One detail you might notice: when you zoom in, lines get thicker. That's because line widths are measured in the scene's own units, so a zoomed-in camera sees them bigger, the way a magnifying glass makes ink lines look fatter. If you need hairlines at high zoom, give those objects thinner strokes.

### 8.3 A magnifying glass · ≈ 1:40

**Visual.** [V8.3a] q08-02: a long ruler with a hundred ticks along the bottom of the
screen. A yellow dot sits at its left end. A small yellow rectangle (the zoomed camera's
frame) hugs the dot. [V8.3b] A larger rectangle pops out in the upper-right corner,
showing a magnified view of the ticks around the dot. [V8.3c] The dot travels along the
ruler; the small frame follows it; the inset scrolls the magnified ticks past.
[V8.3d] Diagram: lines connect the corners of the small frame to the corners of the
inset, labelled "zoom factor 0.25".

**On screen**

```python
frame = self.zoomed_camera.frame
frame.add_updater(lambda m: m.move_to(dot))
self.activate_zooming(animate=True)
```

**QR q08-02** appears at [V8.3c], 8 seconds. Caption: "q08-02 · A magnified inset".

> Sometimes you want to see the detail and the big picture at the same time. That's what a zoomed scene is for. It adds a second camera, with its own small frame, and shows what that camera sees in a display box elsewhere on screen.
>
> Here the small frame is told, with an updater from episode six, to always sit on the dot. As the dot slides along the ruler, the inset shows a close-up of the ticks it's passing over, while the main view still shows the whole ruler.
>
> The zoom factor sets how much of the scene the small frame covers. Zero point two five means it's a quarter of the size of the display box, so everything in the inset looks four times larger.

### 8.4 Stepping into 3D · ≈ 2:00

**Visual.** [V8.4a] A flat `NumberPlane`. It tilts away from the viewer, revealing a
third axis rising out of it: blue x, green y, red z, as in `ThreeDAxes`. [V8.4b] A
transparent sphere surrounds the axes. A small camera icon sits on the sphere. Two
angle arcs: `phi` measured down from the top of the z-axis to the camera, and `theta`
measured around the equator from the x-axis. [V8.4c] The camera icon moves: phi = 0
(looking straight down, the scene looks flat), phi = 90° (looking from the side),
theta sweeping around. A small monitor in the corner shows the view from the icon.
[V8.4d] `self.set_camera_orientation(phi=70 * DEGREES, theta=-50 * DEGREES)` is written
beneath, with phi and theta coloured to match their arcs.

> For three dimensions, we use a three D scene. Points now use their third number: depth, pointing out of the screen, called z.
>
> Where the camera sits is described by two angles, like a position on a globe. Phi is how far the camera is tilted from looking straight down. At zero, you look straight down on the x y plane, and everything looks flat, just like the scenes we've been making. At ninety degrees, you're looking at it edge-on, from the side.
>
> Theta is how far round you've walked, measured around the vertical axis. Changing theta is like walking in a circle around a sculpture.
>
> Set camera orientation puts the camera anywhere on that globe. Seventy degrees of tilt and minus fifty degrees around is a classic view: you can see depth, but the floor is still clearly a floor.

### 8.5 Points in space · ≈ 1:30

**Visual.** [V8.5a] `ThreeDAxes` with x, y and z axes. A dot appears at
`axes.c2p(2, 1, 1.5)`; dashed guide lines drop from it to the floor and run back to each
axis, like a box corner. [V8.5b] The constants `OUT` and `IN` are drawn as arrows along
the z-axis, joining `UP`, `DOWN`, `LEFT` and `RIGHT`. [V8.5c] A `Line` from the origin to
the dot, and a `Dot3D` (a small sphere) replacing the flat dot. The camera tilts a little
to show the sphere stays round from every angle.

**On screen**

```python
axes = ThreeDAxes(x_range=[-3, 3, 1], y_range=[-3, 3, 1], z_range=[-2, 2, 1])
point = axes.c2p(2, 1, 1.5)          # three graph coordinates in, one point out
dot = Dot3D(point, color=YELLOW)
```

> Everything you know about positions carries over to three dimensions. Three D axes work like ordinary axes with a third ruler, and c to p now takes three numbers. The point two, one, one point five is two along x, one along y, and one and a half up.
>
> Directions gain two new members: OUT, toward the viewer when the camera looks straight down, and IN, away. So UP times two plus OUT is a perfectly good point.
>
> Most flat shapes still work in 3D; they simply lie flat in space, like paper cut-outs. For objects that should look solid from every angle, there are 3D versions: Dot three D is a little sphere instead of a disc.

### 8.6 Surfaces · ≈ 1:50

**Visual.** [V8.6a] q08-03: 3D axes draw, then a wavy surface `z = sin(u) cos(v)`
grows over them, coloured blue in the valleys, green on the slopes and yellow on the
peaks. [V8.6b] A close-up shows that the surface is a grid of small four-sided patches,
20 by 20. [V8.6c] The camera begins a slow ambient orbit, and the surface turns in the
light.

**On screen**

```python
surface = axes.plot_surface(lambda u, v: math.sin(u) * math.cos(v),
                            u_range=[-3, 3], v_range=[-3, 3], resolution=(20, 20),
                            colorscale=[BLUE, GREEN, YELLOW], fill_opacity=0.85)
self.begin_ambient_camera_rotation(rate=0.3)
```

**QR q08-03** appears at [V8.6a], 10 seconds. Caption: "q08-03 · A surface in 3D".

> A function of two inputs, u and v, gives you a height for every point on the floor. Plot surface turns that into a landscape.
>
> Like a plot in two dimensions, it can't draw the function exactly, so it samples it. Resolution twenty by twenty means a grid of four hundred little patches, each a flat four-sided face. Raise the resolution for a smoother surface, at the cost of more work.
>
> Colorscale paints each patch according to its height: blue in the valleys, through green, to yellow on the peaks. And begin ambient camera rotation sets the camera slowly orbiting, which is often the single best way to help viewers understand a 3D shape. Movement gives the brain depth cues that a still image can't.

### 8.7 Solids · ≈ 1:20

**Visual.** [V8.7a] q08-04: a sphere, a teal cube and a torus fade in side by side.
[V8.7b] The cube turns a quarter turn about the vertical axis while the torus turns about
the horizontal; their faces brighten and darken as they turn. [V8.7c] The camera swings
round to a new angle. [V8.7d] Diagram: faces of the cube are sorted back to front, and
painted in that order, so nearer faces cover farther ones.

**QR q08-04** appears at [V8.7a], 8 seconds. Caption: "q08-04 · Solids".

> Manim includes ready-made solids: spheres, cubes, tori, cones, cylinders, and more. Each one is built from flat faces, just like the surface.
>
> Two things make them look solid. First, shading: each face is lit according to which way it points, so faces turned away from the light are darker. Second, depth sorting: before drawing a frame, faces are put in order from farthest to nearest, and painted in that order, so near faces cover far ones. Painters have worked this way for centuries, which is why it's often called the painter's algorithm.

### 8.8 Same curve, three views · ≈ 1:40

**Visual.** [V8.8a] q08-05: the title "A helix: (cos t, sin t, t / 4)" is written
flat across the top-left of the screen. A yellow helix grows around the vertical axis.
[V8.8b] The camera rises to look straight down (phi ≈ 10°): the helix appears as a
circle. [V8.8c] The camera swings to the side (phi ≈ 88°, theta = 0): the helix
appears as a wave, rising and falling. The title stays perfectly flat throughout.
[V8.8d] A split screen: on the left, the circle-to-sine scene from episode 6; on the
right, the side view of the helix, turned a quarter turn so it runs left to right.
The two waves line up.

**On screen**

```python
self.add_fixed_in_frame_mobjects(title)      # stays flat on the screen
...
self.move_camera(phi=10 * DEGREES, theta=-90 * DEGREES, run_time=3)   # look straight down
self.move_camera(phi=88 * DEGREES, theta=0, run_time=3)                # look from the side
```

**QR q08-05** appears at [V8.8a], 10 seconds. Caption: "q08-05 · A helix from three angles".

> Here's a helix: a spiral that climbs as it turns, like a spring or a spiral staircase. Its points are cosine of t, sine of t, and t over four.
>
> Notice the title. In a 3D scene, ordinary objects tilt with the world. But titles and labels usually shouldn't, so add fixed in frame mobjects pins them flat to the screen, like a caption on a window.
>
> Now watch what move camera reveals. From straight above, the climbing doesn't show at all, and the helix is just a circle. From the side, the circling doesn't show, and the helix is a wave. In fact, it's exactly the sine wave from episode six. That point going round a circle and the wave it traced were always two shadows of this one spiral.

### 8.9 Choosing a good view · ≈ 1:40

**Visual.** [V8.9a] The same surface shown from four camera positions, as a 2×2 grid:
straight down (looks flat), straight from the side (looks like a single wavy line),
from below (confusing), and from 70° tilt, −50° around (clear). Three get a red cross,
one a green tick. [V8.9b] A slow orbit versus a fast spin, side by side; the fast one
gets a dizzy icon. [V8.9c] A camera path diagram: "establish" (wide view) → "move"
(slow arc) → "hold" (still) → "point" (label appears).

> A 3D scene is only as clear as the view you choose, and some views hide everything. Straight down, a surface looks flat. Straight from the side, it collapses to a single wavy line. From underneath, nothing makes sense.
>
> A tilt of sixty to seventy five degrees, and a turn of thirty to sixty degrees around, is a reliable starting point: it shows depth while keeping the floor recognisable.
>
> Motion helps, but gently. A slow orbit reveals shape. A fast spin makes people dizzy and hides detail. And when you want viewers to read something, stop the camera first. A good rhythm is: establish a wide view, move slowly to where the action is, hold still, and only then point at things.

### 8.10 Behind the scenes in ManimOnline · ≈ 1:00

**Visual.** [V8.10a] A simple pipeline: "Python: 3D points + camera angles, every frame"
→ "Browser: shade, sort, project" → "flat SVG frame". [V8.10b] A cube spinning; beside
it, a stack of frame cards where only the first card holds the cube's points and the
rest hold a small rotation matrix. Caption: "rigid motion: send the shape once".

> A brief look under the hood, because it's a nice piece of engineering. In ManimOnline, Python doesn't flatten the 3D world itself. Each frame records the 3D shapes and where the camera is, and the browser does the shading, sorting and projecting when it draws.
>
> That split pays off when something moves rigidly, like a spinning cube. Instead of sending the cube's points again for every frame, a frame can say: "the same cube as before, turned by this much". Episode ten looks at the rest of that machinery.

### 8.11 Recap · ≈ 0:50

**Visual.** [V8.11a] Summary board: the camera rectangle; the inset with connecting
lines; the globe with phi and theta; a surface patch grid; a cube with sorted faces;
the helix casting a circle and a wave. [V8.11b] QR wall: q08-01 to q08-05 for 10 seconds.
[V8.11c] Teaser: a cursor clicking Export → MP4 (episode 9).

> The camera is a mobject too, so you can move it, zoom it, save it and restore it. A zoomed scene adds a magnifying inset. In three dimensions, phi and theta place the camera on a globe, surfaces and solids are made of flat shaded faces, and fixed-in-frame text stays readable while the world turns.
>
> That completes our tour of what you can draw. Next time, we turn to the practical side of ManimOnline: the gallery, exporting videos, sharing links, saving your work, and its two other languages.
