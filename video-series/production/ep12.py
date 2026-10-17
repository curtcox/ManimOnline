"""Episode 12 · Links that carry code. One Scene per script segment.

    python3 video-series/production/render.py 12 [-ql] [segment ...]

Shot ids in comments ([V12.6b] ...) refer to episodes/12-links-that-carry-code.md.
Every encoded string on screen is computed here (percent encoding, base64, SHA-512, the LZ
tokens) or copied from a real run (the share link, the offline manifest), never invented.
"""
import base64
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import *  # noqa: E402,F403
from ep09 import SHARE_PAYLOAD, SITE, backed, box, check_mark, chip, cross_mark, file_icon, labelled_box, note  # noqa: E402
from ep10 import cook, server_rack  # noqa: E402

LZ_SNIPPET = 'ep12/01-lz-compression.py'
AVALANCHE_SNIPPET = 'ep12/02-avalanche.py'
TINY_SNIPPET = 'ep12/03-tiny.dot'
CID_SNIPPET = 'ep12/04-cid-anatomy.py'

LINKS = {row['id']: row for row in json.loads((SERIES / 'qr-links.json').read_text())}
SHARE_QR = json.loads((PRODUCTION / 'ep12-share-qr.json').read_text())   # the q09-01 share link, level M
MANIFEST_VERSION, LOCAL_FILES, REMOTE_FILES = 'manimonline-offline-v373', 258, 8
# q12-03 laid out by `dot -Tplain` (Graphviz 16.1), in inches: name: (x, y, width).
TINY_NODES = {'scan': (0.90919, 4.25, 0.75823), 'load': (0.53419, 3.25, 0.75), 'edit': (0.53419, 2.25, 0.75),
              'render': (0.47864, 1.25, 0.95727), 'share': (0.90919, 0.25, 0.84354)}
TINY_BACK = [(0.97682, 0.50029), (1.0142, 0.64353), (1.0569, 0.83071), (1.0759, 1), (1.1993, 2.1044), (1.1391, 2.3937),
             (1.0342, 3.5), (1.0236, 3.6114), (1.006, 3.7314), (0.98722, 3.8415)]


def encode_uri_component(text):
    """JavaScript's encodeURIComponent, which the editor uses for addresses."""
    return quote(text, safe="-_.!~*'()")


def b64(data):
    return base64.urlsafe_b64encode(data).decode().rstrip('=')


def lz77(text, min_match=3):
    """q12-01's greedy LZ77: each token is (position, distance back, length); distance 0 is a literal."""
    tokens, i = [], 0
    while i < len(text):
        best_length, best_distance = 0, 0
        for start in range(i):
            length = 0
            while i + length < len(text) and text[start + length] == text[i + length]:
                length += 1
            if length > best_length:
                best_length, best_distance = length, i - start
        if best_length >= min_match:
            tokens.append((i, best_distance, best_length))
            i += best_length
        else:
            tokens.append((i, 0, 1))
            i += 1
    return tokens


def bits_of(data):
    digest = hashlib.sha512(data).digest()
    return [(byte >> (7 - k)) & 1 for byte in digest for k in range(8)]


def bit_grid(bits, cell=0.14):
    squares = VGroup(*[Square(cell, stroke_width=0, fill_opacity=1, fill_color=YELLOW if bit else BLUE_E) for bit in bits])
    return squares.arrange_in_grid(rows=16, cols=32, buff=0)


def matrix_code(rows, height):
    """A QR matrix (rows of 0/1) drawn like qr_code, with a 4-module quiet zone."""
    quiet = 4
    module = height / (len(rows) + 2 * quiet)
    backing = Square(side_length=height).set_fill(WHITE, 1).set_stroke(width=0)
    top_left = backing.get_corner(UL) + (RIGHT + DOWN) * quiet * module
    modules = VGroup()
    for r, row in enumerate(rows):
        for match in re.finditer(r'1+', row):
            run = match.end() - match.start()
            rect = Rectangle(width=run * module * 1.01, height=module * 1.04).set_fill(BLACK, 1).set_stroke(width=0)
            rect.move_to(top_left + RIGHT * (match.start() + run / 2) * module + DOWN * (r + 0.5) * module)
            modules.add(rect)
    return VGroup(backing, modules)


def mono(text, size=22, color=GREY_A):
    return Text(text, font=MONO, font_size=size, color=color)


def wrapped(text, width, size=20, color=GREY_A):
    return VGroup(*[mono(text[i:i + width], size, color) for i in range(0, len(text), width)]).arrange(DOWN, aligned_edge=LEFT, buff=0.1)


def tiny_graph(scale=1.0):
    """q12-03 drawn where dot puts it: five ellipses in a loop."""
    nodes = {}
    for name, (x, y, w) in TINY_NODES.items():
        shape = Ellipse(width=w * scale, height=0.5 * scale).set_stroke(GREY_A, 2).set_fill('#22262d', 1)
        nodes[name] = VGroup(shape, Text(name, font_size=int(20 * scale)).move_to(shape)).move_to([x * scale, y * scale, 0])
    order = ['scan', 'load', 'edit', 'render', 'share']
    edges = VGroup(*[Arrow(nodes[a].get_bottom(), nodes[b].get_top(), buff=0.03, color=GREY_B, stroke_width=3,
                           max_tip_length_to_length_ratio=0.3) for a, b in zip(order, order[1:])])
    back = VMobject().set_points_smoothly([[x * scale, y * scale, 0] for x, y in TINY_BACK]).set_stroke(GREY_B, 3)
    end, before = back.get_end(), back.point_from_proportion(0.95)
    head = Triangle().set_fill(GREY_B, 1).set_stroke(width=0).scale(0.08)
    head.rotate(angle_of_vector(end - before) - PI / 2).move_to(end)
    group = VGroup(*nodes.values(), edges, back, head)
    return group.move_to(ORIGIN)


# ---------------------------------------------------------------- 12.1

class Segment_12_1(Segment):
    """Cold open: a program in a square (q12-03)."""
    EPISODE, SEGMENT = 12, '12.1'

    def construct(self):
        # [V12.1a] q12-03 fills the screen
        link = LINKS['q12-03']
        code = qr_code('q12-03', 6.4)
        self.add(code)
        self.wait(3.0)

        # [V12.1b] pull back: the address it holds, the part after # highlighted
        self.at('Scan it')
        card = qr_card('q12-03')
        cid = link['cid']
        address = VGroup(mono(SITE + '#', 22, GREY_A), wrapped(cid, 36, 22, FOCUS)).arrange(DOWN, aligned_edge=LEFT, buff=0.12)
        address.move_to(UP * 2.2)
        self.play(ReplacementTransform(code, card[2]), FadeIn(card[:2]), FadeIn(address), run_time=1.5)

        # [V12.1c] decoded group by group: 8 characters of length, then 4 characters for every 3
        self.at('spelled out in a compact alphabet')
        source = snippet_source(TINY_SNIPPET).strip()
        prefix, body = cid[:8], cid[8:]
        rows = VGroup()
        head = VGroup(mono(prefix, 24, BLUE), mono('→', 24, GREY_B), note(f'length: {len(source.encode())} bytes', 22, BLUE)).arrange(RIGHT, buff=0.25)
        rows.add(head)
        groups = [body[i:i + 4] for i in range(0, len(body), 4)]
        decoded = [base64.urlsafe_b64decode(g + '=' * (-len(g) % 4)).decode() for g in groups]
        pairs = VGroup(*[VGroup(mono(g, 22, FOCUS), mono(d, 22, WHITE)).arrange(DOWN, buff=0.1) for g, d in zip(groups, decoded)])
        pairs.arrange_in_grid(rows=2, buff=(0.25, 0.3))
        rows.add(pairs)
        rows.arrange(DOWN, buff=0.35).move_to(DOWN * 0.6).to_edge(LEFT, buff=0.5)
        self.play(FadeIn(head))
        self.play(LaggedStart(*[FadeIn(p, shift=DOWN * 0.1) for p in pairs], lag_ratio=0.12), run_time=3)
        program = mono(source, 26, WHITE).next_to(rows, DOWN, buff=0.35).align_to(rows, LEFT)
        self.play(TransformFromCopy(VGroup(*[p[1] for p in pairs]), program), run_time=1.2)

        # [V12.1d] it is a Graphviz diagram: five words in a loop
        self.at('scan, load, edit, render, share')
        graph = tiny_graph(0.75).move_to([1.6, -1.3, 0])
        self.play(FadeOut(VGroup(head, pairs)), program.animate.next_to(address, DOWN, buff=0.4).align_to(address, LEFT))
        self.play(FadeIn(graph, lag_ratio=0.1), run_time=1.5)
        self.at('nothing to look up')
        nothing = note('no server needed: the address is the content', 26, AFTER).to_edge(LEFT, buff=0.5).shift(DOWN * 1.6)
        self.play(FadeIn(nothing))
        self.at('Most programs are far too big')
        self.play(FadeOut(VGroup(nothing, graph)))
        trust = VGroup(note('share code through links and QR codes', 28, GREY_A), note('and know the links can be trusted', 28, FOCUS))
        trust.arrange(DOWN, buff=0.3).move_to(DOWN * 1.4).to_edge(LEFT, buff=0.6)
        self.at('lets you share code')
        self.play(FadeIn(trust[0]))
        self.at('can be trusted')
        self.play(FadeIn(trust[1]))
        self.finish()


# ---------------------------------------------------------------- 12.2

class Segment_12_2(Segment):
    """The problem."""
    EPISODE, SEGMENT = 12, '12.2'

    def construct(self):
        # [V12.2a] you, a friend, and no server of our own
        you = browser_icon(3.0, 2.0).move_to([-4.8, 1.6, 0])
        friend = browser_icon(3.0, 2.0).move_to([4.8, 1.6, 0])
        tags = VGroup(note('you', 26, GREY_A).next_to(you, UP, buff=0.15), note('a friend', 26, GREY_A).next_to(friend, UP, buff=0.15))
        self.play(FadeIn(you), FadeIn(friend), FadeIn(tags))
        self.at('no server of its own')
        server = server_rack().scale(0.8).move_to([0, 1.6, 0])
        self.play(FadeIn(server))
        no = cross_mark(0.6).move_to(server)
        tag = note('no server of our own', 24, WARNING).next_to(server, DOWN, buff=0.3)
        self.play(Create(no), FadeIn(tag))
        self.at("It's just files")
        files = note('just files', 24, GREY_B).next_to(tag, DOWN, buff=0.15)
        self.play(FadeIn(files))

        # [V12.2b] two paths
        self.at('Option one')
        self.play(FadeOut(VGroup(server, no, tag, files)))
        a = chip('A  put the code in the link', BLUE, 26).move_to([0, -0.3, 0])
        b = chip('B  store the code somewhere, by name', AFTER, 26).move_to([0, -1.5, 0])
        path_a = CurvedArrow(you.get_bottom() + DOWN * 0.1, a.get_left() + LEFT * 0.1, angle=0.6, color=BLUE)
        path_b = CurvedArrow(you.get_bottom() + DOWN * 0.1, b.get_left() + LEFT * 0.1, angle=0.6, color=AFTER)
        self.play(Create(path_a), FadeIn(a))
        self.at('Option two')
        self.play(Create(path_b), FadeIn(b))
        self.at('who gets to choose the name')
        question = Text('who chooses the name?', font_size=36, color=FOCUS).next_to(b, DOWN, buff=0.5)
        self.play(Write(question))
        self.finish()


# ---------------------------------------------------------------- 12.3

class Segment_12_3(Segment):
    """Code inside the link."""
    EPISODE, SEGMENT = 12, '12.3'

    def construct(self):
        source = snippet_source('ep01/01-square-to-circle.py')
        code = code_panel(source, font_size=22)
        code.to_edge(LEFT, buff=0.5).shift(UP * 0.8)
        self.play(FadeIn(code))
        self.at('after a hash sign')
        hash_tag = VGroup(mono(SITE, 22, GREY_B), mono('#', 30, FOCUS), mono('your code', 22, FOCUS)).arrange(RIGHT, buff=0.08)
        hash_tag.to_edge(DOWN, buff=1.2)
        never = note('the part after # is never sent to a server', 22, GREY_A).next_to(hash_tag, DOWN, buff=0.2)
        self.play(FadeIn(hash_tag), FadeIn(never))

        # [V12.3a] percent codes: 249 characters become 391
        self.at('addresses have rules')
        self.play(FadeOut(VGroup(hash_tag, never)))
        encoded = encode_uri_component(source)
        lines = wrapped(encoded, 36, 18, GREY_A).next_to(code, RIGHT, buff=0.4).align_to(code, UP)
        percent = VGroup()
        for line, start in zip(lines, range(0, len(encoded), 36)):
            chunk = encoded[start:start + 36]
            for m in re.finditer(r'%[0-9A-F]{2}', chunk):
                percent.add(VGroup(*line[m.start():m.end()]))
        counter = Integer(len(source), font_size=40, color=FOCUS).next_to(code, DOWN, buff=0.5).align_to(code, LEFT)
        counter_tag = note('characters', 24, GREY_A).next_to(counter, RIGHT, buff=0.2)
        self.play(FadeIn(counter), FadeIn(counter_tag))
        self.at('three-character code')
        self.play(FadeIn(lines, lag_ratio=0.05), percent.animate.set_color(FOCUS),
                  ChangeDecimalToValue(counter, len(encoded)), run_time=3)
        bar = RoundedRectangle(width=4.0, height=0.5, corner_radius=0.25).set_stroke(GREY_B, 2).to_edge(DOWN, buff=0.4)
        self.at('Real scenes get long fast')
        self.play(FadeIn(bar))
        self.play(bar.animate.stretch_to_fit_width(13.4), run_time=1.5)

        # [V12.3c] repetition is what compression feeds on
        self.at('It repeats itself')
        self.play(FadeOut(VGroup(lines, counter, counter_tag, bar)))
        rows = source.strip('\n').split('\n')

        def find(needle, color):
            found = VGroup()
            for i, row in enumerate(rows):
                start = row.find(needle)
                while start >= 0:
                    found.add(chars(code_line(code, i), row, start, start + len(needle)))
                    start = row.find(needle, start + 1)
            return found

        self.at('Self dot play, twice')
        plays = find('self.play(', FOCUS)
        self.play(plays.animate.set_color(FOCUS))
        self.at('Indentation, over and over')
        indents = VGroup()
        for i, row in enumerate(rows):
            spaces = len(row) - len(row.lstrip(' '))
            if spaces and row.strip():
                line = code_line(code, i)
                width = spaces * line.width / len(row.strip())
                indents.add(Rectangle(width=width, height=0.32).set_fill(GREY_B, 0.35).set_stroke(width=0)
                            .next_to(line, LEFT, buff=0.03))
        self.play(FadeIn(indents, lag_ratio=0.1))
        self.at('Colour equals, twice')
        colours = find('color=', BLUE)
        self.play(colours.animate.set_color(TEAL))
        self.at('repetition is exactly what compression feeds on')
        feeds = note('repetition is what compression feeds on', 28, FOCUS).to_edge(DOWN, buff=0.6)
        self.play(FadeIn(feeds))
        self.finish()


# ---------------------------------------------------------------- 12.4

MESSAGE = 'the cat sat on the mat; the cat sat'
CELL = 0.36


def letter_row(text, y):
    cells = VGroup(*[Text('·' if ch == ' ' else ch, font=MONO, font_size=26) for ch in text])
    for k, cell in enumerate(cells):
        cell.move_to(RIGHT * (k - (len(text) - 1) / 2) * CELL + UP * y)
    return cells


class Segment_12_4(Segment):
    """Saying "same as before" (q12-01)."""
    EPISODE, SEGMENT = 12, '12.4'

    def construct(self):
        title = VGroup(Text('Lempel and Ziv', font_size=40), note('late 1970s', 26, GREY_A)).arrange(DOWN, buff=0.2)
        self.play(FadeIn(title))
        self.at('Read the text from left to right')
        rule = note('seen before? write "go back d, copy n" instead', 28, FOCUS).to_edge(UP, buff=0.4)
        self.play(FadeOut(title), FadeIn(rule))

        # [V12.4a] the sentence
        source = letter_row(MESSAGE, 1.6)
        self.play(Write(source), run_time=2)

        # [V12.4b/c] literals, then references, as q12-01 does
        self.at('At first everything is new')
        card = qr_card('q12-01')
        self.play(FadeIn(card, shift=UP * 0.2), run_time=0.4)
        x = -(len(MESSAGE) - 1) / 2 * CELL
        output = VGroup()
        literals = references = 0
        cue = {4: 'So we write', 15: 'Later', 24: 'can be copied in one go'}
        for start, distance, length in lz77(MESSAGE):
            if distance == 0:
                cell = source[start].copy().move_to(RIGHT * x + DOWN * 0.4)
                self.play(TransformFromCopy(source[start], cell), run_time=0.2)
                output.add(cell)
                x += CELL
                literals += 1
                continue
            if distance in cue:
                self.at(cue[distance])
            earlier = SurroundingRectangle(source[start - distance:start - distance + length], color=GREEN, buff=0.05)
            repeat = SurroundingRectangle(source[start:start + length], color=YELLOW, buff=0.05)
            token = Text(f'({distance},{length})', font=MONO, font_size=26, color=YELLOW)
            token.move_to(RIGHT * (x + token.width / 2) + DOWN * 0.4)
            self.play(Create(earlier), Create(repeat), run_time=0.6)
            self.play(TransformFromCopy(repeat, token), run_time=0.6)
            self.play(FadeOut(earlier, repeat), run_time=0.3)
            output.add(token)
            x += token.width + 0.1
            references += 1

        # [V12.4d] the summary
        self.at('Thirty five characters became')
        summary = Text(f'{len(MESSAGE)} characters became {literals} letters and {references} references', font_size=28)
        summary.next_to(output, DOWN, buff=0.7).set_x(-1.8)
        self.play(Write(summary))
        self.at('decompressing is just following the notes')
        follow = note('decompressing: follow the notes', 24, AFTER).next_to(summary, DOWN, buff=0.25).set_x(-1.8)
        self.play(FadeIn(follow))

        # lz-string: the same family, link-safe output
        self.at('a library called L Z string')
        self.play(FadeOut(VGroup(source, output, summary, follow, rule, card)))
        lib = labelled_box('lz-string', 3.0, 0.9, 30, BLUE).move_to(UP * 2.0)
        facts = VGroup(note('a dictionary of phrases it has already seen', 26, GREY_A),
                       note('output in characters that are safe in a link', 26, GREY_A)).arrange(DOWN, buff=0.25).next_to(lib, DOWN, buff=0.4)
        sample = VGroup(mono('compressed=', 22, GREY_B), mono(SHARE_PAYLOAD[:44] + '…', 22, FOCUS)).arrange(RIGHT, buff=0.05)
        sample.next_to(facts, DOWN, buff=0.6)
        self.play(FadeIn(lib))
        self.at('It builds a dictionary')
        self.play(FadeIn(facts[0]))
        self.at('safe to put straight into a link')
        self.play(FadeIn(facts[1]), FadeIn(sample))
        self.finish()


# ---------------------------------------------------------------- 12.5

class Segment_12_5(Segment):
    """Where links run out."""
    EPISODE, SEGMENT = 12, '12.5'

    def construct(self):
        perks = VGroup(*[chip(w, AFTER, 24) for w in ('nothing to store', 'nothing to expire', 'the code travels with the link')])
        perks.arrange(RIGHT, buff=0.3).to_edge(UP, buff=0.4)
        for phrase, perk in zip(('nothing to store', 'nothing to expire', 'the code travels'), perks):
            self.at(phrase)
            self.play(FadeIn(perk, shift=DOWN * 0.15), run_time=0.5)

        # [V12.5a] a short address against a compressed share link, at the same size
        self.at("a QR code's size grows")
        short = qr_code('q09-01', 3.6).move_to([-3.4, -0.2, 0])
        dense = matrix_code(SHARE_QR['rows'], 3.6).move_to([3.4, -0.2, 0])
        tags = VGroup(note(f'a series link: {len(LINKS["q09-01"]["url"])} characters', 24, GREY_A).next_to(short, DOWN, buff=0.25),
                      note(f'a compressed share link: {len(SHARE_QR["url"])} characters', 24, GREY_A).next_to(dense, DOWN, buff=0.25))
        self.play(FadeIn(short), FadeIn(tags[0]))
        self.play(FadeIn(dense), FadeIn(tags[1]))
        n = len(qr_matrix_rows('q09-01'))
        modules = VGroup(note(f'{n} × {n} modules', 22, BLUE).next_to(tags[0], DOWN, buff=0.12),
                         note(f'{len(SHARE_QR["rows"])} × {len(SHARE_QR["rows"])} modules', 22, WARNING).next_to(tags[1], DOWN, buff=0.12))
        self.play(FadeIn(modules))
        self.at('too small to scan comfortably')
        frame = box(4.4, 2.5, GREY_B, fill='#000000', radius=0.05, stroke=2).move_to([3.4, -0.2, 0])
        self.play(FadeOut(VGroup(short, tags[0], modules[0])), FadeIn(frame), dense.animate.scale(0.32).move_to(frame.get_corner(DR) + UL * 0.45))
        corner = note('in the corner of a video frame', 22, GREY_A).next_to(frame, UP, buff=0.15)
        self.play(FadeIn(corner))
        rule = note('longer link → more modules → smaller dots', 30, FOCUS).to_edge(DOWN, buff=0.4)
        self.play(FadeIn(rule))

        self.at('That needs option two')
        two = chip('B  store the code somewhere, by name', AFTER, 26).move_to([-3.6, -0.2, 0])
        self.play(FadeIn(two, shift=RIGHT * 0.2))
        self.finish()


def qr_matrix_rows(qr_id):
    return json.loads((PRODUCTION / 'qr-matrices.json').read_text())[qr_id]['rows']


# ---------------------------------------------------------------- 12.6

class Segment_12_6(Segment):
    """Fingerprints for data (q12-02)."""
    EPISODE, SEGMENT = 12, '12.6'

    def construct(self):
        idea = Text('let the code name itself', font_size=40, color=FOCUS)
        self.play(FadeIn(idea))

        # [V12.6a] SHA-512: any data in, 512 bits out
        self.at('A cryptographic hash function')
        machine = labelled_box('SHA-512', 2.8, 1.0, 30, FOCUS).move_to(UP * 2.4)
        message = mono('"Hello, Manim"', 28, WHITE).next_to(machine, LEFT, buff=1.2)
        feed = Arrow(message.get_right(), machine.get_left(), buff=0.15, color=GREY_B, stroke_width=4)
        self.play(FadeOut(idea), FadeIn(machine), FadeIn(message), GrowArrow(feed))
        first_bits = bits_of(b'Hello, Manim')
        grid = bit_grid(first_bits).next_to(machine, DOWN, buff=0.6)
        size = note('512 bits: 16 rows of 32', 22, GREY_A).next_to(grid, DOWN, buff=0.2)
        self.at('five hundred and twelve bits')
        self.play(FadeIn(grid, lag_ratio=0.002), FadeIn(size), run_time=1.5)
        self.at("it's deterministic")
        again = note('same input → same fingerprint, every time', 24, AFTER).next_to(size, DOWN, buff=0.25)
        self.play(FadeIn(again))

        # [V12.6b] q12-02: one letter changed, about half the bits flip
        self.at('the avalanche effect')
        self.play(FadeOut(VGroup(machine, message, feed, size, again)))
        second_bits = bits_of(b'Hello, Manin')
        right = bit_grid(second_bits)
        pair = VGroup(grid.copy(), right).arrange(RIGHT, buff=0.8).shift(UP * 0.5)
        labels = VGroup(Text('"Hello, Manim"', font_size=32).next_to(pair[0], UP), Text('"Hello, Manin"', font_size=32).next_to(pair[1], UP))
        card = qr_card('q12-02')
        self.play(Transform(grid, pair[0]), FadeIn(right), Write(labels), FadeIn(card, shift=UP * 0.2))
        changed = sum(a != b for a, b in zip(first_bits, second_bits))
        marks = VGroup(*[Square(0.14, stroke_width=1.5, color=RED).move_to(square)
                         for square, a, b in zip(right, first_bits, second_bits) if a != b])
        self.at('about half of the bits flip')
        self.play(Create(marks), run_time=2)
        count = Text(f'{changed} of 512 bits changed', font_size=36).next_to(pair, DOWN, buff=0.4)
        self.play(Write(count))
        self.wait(3)

        # [V12.6c] a whole library in, the same size out
        self.at('nobody knows any practical way')
        self.play(FadeOut(VGroup(grid, right, labels, marks, count, card)))
        lite = (SERIES.parent / 'src' / 'manim-lite.py').read_bytes()
        book = VGroup(box(1.6, 2.0, BLUE, radius=0.08), note('manim-lite.py', 20, BLUE), note(f'{len(lite):,} bytes', 18, GREY_A))
        book[1].move_to(book[0]).shift(UP * 0.2)
        book[2].next_to(book[1], DOWN, buff=0.1)
        book.move_to([-4.6, 0.6, 0])
        big = bit_grid(bits_of(lite)).move_to([2.2, 0.6, 0])
        to = Arrow(book.get_right(), big.get_left(), buff=0.3, color=GREY_B, stroke_width=4)
        same = note('a whole library: the same 512 bits of fingerprint', 24, GREY_A).next_to(big, DOWN, buff=0.3)
        self.play(FadeIn(book), GrowArrow(to), FadeIn(big, lag_ratio=0.002), FadeIn(same), run_time=1.5)

        # [V12.6d] the three properties
        cards = VGroup(*[chip(w, c, 22) for w, c in (('same input → same fingerprint', AFTER),
                                                    ('tiny change → completely different', FOCUS),
                                                    ('no practical way to find another input with the same fingerprint', BLUE))])
        cards.arrange(DOWN, buff=0.18).to_edge(DOWN, buff=0.3)
        self.play(FadeIn(cards, lag_ratio=0.3), run_time=1.5)
        self.at('Scan this one')
        card = qr_card('q12-02', corner=UR)
        self.play(FadeIn(card))
        self.finish()


# ---------------------------------------------------------------- 12.7

def address_parts(source, y, kind, width=44):
    data = source.encode()
    prefix = b64(len(data).to_bytes(6, 'big'))
    body = b64(data) if len(data) <= 64 else b64(hashlib.sha512(data).digest())
    head = mono(prefix, 24, BLUE)
    rest = wrapped(body, width, 24, YELLOW)
    address = VGroup(head, rest).arrange(RIGHT, aligned_edge=UP, buff=0.1).move_to(UP * y)
    notes = VGroup(Text(f'length: {len(data)} bytes', font_size=22, color=BLUE).next_to(address, DOWN, buff=0.25).align_to(head, LEFT),
                   Text(kind, font_size=22, color=YELLOW).next_to(rest, UP, buff=0.3))
    return VGroup(address, notes), prefix, body


class Segment_12_7(Segment):
    """Anatomy of a content address (q12-04)."""
    EPISODE, SEGMENT = 12, '12.7'

    def construct(self):
        # [V12.7a] q12-04's two addresses
        short_source = 'digraph{a->b}'
        long_source = 'from manim import *\n' + '# ' + 'long source ' * 10
        short, _, short_body = address_parts(short_source, 2.6, 'the content itself (inline)')
        long, _, _ = address_parts(long_source, -0.1, 'SHA-512 fingerprint of the content')
        card = qr_card('q12-04')
        self.play(FadeIn(card, shift=UP * 0.2))
        self.at('they have two parts')
        self.play(Write(short), run_time=2)
        self.at('The first eight characters')
        self.play(Indicate(short[0][0], color=BLUE), Indicate(short[1][0], color=BLUE))
        self.at('sixty four bytes or less')
        self.play(Indicate(short[0][1], color=YELLOW))

        # [V12.7b] the inline part decodes back to the content
        self.at('our opening QR code')
        decoded = mono(base64.urlsafe_b64decode(short_body + '=' * (-len(short_body) % 4)).decode(), 28, WHITE)
        decoded.next_to(short, RIGHT, buff=0.6)
        self.play(TransformFromCopy(short[0][1], decoded))
        self.at('For anything longer')
        self.play(Write(long), run_time=2.5)

        # [V12.7c] HashBin hands back the box with that name
        self.at("asks hash bin's server")
        self.play(FadeOut(VGroup(short, long, decoded, card)))
        shelf = VGroup()
        for qr_id in ('q12-01', 'q12-02', 'q12-04', 'q00-01'):
            crate = box(2.6, 1.0, GREY_B, radius=0.06, stroke=2)
            label = mono(LINKS[qr_id]['cid'][:14] + '…', 18, FOCUS).move_to(crate)
            shelf.add(VGroup(crate, label))
        shelf.arrange(RIGHT, buff=0.25).move_to(UP * 1.6)
        store = note('HashBin', 26, GREY_A).next_to(shelf, UP, buff=0.2)
        self.play(FadeIn(shelf, lag_ratio=0.1), FadeIn(store))
        request = mono(LINKS['q12-02']['cid'][:14] + '…', 22, FOCUS).move_to([-4.0, -1.2, 0])
        ask = note('give me', 22, GREY_A).next_to(request, LEFT, buff=0.2)
        self.play(FadeIn(ask), FadeIn(request))
        self.play(Indicate(shelf[1], color=FOCUS))
        delivered = shelf[1].copy()
        self.play(delivered.animate.move_to([2.0, -1.2, 0]))

        # [V12.7d] anyone can recompute the fingerprint and check it
        self.at("The name isn't chosen by anyone")
        calc = note('calculated from the content', 26, AFTER).next_to(shelf, DOWN, buff=0.4)
        self.play(FadeIn(calc))
        self.at('a single character')
        changed = note('change one character → a different name', 24, WARNING).next_to(calc, DOWN, buff=0.15)
        self.play(FadeIn(changed))
        self.at('anyone can download the content')
        check = VGroup(note('recompute SHA-512 of the content', 22, GREY_A), check_mark(0.35), note('matches the name', 22, AFTER))
        check.arrange(RIGHT, buff=0.25).next_to(delivered, DOWN, buff=0.35)
        self.play(FadeIn(check[0]))
        self.play(Create(check[1]), FadeIn(check[2]))
        self.finish()


# ---------------------------------------------------------------- 12.8

class Segment_12_8(Segment):
    """Why these QR codes work."""
    EPISODE, SEGMENT = 12, '12.8'

    def construct(self):
        # [V12.8a] every non-inline CID is 94 characters, whatever the size of the scene
        rows = VGroup()
        for qr_id in ('q00-01', 'q12-02', 'q12-04', 'q12-01'):
            row = LINKS[qr_id]
            rows.add(VGroup(note(f'{row["bytes"]:,} bytes', 22, GREY_A), mono(row['cid'], 14, FOCUS)).arrange(RIGHT, buff=0.3))
        rows.arrange(DOWN, aligned_edge=RIGHT, buff=0.22).move_to(UP * 1.4)
        ruler = Line(rows[0][1].get_left(), rows[0][1].get_right(), color=GREY_B).next_to(rows, UP, buff=0.25).align_to(rows[0][1], LEFT)
        ruler_tag = note('94 characters, every time', 24, FOCUS).next_to(ruler, UP, buff=0.12)
        total = note(f'site + # + CID = {len(LINKS["q12-01"]["url"])} characters', 24, GREY_A).next_to(rows, DOWN, buff=0.35)
        self.play(FadeIn(rows, lag_ratio=0.2))
        self.at('about a hundred and thirty characters')
        self.play(Create(ruler), FadeIn(ruler_tag), FadeIn(total))
        self.at('comfortably large dots')
        dots = note('short, fixed-length links: large dots', 26, AFTER).next_to(total, DOWN, buff=0.3)
        self.play(FadeIn(dots))

        # [V12.8b] error correction: a smudged code still scans
        self.at('error correction')
        self.play(FadeOut(VGroup(rows, ruler, ruler_tag, total, dots)))
        code = qr_code('q12-02', 4.4).move_to(LEFT * 3.0)
        module = 4.4 / (len(qr_matrix_rows('q12-02')) + 8)
        finders = VGroup(*[Square(7.6 * module, color=BLUE, stroke_width=5).move_to(code.get_corner(c) - c * 7.5 * module)
                           for c in (UL, UR, DL)])
        self.play(FadeIn(code))
        smudge = Circle(radius=0.55).set_fill(GREY_B, 0.95).set_stroke(width=0).move_to(code.get_center() + RIGHT * 0.7 + DOWN * 0.6)
        notes = VGroup(note('finder squares: where the code is', 24, BLUE), note('part of every code is redundancy', 24, GREY_A),
                       note('a smudge, and it still scans', 24, AFTER)).arrange(DOWN, aligned_edge=LEFT, buff=0.3).move_to([3.4, 0, 0])
        self.play(Create(finders), FadeIn(notes[0]))
        self.play(FadeIn(notes[1]))
        self.at('hidden behind your thumb')
        self.play(FadeIn(smudge), FadeIn(notes[2]))

        # addresses known before anything was uploaded
        self.at('we knew every QR code')
        self.play(FadeOut(VGroup(code, finders, smudge, notes)))
        steps = VGroup(file_icon('.py', BLUE), labelled_box('compute the CID', 3.0, 0.9, 24, FOCUS), labelled_box('QR code', 2.0, 0.9, 24),
                       labelled_box('upload later', 2.4, 0.9, 24, GREY_D)).arrange(RIGHT, buff=0.6).move_to(UP * 1.2)
        links = VGroup(*[Arrow(a.get_right(), b.get_left(), buff=0.12, color=GREY_B, stroke_width=3) for a, b in zip(steps, steps[1:])])
        self.play(FadeIn(steps[:3]), GrowArrow(links[0]), GrowArrow(links[1]))
        self.play(FadeIn(steps[3]), GrowArrow(links[2]))
        self.at('always produces the same name')
        same = note('same bytes → same name', 26, AFTER).next_to(steps, DOWN, buff=0.4)
        self.play(FadeIn(same))

        # [V12.8c] the caveat: stored content must stay paid for; inline content cannot expire
        self.at('one honest caveat')
        self.play(FadeOut(VGroup(steps, links, same)))
        calendar = VGroup(box(1.6, 1.5, WARNING, radius=0.08), Rectangle(width=1.6, height=0.35).set_fill(WARNING, 0.6).set_stroke(width=0))
        calendar[1].align_to(calendar[0], UP)
        stored = VGroup(calendar, note('stored content: a paid retention period', 24, WARNING)).arrange(DOWN, buff=0.25).move_to([-3.5, 0.4, 0])
        inline = VGroup(mono(LINKS['q12-03']['cid'][:24] + '…', 22, FOCUS), note('inline: never expires', 24, AFTER)).arrange(DOWN, buff=0.3)
        inline.move_to([3.6, 0.4, 0])
        self.play(FadeIn(stored))
        self.at('the address still means the same code')
        lapse = note('if it lapses: same meaning, nobody serving it', 22, GREY_A).next_to(stored, DOWN, buff=0.3)
        self.play(FadeIn(lapse))
        self.at('Inline addresses')
        self.play(FadeIn(inline))
        self.finish()


# ---------------------------------------------------------------- 12.9

class Segment_12_9(Segment):
    """An editor that keeps itself."""
    EPISODE, SEGMENT = 12, '12.9'

    def construct(self):
        # [V12.9a] a versioned manifest, copied completely before "Ready offline"
        manifest = VGroup(mono(MANIFEST_VERSION, 22, FOCUS), note(f'{LOCAL_FILES} local files', 22, GREY_A),
                          note(f'{REMOTE_FILES} from CDNs: Pyodide, MathJax, lz-string', 22, GREY_A)).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        panel = box(manifest.width + 0.6, manifest.height + 0.5).move_to(manifest)
        sheet = VGroup(panel, manifest).move_to([-3.6, 2.4, 0])
        self.play(FadeIn(sheet))
        self.at('A service worker')
        keeper = cook('#cfe3f5').scale(0.8).move_to([-1.6, 0.0, 0])
        keeper_tag = note('service worker', 22, BLUE).next_to(keeper, DOWN, buff=0.15)
        cabinet = VGroup(*[box(2.6, 0.5, GREY_B, radius=0.04, stroke=2) for _ in range(5)]).arrange(DOWN, buff=0.06).move_to([2.2, 0.2, 0])
        cabinet_tag = note('on your device', 22, GREY_A).next_to(cabinet, UP, buff=0.15)
        self.play(FadeIn(keeper), FadeIn(keeper_tag), FadeIn(cabinet), FadeIn(cabinet_tag))
        fills = VGroup(*[Rectangle(width=2.4, height=0.36).set_fill(AFTER, 0.5).set_stroke(width=0).move_to(d) for d in cabinet])
        self.at('versioned list')
        for fill in fills:
            paper = file_icon('', GREY_A, 0.3, 0.4).move_to(sheet)
            self.play(paper.animate.move_to(fill), run_time=0.45)
            self.remove(paper)
            self.add(fill)
        self.at('Ready offline')
        ready = VGroup(check_mark(0.35), note('Ready offline', 26, AFTER)).arrange(RIGHT, buff=0.2).next_to(cabinet, DOWN, buff=0.3)
        self.play(Create(ready[0]), FadeIn(ready[1]))

        # [V12.9b] a new version fills a second cabinet completely, then takes over
        self.at('When a new version is released')
        new = mono(MANIFEST_VERSION[:-3] + str(int(MANIFEST_VERSION[-3:]) + 1), 22, FOCUS).move_to(manifest[0], aligned_edge=LEFT)
        second = cabinet.copy().next_to(cabinet, RIGHT, buff=0.6)
        second_fills = VGroup(*[f.copy().move_to(d).set_fill(BLUE, 0.5) for f, d in zip(fills, second)])
        self.play(FadeTransform(manifest[0], new), FadeIn(second))
        self.play(LaggedStart(*[FadeIn(f) for f in second_fills], lag_ratio=0.25), run_time=1.5)
        self.at('half of one version')
        whole = note('the whole new set first, then the switch', 24, GREY_A).to_edge(DOWN, buff=0.5).shift(RIGHT * 1.5)
        self.play(FadeIn(whole), FadeOut(VGroup(cabinet, fills)), VGroup(second, second_fills).animate.move_to(cabinet))
        self.at('unsaved code in an open tab')
        tab = browser_icon(3.4, 2.0).move_to([-4.4, -1.6, 0])
        unsaved = mono('square = Square()', 20, WHITE).move_to(tab).shift(DOWN * 0.15)
        kept = note('unsaved code: kept', 22, AFTER).next_to(tab, UP, buff=0.12)
        self.play(FadeIn(tab), FadeIn(unsaved), FadeIn(kept))
        self.finish()


# ---------------------------------------------------------------- 12.10

def finale_tiles():
    """Ten moments from the series, each a small drawing."""
    tiles = []
    tiles.append(VGroup(Square(1.0, color=BLUE), Circle(radius=0.55, color=BLUE).set_fill(BLUE, 0.5).shift(RIGHT * 1.4)))
    pts = [LEFT + DOWN * 0.5, LEFT * 0.4 + UP * 0.8, RIGHT * 0.4 + UP * 0.8, RIGHT + DOWN * 0.5]
    tiles.append(VGroup(CubicBezier(*pts, color=YELLOW), *[Dot(p, radius=0.06, color=GREY_B) for p in pts],
                        Polygon(*pts).set_stroke(GREY_B, 1).set_fill(opacity=0)))
    tiles.append(MathTex(r'2x + 3 = 7', r'\Rightarrow', r'x = 2', font_size=40))
    tiles.append(VGroup(Circle(radius=0.4, color=BLUE).shift(LEFT * 1.0),
                        FunctionGraph(lambda t: 0.4 * np.sin(t * 2.5), x_range=[-0.5, 1.8], color=YELLOW)))
    axes = Axes(x_range=[0, 2], y_range=[0, 2], x_length=2, y_length=1.2, tips=False, axis_config={'stroke_width': 2})
    tiles.append(VGroup(axes, axes.get_riemann_rectangles(axes.plot(lambda x: x * x / 2), x_range=[0, 2], dx=0.25, fill_opacity=0.7),
                        axes.plot(lambda x: x * x / 2, color=WHITE)))
    tiles.append(ParametricFunction(lambda t: np.array([0.6 * np.cos(t), 0.08 * t, 0]) + np.array([0, 0.25 * np.sin(t), 0]),
                                    t_range=[-TAU, TAU], color=YELLOW))
    tiles.append(cook().scale(0.8))
    tiles.append(VGroup(Square(1.0, color=BLUE).set_fill(BLUE, 0.4), Square(1.0, color=AFTER).set_fill(AFTER, 0.4).shift(RIGHT * 0.15 + UP * 0.1)))
    tiles.append(VGroup(mono('the cat sat', 22, WHITE), mono('(4,3)', 22, YELLOW)).arrange(DOWN, buff=0.15))
    tiles.append(bit_grid(bits_of(b'Hello, Manim'), cell=0.05))
    return tiles


class Segment_12_10(Segment):
    """Series finale."""
    EPISODE, SEGMENT = 12, '12.10'

    def construct(self):
        # [V12.10a] two ways to carry code, then the series in tiles arranged like a QR code
        ways = VGroup(chip('contain it: compressed', BLUE, 28), chip('name it: by its fingerprint', AFTER, 28)).arrange(DOWN, buff=0.4)
        self.play(FadeIn(ways[0]))
        self.at('Or they can name it')
        self.play(FadeIn(ways[1]))
        self.at('that brings us full circle')
        self.play(FadeOut(ways))
        tiles = finale_tiles()
        size = 1.55
        spots = [(1, 0), (2, 0), (0, 1), (1, 1), (3, 1), (2, 2), (3, 2), (1, 3), (2, 3), (3, 3)]
        finders = VGroup()
        for c in ((-1, -1), (4, -1), (-1, 4)):
            outer = Square(size).set_stroke(WHITE, 6)
            inner = Square(size * 0.45).set_fill(WHITE, 1).set_stroke(width=0)
            finders.add(VGroup(outer, inner).move_to([(c[0] - 1.5) * (size + 0.12), (1.5 - c[1]) * (size + 0.12) - 0.2, 0]))
        phrases = ['a stack of frames', 'nouns and verbs', 'curves and equations', 'things that change', 'graphs and cameras',
                   'Python running inside', 'an engine rebuilt', 'links that carry the code']
        shown = VGroup()
        for k, tile in enumerate(tiles):
            frame = Square(size).set_stroke(GREY_D, 2).set_fill('#101418', 1)
            tile.scale_to_fit_width(min(tile.width, size * 0.8))
            if tile.height > size * 0.8:
                tile.scale_to_fit_height(size * 0.8)
            group = VGroup(frame, tile.move_to(frame))
            x, y = spots[k]
            target = [(x - 1.5) * (size + 0.12), (1.5 - y) * (size + 0.12) - 0.2, 0]
            group.scale(2.2).move_to(ORIGIN)
            if k < len(phrases):
                self.at(phrases[k])
            self.play(FadeIn(group, scale=0.8), run_time=0.5)
            self.play(group.animate.scale(1 / 2.2).move_to(target), run_time=0.6)
            shown.add(group)
        self.play(FadeIn(finders, lag_ratio=0.2))

        # [V12.10b] the QR wall, 10 seconds
        self.at('Every scene in this series is one scan away', lead=0.5)
        wall = qr_wall([f'q12-0{i}' for i in range(1, 5)])
        heading = Text('Episode 12 · scan to open each scene', font_size=26, color=SCAFFOLD).to_corner(UL, buff=0.3)
        self.play(FadeOut(VGroup(shown, finders)), FadeIn(wall), FadeIn(heading))
        self.wait(10)

        # [V12.10c] the trailer's showcase, and the last words
        self.play(FadeOut(VGroup(wall, heading)))
        showcase = qr_code('q00-01', 3.2).move_to(UP * 0.7)
        caption = Text(f'q00-01 · {qr_title("q00-01")}', font_size=24).next_to(showcase, UP, buff=0.2)
        words = Text('Now make something.', font_size=48).next_to(showcase, DOWN, buff=0.6)
        self.play(FadeIn(showcase), FadeIn(caption))
        self.at('So go and make something', lead=1.0)
        self.play(Write(words))
        self.wait(6)
        self.finish()
