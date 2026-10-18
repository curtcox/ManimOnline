# Episode 5 · Words and equations

Published video: [Words and Equations: Text, MathTex and Tex · Drawing with Code 5 (Manim)](https://www.youtube.com/watch?v=mqY9GnhD5iI&list=PLXaiuWr3VAhk) · [series playlist](https://www.youtube.com/playlist?list=PLXaiuWr3VAhk)

| | |
|---|---|
| Track | Main |
| Target length | about 17 min (segment estimates; set final timing from the narration audio) |
| Builds on | Episodes 1–4 (outlines as Bézier curves from episode 4) |
| QR codes | q05-01 … q05-05 |

## Learning goals

- Choose between `Text`, `MathTex` and `Tex`, and use raw strings for TeX.
- Explain how a formula becomes vector outlines, in Manim and in ManimOnline.
- Index letters and formula parts to colour and animate them separately.
- Style text with weights, colours and markup; colour symbols with `tex_to_color_map`.
- Animate algebra with `TransformMatchingTex`, and align lines of working.
- Annotate with `Brace`, `Title` and `TransformFromCopy`.

## Script

### 5.1 Cold open: an equation that solves itself · ≈ 0:50

**Visual.** [V5.1a] `2x + 3 = 11` writes itself in the centre of the screen.
[V5.1b] The `3` slides across the equals sign, the `+` fades as a `−` appears, and
`2x` and `=` glide only slightly. [V5.1c] `11 − 3` collapses into `8`. `2x` gives way to `x` while `8` becomes the
fraction `8/2`, which resolves to `4`. A circle is drawn around `x = 4`.

> Watch this equation. <break time="0.5s" /> The three walks across the equals sign. Eleven minus three becomes eight. Divide both sides by two. And there's the answer.
>
> What makes this satisfying is what doesn't disappear. The two x and the equals sign never vanish and reappear; they just glide a little, so your eye can follow only what changed. By the end of this episode you will be able to write that animation yourself, and to understand why letters and numbers are, to Manim, just more shapes.

### 5.2 Three ways to write · ≈ 1:50

**Visual.** [V5.2a] q05-01 plays: "Text uses ordinary fonts" writes at the top;
`e^{iπ} + 1 = 0` writes in the middle; the mixed sentence with the Basel sum writes at
the bottom. [V5.2b] Each line gets a label tag in its own colour: `Text`, `MathTex`,
`Tex`. [V5.2c] A zoom on the code line `MathTex(r"e^{i\pi} + 1 = 0")`, with the `r`
before the string circled and the backslash in `\pi` highlighted.

**On screen**

```python
words = Text("Text uses ordinary fonts", font_size=40)
formula = MathTex(r"e^{i\pi} + 1 = 0", font_size=72)
sentence = Tex(r"Tex mixes words and math: $\sum_{n=1}^{\infty} \frac{1}{n^2} = \frac{\pi^2}{6}$")
```

**QR q05-01** appears at [V5.2a], 8 seconds. Caption: "q05-01 · Text, MathTex and Tex".

> Manim has three main ways to put words on screen.
>
> Text uses ordinary fonts, like a word processor. It is the right choice for titles, labels and sentences. Font size controls how big it is.
>
> Math Tex is for formulas. You write them in the notation of TeX, the typesetting system that mathematicians have used for decades: a caret for superscripts, backslash pi for pi, backslash frac for fractions. Math Tex treats the whole string as mathematics.
>
> And Tex is for sentences that mix words and maths. Ordinary text, with the mathematical parts wrapped in dollar signs.
>
> One habit to pick up straight away: put a lowercase r in front of these strings. It makes it a raw string, which tells Python to leave backslashes alone. Without it, Python might read backslash f in backslash frac as a special character, and the formula breaks in confusing ways.

### 5.3 From TeX to outlines · ≈ 2:00

**Visual.** [V5.3a] A pipeline diagram for standard Manim: `MathTex` string →
"LaTeX (installed on your computer)" → "DVI document" → "dvisvgm: SVG outlines" →
"VMobject: cubic curves". Each stage shows the formula in that form. [V5.3b] The
pipeline for ManimOnline: `MathTex` string → "MathJax, in the page" → "SVG glyph paths"
→ "VMobject". The middle step is labelled "no TeX installation". [V5.3c] A small
loop arrow labelled "measure, then render again" circles from the page back to the
Python worker. [V5.3d] A sign reading "Supported: common mathematical notation.
Not supported: custom LaTeX packages and preambles."

> How does a formula become something Manim can animate? In standard Manim, your formula is handed to a real installation of LaTeX on your computer. LaTeX typesets it, another tool converts the result to scalable vector graphics, and Manim reads those outlines in as cubic curves, exactly like the ones from last episode.
>
> That is why installing Manim traditionally means installing LaTeX too, which is a large download.
>
> ManimOnline cannot assume you have LaTeX, so it takes a different route. It uses MathJax, a library that typesets mathematics inside web pages, to turn your formula into glyph outlines right in the browser. Python asks for the formulas it needs; the page draws them and measures their exact sizes; then the scene renders a second time using those measurements, so that formulas are placed with their true widths and heights.
>
> The honest caveat: MathJax is not LaTeX. Everyday mathematical notation, fractions, roots, sums, integrals, matrices and Greek letters, works well. Custom LaTeX packages and preambles do not. If a formula looks wrong in ManimOnline, simplify it first, and remember that full Manim with a real LaTeX installation is the reference.

### 5.4 Every letter is a shape · ≈ 1:50

**Visual.** [V5.4a] q05-02: "MANIM" writes in large letters. [V5.4b] The first and
last letters turn yellow; numbers `[0]` and `[-1]` hover over them. [V5.4c] The
letters hop up one after another with a there-and-back rate function. [V5.4d] The
formula `a^2 + b^2 = c^2` writes underneath, then its parts turn blue, green and red;
index tags `[0]`, `[2]`, `[4]` hover over the coloured parts and `[1]`, `[3]` over the
plus and equals signs.

**On screen**

```python
formula = MathTex("a^2", "+", "b^2", "=", "c^2", font_size=96)
self.play(formula[0].animate.set_color(BLUE), formula[2].animate.set_color(GREEN),
          formula[4].animate.set_color(RED))
```

**QR q05-02** appears at [V5.4d], 8 seconds. Caption: "q05-02 · Letters and formula parts".

> Because text becomes outlines, every letter is a shape you can grab. Index a Text object like a list, and you get its letters. Zero is the first letter, minus one the last. You can colour them, move them, and animate them one by one with a lagged start.
>
> Formulas work the same way, with one extra option. If you give Math Tex several strings instead of one, each string becomes a separate part, and the parts are typeset together as one formula. Index the formula, and you get the parts. Here a squared is part zero, the plus sign is part one, and so on. That makes it easy to colour a and b and c, or to point at one term while you talk about it.

### 5.5 Styling words, colouring symbols · ≈ 2:00

**Visual.** [V5.5a] The sentence "Manim makes math move" in plain Text. It becomes
bold (`weight=BOLD`), then italic (`slant=ITALIC`), then the word "math" turns yellow
via `t2c`. [V5.5b] The same sentence written as MarkupText with `<b>` and a coloured
`<span>`; the tags are shown dimmed in the code and absent in the picture. [V5.5c] The
formula `x^2 + 2xy + y^2` with `tex_to_color_map={"x": BLUE, "y": GREEN}`: every x
turns blue and every y green, including the ones inside `2xy`. A thin outline around
each coloured glyph shows that each one is its own piece.

**On screen**

```python
Text("Manim makes math move", weight=BOLD, t2c={"math": YELLOW})
MarkupText('Manim makes <span foreground="yellow">math</span> <b>move</b>')
MathTex("x^2 + 2xy + y^2", tex_to_color_map={"x": BLUE, "y": GREEN})
```

> Text has the styling options you'd expect. Weight makes it bold, slant makes it italic, and font chooses a typeface. To colour particular words, pass t two c, short for text to colour: a dictionary from words to colours.
>
> For finer control there's Markup Text, which understands a small set of tags, a bit like a web page: b for bold, i for italic, and span for colours and sizes. The tags shape the text, and never appear in it.
>
> Formulas have their own trick. Tex to color map finds every occurrence of a piece of TeX and colours it. Here every x becomes blue and every y green, even the x and the y tucked inside two x y. To make that possible, Manim isolates each of those symbols as its own piece of the formula, so you can also animate them, which comes in handy in a moment.
>
> Colour is one of the best tools you have for explanation. If x is always blue, in every formula and on every graph, the viewer stops having to read the label.

### 5.6 Algebra that moves · ≈ 2:30

**Visual.** [V5.6a] The q05-03 steps listed vertically as code, each `MathTex`
broken into labelled parts. Matching parts in consecutive steps are joined by thin
coloured lines: `"2x"` to `"2x"`, `"="` to `"="`, `"11"` to `"11"`, `"3"` to `"3"`.
[V5.6b] Back to the full-screen animation from the cold open. During each step,
matching parts glow faintly as they slide; parts with no partner fade out or fade in.
[V5.6c] A step where `"+"` has no partner and `"-"` is new: the plus fades out while
the minus fades in, in the same place.

**On screen**

```python
steps = [
    MathTex("2x", "+", "3", "=", "11"),
    MathTex("2x", "=", "11", "-", "3"),
    MathTex("2x", "=", "8"),
    MathTex("x", "=", r"\frac{8}{2}"),
    MathTex("x", "=", "4"),
]
...
self.play(TransformMatchingTex(current, step))
```

**QR q05-03** appears at [V5.6b], 10 seconds. Caption: "q05-03 · Solve for x".

> Now the equation from the start. Each line of working is a Math Tex with several parts. And the animation between lines is called Transform matching tex.
>
> It looks at the parts of the old formula and the new one, and pairs up any parts whose TeX is identical. Two x goes with two x. The equals sign goes with the equals sign. The three goes with the three, even though it ends up somewhere else. Each matched pair is transformed, so it slides from its old position to its new one.
>
> Parts with no match are handled gently: the old ones fade out, the new ones fade in. In the second step, the plus sign has no partner, and the minus sign is new, so one fades as the other appears.
>
> The art is in how you split the strings. If you want two things to be matched, write them as separate, identical parts. If you write the whole equation as one string, there's nothing to match, and the entire formula simply cross-fades. So think of the parts as the pieces you want the viewer's eye to follow.

### 5.7 Lining up the working · ≈ 1:30

**Visual.** [V5.7a] Three lines of working stacked with `arrange(DOWN)`: each line
is centred, so the equals signs zig-zag; a red dashed vertical line through each equals
sign shows they don't align. [V5.7b] Each line is shifted horizontally so its equals
sign sits under the first one's; the red lines merge into a single green line.
[V5.7c] A close-up of the code: the horizontal difference between two equals signs,
masked to the x direction, is highlighted.

**On screen**

```python
lines = VGroup(line1, line2, line3).arrange(DOWN, buff=0.4)
for line in lines[1:]:
    line.shift(RIGHT * (line1[1].get_x() - line[1].get_x()))   # part 1 is "="
```

> When working is written down a page, mathematicians line up the equals signs, so your eye can run straight down the column. Manim won't do that automatically: arrange centres each line, so the equals signs zig-zag.
>
> Because each equation is split into parts, though, the fix is short. The equals sign is part one of every line. Get x tells you how far across it is. So shift each later line sideways by the difference between its equals sign and the first line's. Now the column is straight, and anything that changes from line to line stands out immediately.

### 5.8 Pointing at things · ≈ 1:40

**Visual.** [V5.8a] q05-04: the title "Completing the square" writes at the top with
an underline. [V5.8b] `f(x) = x² + 2x + 1` writes. A brace grows beneath the last
five parts, and the text "a perfect square" fades up beneath it. [V5.8c] Brace and
label fade, and the formula transforms to `f(x) = (x+1)²`, with `f(x)` and `=` held
still.

**On screen**

```python
brace = Brace(formula[2:], DOWN)
label = brace.get_text("a perfect square")
```

**QR q05-04** appears at [V5.8b], 8 seconds. Caption: "q05-04 · Titles and braces".

> Explanations need pointing. A Brace is a curly bracket that stretches to fit whatever you give it. Here, formula from part two onwards: everything after the equals sign. Ask the brace for get text, and it places a label neatly beside itself.
>
> And Title gives you a heading at the top of the frame, with a line beneath it. Small things, but they do a lot of the work of making a scene feel like an explanation rather than a picture.

### 5.9 Putting it together: Pythagoras · ≈ 1:40

**Visual.** [V5.9a] q05-05: a right triangle draws. Squares grow on each side with
`DrawBorderThenFill`: blue on the bottom, green on the left, red on the hypotenuse.
[V5.9b] Labels `a²`, `b²`, `c²` write in the middle of each square. [V5.9c] Copies of
the three labels fly across the screen to assemble `a² + b² = c²` on the right, in
matching colours, while the plus and equals signs fade in.

**QR q05-05** appears at [V5.9c], 10 seconds. Caption: "q05-05 · Pythagoras with labels".

> Here is a small scene that uses most of today's ideas. A right triangle, with a square on each side. The square on the hypotenuse is positioned using a little vector arithmetic from episode two: a vector as long as the hypotenuse, at right angles to it.
>
> Each square gets a label, a squared, b squared, c squared. Then Transform from copy sends a copy of each label flying to its place in the equation, while the originals stay put. The colours tie each term back to its square, so the viewer can see what the equation is saying, not just read it.

### 5.10 Recap · ≈ 0:50

**Visual.** [V5.10a] Summary board: three labelled lines (Text, MathTex, Tex); the
TeX-to-outline pipelines side by side; the indexed letters; matched parts with
connecting lines; a brace. [V5.10b] QR wall: q05-01 to q05-05 for 10 seconds. [V5.10c]
Teaser: a label clinging to a dot as it flies around the screen (episode 6).

> Text is for words, Math Tex for formulas, and Tex for sentences that mix them. Every glyph becomes outlines, so letters and terms are shapes you can index, colour and move. Split formulas into parts, and Transform matching tex will slide the pieces that stay the same.
>
> So far, everything we have animated changes only when we explicitly tell it to. Next time, we make objects that keep themselves up to date: labels that follow, numbers that count, and shapes that redraw themselves every single frame.
