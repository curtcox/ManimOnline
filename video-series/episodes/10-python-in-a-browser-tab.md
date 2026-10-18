# Episode 10 · Python in a browser tab

Published video: [Python in a Browser Tab: Pyodide and WebAssembly · Drawing with Code 10](https://www.youtube.com/watch?v=FwW81F7Zx2o&list=PLXaiuWr3VAhk) · [series playlist](https://www.youtube.com/playlist?list=PLXaiuWr3VAhk)

| | |
|---|---|
| Track | Deep dive |
| Target length | about 17 min (segment estimates; set final timing from the narration audio) |
| Builds on | Episodes 1–9; comfortable with the idea of a web page running JavaScript |
| QR codes | q10-01 … q10-05 |

Facts to re-check before recording (from `src/unified-worker.js`, `src/manim-client.js`,
`docs/rendering.md`): Pyodide version, the 90-second deadline, 15 fps sampling,
120 s / 1800-frame preview cap, 32 MiB result limit, on-demand packages.

## Learning goals

- Explain why ManimOnline runs Python in the browser rather than on a server.
- Describe WebAssembly and Pyodide at a conceptual level.
- Explain why Python runs in a Web Worker, and why only the page can stop it.
- Explain fresh namespaces and stale-result guards.
- Follow a render from source code to frame data, SVG, and an encoded video.

## Script

### 10.1 Cold open: where is this Python? · ≈ 1:00

**Visual.** [V10.1a] q10-01 running in ManimOnline: three lines write themselves:
"Python 3.12…", "sys.platform = emscripten", "machine = wasm32". [V10.1b] The same
file run in a terminal on a laptop prints "darwin" and "arm64" instead. Side by side.
[V10.1c] The word "emscripten" and "wasm32" are circled.

**QR q10-01** appears at [V10.1a], 8 seconds. Caption: "q10-01 · Where is this Python running?".

> Here is a scene that asks Python a simple question: where am I running? Run it on a laptop, and it says something like darwin, or linux, or windows, and names the computer's processor.
>
> Run it in ManimOnline, and it gives a much stranger answer. Platform: emscripten. Machine: wasm thirty two.
>
> Those words mean this Python isn't running on your operating system at all. It's running inside your web browser, inside a single tab, on an imaginary processor that the browser provides. This episode is about how that works, and about the surprisingly delicate problem of stopping it.

### 10.2 Why not just use a server? · ≈ 1:40

**Visual.** [V10.2a] Diagram: a browser on the left, a server rack on the right. Code
travels from browser to server; video travels back. [V10.2b] Problems appear as red
tags on the server: "cost per render", "queue", "strangers' code", "isolation", "storage".
[V10.2c] The server fades; a dashed outline remains, labelled "static site: just files".
The browser grows a small Python logo inside it.

> The obvious way to build a website that runs Manim is to put Manim on a server. Your browser sends code; the server renders a video; the video comes back.
>
> But think about what that server is agreeing to do. Run arbitrary code, written by anyone on the internet. That code could loop forever, fill the disk, or try to attack the machine it's running on. So every job would need a locked-down sandbox, limits on time and memory, and storage for every result. And every render costs real money, for every visitor, forever.
>
> ManimOnline is a static site: a folder of files hosted on GitHub Pages. There is no server-side program at all. So the Python has to run somewhere else. And the only computer available is the one the visitor already has.

### 10.3 WebAssembly and Pyodide · ≈ 2:20

**Visual.** [V10.3a] The Python interpreter, drawn as a box labelled "CPython (written
in C)". An arrow labelled "compile with Emscripten" leads to a box labelled
"WebAssembly". [V10.3b] Inside the browser: a sandbox boundary, with WebAssembly
running inside it next to JavaScript. [V10.3c] A progress bar labelled "first visit:
download the interpreter" fills; a second visit skips it. [V10.3d] q10-03 plays: dots
from `np.linspace`. A small package icon labelled "NumPy" flies in before the scene
runs; caption: "loaded only because this file says np".

**QR q10-03** appears at [V10.3d], 8 seconds. Caption: "q10-03 · NumPy, loaded on demand".

> The trick is WebAssembly. Browsers can run a compact, low-level kind of program called WebAssembly, safely sandboxed, and nearly as fast as native code.
>
> And the standard Python interpreter is itself a program, written in C. Compile that C to WebAssembly instead of to your laptop's processor, and you get a Python interpreter that runs inside a web page. That project is called Pyodide. Those strange words from the opening, emscripten and wasm thirty two, are the names of the compiler toolchain and of the imaginary processor.
>
> The cost is a download. The interpreter is several megabytes, which is why the first render on your first visit takes a while. After that, the browser keeps a copy.
>
> Libraries are downloaded only when they're needed. ManimOnline looks at your code before running it, and if it mentions NumPy, it fetches NumPy first. This scene says n p, so NumPy is loaded. A scene that never mentions it doesn't pay for it. The same goes for a few other packages, like the one that lays out graphs.
>
> And what about Manim itself? That's a story for next episode. The short version: the real Manim depends on libraries that aren't available here, so ManimOnline brings its own engine, written in plain Python, that runs inside Pyodide.

### 10.4 The cook who cannot be interrupted · ≈ 2:40

**Visual.** [V10.4a] A cartoon kitchen. One cook stands at a single stove labelled
"main thread". Order tickets arrive: "user clicked", "draw frame", "key pressed". The
cook handles them one at a time from a queue labelled "event loop". [V10.4b] A ticket
"run Python: while True" arrives; the cook starts stirring and never stops. Tickets pile
up; the page freezes (a frozen cursor icon). [V10.4c] A second cook, labelled "worker",
gets her own stove in a separate room. The Python ticket goes to her. The first cook
keeps serving the page. [V10.4d] A kitchen timer is set inside the worker's room, to
stop her after 90 seconds. It rings, but the ticket "check the timer" just joins her
queue, behind the loop that never ends. A red "✗". [V10.4e] Outside, the first cook
holds a stopwatch. At 90 seconds, or when "Cancel render" is pressed, he opens the door
and dismisses the worker; a fresh worker arrives for the next order.

> Now the delicate part. A web page's main thread is like a kitchen with one cook. Clicks, key presses, animations, drawing: everything is an order ticket, and the cook handles them one at a time. That's fine as long as each order is quick.
>
> But Python code can take a long time. And it can take forever: a loop that never ends. If that ran on the main thread, the cook would be stuck stirring one pot, and the whole page would freeze. You couldn't even click a button to stop it.
>
> So ManimOnline gives Python its own cook, in its own kitchen: a Web Worker, a separate thread. The page stays responsive while the worker runs your scene.
>
> Here's the subtle part. You might think: just set a timer inside the worker, and stop after ninety seconds. But that timer is also just an order ticket, and it joins the queue behind the Python code that's running. If that code never finishes, the worker never gets round to reading the timer. A timeout inside a busy worker can't interrupt it.
>
> The only one who can stop the worker is someone outside it. So the main page keeps the stopwatch. When ninety seconds pass, or you press Cancel render, or you edit the code so the old result no longer matters, the page simply terminates the worker, and starts a new one for the next render.
>
> That's why Cancel render is instant, even for code that's stuck. The trade-off is that a terminated worker loses its loaded Python, so the next render takes a few seconds to start it again.

### 10.5 Fresh starts and stale answers · ≈ 1:50

**Visual.** [V10.5a] Two renders side by side, each in a fresh, empty box labelled
"namespace". A variable defined in the first box does not exist in the second.
[V10.5b] A timeline race: edit A starts render A (slow); edit B starts render B (fast).
Render B finishes first and is shown; then render A finishes late. Each result carries
a revision number. A's result is stamped "revision 1 < current 2" and dropped into a
bin. [V10.5c] Caption: "show only the newest answer".

> Two more pieces of care make the editor trustworthy.
>
> First, every render starts fresh. Your code runs in a brand new, empty namespace, with ManimOnline's library definitions rebuilt. So nothing left over from an earlier version of your code can quietly affect this one. If it works now, it's because of what's on the screen.
>
> Second, answers can arrive out of order. Suppose you edit, a render starts, and then you edit again. The second render might finish before the first. Without care, the late, outdated result could overwrite the newer one. So every render is stamped with a revision number, and the page only accepts results that match the current revision. Anything older is quietly thrown away. The same rule protects loads from the gallery and from HashBin: if you've typed since asking, your newer edits win.

### 10.6 From Python objects to frames · ≈ 2:30

**Visual.** [V10.6a] q10-02: a dot glides left to right, leaving one small blue dot
behind per frame; a counter above shows "frames so far". It ends near 60. [V10.6b] A
zoom on one frame: it unfolds into a tree of nested boxes: "scene" → "group" → "circle",
each with fields like points, colour, opacity. Caption: "one frame = a snapshot of
every mobject". [V10.6c] Two consecutive frames side by side; most boxes are identical
and turn grey. They merge into a single shared box referenced from both frames, labelled
"pooled". The arrow to the page is labelled "≤ 32 MiB".

**QR q10-02** appears at [V10.6a], 8 seconds. Caption: "q10-02 · One dot per frame".

> So what does the worker actually produce? Not a video. Frames.
>
> As your scene runs, every play and every wait advances a clock, fifteen times per second of animation. At each tick, the engine takes a snapshot of everything on screen: every shape's points, colours, opacity and position. This scene makes that visible: an updater drops a little dot at the moving dot's position on every frame, so you can literally count them. Four seconds, about sixty dots.
>
> Each snapshot is written as structured data: a tree of objects, which is sent from the worker to the page.
>
> That could be a lot of data. A two-minute scene is eighteen hundred frames, and many of them contain hundreds of shapes. But most of a scene doesn't change from one frame to the next. So before sending, identical pieces are pooled: an unchanged shape is sent once, and every frame that contains it simply refers back to it. In 3D, a shape that only turns can even be sent as "the same as before, rotated". Even so, there's a ceiling: results over thirty two megabytes are refused, and that's one reason for the preview-length limits you met last episode.

### 10.7 Drawing, playing and measuring · ≈ 1:50

**Visual.** [V10.7a] A frame tree turning into SVG markup: `<path d="M … C …">`,
with the C commands highlighted as cubic Bézier curves (callback to episode 4).
[V10.7b] The player: a strip of pre-built frames; the seek bar jumps between them
instantly. [V10.7c] q10-04: three formulas with tight yellow boxes. A diagram of two
passes: pass one with estimated boxes (slightly wrong sizes); the page measures each
formula with MathJax; pass two with exact boxes.

**QR q10-04** appears at [V10.7c], 8 seconds. Caption: "q10-04 · Measured formulas".

> On the page, a renderer turns each frame into S V G, the vector picture format browsers draw natively. Every outline becomes an S V G path, and its commands are, once again, cubic Bézier curves. Episode four all the way down.
>
> Because every frame is computed before playback starts, the player is just a flipbook. Seeking is instant: jump to any frame and draw it.
>
> Formulas need one extra round trip. Python can't measure MathJax glyphs, because MathJax lives in the page. So on the first pass, the engine estimates the size of each new formula, and lists the ones it guessed. The page typesets and measures them, then asks for a second render with the real sizes. That's why the boxes around these formulas fit so snugly. A guess wouldn't.

### 10.8 Turning frames into a video file · ≈ 2:00

**Visual.** [V10.8a] q10-05: a clock face with a hand turning once per second, a
seconds readout and a frame counter. [V10.8b] Frames flow into a box labelled
"VideoEncoder (WebCodecs)"; compressed packets come out. Each packet is stamped with a
timestamp computed as "frame number ÷ 15". [V10.8c] A contrasting bad version: packets
stamped with "time on the wall clock when encoded"; because encoding speed varies, the
timestamps are uneven and the clock in the video stutters. [V10.8d] An MP4 file drawn
as two blocks: a small index block "moov" placed before a large data block "mdat".
Caption: "index first: playback can start immediately".

**QR q10-05** appears at [V10.8a], 8 seconds. Caption: "q10-05 · A frame clock".

> Finally, exporting a video. Modern browsers include a video encoder, available to web pages through an interface called WebCodecs. The page draws each frame, hands it to the encoder, and receives compressed video.
>
> One detail matters a lot. Each frame needs a timestamp: when it should appear in the video. You might be tempted to use the clock on the wall, the time each frame was encoded. But encoding speed varies: some frames are harder than others, and your computer is doing other things. Wall-clock timestamps would make the video stutter. So ManimOnline computes every timestamp from the frame number alone: frame forty five appears at exactly three seconds. This scene's clock is a good test. Export it, scrub through the video, and the readout always agrees with the video player.
>
> The encoded frames are then packaged into an MP4 or WebM file, entirely in memory. In the MP4, the index that describes where every frame lives is placed before the frame data, so a player can start showing the video without reading the whole file first.

### 10.9 Recap: the whole journey · ≈ 1:00

**Visual.** [V10.9a] The complete pipeline drawn left to right: editor → (1 s quiet) →
worker with Pyodide → fresh namespace → frames, pooled → page → SVG renderer → player;
a branch from the page to MathJax and back to the worker labelled "second pass"; a
branch to WebCodecs → MP4/WebM. A stopwatch hovers over the worker. [V10.9b] QR wall:
q10-01 to q10-05 for 10 seconds. [V10.9c] Teaser: two squares rotating side by side,
one labelled "Manim", one "manim-lite", moving identically (episode 11).

> Let's follow one render all the way through. You stop typing. The page sends your code to a worker running Python compiled to WebAssembly, with a stopwatch held outside. The code runs in a fresh namespace and produces a snapshot fifteen times a second. Identical pieces are pooled and sent to the page, which ignores anything stale, draws S V G, measures formulas, and plays the flipbook. And if you ask for a video, frames are encoded with timestamps computed from frame numbers alone.
>
> But we skipped the biggest question. If the real Manim can't run in the browser, what exactly is drawing these frames? And how could anyone know that it behaves the same? That's next time.
