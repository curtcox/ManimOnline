# Episode 11 · Rebuilding an engine to match

| | |
|---|---|
| Track | Deep dive |
| Target length | about 18 min (segment estimates; set final timing from the narration audio) |
| Builds on | Episodes 3, 4 and 10 |
| QR codes | q11-01 … q11-05 |

Facts to re-check before recording (from `AGENTS.md`, `docs/completion.md`, the
`tests/` folder): manim-lite's size (about 28,000 lines in one file), the Manim
Community version used as the reference (0.22), the number of reference fixture
cases, and the test counts quoted in 11.5. Keep statements about fidelity
qualitative; never claim full compatibility.

## Learning goals

- Explain why ManimOnline reimplements Manim's API instead of running Manim itself.
- Define compatibility as observable behaviour, and explain why it must be measured.
- Describe four ways manim-lite is compared with Manim Community.
- Recognise several surprising behaviours that a faithful reimplementation must copy.
- State clearly what manim-lite is not.

## Script

### 11.1 Cold open: a bug-for-bug match · ≈ 1:00

**Visual.** [V11.1a] Two panels, labelled "Manim Community" (rendered with the real
library) and "ManimOnline" (rendered in the browser). The same code plays in both: a
square rotated half a turn with `.animate`, collapsing through its centre; an arrow
shrinking with its tip staying the same size; the word "Manim" in Text and in Tex.
[V11.1b] The two panels slide together and overlap with 50 % transparency. Every frame
lines up. [V11.1c] The collapsed-square frame is frozen. Caption: "on purpose".

> On the left: Manim Community, the real thing, installed on a computer. On the right: ManimOnline, in a browser tab. Same code, frame for frame.
>
> Including this. The square that collapses to a point when you rotate it with animate. We met it in episode three, and it's arguably a surprising behaviour. But it's Manim's behaviour, and so ManimOnline does it too, deliberately.
>
> Last episode, we saw that the real Manim can't run in the browser, so ManimOnline brings its own engine. This episode is about that engine, and about a harder question than how to build it: how do you know it's right?

### 11.2 Why not run the real thing? · ≈ 1:40

**Visual.** [V11.2a] A box labelled "Manim Community" with roots spreading beneath
it into labelled boxes: "Cairo (drawing)", "Pango (text)", "FFmpeg (video)", "OpenGL",
"LaTeX (installed separately)", and many Python packages. [V11.2b] A browser outline
slides under the roots; several of them light up red: "compiled libraries not
available here". [V11.2c] The box is replaced by one labelled "manim-lite: the same
names, a different engine". Its output is labelled "frame snapshots → SVG in the page".

> Manim stands on a lot of other software. It draws with a graphics library called Cairo, lays out text with another called Pango, encodes video with FFmpeg, and calls out to a separately installed LaTeX for formulas. Several of those are large compiled libraries, and running them inside a web page is either impossible today or would mean an enormous download.
>
> So ManimOnline took a different approach. Keep the parts people actually type: the class names, the method names, their arguments and their results. And reimplement everything underneath, in plain Python that runs comfortably in Pyodide. Instead of pixels, it produces the frame snapshots we saw last episode, and the page draws them.
>
> That engine is called manim-lite. It's a single Python file, about twenty eight thousand lines long. And its goal is simple to state and hard to achieve: for everything it supports, the same code should produce the same animation as Manim Community.

### 11.3 What does "the same" mean? · ≈ 1:40

**Visual.** [V11.3a] A scene's output broken into measurable layers, stacked like
transparent sheets: "geometry (points, bounds)", "style (colours, opacity, widths)",
"timing (durations, rate functions)", "structure (which objects exist, in what order)".
[V11.3b] A magnifying glass passes over a single shape in each panel; numbers appear:
width 3.8027 vs 3.8027. [V11.3c] A sticky note: "Read the code? Not enough. Measure."

> What does "the same" actually mean? Not that the code looks similar inside. manim-lite is written completely differently. It means that everything you can observe agrees: the shapes and their exact sizes and positions, the colours, how long each animation takes, how it moves, and which objects exist at each moment.
>
> That definition has an important consequence. You can't confirm it by reading code, however carefully. Manim is a large library with years' worth of accumulated decisions in its design, and many of them only show up when you actually run something. The only way to know whether two engines agree is to run both, and compare.

### 11.4 Measuring against the reference · ≈ 2:20

**Visual.** [V11.4a] A pipeline: a pile of test scenes → two machines, "Manim 0.22"
and "manim-lite" → two piles of results → a comparison table with rows coloured green
(match) and amber (differs). [V11.4b] The first source of scenes: a short stack labelled
"reference snippets: hand-picked cases, bounds recorded from Manim". [V11.4c] The second:
a much taller stack labelled "every example in Manim's own documentation". A row of the
comparison table is highlighted: final bounds and total duration for one example, both
matching. [V11.4d] An amber row zooms in: "Text bounds differ: different fonts on this
computer". It's marked "explained".

> So that's what happens. First, a set of reference snippets: small pieces of code chosen to pin down tricky geometry, layout and sizes. Their results were measured once with Manim Community, version zero point twenty two, and saved. Whenever manim-lite changes, its answers are checked against those measurements automatically. If a change moves a shape by even a tiny fraction of a unit, the check fails.
>
> Second, and much bigger: Manim's documentation is full of example scenes, each written to show off some feature. Every one of those examples is extracted and run through both engines, and the final positions, sizes and durations are compared.
>
> Not every difference is a bug. Text, for example, is measured using the fonts installed on the machine, so a laptop and a Linux server can disagree slightly about how wide a word is, even with the real Manim. Part of the work is sorting differences into "manim-lite is wrong" and "this comparison isn't fair", and only trusting the comparisons that are.

### 11.5 Random scenes, and Manim's own tests · ≈ 1:50

**Visual.** [V11.5a] A slot machine labelled "fuzzer" spins and produces random code:
`Square().scale(0.3).rotate(1.2).next_to(Circle(), UL)`; the code runs in both engines
and the results are compared. Thousands of tiny green ticks fill the screen, with a
rare amber one, which is pulled out and turned into a permanent test. [V11.5b] A
second stream: whole random scenes, with several animations and updaters at once.
[V11.5c] A folder labelled "Manim's own unit tests" is run against manim-lite; most
pass; the failures are sorted into labelled boxes: "needs LaTeX files", "OpenGL",
"writes video files", "private helper functions". [V11.5d] A summary card:
"~750 Python tests · ~150 JavaScript tests · browser checks in Chromium, Firefox and WebKit".

> Documentation examples are written to work. Bugs often hide in combinations nobody thought to write down. So there are fuzzers: programs that generate random chains of methods and random scenes, with several animations and updaters overlapping, and compare both engines on each one. Whenever a difference turns up, it's investigated, fixed, and turned into a permanent test, so it can never quietly come back.
>
> And Manim Community has its own suite of unit tests. Those can be pointed at manim-lite too. The tests that still fail fall into known categories, like tests that need real LaTeX files, or that check how video files are written to disk, which don't apply in a browser.
>
> All of this sits on top of ManimOnline's own tests: hundreds of them, plus checks that open the real editor in three different browser engines and confirm that scenes actually render and play.

### 11.6 Case study: the straight path · ≈ 1:40

**Visual.** [V11.6a] q11-01: two squares; each corner leaves a coloured trace. On the
left (`.animate.rotate(PI)`), the four traces are straight lines through the centre,
crossing in an X. On the right (`Rotate(PI)`), the four traces are semicircles.
[V11.6b] Inset: a plot of the left square's width over time, dipping to zero at the
midpoint. [V11.6c] A note: "manim-lite interpolates poses with complex numbers, and
the result equals Manim's point-by-point straight path".

**QR q11-01** appears at [V11.6a], 10 seconds. Caption: "q11-01 · Why the square shrinks".

> Let's look at a few cases where matching Manim meant reproducing something you might not expect.
>
> The collapsing square. This scene draws the path of every corner. With animate, each corner travels in a straight line to the opposite corner, and they all meet in the middle. With Rotate, they travel around semicircles.
>
> manim-lite actually stores shapes differently from Manim. It often keeps a shape's position, scale and rotation separately from its outline, which makes many operations cheaper. But a naive blend of "rotation angle from start to end" would spin the square rigidly, which is not what Manim does. So manim-lite blends the pose in a specific way, treating scale and rotation together as a single complex number, which gives exactly the same straight-line paths as Manim's point-by-point method. Correct, here, means faithfully reproducing the collapse.

### 11.7 Case study: arrow tips keep their size · ≈ 1:30

**Visual.** [V11.7a] q11-02: a yellow Arrow above, a home-made line-plus-triangle
below. Both scale down to 40 %, then back up. The home-made triangle shrinks with its
line; the Arrow's tip keeps its size while the shaft shortens. [V11.7b] A diagram of
what Manim does inside `Arrow.scale`: remove the tip, scale the shaft, put a fresh tip
back on. [V11.7c] Caption: "the tip is capped relative to the arrow's length, so very
short arrows get smaller tips".

**QR q11-02** appears at [V11.7a], 8 seconds. Caption: "q11-02 · Arrow tips keep their size".

> Here's another. Scale an arrow down, and its tip does not shrink with it. Compare the home-made arrow, a line and a triangle grouped together, whose head shrinks in proportion.
>
> That's because Manim's arrow does something particular when scaled: it takes its tip off, scales the shaft, and attaches the tip again. So the tip keeps its size, up to a limit tied to the arrow's length, which is why very short arrows still get smaller tips.
>
> It sounds like a small detail. But it changes where the tip ends up, how long the shaft is, and what happens in every later animation of that arrow. manim-lite mirrors Manim's remove, scale, re-attach sequence literally, because subtly different would accumulate into visibly different.

### 11.8 Case study: same font size, different heights · ≈ 1:30

**Visual.** [V11.8a] q11-05: "Manim" written with `Text` and with `Tex`, both at
font size 96, each in a tight yellow box. Height readouts: about 0.98 and 0.75.
[V11.8b] A visual derivation: "Text: em = font_size / 72" and "Tex: em = font_size /
96", with the two em squares drawn to scale side by side. [V11.8c] Caption: "measured
from Manim 0.22, not assumed".

**QR q11-05** appears at [V11.8a], 8 seconds. Caption: "q11-05 · Same font size, different heights".

> Here's one that surprises most people. Write the same word with Text and with Tex, both at font size ninety six. They come out different sizes. The Text version is about a third larger.
>
> In Manim, those two kinds of text go through completely different software, and each converts font size into screen units with its own rule. For Text, the size of a letter's em square is the font size divided by seventy two. For Tex, it's the font size divided by ninety six.
>
> Those numbers weren't guessed. They were measured from Manim itself. An earlier version of manim-lite used a single, made-up scale for both, and its text was simply the wrong size. A plausible guess, it turns out, is not the same as a measurement.

### 11.9 Case study: randomness, exactly · ≈ 1:50

**Visual.** [V11.9a] q11-03: stream lines flowing around a swirling vector field.
Each line's starting point is marked with a small cross, slightly off a regular grid.
[V11.9b] Two overlays: "Manim, seed 0" and "manim-lite, seed 0": the crosses land in
exactly the same places. [V11.9c] q11-04: a graph of eight labelled vertices in a
spring layout, which reflows into a circle and then into a different spring layout.
[V11.9d] A diagram: a seed → a random number generator box ("PCG64", "Mersenne Twister")
→ a sequence of numbers → positions.

**QR q11-03** appears at [V11.9a], 8 seconds. Caption: "q11-03 · Seeded stream lines".
**QR q11-04** appears at [V11.9c], 8 seconds. Caption: "q11-04 · Graph layouts".

> Some features in Manim are random. Stream lines start from points with a little random jitter, so they don't look mechanical. Graph layouts place vertices by simulating springs from random starting positions.
>
> But computer randomness is reproducible: a generator starts from a number called a seed, and produces the same sequence every time. Manim uses NumPy's generator for the stream lines, and the networkx library's random choices for graph layouts.
>
> So for manim-lite to draw the same stream lines and the same graphs, it has to produce the same random numbers, bit for bit. And it does: it contains exact reimplementations of those generators, an algorithm called P C G sixty four, and another called the Mersenne Twister. Same seed, same numbers, same picture, whether or not NumPy is even loaded.

### 11.10 Case study: the order of addition · ≈ 1:20

**Visual.** [V11.10a] Two sums on screen: `(0.1 + 0.2) + 0.3` and `0.1 + (0.2 + 0.3)`.
Their results print: `0.6000000000000001` and `0.6`. [V11.10b] A binary search
narrowing in on a point along a curve; at the last step, two candidates sit within a
hair of each other, and the tiny difference decides which one is chosen. [V11.10c]
Caption: "same additions, same order as Manim".

> One last case, and it's the most extreme. Here are the same three numbers, added in two different orders. The answers differ, in the sixteenth decimal place. Computers store numbers with finite precision, so rounding happens at every step, and the order of the steps matters.
>
> Normally that's irrelevant. But some of Manim's searches, like finding where along a curve a given point lies, can land on a near tie, where the sixteenth decimal place decides the answer. So in a few places manim-lite reproduces not just Manim's formulas, but the exact order in which NumPy adds things up. That's how far "the same" sometimes has to go.

### 11.11 What manim-lite is not · ≈ 1:20

**Visual.** [V11.11a] The two-circle diagram from episode 9: "Manim Community"
containing "manim-lite". Labels in the outer ring: "real LaTeX packages", "OpenGL
renderer", "your installed fonts", "60 fps and high resolution", "writing files to
disk". [V11.11b] An error message in the editor for an unsupported feature, stated
plainly. Caption: "unsupported means an honest error, never a silent guess".

> All of this effort deserves an honest boundary. manim-lite is a compatibility subset, not Manim Community. It doesn't have real LaTeX: formulas go through MathJax. Text uses built-in font measurements, not your computer's fonts. Previews run at fifteen frames per second. And there are features it doesn't support at all.
>
> The design principle is that when something isn't supported, it should say so with a clear error, not quietly draw something different. A wrong picture that looks plausible is far worse than an error message, because you might never notice.

### 11.12 Recap · ≈ 0:50

**Visual.** [V11.12a] Summary: the dependency roots; the "same means observable"
layers; the comparison pipeline with its four sources (reference snippets,
documentation examples, fuzzers, Manim's tests); five case-study icons (X-shaped
traces, fixed tip, two em squares, a seed, two sums). [V11.12b] QR wall: q11-01 to
q11-05 for 10 seconds. [V11.12c] Teaser: a QR code dissolving into a string of letters
and digits (episode 12).

> The real Manim can't run in the browser, so manim-lite reimplements its interface on a new engine. "The same" means the same observable result, and the only way to know is to measure: against recorded references, against every documentation example, against random scenes, and against Manim's own tests. Along the way, faithfulness means copying surprising behaviours: straight paths, fixed tips, two font scales, exact random numbers, even the order of addition.
>
> One question remains. Every QR code in this series opened code in this engine, with no server storing your work. How does a link, or a little square of dots, carry an entire program? That's our final episode.
