# Episode 12 · Links that carry code

Published video: [Links That Carry Code: Compression, Hashes and QR Codes · Drawing with Code 12](https://www.youtube.com/watch?v=u7ArYmhyNxE&list=PLXaiuWr3VAhk) · [series playlist](https://www.youtube.com/playlist?list=PLXaiuWr3VAhk)

| | |
|---|---|
| Track | Deep dive (series finale) |
| Target length | about 16 min (segment estimates; set final timing from the narration audio) |
| Builds on | Episodes 9 and 10 |
| QR codes | q12-01 … q12-04 |

Facts to re-check before recording (from `src/share-links.js`, `src/hashbin.js`,
`service-worker.js`): Share links use lz-string's URL-safe compression; CIDs are a
6-byte length plus either the content (64 bytes or fewer) or its SHA-512 digest,
in URL-safe base64; non-inline content loads from 256t.us and can expire.

## Learning goals

- Explain the two ways ManimOnline shares code without its own server.
- Explain dictionary compression with back-references (the Lempel–Ziv idea).
- Describe a cryptographic hash's key properties, including the avalanche effect.
- Read the anatomy of a HashBin content identifier, including inline content.
- Explain why content-addressed links suit QR codes, and what can still go wrong.
- Describe, briefly, how the editor itself stays available offline.

## Script

### 12.1 Cold open: a program in a square · ≈ 1:00

**Visual.** [V12.1a] A single QR code fills the screen: q12-03. [V12.1b] The camera
pulls back to show the URL it encodes beneath it; the part after "#" is highlighted.
[V12.1c] That highlighted string is decoded on screen, character group by character
group, into: `digraph{scan->load->edit->render->share->scan}`. [V12.1d] The decoded
text drops into the editor, and the Graphviz diagram appears: five words in a loop.

**QR q12-03** appears at [V12.1a] and stays for 12 seconds. Caption: "q12-03 · A program inside its own address".

> This QR code doesn't point to a program stored somewhere. It is the program.
>
> Scan it, and the address it holds contains, spelled out in a compact alphabet, a tiny Graphviz diagram: scan, load, edit, render, share, and back to scan. No server needed to look it up, because there's nothing to look up.
>
> Most programs are far too big to fit inside an address like that. But this little one shows the destination of this final episode: how a static website, with no database of its own, lets you share code through links and QR codes, and why those links can be trusted.

### 12.2 The problem · ≈ 1:20

**Visual.** [V12.2a] Two browsers, "you" and "a friend", with no line between them.
A server icon appears between them, then is crossed out: "no server of our own".
[V12.2b] Two paths appear: path A, "put the code in the link", and path B, "store the
code somewhere, by name". [V12.2c] Under path B, a question: "who chooses the name?"

> When you click Share, where does your code go? ManimOnline has no server of its own and no database. It's just files. So it has two options.
>
> Option one: put the code inside the link itself. Option two: store the code somewhere, and put a name for it in the link. Both are used, and each solves a different problem. And option two hides a really interesting question: who gets to choose the name?

### 12.3 Code inside the link · ≈ 1:30

**Visual.** [V12.3a] The `SquareToCircle` source (249 characters). Each space, newline,
colon, comma and equals sign becomes a percent code as `encodeURIComponent` makes it
URL-safe (the editor's own encoding); a character counter climbs to 391. [V12.3b] A browser address bar stretches comically to fit it. [V12.3c]
The source is highlighted for repetition: `self.play(` twice, `Transform`/`Create`,
`color=`, the indentation runs. Each repeat glows the same colour as its first
appearance.

> The first option sounds easy. Take the source code, and put it in the address after a hash sign, the part of a link that browsers never send to a server.
>
> But addresses have rules: spaces, new lines, colons and equals signs aren't allowed as they are, so each one gets replaced by a three-character code. Our little scene grows from two hundred and forty nine characters to three hundred and ninety one. Real scenes get long fast.
>
> Look at the code again, though. It repeats itself. Self dot play, twice. Indentation, over and over. Colour equals, twice. Code is full of repetition, and repetition is exactly what compression feeds on.

### 12.4 Saying "same as before" · ≈ 2:30

**Visual.** [V12.4a] q12-01 plays: the sentence "the cat sat on the mat; the cat sat"
written across the top in fixed-width letters. [V12.4b] Letters are copied down one
at a time into a second row. When the scan reaches "at " in "sat", a green box
highlights the earlier "at " in "cat", a yellow box highlights the repeat, and a token
`(4,3)` drops into the output: "go back 4, copy 3". [V12.4c] The same happens for
"the " (back 15, copy 4), " the " (back 9, copy 5) and "cat sat" (back 24, copy 7).
[V12.4d] The summary: "35 characters became 16 letters and 4 references".

**QR q12-01** appears at [V12.4b], 10 seconds. Caption: "q12-01 · LZ compression, step by step".

> Here's the core idea of a whole family of compression methods, first described by Abraham Lempel and Jacob Ziv in the late nineteen seventies.
>
> Read the text from left to right. Whenever the next few characters have appeared before, don't write them out again. Write a note instead: go back this many characters, and copy this many.
>
> At first everything is new, so letters are copied as they are. But "at space", in "sat", already appeared in "cat", four characters back. So we write: back four, copy three. Later, "the" reappears, fifteen characters back. And "cat sat" at the end can be copied in one go from twenty four characters back.
>
> Thirty five characters became sixteen letters and four references. On a short sentence that's a modest saving. On source code, where whole lines repeat, it's dramatic, and decompressing is just following the notes.
>
> ManimOnline's Share button uses a library called lz-string, from the same family. It builds a dictionary of phrases it has already seen, and writes its output in characters that are safe to put straight into a link.

### 12.5 Where links run out · ≈ 1:10

**Visual.** [V12.5a] Two QR codes side by side: on the left, one encoding a short
address (sparse); on the right, one encoding a compressed share link for a full scene
(dense, with tiny modules). A phone camera icon struggles with the right one, shown
small on a video frame. [V12.5b] Text: "longer link → more modules → smaller dots".

> Compressed links are wonderful: nothing to store, nothing to expire, and the code travels with the link. But they still grow with the code. And a QR code's size grows with the length of what it holds. A compressed link to a full scene makes a dense code, with dots too small to scan comfortably from a video in the corner of a screen.
>
> For this series, we wanted short, fixed-length links that point to code of any size. That needs option two.

### 12.6 Fingerprints for data · ≈ 2:20

**Visual.** [V12.6a] A machine labelled "SHA-512". "Hello, Manim" goes in; a 512-bit
fingerprint comes out, shown as a grid of 16 rows by 32 squares: yellow for 1, dark
blue for 0. [V12.6b] q12-02: "Hello, Manin" (one letter changed) goes in; its grid
appears beside the first. Red outlines mark every square that differs; they're
scattered everywhere. "266 of 512 bits changed". [V12.6c] A huge book goes in; a grid
of exactly the same size comes out. [V12.6d] Three property cards: "same input → same
fingerprint", "tiny change → completely different", "no practical way to find another
input with the same fingerprint".

**QR q12-02** appears at [V12.6b], 10 seconds. Caption: "q12-02 · The avalanche effect".

> Option two needs a name for each piece of code. And here's the elegant answer: let the code name itself.
>
> A cryptographic hash function is a machine that takes any data, a word or a whole library, and produces a fixed-size fingerprint. The one used here, called SHA five twelve, produces five hundred and twelve bits, shown here as a grid of squares.
>
> It has three properties that matter. First, it's deterministic: the same input always gives the same fingerprint, on any computer, forever.
>
> Second, the avalanche effect. Change one letter, Manim to Manin, and about half of the bits flip: two hundred and sixty six of five hundred and twelve in this case, scattered with no visible pattern. A small change to the code doesn't give a similar fingerprint. It gives an unrelated one.
>
> Third, nobody knows any practical way to work backwards, or to find two different inputs with the same fingerprint. So in practice, a fingerprint stands for exactly one piece of data.
>
> Scan this one and change either message. Every edit reshuffles the grid.

### 12.7 Anatomy of a content address · ≈ 2:10

**Visual.** [V12.7a] q12-04: two addresses, each split into coloured parts. The top
one, for `digraph{a->b}`: a blue 8-character prefix labelled "length: 13 bytes", then a
yellow part labelled "the content itself (inline)". The bottom one, for a longer
source: the same blue prefix structure, then 86 yellow characters labelled "SHA-512
fingerprint of the content". [V12.7b] The yellow part of the top address is decoded
back into `digraph{a->b}`. [V12.7c] A store, labelled "HashBin", holds a shelf of
boxes; each box is labelled with its own content address. A request arrives for one
address; the matching box is handed back. [V12.7d] A reader recomputes the fingerprint
of the box's contents and compares it with the label: a green check.

**QR q12-04** appears at [V12.7a], 10 seconds. Caption: "q12-04 · Anatomy of a content address".

> HashBin, the storage service ManimOnline saves to, names everything this way. Its addresses are called content identifiers, or C I Ds, and they have two parts.
>
> The first eight characters encode the content's length in bytes. The rest depends on the size. If the content is sixty four bytes or less, the rest is simply the content itself, written in a link-safe alphabet. That's what our opening QR code was: an address that contains its own content, so nothing needs to be fetched at all.
>
> For anything longer, the rest is the content's SHA five twelve fingerprint. To load it, the editor asks HashBin's server for the content with that name.
>
> Now think about what this means. The name isn't chosen by anyone. It's calculated from the content. If someone changed a single character of a stored scene, it would have a different fingerprint, and so a different name. The old address can only ever mean the original bytes. And because the recipe is public, anyone can download the content, recompute its fingerprint, and check that it matches.

### 12.8 Why these QR codes work · ≈ 1:40

**Visual.** [V12.8a] One of the series' QR codes, with its URL beneath: site + "#" +
94-character CID. A ruler shows that every CID has the same length, whatever the size
of the scene. [V12.8b] The QR code's anatomy: three large finder squares at the
corners; the data modules; a portion is smudged out, and the code still scans.
Caption: "error correction: part of the code is redundancy". [V12.8c] A calendar icon
with a retention period, labelled "stored content must be kept paid for"; next to it,
an inline CID labelled "never expires".

> So every QR code in this series encodes the ManimOnline address, a hash sign, and a C I D. That's about a hundred and thirty characters, whether the scene behind it is five lines long or a hundred. Short, fixed-length links make QR codes with comfortably large dots.
>
> QR codes also carry error correction: a portion of each code is redundant, so it still scans if part of it is blurred by video compression or hidden behind your thumb.
>
> And because the addresses are computed from the code, we knew every QR code's address before anything was uploaded. Saving the exact same bytes always produces the same name.
>
> There is one honest caveat. A content address guarantees what the content is, not that someone is still storing it. HashBin keeps content for a retention period that's paid for in advance. If that lapses, the address still means the same code, but nobody is serving it any more. Inline addresses, like the opening one, can never expire, because there's nothing to serve.

### 12.9 An editor that keeps itself · ≈ 1:20

**Visual.** [V12.9a] The ManimOnline files listed as a manifest with a version
number. A service worker, drawn as a small librarian, copies every file into a local
cabinet. The status reads "Ready offline" only when the last file is in. [V12.9b] A
new version is announced; the librarian fills a second cabinet completely before
switching over. An open editor tab, with unsaved code, keeps that code through the
switch.

> One last piece completes the picture. The editor itself is just files too, and the same care about exact content applies to them.
>
> A service worker, a small script that browsers let a site install, keeps a complete local copy of an exact, versioned list of the editor's files, including the Python runtime. Only when every file is safely stored does the editor say Ready offline. When a new version is released, the new set is downloaded in full before it replaces the old one, so you never end up running half of one version and half of another. And unsaved code in an open tab is preserved through the switch.

### 12.10 Series finale · ≈ 1:30

**Visual.** [V12.10a] The full series in one zoom-out: the square becoming a circle;
the Bézier construction; the equation solving itself; the circle unrolling into a sine
wave; the Riemann rectangles; the helix; the worker kitchen; the two engines
overlapping; the cat-sat compression; the fingerprint grid. Each shrinks into a tile,
and the tiles arrange themselves into the shape of a QR code. [V12.10b] QR wall:
q12-01 to q12-04 for 10 seconds. [V12.10c] The final frame: the trailer's Showcase
scene QR (q00-01) and the words "Now make something."

> Links can carry code in two ways. They can contain it, compressed by noticing what's been said before. Or they can name it, by its own fingerprint, so that the name can never be pointed at anything else.
>
> And that brings us full circle. We started by noticing that an animation is a stack of frames, and that a precise description of change is a program. We gave that program nouns and verbs, curves and equations, things that change, graphs and cameras. Then we looked underneath: Python running inside a browser tab, an engine rebuilt and measured until it matches, and links that carry the code you write.
>
> Every scene in this series is one scan away, ready for you to change. The best way to understand any of it is to break it, fix it, and make it your own. <break time="0.8s" /> So go and make something.
