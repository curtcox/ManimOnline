# Episode 9 · From sketch to shareable

| | |
|---|---|
| Track | Main |
| Target length | about 17 min (segment estimates; set final timing from the narration audio) |
| Builds on | Episodes 1–8 |
| QR codes | q09-01 … q09-05 |

Record the editor footage for this episode on the deployed site, with an empty
browser profile, so that first-load, offline and HashBin screens look as a new
viewer will see them. Do not show a real HashBin balance; use a test account.

## Learning goals

- Find and load examples from the Sample gallery.
- Choose a scene in a file with several scenes.
- Understand automatic rendering, Render animation, Cancel render and the limits.
- Export SVG and PNG frames, and MP4 or WebM videos.
- Share work with a link, and save it permanently with HashBin.
- Use ManimOnline offline, and recognise its Graphviz and modl modes.
- Build larger scenes in small, checkpointed steps.
- Know when and how to move to a full Manim installation.

## Script

### 9.1 Cold open: now what? · ≈ 0:40

**Visual.** [V9.1a] The recurring motif: three rounded boxes, "edit → render →
preview", joined in a loop. A fourth box fades in to the right: "share". [V9.1b] Quick
cuts from previous episodes' finished scenes, each shrinking into a thumbnail that
stacks into a pile.

> Over eight episodes, you've learned to draw, animate, write equations, plot graphs and fly a camera through three dimensions. You've probably made a few things of your own along the way.
>
> So: now what? How do you keep your work, turn it into a real video file, show it to a friend, or find inspiration for the next one? This episode is a practical tour of ManimOnline itself, from the first click to the finished, shareable thing.

### 9.2 The gallery · ≈ 1:20

**Visual.** [V9.2a] Screen recording: the "Sample gallery ↗" link opens the gallery
in a new tab. A grid of cards, each with a cover image and a title. [V9.2b] The search
box: typing "arrow" filters the cards. The language filter switches between all,
Manim, Graphviz and modl. [V9.2c] "▶ Play preview" on a card plays a short video in
place. [V9.2d] "Load in editor →" opens the editor with that sample rendered.

> The quickest way to learn what's possible is to look at what others have made. The Sample gallery opens in a new tab, so your current work stays put.
>
> Each card has a cover picture, and animated samples have a Play preview button, which plays a short pre-rendered video, without running any Python at all. You can search by title, and filter by language.
>
> When something catches your eye, choose Load in editor. The source opens and renders, ready for you to pull apart and change. And the editor remembers your edits in the page address, so reloading the page keeps your version, not the original.

### 9.3 Several scenes in one file · ≈ 1:20

**Visual.** [V9.3a] q09-01 in the editor: three classes, `Intro`, `Middle` and
`Outro`. The Scene field in the toolbar shows "Middle". The preview shows the
rotating blue square. [V9.3b] The cursor clears the field: the placeholder reads
"First scene", and the preview re-renders `Intro`. [V9.3c] The cursor types "O"; a
suggestion list offers the scene names; choosing `Outro` renders it.

**QR q09-01** appears at [V9.3a], 8 seconds. Caption: "q09-01 · Several scenes in one file".

> A single file can hold several scenes. That's handy for keeping the parts of a longer video together, sharing helper functions between them.
>
> The Scene field in the toolbar chooses which one to render. Leave it empty, and you get the first scene in the file. Start typing, and it suggests the scene names it found the last time the file rendered.
>
> This code opens with Middle selected, because the scene choice is saved along with the source. Try switching to Intro and Outro.

### 9.4 Rendering, and its limits · ≈ 2:00

**Visual.** [V9.4a] The editor: the user types, pauses; a subtle timer ring
completes after one second and the preview re-renders. [V9.4b] The "Render
animation" button is clicked; rendering starts immediately. [V9.4c] q09-05: the
"Runaway" scene, an infinite loop. The status shows the render in progress. "Cancel
render" is clicked; the render stops, and the editor stays responsive. [V9.4d] A
card lists the limits: "Previews: 15 frames per second", "Up to 120 seconds (1,800
frames) per preview", "Each render must finish within 90 seconds".

**On screen**

```python
while True:      # an infinite loop: the editor stops it after 90 seconds,
    pass         # or press Cancel render to stop it sooner
```

**QR q09-05** appears at [V9.4c], 8 seconds. Caption: "q09-05 · A scene that never ends".

> You have probably noticed that ManimOnline renders by itself. When you stop typing for about a second, it starts. If you don't want to wait, the Render animation button starts immediately, and it's also how you retry after an error.
>
> But what if your code never finishes? Programs can loop forever, and this one does, on purpose. Scan it if you like. The editor stays perfectly responsive, because the Python runs separately from the page. Press Cancel render, and that separate process is simply stopped. If you don't, the editor stops it for you after ninety seconds.
>
> There are a few other limits worth knowing. Previews run at fifteen frames per second, to keep rendering fast. A single preview can be up to a hundred and twenty seconds long. For longer videos, split them into several scenes. Episode ten explains why these limits exist, and how that "separate process" actually works.

### 9.5 Exporting pictures and videos · ≈ 1:50

**Visual.** [V9.5a] q09-02: three star polygrams draw, rotate and fill; the caption
"Export: MP4 video" writes. [V9.5b] The toolbar's Export menu opens: SVG frame, PNG
frame, MP4 video, WebM video. [V9.5c] With the seek bar part-way through, "SVG frame"
then Download: a file saves. Opening it shows crisp vector shapes at any zoom.
[V9.5d] "MP4 video", then Download: the button reads "Cancel video" while a status line
reports progress; the file saves and plays in a system video player.

**QR q09-02** appears at [V9.5a], 8 seconds. Caption: "q09-02 · Export me as a video".

> To keep what you've made, use the Export menu next to the Download button.
>
> S V G frame saves the current frame as a vector image, which stays sharp at any size. It's perfect for slides, posters or a blog post. P N G frame saves the current frame as an ordinary picture.
>
> MP4 and WebM save the whole animation as a video file. The video is encoded right there in your browser, from the frames it already computed. Nothing is uploaded anywhere. This needs a browser with built-in video encoding, which recent versions of the major browsers have, and if yours doesn't, the editor tells you.
>
> Keep in mind that these videos have the same frame rate as the preview, fifteen frames per second. That's great for sharing an idea quickly. For a polished, sixty-frames-per-second production, which is how this series is made, you'll want full Manim, and we'll come to that in a moment.

### 9.6 Sharing a link · ≈ 1:20

**Visual.** [V9.6a] The Share button is clicked; a long link appears in the box beside
it, already selected for copying. [V9.6b] The link is shown enlarged; the part after
"compressed=" is highlighted and labelled "your code, compressed". [V9.6c] "Shorten
link" produces a short link. [V9.6d] Editing the code invalidates the shown link;
Share is clicked again to make a new one.

> The quickest way to show someone your work is the Share button. It produces a link, and here's the surprising part: that link contains your entire program. The code is compressed, and tucked into the address itself, along with your scene choice and renderer settings. Anyone who opens it sees exactly what you saw.
>
> Because the code is inside the link, nothing is stored on a server, and it can never go missing. The price is length: bigger programs make longer links. Shorten link asks a public link-shortening service for a compact version, which is handy for chat messages, though it depends on that service being available.
>
> If you keep editing after you share, the old link still holds the old version, so share again when you're done.

### 9.7 Saving to HashBin · ≈ 1:40

**Visual.** [V9.7a] "Save to HashBin" is clicked. The first time, a connection step
appears. After returning, a dialog shows a price quote, the account balance (blurred),
and the retention period. "Save" is clicked. [V9.7b] The page address now ends in "#"
followed by a long string of letters and digits. Label: "CID: content identifier".
[V9.7c] The same CID typed into "HashBin CID or saved link" in another browser loads
the same scene. [V9.7d] The corner QR code from this segment enlarges, and the URL it
encodes is shown underneath: the same site, a "#", and a CID.

> For a short, permanent address that doesn't grow with your code, there's HashBin. Save to HashBin stores your source, together with your scene choice, and gives back a content identifier, a C I D, which becomes the end of the page's address.
>
> HashBin is a paid storage service, so the first time you'll connect an account, and before anything is saved, the editor shows you the price and how long the file will be kept. Loading saved work is free, and anyone can do it: paste a C I D or a saved link into the box beside the button, or simply open the link.
>
> And now you know what's inside every QR code in this series. Each one is a HashBin link. The content identifier isn't a random number: it's computed from the code itself, in a way that means it can only ever refer to that exact code. Episode twelve shows how that works, and why it means a QR code can't be quietly changed to point somewhere else.

### 9.8 Working offline · ≈ 0:50

**Visual.** [V9.8a] The toolbar status reads "Ready offline". [V9.8b] The laptop's
network icon switches off. The page is reloaded; it opens normally, and a gallery
sample renders. [V9.8c] Caption: "First visit needs a connection. Sharing and saving
need one too."

> After your first visit, ManimOnline quietly saves everything it needs on your device: the editor, the gallery, and the Python runtime. When that's finished, the toolbar says Ready offline. From then on, you can open the page and render scenes with no internet connection at all, on a plane, say. Only the things that genuinely need the internet, like saving to HashBin or shortening links, wait until you're back online.

### 9.9 Two more languages · ≈ 1:40

**Visual.** [V9.9a] q09-03 in the editor: a Graphviz `digraph` describing
ManimOnline's own pipeline. The Renderer selector reads "Auto"; the preview shows the
laid-out diagram. [V9.9b] The Engine menu switches from `dot` to `neato`; the layout
changes. [V9.9c] q09-04: the same idea written in modl, one node or edge per line. The
preview draws it; the cursor drags a node to a new position, and the arrows follow.

**QR q09-03** appears at [V9.9a], 8 seconds. Caption: "q09-03 · ManimOnline as a Graphviz diagram".
**QR q09-04** appears at [V9.9c], 8 seconds. Caption: "q09-04 · The workflow as a modl diagram".

> ManimOnline started life as an editor for diagrams, and it still speaks two diagram languages alongside Manim.
>
> Graphviz describes graphs: boxes, and arrows between them. You say what connects to what, and Graphviz works out the layout. This diagram, fittingly, is ManimOnline's own pipeline. The Engine menu chooses different layout styles.
>
> modl is a lighter language: one line per node or arrow, with shapes, colours and labels. Its diagrams are interactive, so you can drag nodes into place, and the positions are saved with your work.
>
> You never have to tell ManimOnline which language you're writing. It reads the code, recognises the style, and picks the right renderer. If it guesses wrong, the Renderer menu lets you choose.

### 9.10 A workflow that scales · ≈ 1:50

**Visual.** [V9.10a] A scene built up in stages: four versions of the same file,
each adding one element (the shape, then a label, then the animation, then the
camera move). After each addition, a green tick: "renders". [V9.10b] The file
reorganised into helper functions (`def labelled_dot(...)`) and constants at the top
(`COLOR_X = BLUE`); the same names light up across two scenes. [V9.10c] A side-by-side:
one huge scene versus three small scenes, with the Scene field switching between them.
[V9.10d] HashBin "checkpoints": three saved links, each annotated with what changed.

> A few habits make a big difference once your scenes grow beyond a few lines.
>
> Build in small steps. Add one thing, let it render, and check it, before adding the next. When something breaks, you'll know exactly what broke it. Because ManimOnline re-renders as you type, this rhythm comes almost for free.
>
> Give names to things you repeat. If you draw three labelled dots, write a little function that makes a labelled dot. If x is always blue, define a constant for that colour at the top of the file and use it everywhere. Then changing your mind is a one-line edit.
>
> Prefer several short scenes to one long one. They render faster, they stay under the preview limit, and you can perfect each part on its own.
>
> And keep checkpoints. A share link, or a HashBin save, is a snapshot of your work at that moment. Make one whenever something works, and you can always go back.

### 9.11 Graduating to full Manim · ≈ 1:20

**Visual.** [V9.11a] A terminal window: `pip install manim`, then
`manim -pql scene.py SquareToCircle`. A video window pops up. [V9.11b] The flags are
labelled: `-p` "play when done", `-ql` "quality: low (fast)"; then `-qh` "quality: high".
[V9.11c] A two-circle diagram: a large circle "Manim Community" containing a smaller
circle "ManimOnline subset". Arrows: "code that works in ManimOnline is written for
Manim" and, from the outer ring, "not everything in Manim runs in ManimOnline".

> At some point, you may want full Manim on your own computer: for sixty-frame-per-second, high-resolution video, for very long scenes, or for features ManimOnline doesn't support.
>
> The Manim Community documentation walks you through installing it. Then you run your scene from a terminal: manim, a quality flag, your file, and the scene's name. Your code moves across almost unchanged, because ManimOnline's goal is to behave like Manim Community for everything it supports.
>
> But be clear about the direction. ManimOnline runs a compatibility subset, not all of Manim. Most of what you write in ManimOnline should run in Manim. Not everything written for Manim will run in ManimOnline, and when it can't, it says so.

### 9.12 Recap: the end of the main track · ≈ 0:50

**Visual.** [V9.12a] The motif loop "edit → render → preview → share" lights box by
box, each with an icon from this episode. [V9.12b] QR wall: q09-01 to q09-05 for 10
seconds. [V9.12c] A fork in the road: one path labelled "keep making things", the other
"how does it work?", leading to a closed door marked "10".

> Gallery for inspiration. Scenes chosen by name. Rendering that you can always cancel. Exports as pictures and videos, links that carry your code, and HashBin for permanent, short addresses. Offline whenever you need it, with diagrams on the side.
>
> That's the end of the main track. You now know enough to make real explanations. If you've ever wondered how a website runs Python with no server, or how you'd even check that a homemade animation engine behaves like the real one, the next three episodes open the hood.
