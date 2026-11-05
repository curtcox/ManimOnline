// Generated from the app-owned examples and catalog.
globalThis.ManimGalleryCatalog=[
  {
    "id": "modl",
    "label": "modl diagram",
    "path": "examples/basic_diagram.modl",
    "type": "modl",
    "cover": "gallery/previews/modl.png",
    "video": null,
    "editorURL": "./?example=modl&url=examples%2Fbasic_diagram.modl",
    "title": "modl diagram",
    "tags": [
      "modl"
    ],
    "description": "Editable modl diagram.",
    "document": {
      "src": "# Nodes: id [size] [shape] [color] [url] [text...]\neditor square blue Edit source\npreview circle green Preview diagram\nsaved diamond purple Save to HashBin\n\n# Edges: from -> to [size] [style] [color] [url] [text...]\neditor -> preview solid teal Render\npreview -> saved dashed purple Save\nsaved -> editor dotted orange Load\n"
    }
  },
  {
    "id": "modlpipeline",
    "label": "Data pipeline with chained edges",
    "path": "examples/data_pipeline.modl",
    "type": "modl",
    "cover": "gallery/previews/modlpipeline.png",
    "video": null,
    "editorURL": "./?example=modlpipeline&url=examples%2Fdata_pipeline.modl",
    "title": "Data pipeline with chained edges",
    "tags": [
      "modl"
    ],
    "description": "Editable modl diagram.",
    "document": {
      "src": "# A chain applies the same edge style to each step.\ncollect square blue Collect\nclean square teal Clean\nanalyze hex purple Analyze\nreport circle green Report\n\ncollect -> clean -> analyze -> report bold teal\ncollect -> report dotted gray Audit\n"
    }
  },
  {
    "id": "modlfeedback",
    "label": "Design feedback loop",
    "path": "examples/design_feedback.modl",
    "type": "modl",
    "cover": "gallery/previews/modlfeedback.png",
    "video": null,
    "editorURL": "./?example=modlfeedback&url=examples%2Fdesign_feedback.modl",
    "title": "Design feedback loop",
    "tags": [
      "modl"
    ],
    "description": "Editable modl diagram.",
    "document": {
      "src": "# Separate lines make branches and a feedback loop.\ndraft circle blue Idea\nprototype square teal Prototype\nreview diamond orange Test\nshipped hex green Launch\n\ndraft -> prototype solid blue Build\nprototype -> review solid teal Try\nreview -> shipped bold green Ready\nreview -> draft dashed orange Revise\n"
    }
  },
  {
    "id": "modlnavigation",
    "label": "Website navigation map",
    "path": "examples/site_navigation.modl",
    "type": "modl",
    "cover": "gallery/previews/modlnavigation.png",
    "video": null,
    "editorURL": "./?example=modlnavigation&url=examples%2Fsite_navigation.modl",
    "title": "Website navigation map",
    "tags": [
      "modl"
    ],
    "description": "Editable modl diagram.",
    "document": {
      "src": "# A small hierarchy; labels can be quoted to keep spaces together.\nhome big hex blue Home\ngallery square purple Gallery\nguides square teal Guides\nabout square orange About\nsamples circle purple Samples\n\nhome -> gallery solid purple\nhome -> guides solid teal\nhome -> about solid orange\ngallery -> samples dotted purple\n"
    }
  },
  {
    "id": "modlteam",
    "label": "Team responsibilities",
    "path": "examples/team_responsibilities.modl",
    "type": "modl",
    "cover": "gallery/previews/modlteam.png",
    "video": null,
    "editorURL": "./?example=modlteam&url=examples%2Fteam_responsibilities.modl",
    "title": "Team responsibilities",
    "tags": [
      "modl"
    ],
    "description": "Editable modl diagram.",
    "document": {
      "src": "# Size and shape distinguish the project from the people supporting it.\nproject big hex purple Project\ndesign circle pink Design\nbuild square blue Build\nquality diamond green Quality\n\ndesign -> project solid pink Research\nbuild -> project bold blue Develop\nquality -> project dashed green Verify\ndesign -> build dotted gray Handoff\n"
    }
  },
  {
    "id": "modlstyles",
    "label": "Shapes, sizes and quoted labels",
    "path": "examples/diagram_styles.modl",
    "type": "modl",
    "cover": "gallery/previews/modlstyles.png",
    "video": null,
    "editorURL": "./?example=modlstyles&url=examples%2Fdiagram_styles.modl",
    "title": "Shapes, sizes and quoted labels",
    "tags": [
      "modl"
    ],
    "description": "Editable modl diagram.",
    "document": {
      "src": "# Quoted keywords are labels, rather than style attributes.\n\"circle node\" normal circle blue \"blue\"\nsquare normal square teal \"square\"\ndiamond big diamond orange \"diamond\"\ntriangle small triangle pink \"triangle\"\nhex normal hex purple \"hex\"\n\n\"circle node\" -> diamond solid blue \"solid\"\ndiamond -> hex dashed orange \"dashed\"\nhex -> square dotted purple \"dotted\"\nsquare -> triangle bold teal \"bold\"\n"
    }
  },
  {
    "id": "glyphstyle",
    "label": "Gradient styles on text and formulas",
    "path": "examples/glyph_style_scene.py",
    "type": "manim",
    "cover": "gallery/previews/glyphstyle.png",
    "video": "gallery/previews/glyphstyle.mp4",
    "editorURL": "./?example=glyphstyle&url=examples%2Fglyph_style_scene.py",
    "title": "Gradient styles on text and formulas",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "from manim import *\n\n\nclass GlyphStyles(Scene):\n    def construct(self):\n        title = Text(\"Gradient styles\", font_size=48).shift(1.6 * UP)\n        formula = MathTex(r\"x^2+y^2=1\", font_size=64).shift(.3 * DOWN)\n        number = DecimalNumber(12.5, font_size=48).shift(1.8 * DOWN)\n        labels = VGroup(title, formula, number)\n        labels.set_fill([BLUE, GREEN], opacity=[.35, 1])\n        labels.set_stroke(WHITE, width=.7, opacity=[.3, .8])\n        labels.set_background_stroke([PURPLE, WHITE], width=8, opacity=[.2, .7])\n        labels.set_sheen_direction(UP)\n        self.play(Write(title), Write(formula), Write(number), run_time=2)\n        self.play(\n            labels.animate.set_fill([RED, YELLOW], opacity=[1, .4])\n            .set_background_stroke([BLUE, GREEN], width=12, opacity=[.8, .3]),\n            run_time=2,\n            rate_func=linear,\n        )\n        self.wait(1)\n        self.play(FadeOut(labels), run_time=1)\n        self.wait(2)\n"
    }
  },
  {
    "id": "stylecopy",
    "label": "Copy styles across different shapes",
    "path": "examples/style_copy_scene.py",
    "type": "manim",
    "cover": "gallery/previews/stylecopy.png",
    "video": "gallery/previews/stylecopy.mp4",
    "editorURL": "./?example=stylecopy&url=examples%2Fstyle_copy_scene.py",
    "title": "Copy styles across different shapes",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "from manim import *\n\n\nclass StyleCopyScene(Scene):\n    def construct(self):\n        template = Circle(radius=.7, fill_color=[BLUE, YELLOW], fill_opacity=[.3, 1],\n                          stroke_color=[WHITE, GREEN], stroke_width=5)\n        template.set_background_stroke([PURPLE, RED], width=14, opacity=[.2, .9])\n        template.shift(3 * LEFT)\n        shapes = VGroup(Square(side_length=1.2), Triangle().scale(1.4), Circle(radius=.6))\n        shapes.arrange(RIGHT, buff=.8).shift(2 * RIGHT)\n        self.play(FadeIn(template), FadeIn(shapes), run_time=1)\n        self.play(shapes.animate.match_style(template), run_time=2)\n        self.wait(2)\n        self.play(FadeOut(template), FadeOut(shapes), run_time=1)\n        self.wait(2)\n"
    }
  },
  {
    "id": "familygradient",
    "label": "Rotated and family color gradients",
    "path": "examples/family_gradient_scene.py",
    "type": "manim",
    "cover": "gallery/previews/familygradient.png",
    "video": "gallery/previews/familygradient.mp4",
    "editorURL": "./?example=familygradient&url=examples%2Ffamily_gradient_scene.py",
    "title": "Rotated and family color gradients",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "from manim import *\n\n\nclass FamilyGradientScene(Scene):\n    def construct(self):\n        tilted = Rectangle(width=4, height=2, fill_color=[RED, BLUE],\n                           fill_opacity=1, stroke_width=0)\n        tilted.rotate(PI / 4).scale(.7).shift(3 * LEFT)\n        family = Square(side_length=2, fill_color=[BLUE, YELLOW],\n                        fill_opacity=[.3, 1], stroke_width=0)\n        marker = Dot(2 * RIGHT, color=WHITE)\n        family.add(marker)\n        family.set_stroke([WHITE, GREEN], width=12, opacity=[.2, 1],\n                          background=True, family=False)\n        family.shift(2 * RIGHT)\n        child = Rectangle(width=2, height=1, fill_color=[GREEN, PURPLE],\n                          fill_opacity=1, stroke_width=0)\n        nested = Square(side_length=1.2, stroke_width=2).add(child)\n        nested.rotate(PI / 4).shift(2.5 * UP)\n        self.play(FadeIn(tilted), FadeIn(family), FadeIn(nested), run_time=2, rate_func=linear)\n        self.wait(2)\n        self.play(FadeOut(tilted), FadeOut(family), FadeOut(nested), run_time=2, rate_func=linear)\n        self.wait(2)\n"
    }
  },
  {
    "id": "spatialgradient",
    "label": "Gradients through a moving 3D camera",
    "path": "examples/spatial_gradient_scene.py",
    "type": "manim",
    "cover": "gallery/previews/spatialgradient.png",
    "video": "gallery/previews/spatialgradient.mp4",
    "editorURL": "./?example=spatialgradient&url=examples%2Fspatial_gradient_scene.py",
    "title": "Gradients through a moving 3D camera",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "from manim import *\n\n\nclass SpatialGradientScene(ThreeDScene):\n    def construct(self):\n        self.set_camera_orientation(phi=65 * DEGREES, theta=-60 * DEGREES)\n        panel = Square(side_length=2.4, fill_opacity=1, fill_color=[BLUE, YELLOW], stroke_width=0)\n        panel.rotate(PI / 2, axis=RIGHT).shift(2 * LEFT)\n        panel.set_sheen_direction(OUT)\n        shaded = Square(side_length=2.4, fill_opacity=1, fill_color=[RED, BLUE],\n                        stroke_width=0, shade_in_3d=True)\n        shaded.rotate(PI / 2, axis=RIGHT).shift(2 * RIGHT)\n        self.play(FadeIn(panel), FadeIn(shaded), run_time=1)\n        self.move_camera(theta=-120 * DEGREES, run_time=2)\n        self.play(panel.animate.shift(OUT), Rotate(shaded, angle=PI / 3, axis=OUT), run_time=2)\n        self.move_camera(theta=-60 * DEGREES, run_time=1)\n        self.play(FadeOut(panel), FadeOut(shaded), run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "rasterpaint",
    "label": "Color paths from a screen image",
    "path": "examples/raster_paint_scene.py",
    "type": "manim",
    "cover": "gallery/previews/rasterpaint.png",
    "video": "gallery/previews/rasterpaint.mp4",
    "editorURL": "./?example=rasterpaint&url=examples%2Fraster_paint_scene.py",
    "title": "Color paths from a screen image",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Screen-position raster coloring of moving outlines and flowing streams.\"\"\"\nfrom manim import *\n\n\nclass RasterPaintScene(Scene):\n    def construct(self):\n        flow = lambda p: (-p[1], p[0] / 2, 0)\n        field = VectorField(flow, min_color_scheme_value=0, max_color_scheme_value=4,\n                            colors=[BLUE_E, GREEN, YELLOW, RED])\n        image = field.get_colored_background_image(sampling_rate=10)\n        ring = Circle(radius=1.4, fill_opacity=.4, stroke_width=8).shift(LEFT*3)\n        ring.color_using_background_image(image)\n        streams = StreamLines(flow, x_range=[-4,4,2], y_range=[-2,2,2],\n                              noise_factor=0, virtual_time=1.5, stroke_width=5,\n                              min_color_scheme_value=0, max_color_scheme_value=4,\n                              colors=[BLUE_E, GREEN, YELLOW, RED])\n        self.play(Create(ring), streams.create(), run_time=2)\n        self.add(streams)\n        streams.start_animation(warm_up=False, flow_speed=1.5)\n        self.play(ring.animate.shift(RIGHT*6), run_time=3)\n        self.play(streams.end_animation(), run_time=1)\n        self.play(FadeOut(ring), FadeOut(streams), run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "fieldimage",
    "label": "Sample a vector-field color map",
    "path": "examples/field_image_scene.py",
    "type": "manim",
    "cover": "gallery/previews/fieldimage.png",
    "video": "gallery/previews/fieldimage.mp4",
    "editorURL": "./?example=fieldimage&url=examples%2Ffield_image_scene.py",
    "title": "Sample a vector-field color map",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"A sampled vector-field color map, real arrows and an advected marker.\"\"\"\nfrom manim import *\n\n\nclass FieldImageScene(Scene):\n    def construct(self):\n        flow = lambda p: (-p[1], p[0] / 2, 0)\n        field = VectorField(flow, min_color_scheme_value=0, max_color_scheme_value=4,\n                            colors=[BLUE_E, GREEN, YELLOW, RED])\n        background = ImageMobject(field.get_colored_background_image(sampling_rate=10))\n        background.height = config.frame_height\n        background.set_opacity(.7)\n        arrows = ArrowVectorField(flow, color=WHITE, x_range=[-5,5,1.5], y_range=[-3,3,1.5])\n        marker = Dot(LEFT*3+DOWN, color=WHITE, radius=.14)\n        self.play(FadeIn(background), Create(arrows), FadeIn(marker), run_time=2)\n        marker.add_updater(field.get_nudge_updater(speed=.5))\n        self.wait(4)\n        marker.clear_updaters()\n        self.play(FadeOut(arrows), FadeOut(marker), FadeOut(background), run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "minimal",
    "label": "First animation",
    "path": "examples/minimal_scene.py",
    "type": "manim",
    "cover": "gallery/previews/minimal.png",
    "video": "gallery/previews/minimal.mp4",
    "editorURL": "./?example=minimal&url=examples%2Fminimal_scene.py",
    "title": "First animation",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Small Manim Community scene for the first render/playback check.\n\nWith Manim installed: manim -ql examples/minimal_scene.py MinimalScene\n\"\"\"\n\nfrom manim import Circle, Create, Scene, Square, Transform\n\n\nclass MinimalScene(Scene):\n    def construct(self):\n        circle = Circle()\n        square = Square()\n        self.play(Create(circle))\n        self.play(Transform(circle, square))\n        self.wait(0.5)\n"
    }
  },
  {
    "id": "math",
    "label": "Math formulas",
    "path": "examples/math_scene.py",
    "type": "manim",
    "cover": "gallery/previews/math.png",
    "video": "gallery/previews/math.mp4",
    "editorURL": "./?example=math&url=examples%2Fmath_scene.py",
    "title": "Math formulas",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "from manim import *\n\n\nclass MathScene(Scene):\n    def construct(self):\n        title = Text(\"Math rendered as vector paths\", font_size=30).shift(UP * 3)\n        formula = MathTex(r\"\\int_0^1 x^2\\,dx = \\frac{1}{3}\", color=BLUE).shift(UP)\n        identity = MathTex(r\"a^2 + b^2 = c^2\", color=GREEN).shift(DOWN)\n        self.add(title)\n        self.play(Write(formula), Create(identity), run_time=2)\n        self.play(Indicate(formula), run_time=2)\n        target = MathTex(r\"\\sum_{k=1}^n k = \\frac{n(n+1)}{2}\", color=ORANGE).shift(UP)\n        self.play(Transform(formula, target), run_time=2)\n        self.wait(1)\n"
    }
  },
  {
    "id": "scenes",
    "label": "Multiple scenes",
    "path": "examples/multiple_scenes.py",
    "type": "manim",
    "cover": "gallery/previews/scenes.png",
    "video": "gallery/previews/scenes.mp4",
    "editorURL": "./?example=scenes&url=examples%2Fmultiple_scenes.py",
    "title": "Multiple scenes",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Render either scene by entering its class name in the browser's Scene field.\"\"\"\nfrom manim import *\n\n\nclass Circles(Scene):\n    def construct(self):\n        self.play(Create(Circle(color=BLUE)))\n        self.wait(1)\n\n\nclass RotatingSquare(Scene):\n    def construct(self):\n        square = Square(color=YELLOW).scale(0.6)\n        self.play(Create(square))\n        self.play(square.animate.scale(2).rotate(PI / 4), run_time=2)\n        self.wait(1)\n"
    }
  },
  {
    "id": "creation",
    "label": "Creation and rotation",
    "path": "examples/creation_and_rotation.py",
    "type": "manim",
    "cover": "gallery/previews/creation.png",
    "video": "gallery/previews/creation.mp4",
    "editorURL": "./?example=creation&url=examples%2Fcreation_and_rotation.py",
    "title": "Creation and rotation",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Draw an orbit, move a square around it, then erase the square's outline.\"\"\"\nfrom manim import *\n\n\nclass Orbit(Scene):\n    def construct(self):\n        orbit = Circle(radius=2, color=BLUE)\n        square = Square(side_length=0.6, color=YELLOW).shift(RIGHT * 2)\n        self.play(Create(orbit), Create(square), run_time=2)\n        self.play(Rotate(square, TAU, about_point=ORIGIN), run_time=4, rate_func=linear)\n        self.play(Uncreate(square), run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "layout",
    "label": "Position and arrange",
    "path": "examples/layout_scene.py",
    "type": "manim",
    "cover": "gallery/previews/layout.png",
    "video": "gallery/previews/layout.mp4",
    "editorURL": "./?example=layout&url=examples%2Flayout_scene.py",
    "title": "Position and arrange",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "from manim import *\n\n\nclass LayoutScene(Scene):\n    def construct(self):\n        shapes = VGroup(\n            Circle(radius=0.5, color=BLUE),\n            Square(side_length=0.8, color=RED),\n            Triangle(color=GREEN).scale(0.8),\n        ).arrange(RIGHT, buff=0.6)\n        marker = Dot(color=YELLOW).next_to(shapes, DOWN, buff=0.4)\n        self.play(Create(shapes), FadeIn(marker), run_time=2)\n        self.play(marker.animate.next_to(shapes, UP, buff=0.4), run_time=2)\n        self.play(shapes.animate.arrange(DOWN, buff=0.35), run_time=2)\n        self.play(marker.animate.next_to(shapes, RIGHT, buff=0.4))\n        self.wait(1)\n"
    }
  },
  {
    "id": "stagger",
    "label": "Staggered animations",
    "path": "examples/staggered_scene.py",
    "type": "manim",
    "cover": "gallery/previews/stagger.png",
    "video": "gallery/previews/stagger.mp4",
    "editorURL": "./?example=stagger&url=examples%2Fstaggered_scene.py",
    "title": "Staggered animations",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "from manim import *\n\n\nclass StaggeredScene(Scene):\n    def construct(self):\n        dots = VGroup(\n            Dot(LEFT * 2, radius=0.25, color=BLUE),\n            Dot(radius=0.25, color=RED),\n            Dot(RIGHT * 2, radius=0.25, color=GREEN),\n        )\n        self.play(LaggedStart(\n            *[FadeIn(dot, rate_func=linear) for dot in dots],\n            lag_ratio=0.5,\n            run_time=4,\n        ))\n        self.play(AnimationGroup(\n            *[dot.animate.shift(UP) for dot in dots],\n            lag_ratio=0.25,\n            run_time=3,\n        ))\n        self.play(LaggedStart(\n            *[FadeOut(dot) for dot in dots],\n            lag_ratio=0.5,\n            run_time=2,\n        ))\n        self.wait(1)\n"
    }
  },
  {
    "id": "succession",
    "label": "Animate in sequence",
    "path": "examples/succession_scene.py",
    "type": "manim",
    "cover": "gallery/previews/succession.png",
    "video": "gallery/previews/succession.mp4",
    "editorURL": "./?example=succession&url=examples%2Fsuccession_scene.py",
    "title": "Animate in sequence",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "from manim import *\n\n\nclass SuccessionScene(Scene):\n    def construct(self):\n        title = Text(\"Create, rotate twice, move, replace, remove\", font_size=26).shift(UP * 3)\n        shape = Square(color=BLUE).shift(LEFT * 2)\n        target = Circle(color=ORANGE).shift(RIGHT * 2)\n        self.add(title)\n        self.play(Succession(\n            Create(shape),\n            Rotate(shape, PI / 2, run_time=2, rate_func=linear),\n            Rotate(shape, PI / 2, run_time=2, rate_func=linear),\n            shape.animate.shift(UP),\n            ReplacementTransform(shape, target),\n            Indicate(target),\n            FadeOut(target),\n        ))\n        self.wait(1)\n"
    }
  },
  {
    "id": "annulus",
    "label": "Rings with separate contours",
    "path": "examples/annulus_scene.py",
    "type": "manim",
    "cover": "gallery/previews/annulus.png",
    "video": "gallery/previews/annulus.mp4",
    "editorURL": "./?example=annulus&url=examples%2Fannulus_scene.py",
    "title": "Rings with separate contours",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Render separate ring contours, trace them and change ring dimensions.\"\"\"\nfrom manim import *\n\n\nclass AnnulusScene(Scene):\n    def construct(self):\n        ring = Annulus(inner_radius=.7, outer_radius=1.5, color=BLUE,\n                       stroke_width=3).save_state()\n        self.play(Create(ring), run_time=2)\n        dot = Dot(color=YELLOW).move_to(ring.get_start())\n        self.add(dot)\n        self.play(MoveAlongPath(dot, ring), run_time=4, rate_func=linear)\n        self.play(FadeOut(dot), Transform(ring, Annulus(inner_radius=1.2,\n                  outer_radius=2, color=GREEN, stroke_width=3)), run_time=2)\n        self.play(Restore(ring), run_time=2)\n        self.wait(1)\n"
    }
  },
  {
    "id": "subpaths",
    "label": "Morph separate contours",
    "path": "examples/subpath_scene.py",
    "type": "manim",
    "cover": "gallery/previews/subpaths.png",
    "video": "gallery/previews/subpaths.mp4",
    "editorURL": "./?example=subpaths&url=examples%2Fsubpath_scene.py",
    "title": "Morph separate contours",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Keep separate contours while following, morphing, collapsing and restoring.\"\"\"\nfrom manim import *\n\n\nclass SubpathScene(Scene):\n    def construct(self):\n        path = VMobject(color=BLUE, fill_opacity=.35)\n        path.start_new_path(UR*2).add_points_as_corners([UL*2, DL*2, DR*2]).close_path()\n        path.start_new_path(UR).add_points_as_corners([DR, DL, UL]).close_path()\n        path.save_state()\n        self.play(Create(path), run_time=2)\n        dot = Dot(color=YELLOW).move_to(path.get_start())\n        self.add(dot)\n        self.play(MoveAlongPath(dot, path), run_time=4, rate_func=linear)\n        ring = Annulus(inner_radius=1, outer_radius=2, color=GREEN, stroke_width=4)\n        self.play(FadeOut(dot), Transform(path, ring), run_time=2)\n        self.play(Transform(path, RoundedRectangle(color=PURPLE, fill_opacity=.35)), run_time=2)\n        self.play(Restore(path), run_time=2)\n        self.wait(1)\n"
    }
  },
  {
    "id": "points",
    "label": "Edit cubic point arrays",
    "path": "examples/point_array_scene.py",
    "type": "manim",
    "cover": "gallery/previews/points.png",
    "video": "gallery/previews/points.mp4",
    "editorURL": "./?example=points&url=examples%2Fpoint_array_scene.py",
    "title": "Edit cubic point arrays",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Build and edit raw cubic points, append a ring, and restore the original curve.\"\"\"\nfrom manim import *\n\n\nclass PointArrayScene(Scene):\n    def construct(self):\n        seed = CubicBezier((-3,-1,0), (-1,2,0), (1,-2,0), (3,1,0)).rotate(PI/6)\n        points = seed.get_points()\n        path = VMobject(color=BLUE).set_points(points[:1]).append_points(points[1:])\n        path.save_state()\n        self.play(Create(path), run_time=2)\n        edited = [(point[0], point[1]+(1.5 if i in (1,2) else 0), point[2])\n                  for i, point in enumerate(path.get_points())]\n        self.play(path.animate.set_points(edited), run_time=2)\n        path.append_vectorized_mobject(Annulus(inner_radius=.35, outer_radius=.8,\n                                               arc_center=UP*2))\n        self.wait(1)\n        self.play(Restore(path), run_time=2)\n        self.wait(1)\n"
    }
  },
  {
    "id": "partial",
    "label": "Extract and wrap curve highlights",
    "path": "examples/partial_curve_scene.py",
    "type": "manim",
    "cover": "gallery/previews/partial.png",
    "video": "gallery/previews/partial.mp4",
    "editorURL": "./?example=partial&url=examples%2Fpartial_curve_scene.py",
    "title": "Extract and wrap curve highlights",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Extract exact cubic portions and wrap a highlight across a closed outline.\"\"\"\nfrom manim import *\n\n\nclass PartialCurveScene(Scene):\n    def construct(self):\n        curve = CubicBezier((-3,-1,0), (-2,3,0), (2,-3,0), (3,1,0)).rotate(PI/8)\n        curve.set_stroke(color=GRAY, width=3)\n        highlight = curve.get_subcurve(.2,.8).set_stroke(color=YELLOW, width=7)\n        ring = Circle(radius=1.2, color=GRAY).shift(UP*2)\n        wrapped = ring.get_subcurve(.85,.15).set_stroke(color=BLUE, width=7)\n        self.play(Create(curve), Create(ring), run_time=2)\n        self.play(Create(highlight), Create(wrapped), run_time=2)\n        self.play(highlight.animate.pointwise_become_partial(curve,.6,1), run_time=2)\n        self.play(FadeOut(highlight), FadeOut(wrapped), run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "flash",
    "label": "Traveling outline highlights",
    "path": "examples/passing_flash_scene.py",
    "type": "manim",
    "cover": "gallery/previews/flash.png",
    "video": "gallery/previews/flash.mp4",
    "editorURL": "./?example=flash&url=examples%2Fpassing_flash_scene.py",
    "title": "Traveling outline highlights",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Traveling outline highlights, simultaneous groups, and reusable flash objects.\"\"\"\nfrom manim import *\n\n\nclass PassingFlashScene(Scene):\n    def construct(self):\n        curve = CubicBezier((-3,-1,0), (-2,2,0), (2,-2,0), (3,1,0)).shift(DOWN)\n        outlines = VGroup(Circle(radius=.9).shift(LEFT*1.5),\n                          RoundedRectangle(width=2, height=1.6, corner_radius=.3).shift(RIGHT*1.5))\n        outlines.rotate(PI/12).shift(UP*1.5)\n        curve.set_stroke(color=GRAY, width=3)\n        outlines.set_stroke(color=GRAY, width=3)\n        flash = curve.copy().set_stroke(color=YELLOW, width=8)\n        group_flash = outlines.copy().set_stroke(color=BLUE, width=7)\n        self.add(curve, outlines)\n        self.play(ShowPassingFlash(flash, time_width=.3, rate_func=linear),\n                  ShowPassingFlash(group_flash, time_width=.4, rate_func=linear), run_time=4)\n        self.play(Succession(ShowPassingFlash(flash, time_width=.6, run_time=2),\n                             ShowPassingFlash(flash, time_width=.2, run_time=2)))\n        self.wait(1)\n"
    }
  },
  {
    "id": "numberline",
    "label": "Follow numeric coordinates",
    "path": "examples/number_line_scene.py",
    "type": "manim",
    "cover": "gallery/previews/numberline.png",
    "video": "gallery/previews/numberline.mp4",
    "editorURL": "./?example=numberline&url=examples%2Fnumber_line_scene.py",
    "title": "Follow numeric coordinates",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Numeric coordinates and a marker following an animated number line.\"\"\"\nfrom manim import *\n\n\nclass NumberLineScene(Scene):\n    def construct(self):\n        line = NumberLine(x_range=[-3,3,1], length=8.5, include_tip=True,\n                          include_numbers=True, font_size=24, line_to_number_buff=.4,\n                          numbers_with_elongated_ticks=[0], color=BLUE)\n        line.save_state()\n        value = ValueTracker(-2.5)\n        marker = Dot(line.n2p(value.get_value()), color=YELLOW)\n        marker.add_updater(lambda mob: mob.move_to(line.n2p(value.get_value())))\n        label = DecimalNumber(value.get_value(), num_decimal_places=1).shift(UP*2.5)\n        label.add_updater(lambda mob: mob.set_value(value.get_value()))\n        self.add(label)\n        self.play(Create(line), FadeIn(marker), run_time=2)\n        self.play(value.animate.set_value(2.5), run_time=3, rate_func=linear)\n        self.play(line.animate.rotate(PI/6).scale(.8).shift(UP),\n                  value.animate.set_value(-1.5), run_time=3, rate_func=linear)\n        self.play(Restore(line), value.animate.set_value(0), run_time=2)\n        self.wait(1)\n"
    }
  },
  {
    "id": "axes",
    "label": "Animate Cartesian coordinates",
    "path": "examples/axes_scene.py",
    "type": "manim",
    "cover": "gallery/previews/axes.png",
    "video": "gallery/previews/axes.mp4",
    "editorURL": "./?example=axes&url=examples%2Faxes_scene.py",
    "title": "Animate Cartesian coordinates",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Coordinate-driven geometry follows an animated Cartesian frame.\"\"\"\nfrom manim import *\n\n\nclass AxesScene(Scene):\n    def construct(self):\n        axes = Axes(x_range=[-3,3,1], y_range=[-2,3,1], x_length=8, y_length=4,\n                    axis_config=dict(font_size=22, line_to_number_buff=.4)).add_coordinates()\n        axes.save_state()\n        value = ValueTracker(-2)\n        curve = always_redraw(lambda: VMobject(color=BLUE).set_points_as_corners(\n            [axes.c2p(x,x*x/3-1) for x in (-3,-2.5,-2,-1.5,-1,-.5,0,.5,1,1.5,2,2.5,3)]))\n        marker = Dot(axes.c2p(value.get_value(),value.get_value()**2/3-1),color=YELLOW)\n        marker.add_updater(lambda mob: mob.move_to(\n            axes.c2p(value.get_value(),value.get_value()**2/3-1)))\n        readout = DecimalNumber(value.get_value(),num_decimal_places=1).shift(UP*3)\n        readout.add_updater(lambda mob: mob.set_value(value.get_value()))\n        self.add(readout)\n        self.play(Create(axes), Create(curve), FadeIn(marker), run_time=2)\n        self.play(value.animate.set_value(2), run_time=3, rate_func=linear)\n        self.play(axes.animate.rotate(PI/12).scale(.9).shift(UP*.2),\n                  value.animate.set_value(-1), run_time=3, rate_func=linear)\n        self.play(Restore(axes), value.animate.set_value(0), run_time=2)\n        self.wait(1)\n"
    }
  },
  {
    "id": "pointmaps",
    "label": "Shear and warp vector shapes",
    "path": "examples/point_map_scene.py",
    "type": "manim",
    "cover": "gallery/previews/pointmaps.png",
    "video": "gallery/previews/pointmaps.mp4",
    "editorURL": "./?example=pointmaps&url=examples%2Fpoint_map_scene.py",
    "title": "Shear and warp vector shapes",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Shear and warp a grid with matrix, point and complex function maps.\"\"\"\nfrom manim import *\n\n\nclass PointMapScene(Scene):\n    def construct(self):\n        grid = VGroup(*(Line((x,-1,0),(x,1,0),color=GRAY,stroke_width=1)\n                        for x in (-3,-2,-1,0,1,2,3)),\n                      *(Line((-3,y,0),(3,y,0),color=GRAY,stroke_width=1)\n                        for y in (-1,0,1)))\n        circle = Circle(radius=.7,color=BLUE).shift(LEFT*1.5)\n        square = Square(side_length=.9,color=GREEN).shift(RIGHT*1.5)\n        arrow = DoubleArrow(LEFT*3+UP*1.4,RIGHT*3+UP*1.4,buff=0,color=YELLOW)\n        family = VGroup(grid,circle,square,arrow)\n        self.play(Create(family),run_time=2)\n        family.save_state()\n        self.play(family.animate.apply_matrix([[1,.5],[0,1]]),run_time=2)\n        self.play(family.animate.apply_function(lambda p:(p[0],p[1]+.15*p[0]**2,0)),run_time=2)\n        self.play(family.animate.apply_complex_function(lambda z:z*(.8+.2j)),run_time=2)\n        self.play(Restore(family),run_time=1)\n        self.play(FadeOut(family),run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "positioning",
    "label": "Align to edges and color gradients",
    "path": "examples/positioning_scene.py",
    "type": "manim",
    "cover": "gallery/previews/positioning.png",
    "video": "gallery/previews/positioning.mp4",
    "editorURL": "./?example=positioning&url=examples%2Fpositioning_scene.py",
    "title": "Align to edges and color gradients",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Place shapes against frame edges, align them and color them by gradient.\"\"\"\nfrom manim import *\n\n\nclass PositioningScene(Scene):\n    def construct(self):\n        row = VGroup(*(Square(side_length=.8, fill_opacity=.6) for _ in range(5))).arrange(buff=SMALL_BUFF)\n        row.set_color_by_gradient(BLUE_E, TEAL, GOLD_A)\n        row.to_edge(UP, buff=MED_LARGE_BUFF)\n        marker = Triangle(color=MAROON).scale(.8).to_corner(DL)\n        arrow = Arrow(LEFT, RIGHT, buff=0, color=GREY_B).to_edge(RIGHT)\n        self.play(Create(row), Create(marker), Create(arrow), run_time=2)\n        self.play(marker.animate.align_to(row, LEFT).set_y(0), run_time=1)\n        self.play(arrow.animate.match_width(row).next_to(marker, RIGHT).flip(), run_time=2)\n        self.play(row.animate.to_corner(DR, buff=SMALL_BUFF).fade(.5), run_time=2)\n        self.play(Rotate(marker, PI, about_edge=DR), run_time=1)\n        self.play(marker.animate.center(), row.animate.set_x(0), run_time=1)\n        self.play(FadeOut(row), FadeOut(marker), FadeOut(arrow), run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "polygrams",
    "label": "Polygrams, stars and shape matchers",
    "path": "examples/polygram_scene.py",
    "type": "manim",
    "cover": "gallery/previews/polygrams.png",
    "video": "gallery/previews/polygrams.mp4",
    "editorURL": "./?example=polygrams&url=examples%2Fpolygram_scene.py",
    "title": "Polygrams, stars and shape matchers",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Regular polygons, stars and polygrams with surrounding shape matchers.\"\"\"\nfrom manim import *\n\n\nclass PolygramScene(Scene):\n    def construct(self):\n        shapes = VGroup(\n            RegularPolygon(5, color=TEAL, fill_opacity=.4),\n            Star(outer_radius=1.1, color=GOLD, fill_opacity=.4),\n            RegularPolygram(6, radius=1.1, color=PURPLE_B),\n            Triangle(color=MAROON_B).round_corners(.25),\n        ).arrange(buff=.6).shift(UP * .5)\n        self.play(LaggedStart(*(Create(s) for s in shapes), lag_ratio=.3), run_time=2)\n        shapes.scale(.8).to_edge(UP)\n        box = SurroundingRectangle(shapes[1], corner_radius=.15)\n        line = Underline(shapes[0], color=TEAL)\n        cross = Cross(shapes[3], stroke_width=4)\n        self.play(Create(box), Create(line), run_time=1)\n        self.play(box.animate.become(SurroundingRectangle(shapes[2], corner_radius=.15)), run_time=1)\n        self.play(Create(cross), run_time=1)\n        backdrop = BackgroundRectangle(shapes, color=GREY_E, fill_opacity=1, buff=MED_SMALL_BUFF)\n        self.play(FadeIn(backdrop), run_time=1)\n        self.bring_to_back(backdrop)\n        self.play(Transform(shapes[1], RegularPolygram(5, radius=1.1, color=GOLD).move_to(shapes[1])), run_time=2)\n        self.play(*(FadeOut(m) for m in (*shapes, box, line, cross, backdrop)), run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "textlayout",
    "label": "Measured text and formula layout",
    "path": "examples/text_layout_scene.py",
    "type": "manim",
    "cover": "gallery/previews/textlayout.png",
    "video": "gallery/previews/textlayout.mp4",
    "editorURL": "./?example=textlayout&url=examples%2Ftext_layout_scene.py",
    "title": "Measured text and formula layout",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Lay out text, numbers and formulas using their measured ink bounds.\"\"\"\nfrom manim import *\n\n\nclass TextLayoutScene(Scene):\n    def construct(self):\n        title = Text(\"Measured text layout\", font_size=40).to_edge(UP)\n        line = Underline(title, color=BLUE)\n        items = VGroup(\n            Text(\"Text uses Liberation Sans metrics\", font_size=28),\n            Text(\"Numbers use TeX digit layout\", font_size=28),\n            Text(\"Formulas are measured by MathJax\", font_size=28),\n        ).arrange(DOWN, aligned_edge=LEFT, buff=MED_SMALL_BUFF).next_to(line, DOWN, buff=MED_LARGE_BUFF)\n        formula = MathTex(r\"e^{i\\pi} + 1 = 0\", font_size=60).next_to(items, DOWN, buff=MED_LARGE_BUFF)\n        box = SurroundingRectangle(formula, color=YELLOW, buff=SMALL_BUFF)\n        tracker = ValueTracker(0)\n        number = always_redraw(lambda: DecimalNumber(tracker.get_value(), font_size=36)\n                               .next_to(box, RIGHT, buff=MED_SMALL_BUFF))\n        self.play(Write(title), Create(line), run_time=1)\n        self.play(LaggedStart(*(FadeIn(item) for item in items), lag_ratio=.3), run_time=2)\n        self.play(Write(formula), Create(box), run_time=1)\n        self.add(number)\n        self.play(tracker.animate.set_value(1234.5), run_time=2)\n        self.play(Indicate(items[1]), run_time=1)\n        self.play(items[1].animate.set_color(GOLD), run_time=1)\n        self.play(*(FadeOut(m) for m in (title, line, *items, formula, box, number)), run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "animationtour",
    "label": "Entrances, emphasis, swaps and exits",
    "path": "examples/animation_tour_scene.py",
    "type": "manim",
    "cover": "gallery/previews/animationtour.png",
    "video": "gallery/previews/animationtour.mp4",
    "editorURL": "./?example=animationtour&url=examples%2Fanimation_tour_scene.py",
    "title": "Entrances, emphasis, swaps and exits",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Community entrance, emphasis, swap and exit animations with rate functions.\"\"\"\nfrom manim import *\n\n\nclass AnimationTourScene(Scene):\n    def construct(self):\n        title = Text(\"Animation tour\", font_size=36).to_edge(UP)\n        shapes = VGroup(Square(color=BLUE), Circle(color=RED), Triangle(color=GREEN)).arrange(buff=1)\n        arrow = Arrow(LEFT * 3, RIGHT * 3, color=GOLD).next_to(shapes, DOWN)\n        self.play(Write(title))\n        self.play(Create(shapes), run_time=2)\n        self.play(GrowArrow(arrow), rate_func=rate_functions.ease_out_bounce)\n        self.play(Circumscribe(shapes[0]), Flash(shapes[1], color=YELLOW), Wiggle(shapes[2]))\n        self.play(Swap(shapes[0], shapes[2]))\n        shapes[1].generate_target()\n        shapes[1].target.scale(.5).set_color(PURPLE).next_to(arrow, DOWN)\n        self.play(MoveToTarget(shapes[1]), rate_func=there_and_back_with_pause, run_time=2)\n        self.play(FadeOut(title, shift=UP), FadeOut(arrow, shift=DOWN),\n                  FadeOut(VGroup(shapes[0], shapes[2]), lag_ratio=.5, scale=.5))\n        self.play(Unwrite(shapes[1]))\n        self.wait(1)\n"
    }
  },
  {
    "id": "annotations",
    "label": "Titles, braces, bullets and variables",
    "path": "examples/annotation_scene.py",
    "type": "manim",
    "cover": "gallery/previews/annotations.png",
    "video": "gallery/previews/annotations.mp4",
    "editorURL": "./?example=annotations&url=examples%2Fannotation_scene.py",
    "title": "Titles, braces, bullets and variables",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Titles, braces with labels, Tex text, bullet lists, vectors and variables.\"\"\"\nfrom manim import *\n\n\nclass AnnotationScene(Scene):\n    def construct(self):\n        title = Title(r\"Annotating a rectangle\")\n        rect = Rectangle(width=4, height=2, color=BLUE).shift(LEFT * 2.5 + DOWN * .5)\n        width = BraceLabel(rect, r\"w = 4\", brace_direction=DOWN)\n        height = Brace(rect, direction=LEFT)\n        height_label = height.get_tex(r\"h = 2\")\n        notes = BulletedList(r\"Area is $w \\cdot h$\", r\"Perimeter is $2(w + h)$\", font_size=32)\n        notes.next_to(rect, RIGHT, buff=1)\n        area = Variable(0, \"A\", num_decimal_places=1).next_to(notes, DOWN, buff=.6, aligned_edge=LEFT)\n        diagonal = Vector(rect.get_corner(UR) - rect.get_corner(DL), color=YELLOW).shift(rect.get_corner(DL))\n        self.play(Write(title))\n        self.play(Create(rect))\n        self.play(width.creation_anim(), GrowFromCenter(height), FadeIn(height_label))\n        self.play(FadeIn(notes, shift=RIGHT * .5), FadeIn(area))\n        self.play(GrowArrow(diagonal), area.tracker.animate.set_value(8), run_time=2)\n        self.play(notes.animate.fade_all_but(0), Indicate(height_label))\n        self.play(*(FadeOut(m) for m in (title, rect, width, height, height_label, notes, area, diagonal)))\n        self.wait(1)\n"
    }
  },
  {
    "id": "formulaparts",
    "label": "Formula parts and matching transforms",
    "path": "examples/formula_parts_scene.py",
    "type": "manim",
    "cover": "gallery/previews/formulaparts.png",
    "video": "gallery/previews/formulaparts.mp4",
    "editorURL": "./?example=formulaparts&url=examples%2Fformula_parts_scene.py",
    "title": "Formula parts and matching transforms",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Color, indicate and rearrange the parts of multi-string formulas.\"\"\"\nfrom manim import *\n\n\nclass FormulaPartsScene(Scene):\n    def construct(self):\n        first = MathTex(\"a^2\", \"+\", \"b^2\", \"=\", \"c^2\", font_size=72)\n        first.set_color_by_tex(\"a^2\", BLUE).set_color_by_tex(\"b^2\", GREEN)\n        self.play(Write(first))\n        self.play(Indicate(first[4]), Circumscribe(first[0]))\n        second = MathTex(\"c^2\", \"-\", \"b^2\", \"=\", \"a^2\", font_size=72)\n        second.set_color_by_tex_to_color_map({\"a^2\": BLUE, \"b^2\": GREEN})\n        self.play(TransformMatchingTex(first, second), run_time=2)\n        label = Tex(r\"Solve for $a^2$\", font_size=40).next_to(second, UP, buff=.6)\n        self.play(FadeIn(label, shift=DOWN * .3))\n        isolated = MathTex(r\"e^{i\\pi} + 1 = 0\", substrings_to_isolate=[\"e\", r\"\\pi\"],\n                           tex_to_color_map={r\"\\pi\": YELLOW}).next_to(second, DOWN, buff=.8)\n        self.play(Write(isolated))\n        self.play(FadeOut(label), FadeOut(second), FadeOut(isolated))\n        self.wait(1)\n"
    }
  },
  {
    "id": "matrixtable",
    "label": "Matrices, determinants and tables",
    "path": "examples/matrix_table_scene.py",
    "type": "manim",
    "cover": "gallery/previews/matrixtable.png",
    "video": "gallery/previews/matrixtable.mp4",
    "editorURL": "./?example=matrixtable&url=examples%2Fmatrix_table_scene.py",
    "title": "Matrices, determinants and tables",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Matrices with stretched brackets, a determinant and a labeled table.\"\"\"\nfrom manim import *\n\n\nclass MatrixTableScene(Scene):\n    def construct(self):\n        m = Matrix([[2, -1], [1, 3]]).shift(LEFT * 3 + UP * 1.5)\n        m.set_column_colors(BLUE, GREEN)\n        det = get_det_text(m, determinant=7)\n        v = IntegerMatrix([[1], [2]]).next_to(m, DOWN, buff=.5)\n        self.play(Write(m), Write(v))\n        self.play(FadeIn(det))\n        table = Table([[\"0\", \"1\"], [\"1\", \"0\"]], row_labels=[Text(\"A\"), Text(\"B\")],\n                      col_labels=[Text(\"x\"), Text(\"y\")], include_outer_lines=True).scale(.6).shift(RIGHT * 3.5 + UP * .5)\n        self.play(table.create(), run_time=2)\n        table.add_highlighted_cell((2, 3), color=YELLOW)\n        self.play(Indicate(table.get_entries((2, 3))))\n        decimals = DecimalMatrix([[0.5, 1.25], [2.0, -3.5]]).scale(.8).to_corner(DR)\n        self.play(FadeIn(decimals, shift=UP))\n        self.play(*(FadeOut(mob) for mob in (m, det, v, decimals)), FadeOut(table))\n        self.wait(1)\n"
    }
  },
  {
    "id": "texteffects",
    "label": "Letter colors, markup and gradients",
    "path": "examples/text_effects_scene.py",
    "type": "manim",
    "cover": "gallery/previews/texteffects.png",
    "video": "gallery/previews/texteffects.mp4",
    "editorURL": "./?example=texteffects&url=examples%2Ftext_effects_scene.py",
    "title": "Letter colors, markup and gradients",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Glyph-level Text: per-letter colors, markup, gradients and letter animations.\"\"\"\nfrom manim import *\n\n\nclass TextEffectsScene(Scene):\n    def construct(self):\n        title = Text(\"Hello, Manim!\", font_size=64, t2c={\"Manim\": BLUE, \"[0:5]\": YELLOW})\n        self.play(Write(title))\n        self.play(title[0].animate.scale(1.5).set_color(RED), Indicate(title[-1]))\n        self.play(title.animate.to_edge(UP))\n        rainbow = Text(\"Gradient text\", gradient=(RED, YELLOW, GREEN, BLUE), font_size=56)\n        markup = MarkupText('Some <b>bold</b>, <i>italic</i> and <span foreground=\"#83C167\">green</span> words',\n                            font_size=36).next_to(rainbow, DOWN, buff=.6)\n        self.play(FadeIn(rainbow, shift=UP), AddTextLetterByLetter(markup))\n        self.play(LaggedStart(*(g.animate.shift(UP * .3) for g in rainbow), lag_ratio=.1), run_time=2)\n        self.play(*(FadeOut(m) for m in (title, rainbow, markup)))\n        self.wait(1)\n"
    }
  },
  {
    "id": "pointclouds",
    "label": "Point clouds and scene sections",
    "path": "examples/point_cloud_scene.py",
    "type": "manim",
    "cover": "gallery/previews/pointclouds.png",
    "video": "gallery/previews/pointclouds.mp4",
    "editorURL": "./?example=pointclouds&url=examples%2Fpoint_cloud_scene.py",
    "title": "Point clouds and scene sections",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Point clouds, instant additions in a Succession, sections and scene updaters.\"\"\"\nfrom manim import *\n\n\nclass PointCloudScene(Scene):\n    def construct(self):\n        disk = PointCloudDot(center=LEFT * 3, radius=1.5, color=YELLOW)\n        disk.set_colors_by_radial_gradient(inner_color=YELLOW, outer_color=RED, radius=1.5)\n        line = Mobject1D(density=20)\n        line.add_line(LEFT * 1, RIGHT * 4, color=TEAL)\n        line.add_line(RIGHT * 4, RIGHT * 4 + UP * 2, color=BLUE)\n        self.play(FadeIn(disk), FadeIn(line))\n        title = Text(\"Point clouds\", font_size=36).to_edge(UP)\n        self.play(Succession(Add(title), disk.animate.rotate(PI / 2), line.animate.shift(DOWN)))\n        self.next_section(\"hidden setup\", skip_animations=True)\n        self.play(line.animate.scale(.6))\n        self.next_section(\"finale\")\n        clock = ValueTracker(0)\n        self.add_updater(lambda dt: clock.increment_value(dt))\n        marker = always_redraw(lambda: Dot(disk.get_center() + 1.8 * (np.cos(clock.get_value() * 2) * RIGHT\n                                                                     + np.sin(clock.get_value() * 2) * UP)))\n        self.add(marker)\n        self.wait(2)\n"
    }
  },
  {
    "id": "zoomed",
    "label": "Zoomed inset camera",
    "path": "examples/zoomed_scene.py",
    "type": "manim",
    "cover": "gallery/previews/zoomed.png",
    "video": "gallery/previews/zoomed.mp4",
    "editorURL": "./?example=zoomed&url=examples%2Fzoomed_scene.py",
    "title": "Zoomed inset camera",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"ZoomedScene: a magnified inset of the zoomed camera frame, popped out and reshaped.\"\"\"\nfrom manim import *\n\n\nclass ZoomedSceneExample(ZoomedScene):\n    def __init__(self, **kwargs):\n        ZoomedScene.__init__(\n            self,\n            zoom_factor=0.3,\n            zoomed_display_height=1,\n            zoomed_display_width=6,\n            image_frame_stroke_width=20,\n            zoomed_camera_config={\"default_frame_stroke_width\": 3},\n            **kwargs\n        )\n\n    def construct(self):\n        dot = Dot().shift(UL * 2)\n        image = ImageMobject(np.uint8([[0, 100, 30, 200],\n                                       [255, 0, 5, 33]]))\n        image.height = 7\n        frame_text = Text(\"Frame\", color=PURPLE, font_size=67)\n        zoomed_camera_text = Text(\"Zoomed camera\", color=RED, font_size=67)\n\n        self.add(image, dot)\n        zoomed_camera = self.zoomed_camera\n        zoomed_display = self.zoomed_display\n        frame = zoomed_camera.frame\n        zoomed_display_frame = zoomed_display.display_frame\n\n        frame.move_to(dot)\n        frame.set_color(PURPLE)\n        zoomed_display_frame.set_color(RED)\n        zoomed_display.shift(DOWN)\n\n        zd_rect = BackgroundRectangle(zoomed_display, fill_opacity=0, buff=MED_SMALL_BUFF)\n        self.add_foreground_mobject(zd_rect)\n\n        unfold_camera = UpdateFromFunc(zd_rect, lambda rect: rect.replace(zoomed_display))\n\n        frame_text.next_to(frame, DOWN)\n\n        self.play(Create(frame), FadeIn(frame_text, shift=UP))\n        self.activate_zooming()\n\n        self.play(self.get_zoomed_display_pop_out_animation(), unfold_camera)\n        zoomed_camera_text.next_to(zoomed_display_frame, DOWN)\n        self.play(FadeIn(zoomed_camera_text, shift=UP))\n        # Scale in        x   y  z\n        scale_factor = [0.5, 1.5, 0]\n        self.play(\n            frame.animate.scale(scale_factor),\n            zoomed_display.animate.scale(scale_factor),\n            FadeOut(zoomed_camera_text),\n            FadeOut(frame_text)\n        )\n        self.wait()\n        self.play(ScaleInPlace(zoomed_display, 2))\n        self.wait()\n        self.play(frame.animate.shift(2.5 * DOWN))\n        self.wait()\n        self.play(self.get_zoomed_display_pop_out_animation(), unfold_camera, rate_func=lambda t: smooth(1 - t))\n        self.play(Uncreate(zoomed_display_frame), FadeOut(frame))\n        self.wait()\n"
    }
  },
  {
    "id": "lineartransform",
    "label": "Linear transformations of the plane",
    "path": "examples/linear_transformation_scene.py",
    "type": "manim",
    "cover": "gallery/previews/lineartransform.png",
    "video": "gallery/previews/lineartransform.mp4",
    "editorURL": "./?example=lineartransform&url=examples%2Flinear_transformation_scene.py",
    "title": "Linear transformations of the plane",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"LinearTransformationScene: basis vectors, labels and a unit square follow matrices.\"\"\"\nfrom manim import *\n\n\nclass LinearTransformationExample(LinearTransformationScene):\n    def __init__(self, **kwargs):\n        LinearTransformationScene.__init__(\n            self, show_coordinates=True, leave_ghost_vectors=True, **kwargs\n        )\n\n    def construct(self):\n        self.add_title(\"A shear, then a rotation\")\n        self.add_unit_square()\n        vector = self.add_vector([1, 2], color=PURE_YELLOW)\n        self.add_transformable_label(vector, \"v\", animate=False)\n        self.apply_matrix([[1, 1], [0, 1]])\n        self.wait(0.5)\n        self.apply_matrix([[0, -1], [1, 0]])\n        self.wait(0.5)\n        self.apply_inverse([[0, -1], [1, 0]], run_time=2)\n        self.wait()\n\n\nclass NonlinearWarp(LinearTransformationScene):\n    def construct(self):\n        self.apply_nonlinear_transformation(\n            lambda p: [p[0] + np.sin(p[1]), p[1] + np.sin(p[0]), 0]\n        )\n        self.wait()\n"
    }
  },
  {
    "id": "banner",
    "label": "Logo banner, sample spaces and utilities",
    "path": "examples/banner_scene.py",
    "type": "manim",
    "cover": "gallery/previews/banner.png",
    "video": "gallery/previews/banner.mp4",
    "editorURL": "./?example=banner&url=examples%2Fbanner_scene.py",
    "title": "Logo banner, sample spaces and utilities",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"ManimBanner, SampleSpace divisions and Community utility helpers.\"\"\"\nfrom manim import *\n\n\nclass BannerScene(Scene):\n    def construct(self):\n        banner = ManimBanner().scale(0.6).shift(UP * 1.5)\n        self.play(banner.create())\n        self.play(banner.expand())\n\n        space = SampleSpace(width=4, height=2.4).shift(DOWN * 1.8 + LEFT * 3)\n        space.divide_horizontally([0.3])\n        # Community 0.22's get_side_braces_and_labels passes Brace an unsupported keyword.\n        braces = VGroup(*(BraceLabel(part, label, LEFT)\n                          for part, label in zip(space.horizontal_parts, [r\"P(A)\", r\"P(\\bar A)\"])))\n        self.play(FadeIn(space), FadeIn(braces))\n\n        # Utilities: regular vertices, rotate_vector and a clockwise path.\n        corners, _ = regular_vertices(5, radius=1.1)\n        star = Polygon(*corners, color=TEAL).shift(DOWN * 1.8 + RIGHT * 3.5)\n        pointer = Dot(star.get_center() + rotate_vector(RIGHT * 1.6, PI / 5), color=YELLOW)\n        self.play(Create(star), FadeIn(pointer))\n        self.play(Transform(pointer, pointer.copy().shift(LEFT * 2.2), path_func=clockwise_path()))\n        self.play(Rotate(star, PI), FadeIn(Circle(radius=1.1, color=RED).move_to(star)))\n        self.wait()\n"
    }
  },
  {
    "id": "threed",
    "label": "3D axes, surfaces and solids",
    "path": "examples/three_d_scene.py",
    "type": "manim",
    "cover": "gallery/previews/threed.png",
    "video": "gallery/previews/threed.mp4",
    "editorURL": "./?example=threed&url=examples%2Fthree_d_scene.py",
    "title": "3D axes, surfaces and solids",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"ThreeDAxes, plotted surfaces, solids and camera motion in a ThreeDScene.\"\"\"\nimport math\n\nfrom manim import *\n\n\nclass ThreeDSurfaceScene(ThreeDScene):\n    def construct(self):\n        axes = ThreeDAxes(x_range=(-3, 3, 1), y_range=(-3, 3, 1), z_range=(-2, 2, 1),\n                          x_length=6, y_length=6, z_length=4)\n        labels = axes.get_axis_labels()\n        self.set_camera_orientation(phi=70 * DEGREES, theta=-50 * DEGREES)\n        self.add(axes, labels)\n\n        surface = axes.plot_surface(\n            lambda u, v: 0.6 * math.sin(u) * math.cos(v),\n            u_range=(-3, 3), v_range=(-3, 3), resolution=(16, 16),\n            colorscale=[BLUE, GREEN, YELLOW, RED], fill_opacity=0.85)\n        self.play(Create(surface), run_time=2)\n\n        helix = axes.plot_parametric_curve(\n            lambda t: (1.5 * math.cos(t), 1.5 * math.sin(t), t / 4), t_range=(-6, 6), color=ORANGE)\n        title = Text(\"ThreeDAxes\", font_size=36).to_corner(UL)\n        self.add_fixed_in_frame_mobjects(title)\n        self.play(Create(helix), FadeIn(title))\n\n        self.move_camera(phi=55 * DEGREES, theta=20 * DEGREES, run_time=2)\n        self.begin_ambient_camera_rotation(rate=0.4)\n        self.wait(2)\n        self.stop_ambient_camera_rotation()\n\n\nclass SolidsScene(ThreeDScene):\n    def construct(self):\n        self.set_camera_orientation(phi=65 * DEGREES, theta=-40 * DEGREES)\n        sphere = Sphere(radius=0.9, resolution=(16, 8)).shift(LEFT * 2.6)\n        cube = Cube(side_length=1.4, fill_color=TEAL)\n        torus = Torus(major_radius=0.8, minor_radius=0.25, resolution=(16, 8)).shift(RIGHT * 2.6)\n        arrow = Arrow3D(start=DOWN * 2 + LEFT * 2, end=DOWN * 2 + RIGHT * 2, color=YELLOW, resolution=8)\n        self.play(FadeIn(sphere), FadeIn(cube), FadeIn(torus))\n        self.play(Create(arrow))\n        self.play(Rotate(cube, PI / 2, axis=UP), Rotate(torus, PI / 2, axis=RIGHT), run_time=2)\n        self.move_camera(theta=40 * DEGREES, run_time=2)\n        self.wait()\n\n\nclass PolyhedraScene(ThreeDScene):\n    def construct(self):\n        self.set_camera_orientation(phi=70 * DEGREES, theta=-60 * DEGREES)\n        tetra = Tetrahedron(edge_length=2.2).shift(LEFT * 2)\n        hull = ConvexHull3D(*[[math.cos(a), math.sin(a), (-1) ** k * 0.6]\n                              for k, a in enumerate([i * TAU / 7 for i in range(7)])],\n                            faces_config={\"fill_color\": TEAL, \"fill_opacity\": 0.7}).shift(RIGHT * 2)\n        self.play(Create(tetra), Create(hull))\n        # Moving a vertex dot drags its faces along (Polyhedron's face updater).\n        self.play(tetra.graph[0].animate.shift(OUT + RIGHT * 0.5))\n        self.wait(0.5)\n"
    }
  },
  {
    "id": "logaxes",
    "label": "Logarithmic axes and colors",
    "path": "examples/log_axes_scene.py",
    "type": "manim",
    "cover": "gallery/previews/logaxes.png",
    "video": "gallery/previews/logaxes.mp4",
    "editorURL": "./?example=logaxes&url=examples%2Flog_axes_scene.py",
    "title": "Logarithmic axes and colors",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Logarithmic axes with base-10 labels, exponential growth and ManimColor helpers.\"\"\"\nfrom manim import *\n\n\nclass LogAxesScene(Scene):\n    def construct(self):\n        axes = Axes(x_range=[0, 10, 1], y_range=[-1, 4, 1], x_length=9, y_length=5.5, tips=False,\n                    axis_config={\"include_numbers\": True},\n                    y_axis_config={\"scaling\": LogBase(custom_labels=True)})\n        self.play(Create(axes), run_time=2)\n        palette = RandomColorGenerator(seed=7)\n        curves = VGroup(*(axes.plot(lambda x, b=b: b ** x, x_range=[0, min(10, 4 / np.log10(b))], color=palette.next())\n                          for b in (2, 3, 10)))\n        self.play(LaggedStart(*(Create(c) for c in curves), lag_ratio=.4), run_time=3)\n        dot = Dot(axes.c2p(1, 2), color=ManimColor(\"#FFD700\"))\n        label = DecimalNumber(2, num_decimal_places=1, unit=r\"\\,\\text{units}\", font_size=30)\n        label.add_updater(lambda m: m.set_value(axes.p2c(dot.get_center())[1]).next_to(dot, UR, buff=.1))\n        self.add(dot, label)\n        self.play(MoveAlongPath(dot, curves[0]), run_time=3)\n        self.play(curves.animate.set_color(RED.lighter(.4)))\n        self.wait(.5)\n"
    }
  },
  {
    "id": "typing",
    "label": "Typing, boundaries and implicit curves",
    "path": "examples/typing_scene.py",
    "type": "manim",
    "cover": "gallery/previews/typing.png",
    "video": "gallery/previews/typing.mp4",
    "editorURL": "./?example=typing&url=examples%2Ftyping_scene.py",
    "title": "Typing, boundaries and implicit curves",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Typing with a cursor, animated boundaries, re-timed motion and implicit curves.\"\"\"\nfrom manim import *\n\n\nclass TypingScene(Scene):\n    def construct(self):\n        text = Text(\"Hello, Manim!\", font=\"Monospace\", font_size=40).to_edge(UP)\n        cursor = Rectangle(height=.6, width=.25, fill_opacity=1, stroke_width=0, color=GREY_A).move_to(text[0])\n        self.play(TypeWithCursor(text, cursor))\n        self.play(Blink(cursor, blinks=2, time_on=.2, time_off=.2))\n        heart = ImplicitFunction(lambda x, y: (x * x + y * y - 1) ** 3 - x * x * y ** 3,\n                                 x_range=[-1.5, 1.5], y_range=[-1.3, 1.6], color=RED).scale(1.3).shift(LEFT * 3)\n        boundary = AnimatedBoundary(Square(2.6).move_to(heart), cycle_rate=1)\n        self.play(Create(heart))\n        self.add(boundary)\n        dot = Dot(RIGHT * 1.5 + DOWN, color=YELLOW)\n        self.add(dot)\n        self.play(ChangeSpeed(dot.animate.shift(RIGHT * 4), {0.4: .2, 0.8: 3}, rate_func=linear), run_time=2)\n        room = LabeledPolygram([(1, 1.5, 0), (5, 1.5, 0), (5, 0, 0), (3, 0, 0), (3, -.8, 0), (1, -.8, 0)],\n                               label=\"Room\", color=TEAL)\n        self.play(FadeIn(room))\n        self.play(ShowPassingFlashWithThinningStrokeWidth(heart.copy().set_color(YELLOW), n_segments=8, time_width=.4))\n        self.play(UntypeWithCursor(text, cursor))\n        self.wait(.5)\n"
    }
  },
  {
    "id": "svgimage",
    "label": "Inline SVG and pixel images",
    "path": "examples/svg_image_scene.py",
    "type": "manim",
    "cover": "gallery/previews/svgimage.png",
    "video": "gallery/previews/svgimage.mp4",
    "editorURL": "./?example=svgimage&url=examples%2Fsvg_image_scene.py",
    "title": "Inline SVG and pixel images",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"SVG drawings written to a file, and pixel-array images (no uploads are needed in the browser).\"\"\"\nfrom pathlib import Path\n\nfrom manim import *\n\nLOGO = \"\"\"<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 120 100\">\n  <circle cx=\"35\" cy=\"50\" r=\"30\" fill=\"#58C4DD\"/>\n  <rect x=\"55\" y=\"20\" width=\"60\" height=\"60\" rx=\"8\" fill=\"#FC6255\"/>\n  <path d=\"M 20 90 Q 60 60 100 90\" fill=\"none\" stroke=\"#FFFF00\" stroke-width=\"4\"/>\n  <polygon points=\"60,5 70,25 50,25\" fill=\"#83C167\"/>\n</svg>\"\"\"\n\n\nclass SvgImageScene(Scene):\n    def construct(self):\n        # Manim reads SVG files; the browser's Python has a writable in-memory file system.\n        Path(\"logo.svg\").write_text(LOGO)\n        logo = SVGMobject(\"logo.svg\", height=2.5).to_edge(LEFT, buff=1)\n        self.play(LaggedStart(*(DrawBorderThenFill(part) for part in logo), lag_ratio=.3), run_time=2)\n        # A 48 x 48 RGB gradient built from plain lists.\n        pixels = [[[int(255 * x / 47), int(255 * y / 47), 160] for x in range(48)] for y in range(48)]\n        # Height = rows / scale_to_resolution * frame height: 48 rows -> 2 units.\n        image = ImageMobject(pixels, scale_to_resolution=192).to_edge(RIGHT, buff=1)\n        checker = ImageMobject([[255 * ((x + y) % 2) for x in range(8)] for y in range(8)], scale_to_resolution=64)\n        checker.set_resampling_algorithm(RESAMPLING_ALGORITHMS[\"nearest\"]).next_to(image, DOWN)\n        self.play(FadeIn(image, shift=LEFT), FadeIn(checker))\n        self.play(image.animate.rotate(PI / 6).scale(.8), logo.animate.scale(.8))\n        self.play(Transform(logo[1], Circle(radius=.6, color=RED, fill_opacity=1).move_to(logo[1])))\n        self.wait(.5)\n"
    }
  },
  {
    "id": "code",
    "label": "Syntax-highlighted code",
    "path": "examples/code_scene.py",
    "type": "manim",
    "cover": "gallery/previews/code.png",
    "video": "gallery/previews/code.mp4",
    "editorURL": "./?example=code&url=examples%2Fcode_scene.py",
    "title": "Syntax-highlighted code",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Syntax-highlighted code listings with line numbers and window backgrounds.\"\"\"\nfrom manim import *\n\n\nclass CodeScene(Scene):\n    def construct(self):\n        source = '''def fibonacci(n):\n    \"\"\"Return the first n Fibonacci numbers.\"\"\"\n    a, b = 0, 1\n    for _ in range(n):\n        yield a\n        a, b = b, a + b\n\nprint(list(fibonacci(8)))'''\n        code = Code(code_string=source, language=\"python\", background=\"window\",\n                    formatter_style=\"monokai\")\n        self.play(FadeIn(code.background), run_time=.5)\n        self.play(Write(code.line_numbers), AddTextLetterByLetter(code.code_lines[0]))\n        self.play(LaggedStart(*(FadeIn(line, shift=RIGHT * .2) for line in code.code_lines[1:]), lag_ratio=.2))\n        box = SurroundingRectangle(code.code_lines[5], color=YELLOW, buff=.05)\n        self.play(Create(box))\n        self.play(box.animate.become(SurroundingRectangle(code.code_lines[3], color=YELLOW, buff=.05)))\n        self.play(code.animate.scale(.7).to_edge(LEFT), FadeOut(box))\n        result = Code(code_string=\"[0, 1, 1, 2, 3, 5, 8, 13]\", language=\"python\", add_line_numbers=False)\n        result.next_to(code, RIGHT, buff=.5)\n        self.play(FadeIn(result, shift=LEFT))\n        self.wait(.5)\n"
    }
  },
  {
    "id": "boolean",
    "label": "Boolean shape operations",
    "path": "examples/boolean_scene.py",
    "type": "manim",
    "cover": "gallery/previews/boolean.png",
    "video": "gallery/previews/boolean.mp4",
    "editorURL": "./?example=boolean&url=examples%2Fboolean_scene.py",
    "title": "Boolean shape operations",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Union, intersection, difference and exclusion of overlapping outlines.\"\"\"\nfrom manim import *\n\n\nclass BooleanScene(Scene):\n    def construct(self):\n        circle = Circle(radius=1, color=BLUE, fill_opacity=.4).shift(LEFT * .6)\n        square = Square(1.8, color=RED, fill_opacity=.4).shift(RIGHT * .6).rotate(PI / 8)\n        pair = VGroup(circle, square).shift(UP * 1.6)\n        self.play(Create(circle), Create(square))\n        operations = VGroup(\n            Union(circle, square, color=TEAL, fill_opacity=.6),\n            Intersection(circle, square, color=YELLOW, fill_opacity=.6),\n            Difference(circle, square, color=PURPLE, fill_opacity=.6),\n            Exclusion(circle, square, color=GREEN, fill_opacity=.6),\n        ).scale(.6)\n        names = VGroup(*(Text(n, font_size=22) for n in (\"Union\", \"Intersection\", \"Difference\", \"Exclusion\")))\n        # Arrange each result above its name so labels never collide.\n        columns = VGroup(*(VGroup(op, name).arrange(DOWN) for op, name in zip(operations, names)))\n        columns.arrange(RIGHT, buff=.5, aligned_edge=DOWN).shift(DOWN * 1.6)\n        self.play(LaggedStart(*(TransformFromCopy(pair, op) for op in operations), lag_ratio=.3), run_time=3)\n        self.play(FadeIn(names))\n        holed = Difference(Square(2.4), Circle(.6), color=GOLD, fill_opacity=.8).move_to(pair)\n        self.play(FadeOut(circle), FadeOut(square), FadeIn(holed))\n        self.play(Transform(holed, Union(Circle(1), Square(1.4).shift(RIGHT), color=GOLD, fill_opacity=.8).move_to(holed)))\n        self.wait(.5)\n"
    }
  },
  {
    "id": "graphs",
    "label": "Graph layouts and directed trees",
    "path": "examples/graph_scene.py",
    "type": "manim",
    "cover": "gallery/previews/graphs.png",
    "video": "gallery/previews/graphs.mp4",
    "editorURL": "./?example=graphs&url=examples%2Fgraph_scene.py",
    "title": "Graph layouts and directed trees",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Graph layouts, moving vertices with attached edges, and directed trees.\"\"\"\nfrom manim import *\n\n\nclass GraphScene(Scene):\n    def construct(self):\n        vertices = [1, 2, 3, 4, 5, 6]\n        edges = [(1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 1), (1, 4)]\n        graph = Graph(vertices, edges, layout=\"circular\", labels=True,\n                      vertex_config={\"fill_color\": TEAL}, edge_config={\"stroke_width\": 3})\n        self.play(Create(graph), run_time=2)\n        self.play(graph[1].animate.move_to(UP * 2.5 + RIGHT * 2))\n        self.play(graph.animate.change_layout(\"spring\", layout_config={\"seed\": 2}))\n        self.play(graph.animate.add_vertices(7, positions={7: DOWN * 3}))\n        self.play(graph.animate.add_edges((7, 3), (7, 6)))\n        self.play(graph.animate.remove_vertices(4))\n        self.play(graph.animate.scale(.6).to_edge(LEFT))\n        tree = DiGraph([1, 2, 3, 4, 5, 6, 7], [(1, 2), (1, 3), (2, 4), (2, 5), (3, 6), (3, 7)],\n                       layout=\"tree\", root_vertex=1, layout_scale=2,\n                       vertex_config={\"color\": GOLD}, edge_config={\"tip_config\": {\"tip_length\": .2}})\n        tree.to_edge(RIGHT)\n        self.play(Create(tree), run_time=2)\n        self.play(tree[5].animate.shift(DOWN * .8 + RIGHT * .5))\n        self.wait(.5)\n"
    }
  },
  {
    "id": "effects",
    "label": "Hulls, cutouts and attention effects",
    "path": "examples/effects_scene.py",
    "type": "manim",
    "cover": "gallery/previews/effects.png",
    "video": "gallery/previews/effects.mp4",
    "editorURL": "./?example=effects&url=examples%2Feffects_scene.py",
    "title": "Hulls, cutouts and attention effects",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Hulls, cutouts, tangent arcs, arc braces and attention effects.\"\"\"\nfrom manim import *\n\n\nclass EffectsScene(Scene):\n    def construct(self):\n        title = Text(\"Shapes and effects\", font_size=36).to_edge(UP)\n        self.play(AddTextWordByWord(title))\n        points = [LEFT * 2 + DOWN, RIGHT * 2 + DOWN * 1.5, RIGHT * 2.5 + UP, UP * 1.5, LEFT * 2.5 + UP * .5, ORIGIN]\n        dots = VGroup(*(Dot(p) for p in points))\n        hull = ConvexHull(*points, color=TEAL, fill_opacity=.3)\n        shapes = VDict({\"hull\": VGroup(dots, hull).scale(.6).shift(LEFT * 4)})\n        shapes[\"cutout\"] = Cutout(Square(2.5), Circle(.6).shift(LEFT * .5), Square(.6).shift(RIGHT * .6 + UP * .4),\n                                  fill_opacity=.8, color=BLUE, stroke_width=2)\n        l1, l2 = Line(LEFT * 1.5, RIGHT * 1.5), Line(DOWN * 1.2 + LEFT * .8, UP * 1.2 + RIGHT * .8)\n        arc = TangentialArc(l1, l2, radius=.5, color=YELLOW)\n        shapes[\"corner\"] = VGroup(l1, l2, arc).shift(RIGHT * 4)\n        self.play(LaggedStartMap(FadeIn, VGroup(*shapes.get_all_submobjects()), shift=UP * .3), run_time=2)\n        self.play(Broadcast(Circle(radius=1.5, color=YELLOW), focal_point=shapes[\"corner\"].get_center(), n_mobs=3))\n        self.play(Blink(shapes[\"cutout\"], blinks=2, time_on=.25, time_off=.25))\n        ring = Arc(radius=1.5, start_angle=PI / 4, angle=PI / 2).move_to(DOWN * 2.6 + LEFT * 3)\n        brace = ArcBrace(ring, color=GOLD)\n        self.play(Create(ring), FadeIn(brace))\n        stars = VGroup(*(Star(outer_radius=.3, color=c, fill_opacity=.8) for c in (RED, GREEN, BLUE, PURPLE)))\n        stars.arrange(RIGHT, buff=.4).to_edge(DOWN).shift(RIGHT * 2.5)\n        self.play(SpiralIn(stars), run_time=2)\n        self.wait(.5)\n"
    }
  },
  {
    "id": "vectorfields",
    "label": "Vector fields and stream lines",
    "path": "examples/vector_field_scene.py",
    "type": "manim",
    "cover": "gallery/previews/vectorfields.png",
    "video": "gallery/previews/vectorfields.mp4",
    "editorURL": "./?example=vectorfields&url=examples%2Fvector_field_scene.py",
    "title": "Vector fields and stream lines",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Arrow fields, particles nudged along a field, and flowing stream lines.\"\"\"\nfrom manim import *\n\n\nclass VectorFieldScene(Scene):\n    def construct(self):\n        func = lambda pos: np.sin(pos[0] / 2) * UR + np.cos(pos[1] / 2) * LEFT\n        field = ArrowVectorField(func, x_range=[-7, 7, 1], y_range=[-4, 4, 1])\n        self.play(Create(field), run_time=1.5)\n        dots = VGroup(*(Dot(point, color=WHITE) for point in (LEFT * 3, ORIGIN, RIGHT * 3 + UP)))\n        self.add(dots)\n        for dot in dots:\n            dot.add_updater(field.get_nudge_updater(speed=1.5))\n        self.wait(2)\n        for dot in dots:\n            dot.clear_updaters()\n        self.play(FadeOut(field), FadeOut(dots), run_time=.5)\n        swirl = lambda pos: (pos[0] * UR + pos[1] * LEFT) - pos\n        # Sparse starts and short traces keep the preview's frame data small.\n        stream = StreamLines(swirl, stroke_width=2, max_anchors_per_line=15, virtual_time=1.5,\n                             x_range=[-6, 6, 1.5], y_range=[-3.5, 3.5, 1.5])\n        self.play(stream.create(), run_time=2)\n        self.add(stream)  # The flow updater runs on the field, so it must be in the scene.\n        stream.start_animation(warm_up=False, flow_speed=1.5)\n        self.wait(1.5)\n        self.play(stream.end_animation())\n        self.wait(.5)\n"
    }
  },
  {
    "id": "charts",
    "label": "Bar charts and polar planes",
    "path": "examples/chart_scene.py",
    "type": "manim",
    "cover": "gallery/previews/charts.png",
    "video": "gallery/previews/charts.mp4",
    "editorURL": "./?example=charts&url=examples%2Fchart_scene.py",
    "title": "Bar charts and polar planes",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Bar charts with animated values, and polar coordinates with a rotating vector.\"\"\"\nfrom manim import *\n\n\nclass ChartScene(Scene):\n    def construct(self):\n        chart = BarChart([3, 5, 2, 4], bar_names=[\"A\", \"B\", \"C\", \"D\"], y_range=[0, 6, 2],\n                         y_length=4, x_length=5).to_edge(LEFT)\n        labels = chart.get_bar_labels(font_size=24)\n        self.play(Create(chart), run_time=2)\n        self.play(FadeIn(labels), run_time=.5)\n        self.play(FadeOut(labels), chart.animate.change_bar_values([5, 2, 4, 1]), run_time=1.5)\n        plane = PolarPlane(size=4, azimuth_units=\"PI radians\").add_coordinates().to_edge(RIGHT)\n        angle = ValueTracker(PI / 6)\n        vector = always_redraw(lambda: Arrow(plane.get_origin(), plane.pr2pt(1.5, angle.get_value()),\n                                             buff=0, color=YELLOW))\n        self.play(Create(plane), run_time=2)\n        self.add(vector)\n        self.play(angle.animate.set_value(PI * 4 / 3), run_time=2)\n        self.wait(.5)\n"
    }
  },
  {
    "id": "stretch",
    "label": "Stretch nested vector shapes",
    "path": "examples/stretch_scene.py",
    "type": "manim",
    "cover": "gallery/previews/stretch.png",
    "video": "gallery/previews/stretch.mp4",
    "editorURL": "./?example=stretch&url=examples%2Fstretch_scene.py",
    "title": "Stretch nested vector shapes",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Stretch nested vector families, including curved shafts and real tips.\"\"\"\nfrom manim import *\n\n\nclass StretchScene(Scene):\n    def construct(self):\n        circle = Circle(color=BLUE).shift(LEFT*2)\n        box = Rectangle(width=1.4, height=.7, color=GREEN).shift(DOWN*.6)\n        arrow = CurvedDoubleArrow(LEFT, RIGHT, angle=PI/2, color=YELLOW).shift(UP*.7)\n        family = VGroup(circle, VGroup(box, arrow).shift(RIGHT*2)).rotate(PI/12)\n        self.play(Create(family), run_time=2)\n        family.save_state()\n        self.play(family.animate.stretch(1.4, 0), run_time=2)\n        self.play(family.animate.stretch_to_fit_height(2), run_time=2)\n        self.play(Restore(family), run_time=1)\n        self.play(FadeOut(family), run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "surround",
    "label": "Surround moving shapes",
    "path": "examples/surround_scene.py",
    "type": "manim",
    "cover": "gallery/previews/surround.png",
    "video": "gallery/previews/surround.mp4",
    "editorURL": "./?example=surround&url=examples%2Fsurround_scene.py",
    "title": "Surround moving shapes",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"A surrounding circle follows a rectangle's transformed bounds.\"\"\"\nfrom manim import *\n\n\nclass SurroundScene(Scene):\n    def construct(self):\n        target = Rectangle(width=3, height=1.5, color=BLUE).shift(LEFT)\n        ring = Circle(color=YELLOW).surround(target, buffer_factor=1.1)\n        target.save_state()\n        self.play(Create(target), Create(ring), run_time=2)\n        # Follow only once both are drawn: while Create draws the target, Manim's copy of the\n        # ring would surround the collapsed rectangle and could never grow back.\n        ring.add_updater(lambda mob: mob.surround(target, buffer_factor=1.1))\n        self.play(target.animate.rotate(PI/4).scale(1.2), run_time=2)\n        self.play(target.animate.scale_to_fit_width(2).shift(RIGHT*3), run_time=2)\n        self.play(Restore(target), run_time=1)\n        ring.clear_updaters()\n        self.play(FadeOut(target), FadeOut(ring), run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "circleconstruction",
    "label": "Construct circles through three points",
    "path": "examples/circle_construction_scene.py",
    "type": "manim",
    "cover": "gallery/previews/circleconstruction.png",
    "video": "gallery/previews/circleconstruction.mp4",
    "editorURL": "./?example=circleconstruction&url=examples%2Fcircle_construction_scene.py",
    "title": "Construct circles through three points",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Construct a circle through three points and follow its rotated boundary.\"\"\"\nfrom manim import *\n\n\nclass CircleConstructionScene(Scene):\n    def construct(self):\n        points = [LEFT*2, UP*2, RIGHT*2]\n        circle = Circle.from_three_points(*points, color=BLUE)\n        dots = VGroup(*(Dot(point, color=YELLOW) for point in points))\n        marker = Dot(circle.point_at_angle(PI/2), color=RED, radius=.12)\n        marker.add_updater(lambda mob: mob.move_to(circle.point_at_angle(PI/2)))\n        circle.save_state()\n        self.play(Create(circle), FadeIn(dots), FadeIn(marker), run_time=2)\n        self.play(circle.animate.rotate(PI/3).scale(.7), run_time=2)\n        self.play(circle.animate.move_arc_center_to(RIGHT*2+DOWN), run_time=2)\n        self.play(Restore(circle), run_time=1)\n        self.play(FadeOut(circle), FadeOut(dots), FadeOut(marker), run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "generictips",
    "label": "Attach tips to arcs and circles",
    "path": "examples/generic_tips_scene.py",
    "type": "manim",
    "cover": "gallery/previews/generictips.png",
    "video": "gallery/previews/generictips.mp4",
    "editorURL": "./?example=generictips&url=examples%2Fgeneric_tips_scene.py",
    "title": "Attach tips to arcs and circles",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Shared tip APIs on open arcs and closed circle outlines.\"\"\"\nfrom manim import *\n\n\nclass GenericTipsScene(Scene):\n    def construct(self):\n        arc = Arc(radius=1.6, start_angle=PI/6, angle=4*PI/3,\n                  arc_center=LEFT*2, color=BLUE, tip_length=.5)\n        arc.add_tip().add_tip(at_start=True, tip_shape=ArrowTriangleTip)\n        circle = Circle(radius=1.3, color=GREEN, tip_length=.5).shift(RIGHT*2)\n        circle.add_tip(tip_shape=StealthTip)\n        arc.save_state()\n        circle.save_state()\n        self.play(Create(arc), Create(circle), run_time=2)\n        self.play(arc.animate.rotate(PI/4).scale(.8),\n                  circle.animate.rotate(-PI/3).scale(.8), run_time=2)\n        self.play(arc.animate.put_start_and_end_on(LEFT*3+DOWN, LEFT+UP),\n                  circle.animate.shift(UP), run_time=2)\n        self.play(Restore(arc), Restore(circle), run_time=1)\n        self.play(FadeOut(arc), FadeOut(circle), run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "tipstyles",
    "label": "Style and build arrow tips",
    "path": "examples/tip_style_scene.py",
    "type": "manim",
    "cover": "gallery/previews/tipstyles.png",
    "video": "gallery/previews/tipstyles.mp4",
    "editorURL": "./?example=tipstyles&url=examples%2Ftip_style_scene.py",
    "title": "Style and build arrow tips",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Tip style dictionaries, independent widths and detached tip factories.\"\"\"\nfrom manim import *\n\n\nclass TipStyleScene(Scene):\n    def construct(self):\n        straight = Arrow(LEFT*3+UP,RIGHT*3+UP,buff=0,color=BLUE,tip_length=.6,\n                         tip_style={\"fill_color\":RED,\"stroke_color\":YELLOW,\n                                    \"fill_opacity\":.4,\"stroke_width\":3,\"width\":.8})\n        curved = CurvedDoubleArrow(LEFT*3+DOWN,RIGHT*3+DOWN,angle=PI/2,color=GREEN,\n                                  tip_length=.6,\n                                  tip_style={\"fill_color\":YELLOW,\"stroke_color\":PURPLE,\n                                             \"fill_opacity\":.5,\"stroke_width\":3,\"width\":.7})\n        straight.save_state()\n        curved.save_state()\n        self.play(Create(straight),Create(curved),run_time=2)\n        self.play(straight.animate.rotate(PI/10).scale(.8),\n                  curved.animate.rotate(-PI/10).scale(.8),run_time=2)\n        straight.tip_style.pop(\"width\")\n        head = straight.create_tip(tip_length=.6,tip_width=1.1)\n        # The factory positions a detached tip before it is attached.\n        head.set_fill(GREEN,opacity=.8).set_stroke(WHITE,width=2)\n        straight.pop_tips()\n        straight.add_tip(tip=head)\n        self.wait(2)\n        self.play(Restore(straight),Restore(curved),run_time=1)\n        self.play(FadeOut(straight),FadeOut(curved),run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "curvedarrows",
    "label": "Animate tangent-aligned curved arrows",
    "path": "examples/curved_arrow_scene.py",
    "type": "manim",
    "cover": "gallery/previews/curvedarrows.png",
    "video": "gallery/previews/curvedarrows.mp4",
    "editorURL": "./?example=curvedarrows&url=examples%2Fcurved_arrow_scene.py",
    "title": "Animate tangent-aligned curved arrows",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Tangent-aligned curved arrows, affine endpoint fitting and restoration.\"\"\"\nfrom manim import *\n\n\nclass CurvedArrowScene(Scene):\n    def construct(self):\n        upper = CurvedArrow(LEFT*3+UP,RIGHT*3+UP,angle=-PI/2,color=BLUE,tip_length=.6)\n        lower = CurvedDoubleArrow(LEFT*3+DOWN,RIGHT*3+DOWN,angle=PI/2,color=GREEN,\n                                 tip_shape_start=ArrowSquareTip,\n                                 tip_shape_end=ArrowCircleFilledTip,tip_length=.6)\n        upper.save_state()\n        lower.save_state()\n        markers = VGroup(Dot(upper.get_start(),color=RED,radius=.08),\n                         Dot(upper.get_end(),color=WHITE,radius=.08),\n                         Dot(lower.get_start(),color=PURPLE,radius=.08),\n                         Dot(lower.get_end(),color=YELLOW,radius=.08))\n        markers[0].add_updater(lambda dot:dot.move_to(upper.get_start()))\n        markers[1].add_updater(lambda dot:dot.move_to(upper.get_end()))\n        markers[2].add_updater(lambda dot:dot.move_to(lower.get_start()))\n        markers[3].add_updater(lambda dot:dot.move_to(lower.get_end()))\n        self.play(Create(upper),Create(lower),FadeIn(markers),run_time=2)\n        self.play(upper.animate.rotate(PI/8).scale(.8),\n                  lower.animate.rotate(-PI/8).scale(.8),run_time=2)\n        self.play(upper.animate.put_start_and_end_on(LEFT*2+UP,RIGHT*2+UP*2),\n                  lower.animate.put_start_and_end_on(LEFT*2+DOWN,RIGHT*2+DOWN*2),run_time=2)\n        self.play(Restore(upper),Restore(lower),run_time=1)\n        self.play(FadeOut(upper),FadeOut(lower),FadeOut(markers),run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "doublearrow",
    "label": "Animate two-ended arrows",
    "path": "examples/double_arrow_scene.py",
    "type": "manim",
    "cover": "gallery/previews/doublearrow.png",
    "video": "gallery/previews/doublearrow.mp4",
    "editorURL": "./?example=doublearrow&url=examples%2Fdouble_arrow_scene.py",
    "title": "Animate two-ended arrows",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Two-ended arrows with separate shapes, endpoint updates and checkpoints.\"\"\"\nfrom manim import *\n\n\nclass DoubleArrowScene(Scene):\n    def construct(self):\n        default = DoubleArrow(LEFT*3+UP,RIGHT*3+UP,buff=0,color=BLUE,tip_length=.6)\n        mixed = DoubleArrow(LEFT*3+DOWN,RIGHT*3+DOWN,buff=0,color=GREEN,\n                            tip_shape_start=ArrowSquareTip,\n                            tip_shape_end=ArrowCircleFilledTip,tip_length=.6)\n        default.save_state()\n        mixed.save_state()\n        markers = VGroup(Dot(default.get_start(),color=RED,radius=.08),\n                         Dot(default.get_end(),color=WHITE,radius=.08),\n                         Dot(mixed.get_start(),color=PURPLE,radius=.08),\n                         Dot(mixed.get_end(),color=YELLOW,radius=.08))\n        markers[0].add_updater(lambda dot:dot.move_to(default.get_start()))\n        markers[1].add_updater(lambda dot:dot.move_to(default.get_end()))\n        markers[2].add_updater(lambda dot:dot.move_to(mixed.get_start()))\n        markers[3].add_updater(lambda dot:dot.move_to(mixed.get_end()))\n        self.play(Create(default),Create(mixed),FadeIn(markers),run_time=2)\n        self.play(default.animate.rotate(PI/6).scale(.7),\n                  mixed.animate.rotate(-PI/6).scale(.7),run_time=2)\n        self.play(default.animate.put_start_and_end_on(LEFT*2+UP,RIGHT*2+UP*2),\n                  mixed.animate.put_start_and_end_on(LEFT*2+DOWN,RIGHT*2+DOWN*2),run_time=2)\n        self.play(Restore(default),Restore(mixed),run_time=1)\n        self.play(FadeOut(default),FadeOut(mixed),FadeOut(markers),run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "roundsquaretips",
    "label": "Render circular and square arrow tips",
    "path": "examples/round_square_tips_scene.py",
    "type": "manim",
    "cover": "gallery/previews/roundsquaretips.png",
    "video": "gallery/previews/roundsquaretips.mp4",
    "editorURL": "./?example=roundsquaretips&url=examples%2Fround_square_tips_scene.py",
    "title": "Render circular and square arrow tips",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Circular and square tips with transformed shafts and endpoint markers.\"\"\"\nfrom manim import *\n\n\nclass RoundSquareTipsScene(Scene):\n    def construct(self):\n        circle = Arrow(LEFT*3+UP,RIGHT*3+UP,buff=0,color=BLUE,\n                       tip_shape=ArrowCircleFilledTip,tip_length=.7)\n        circle.add_tip(at_start=True,tip_shape=ArrowCircleTip,tip_length=.7)\n        square = Arrow(LEFT*3+DOWN,RIGHT*3+DOWN,buff=0,color=GREEN,\n                       tip_shape=ArrowSquareFilledTip,tip_length=.7)\n        square.add_tip(at_start=True,tip_shape=ArrowSquareTip,tip_length=.7)\n        circle.save_state()\n        square.save_state()\n        top = Dot(circle.get_end(),color=WHITE,radius=.08)\n        bottom = Dot(square.get_end(),color=YELLOW,radius=.08)\n        top.add_updater(lambda dot:dot.move_to(circle.get_end()))\n        bottom.add_updater(lambda dot:dot.move_to(square.get_end()))\n        self.play(Create(circle),Create(square),FadeIn(top),FadeIn(bottom),run_time=2)\n        self.play(circle.animate.rotate(PI/6).scale(.8),\n                  square.animate.rotate(-PI/6).scale(.8),run_time=2)\n        self.play(circle.animate.put_start_and_end_on(LEFT*2+UP,RIGHT*2+UP*2),\n                  square.animate.put_start_and_end_on(LEFT*2+DOWN,RIGHT*2+DOWN*2),run_time=2)\n        self.play(Restore(circle),Restore(square),run_time=1)\n        self.play(FadeOut(circle),FadeOut(square),FadeOut(top),FadeOut(bottom),run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "arrowtips",
    "label": "Manage arrow tips and shafts",
    "path": "examples/arrow_tips_scene.py",
    "type": "manim",
    "cover": "gallery/previews/arrowtips.png",
    "video": "gallery/previews/arrowtips.mp4",
    "editorURL": "./?example=arrowtips&url=examples%2Farrow_tips_scene.py",
    "title": "Manage arrow tips and shafts",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Real arrow tip children, endpoint edits, fixed-size heads and restoration.\"\"\"\nfrom manim import *\n\n\nclass ArrowTipsScene(Scene):\n    def construct(self):\n        arrow = Arrow(LEFT*3,RIGHT*3,buff=0,color=BLUE,tip_length=.6)\n        arrow.add_tip(at_start=True,tip_shape=ArrowTriangleTip,tip_length=.6)\n        arrow.save_state()\n        point = Dot(arrow.get_end(),color=WHITE,radius=.1)\n        point.add_updater(lambda dot:dot.move_to(arrow.get_end()))\n        self.play(Create(arrow),FadeIn(point),run_time=2)\n        self.play(arrow.animate.scale(.6).rotate(PI/4),run_time=2)\n        self.play(arrow.animate.put_start_and_end_on(LEFT*2+DOWN,RIGHT*2+UP),run_time=2)\n        arrow.pop_tips()\n        arrow.add_tip(tip_shape=StealthTip,tip_length=.6)\n        self.wait(1)\n        self.play(Restore(arrow),run_time=1)\n        self.play(FadeOut(arrow),FadeOut(point),run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "tipgeometry",
    "label": "Edit arrow tip outlines",
    "path": "examples/tip_geometry_scene.py",
    "type": "manim",
    "cover": "gallery/previews/tipgeometry.png",
    "video": "gallery/previews/tipgeometry.mp4",
    "editorURL": "./?example=tipgeometry&url=examples%2Ftip_geometry_scene.py",
    "title": "Edit arrow tip outlines",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Editable arrow-tip outlines, transforms, live anchor queries and restoration.\"\"\"\nfrom manim import *\n\n\nclass TipGeometryScene(Scene):\n    def construct(self):\n        outline = ArrowTriangleTip(length=1.5,width=1,color=BLUE).shift(LEFT*3)\n        filled = ArrowTriangleFilledTip(length=1.5,width=1,color=GREEN)\n        stealth = StealthTip(length=1.5,color=YELLOW).shift(RIGHT*3)\n        filled.save_state()\n        point = Dot(filled.tip_point,color=WHITE,radius=.1)\n        base = Dot(filled.base,color=PURPLE,radius=.1)\n        point.add_updater(lambda dot:dot.move_to(filled.tip_point))\n        base.add_updater(lambda dot:dot.move_to(filled.base))\n        self.play(Create(outline),Create(filled),Create(stealth),FadeIn(point),FadeIn(base),run_time=2)\n        self.play(filled.animate.rotate(PI/2).scale(1.4),run_time=2)\n        self.play(Transform(filled,StealthTip(length=1.5,color=RED).move_to(filled.get_center())),run_time=2)\n        self.play(Restore(filled),run_time=1)\n        self.play(FadeOut(outline),FadeOut(filled),FadeOut(stealth),FadeOut(point),FadeOut(base),run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "shapelayout",
    "label": "Arrange children on a shape",
    "path": "examples/shape_layout_scene.py",
    "type": "manim",
    "cover": "gallery/previews/shapelayout.png",
    "video": "gallery/previews/shapelayout.mp4",
    "editorURL": "./?example=shapelayout&url=examples%2Fshape_layout_scene.py",
    "title": "Arrange children on a shape",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Arrange a shape's children while preserving its own transformed outline.\"\"\"\nfrom manim import *\n\n\nclass ShapeLayoutScene(Scene):\n    def construct(self):\n        host = Rectangle(width=6,height=4,color=BLUE,fill_opacity=.1)\n        host.add(*(Dot(LEFT*1.5,color=color,radius=.15)\n                   for color in (GREEN,YELLOW,RED,PURPLE)))\n        host.arrange_submobjects(RIGHT,buff=.5,center=False)\n        host.rotate(PI/8).scale(.8)\n        host.save_state()\n        anchor = Dot(host.get_start(),color=WHITE)\n        self.play(Create(host),FadeIn(anchor),run_time=2)\n        self.play(host.animate.arrange_in_grid(rows=2,cols=2,buff=(.6,.5)),run_time=2)\n        self.play(host.animate.arrange_submobjects(DOWN,buff=.4,center=False),run_time=2)\n        self.play(Restore(host),run_time=1)\n        self.play(FadeOut(host),FadeOut(anchor),run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "gridlayout",
    "label": "Reflow a transformed grid",
    "path": "examples/grid_layout_scene.py",
    "type": "manim",
    "cover": "gallery/previews/gridlayout.png",
    "video": "gallery/previews/gridlayout.mp4",
    "editorURL": "./?example=gridlayout&url=examples%2Fgrid_layout_scene.py",
    "title": "Reflow a transformed grid",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Reflow a transformed grid while preserving shape orientation.\"\"\"\nfrom manim import *\n\n\nclass GridLayoutScene(Scene):\n    def construct(self):\n        shapes = VGroup(\n            Rectangle(width=1.4,height=.8,color=BLUE),\n            Circle(radius=.45,color=GREEN),\n            Square(side_length=.7,color=YELLOW),\n            Circle(radius=.35,color=RED),\n            Rectangle(width=1,height=.6,color=PURPLE),\n            Square(side_length=.9,color=WHITE),\n        ).arrange_in_grid(rows=2,cols=3,buff=(.5,.4)).rotate(PI/10).scale(.8)\n        shapes.save_state()\n        self.play(Create(shapes),run_time=2)\n        self.play(shapes.animate.arrange_in_grid(rows=3,cols=2,buff=(.6,.3),col_alignments='lr'),run_time=2)\n        self.play(shapes.animate.arrange_in_grid(rows=2,cols=3,buff=(.4,.6),flow_order='ur'),run_time=2)\n        self.play(Restore(shapes),run_time=1)\n        self.play(FadeOut(shapes),run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "transformedlayout",
    "label": "Arrange rotated and scaled groups",
    "path": "examples/transformed_layout_scene.py",
    "type": "manim",
    "cover": "gallery/previews/transformedlayout.png",
    "video": "gallery/previews/transformedlayout.mp4",
    "editorURL": "./?example=transformedlayout&url=examples%2Ftransformed_layout_scene.py",
    "title": "Arrange rotated and scaled groups",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Arrange transformed shapes in screen directions without changing orientation.\"\"\"\nfrom manim import *\n\n\nclass TransformedLayoutScene(Scene):\n    def construct(self):\n        shapes = VGroup(\n            Rectangle(width=1.5,height=.8,color=BLUE),\n            Circle(radius=.45,color=GREEN),\n            Square(side_length=.7,color=YELLOW),\n        ).arrange(RIGHT,buff=.5).rotate(PI/6).scale(.8)\n        shapes.save_state()\n        self.play(Create(shapes),run_time=2)\n        self.play(shapes.animate.arrange(DOWN,buff=.5,aligned_edge=LEFT),run_time=2)\n        self.play(shapes.animate.arrange(RIGHT,buff=.7),run_time=2)\n        self.play(Restore(shapes),run_time=1)\n        self.play(FadeOut(shapes),run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "groupmotion",
    "label": "Move children inside nested groups",
    "path": "examples/group_motion_scene.py",
    "type": "manim",
    "cover": "gallery/previews/groupmotion.png",
    "video": "gallery/previews/groupmotion.mp4",
    "editorURL": "./?example=groupmotion&url=examples%2Fgroup_motion_scene.py",
    "title": "Move children inside nested groups",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Moving, adding and removing children must not move their group siblings.\"\"\"\nfrom manim import *\n\n\nclass GroupMotionScene(Scene):\n    def construct(self):\n        x = ValueTracker(-3)\n        child = Dot(LEFT*3,color=YELLOW,radius=.2)\n        child.add_updater(lambda dot:dot.move_to((x.get_value(),.5,0)))\n        sibling = Circle(radius=.6,color=GREEN)\n        inner = VGroup(child,sibling).rotate(PI/6).scale(.8)\n        fixed = Square(side_length=1,color=BLUE).shift(RIGHT*3)\n        host = Group(inner,fixed).rotate(-PI/8).scale(.9)\n        anchor = Dot(sibling.get_center(),color=RED)\n        self.play(FadeIn(host),FadeIn(anchor),run_time=2)  # Community's Create needs VMobjects.\n        self.play(x.animate.set_value(3),run_time=3)\n        extra = Dot(LEFT*4,color=PURPLE,radius=.2)\n        host.add(extra)\n        self.wait(1)\n        host.remove(extra)\n        self.play(x.animate.set_value(-1),run_time=2)\n        self.play(FadeOut(host),FadeOut(anchor),run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "childmotion",
    "label": "Move children inside transformed shapes",
    "path": "examples/child_motion_scene.py",
    "type": "manim",
    "cover": "gallery/previews/childmotion.png",
    "video": "gallery/previews/childmotion.mp4",
    "editorURL": "./?example=childmotion&url=examples%2Fchild_motion_scene.py",
    "title": "Move children inside transformed shapes",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Moving a child updates family bounds without moving the transformed host.\"\"\"\nfrom manim import *\n\n\nclass ChildMotionScene(Scene):\n    def construct(self):\n        x = ValueTracker(-3)\n        child = Dot(LEFT*3,color=YELLOW,radius=.2)\n        child.add_updater(lambda dot:dot.move_to((x.get_value(),.5,0)))\n        sibling = Dot(ORIGIN,color=GREEN,radius=.2)\n        host = Rectangle(width=3,height=1.5,color=BLUE,fill_opacity=.2)\n        host.add(child,sibling).rotate(PI/6).scale(.8)\n        anchor = Dot(host.get_start(),color=RED)\n        self.play(Create(host),FadeIn(anchor),run_time=2)\n        self.play(x.animate.set_value(3),run_time=3)\n        self.play(x.animate.set_value(-1),run_time=2)\n        self.play(FadeOut(host),FadeOut(anchor),run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "familybounds",
    "label": "Frame shapes and distant children",
    "path": "examples/family_bounds_scene.py",
    "type": "manim",
    "cover": "gallery/previews/familybounds.png",
    "video": "gallery/previews/familybounds.mp4",
    "editorURL": "./?example=familybounds&url=examples%2Ffamily_bounds_scene.py",
    "title": "Frame shapes and distant children",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Family framing includes distant children while attachment preserves the host.\"\"\"\nfrom manim import *\n\n\nclass FamilyBoundsScene(MovingCameraScene):\n    def construct(self):\n        host = Rectangle(width=2,height=1,color=BLUE,fill_opacity=.15)\n        host.rotate(PI/6).scale(.7).shift(LEFT*.5)\n        host.add(Circle(radius=.6,color=GREEN).shift(RIGHT*4))\n        anchor = Dot(host.get_start(),color=RED)\n        bounds = always_redraw(lambda:Rectangle(width=host.get_width(),\n                 height=host.get_height(),color=YELLOW,stroke_opacity=.5)\n                 .move_to(host.get_center()))\n        self.play(Create(host),FadeIn(bounds),FadeIn(anchor),run_time=2)\n        self.play(self.camera.auto_zoom(host,margin=1),run_time=2)\n        far = Circle(radius=.5,color=PURPLE).shift(LEFT*4)\n        host.add(far)\n        self.wait(1)\n        self.play(self.camera.auto_zoom(host,margin=1),run_time=2)\n        host.remove(far)\n        self.wait(1)\n        self.play(FadeOut(host),FadeOut(bounds),FadeOut(anchor),run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "shapefamilies",
    "label": "Attach and restore children on shapes",
    "path": "examples/shape_family_scene.py",
    "type": "manim",
    "cover": "gallery/previews/shapefamilies.png",
    "video": "gallery/previews/shapefamilies.mp4",
    "editorURL": "./?example=shapefamilies&url=examples%2Fshape_family_scene.py",
    "title": "Attach and restore children on shapes",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Ordinary shapes retain their own path while hosting child geometry.\"\"\"\nfrom manim import *\n\n\nclass ShapeFamilyScene(Scene):\n    def construct(self):\n        host = Rectangle(width=4,height=2,color=BLUE,fill_opacity=.15)\n        left = Dot(LEFT,color=YELLOW,radius=.2)\n        right = Dot(RIGHT,color=GREEN,radius=.2)\n        host.add(left,right).save_state()\n        nested = Circle(radius=.45,color=RED).add(Dot(color=WHITE))\n        self.play(Create(host),run_time=2)\n        self.play(host.animate.rotate(PI/4).shift(LEFT),run_time=2)\n        host.add_to_back(nested)\n        self.wait(1)\n        host.remove(left)\n        self.wait(1)\n        self.play(Restore(host),run_time=2)\n        self.play(FadeOut(host),run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "anglepaths",
    "label": "Follow and restore an editable angle path",
    "path": "examples/angle_path_scene.py",
    "type": "manim",
    "cover": "gallery/previews/anglepaths.png",
    "video": "gallery/previews/anglepaths.mp4",
    "editorURL": "./?example=anglepaths&url=examples%2Fangle_path_scene.py",
    "title": "Follow and restore an editable angle path",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Angle owns an editable path; its dot remains a separate child.\"\"\"\nfrom manim import *\n\n\nclass AnglePathScene(Scene):\n    def construct(self):\n        first = Line(ORIGIN,RIGHT*3,color=BLUE)\n        second = Line(ORIGIN,UP*3,color=BLUE)\n        angle = Angle(first,second,radius=2,dot=True,dot_color=GREEN,\n                      color=YELLOW,stroke_width=5).save_state()\n        marker = Dot(angle.get_start(),color=WHITE)\n        self.add(VGroup(first,second))\n        self.play(FadeIn(marker),Create(angle),run_time=2)\n        self.play(MoveAlongPath(marker,angle),run_time=3)\n        self.play(Transform(angle,RightAngle(first,second,length=2,color=RED,\n                                            stroke_width=5)),run_time=2)\n        self.play(Restore(angle),run_time=1)\n        self.play(FadeOut(angle),FadeOut(marker),run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "arcpolygons",
    "label": "Morph polygons with curved edges",
    "path": "examples/arc_polygon_scene.py",
    "type": "manim",
    "cover": "gallery/previews/arcpolygons.png",
    "video": "gallery/previews/arcpolygons.mp4",
    "editorURL": "./?example=arcpolygons&url=examples%2Farc_polygon_scene.py",
    "title": "Morph polygons with curved edges",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"A filled curved triangle morphs while its defining edges keep their colors.\"\"\"\nfrom manim import *\n\n\nclass ArcPolygonScene(Scene):\n    def construct(self):\n        vertices = [(-2,-1,0),(2,-1,0),(0,2,0)]\n        edges = [{'angle':PI/3,'color':YELLOW},\n                 {'angle':PI/3,'color':GREEN},\n                 {'angle':PI/3,'color':RED}]\n        polygon = ArcPolygon(*vertices,arc_config=edges,color=BLUE,\n                             fill_opacity=.35,stroke_width=0)\n        target = ArcPolygon(*vertices,arc_config=[\n                 {'angle':-PI/4,'color':YELLOW},\n                 {'angle':0,'color':GREEN},\n                 {'angle':-PI/4,'color':RED}],color=PURPLE,\n                 fill_opacity=.5,stroke_width=0)\n        marker = Dot(polygon.get_start(),color=WHITE)\n        self.play(Create(polygon),FadeIn(marker),run_time=2)\n        self.play(MoveAlongPath(marker,polygon),run_time=3)\n        self.play(Transform(polygon,target),run_time=2)\n        self.play(FadeOut(polygon),FadeOut(marker),run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "endpointarcs",
    "label": "Bend arcs between moving endpoints",
    "path": "examples/endpoint_arc_scene.py",
    "type": "manim",
    "cover": "gallery/previews/endpointarcs.png",
    "video": "gallery/previews/endpointarcs.mp4",
    "editorURL": "./?example=endpointarcs&url=examples%2Fendpoint_arc_scene.py",
    "title": "Bend arcs between moving endpoints",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Endpoint arcs bend in opposite directions and follow moving endpoints.\"\"\"\nfrom manim import *\n\n\nclass EndpointArcScene(Scene):\n    def construct(self):\n        height = ValueTracker(0)\n        bend = ValueTracker(PI/2)\n        start = LEFT*2\n        def end():\n            return RIGHT*2+UP*height.get_value()\n        positive = always_redraw(lambda:ArcBetweenPoints(start,end(),angle=bend.get_value(),color=YELLOW))\n        negative = always_redraw(lambda:ArcBetweenPoints(start,end(),radius=-3,color=GREEN))\n        markers = always_redraw(lambda:VGroup(Dot(start,color=RED),Dot(end(),color=RED)))\n        chord = always_redraw(lambda:Line(start,end(),color=BLUE,stroke_opacity=.4))\n        self.add(chord,markers)\n        self.play(Create(positive),Create(negative),run_time=2)\n        self.play(height.animate.set_value(1.5),run_time=3)\n        self.play(bend.animate.set_value(0),run_time=2)\n        self.play(FadeOut(positive),FadeOut(negative),run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "angles",
    "label": "Mark angles between moving lines",
    "path": "examples/angle_scene.py",
    "type": "manim",
    "cover": "gallery/previews/angles.png",
    "video": "gallery/previews/angles.mp4",
    "editorURL": "./?example=angles&url=examples%2Fangle_scene.py",
    "title": "Mark angles between moving lines",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Signed angle marks follow a rotating line; corner marks stay independent.\"\"\"\nfrom manim import *\n\n\nclass AngleScene(Scene):\n    def construct(self):\n        vertex = LEFT*2\n        base = Line(vertex,vertex+RIGHT*2.5,color=BLUE)\n        moving = Line(vertex,vertex+RIGHT*2.5,color=BLUE).set_angle(PI/6)\n        mark = always_redraw(lambda:Angle(base,moving,radius=.7,color=YELLOW,\n                             dot=True,dot_color=GREEN))\n        label = always_redraw(lambda:DecimalNumber(\n                    Angle(base,moving).get_value(degrees=True),num_decimal_places=0,\n                    font_size=30,color=YELLOW).move_to((-2,2.2,0)))\n        horizontal = Line(RIGHT,RIGHT*3,color=BLUE)\n        vertical = Line(RIGHT,RIGHT+UP*2,color=BLUE)\n        corner = RightAngle(horizontal,vertical,length=.5,color=GREEN)\n        reverse = Angle(horizontal,vertical,radius=.9,other_angle=True,color=RED)\n        self.add(base,moving,horizontal,vertical)\n        self.play(FadeIn(mark),FadeIn(label),Create(corner),Create(reverse),run_time=2)\n        self.play(moving.animate.set_angle(PI*2/3),run_time=3)\n        self.play(moving.animate.set_angle(PI/2),run_time=2)\n        self.play(FadeOut(mark),FadeOut(label),FadeOut(corner),FadeOut(reverse),run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "tangents",
    "label": "Follow tangents along curved paths",
    "path": "examples/tangent_paths_scene.py",
    "type": "manim",
    "cover": "gallery/previews/tangents.png",
    "video": "gallery/previews/tangents.mp4",
    "editorURL": "./?example=tangents&url=examples%2Ftangent_paths_scene.py",
    "title": "Follow tangents along curved paths",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Finite path tangents track motion and grow without changing the source.\"\"\"\nfrom manim import *\n\n\nclass TangentPathsScene(Scene):\n    def construct(self):\n        ellipse = Ellipse(width=3,height=2,color=BLUE).shift(LEFT*2.3)\n        curve = CubicBezier((.3,-1.5,0),(1,3,0),(2,-3,0),(4,1.5,0),color=BLUE)\n        alpha = ValueTracker(.1)\n        extent = ValueTracker(1.8)\n        left = always_redraw(lambda:VGroup(\n               TangentLine(ellipse,alpha.get_value(),length=extent.get_value(),color=YELLOW,stroke_width=4),\n               Dot(ellipse.point_from_proportion(alpha.get_value()),color=YELLOW)))\n        right = always_redraw(lambda:VGroup(\n                TangentLine(curve,alpha.get_value(),length=extent.get_value(),color=GREEN,stroke_width=4),\n                Dot(curve.point_from_proportion(alpha.get_value()),color=GREEN)))\n        labels = VGroup(Text('Ellipse tangent',font_size=24).move_to((-2.3,2.5,0)),\n                        Text('Cubic tangent',font_size=24).move_to((2,2.5,0)))\n        self.add(labels)\n        self.play(Create(ellipse),Create(curve),FadeIn(left),FadeIn(right),run_time=2)\n        self.play(alpha.animate.set_value(.8),run_time=3)\n        self.play(extent.animate.set_value(3),run_time=2)\n        self.play(FadeOut(left),FadeOut(right),run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "dashedpaths",
    "label": "Dash curved paths and shift their phase",
    "path": "examples/dashed_paths_scene.py",
    "type": "manim",
    "cover": "gallery/previews/dashedpaths.png",
    "video": "gallery/previews/dashedpaths.mp4",
    "editorURL": "./?example=dashedpaths&url=examples%2Fdashed_paths_scene.py",
    "title": "Dash curved paths and shift their phase",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Wrap ring dashes and compare equal-length versus parameter spacing.\"\"\"\nfrom manim import *\n\n\nclass DashedPathsScene(Scene):\n    def construct(self):\n        loop = Circle(radius=1.4,color=GREEN).shift(LEFT*2.2)\n        curve = CubicBezier((.3,-1.6,0),(2.5,3,0),(1,-3.5,0),(4,1.6,0),color=BLUE)\n        references = VGroup(loop.copy().set_stroke(opacity=.2),\n                            curve.copy().shift(UP*.65).set_stroke(opacity=.2),\n                            curve.copy().shift(DOWN*.65).set_stroke(opacity=.2))\n        labels = VGroup(Text('Wrapped phase',font_size=24).move_to((-2.2,2.5,0)),\n                        Text('Even lengths',font_size=24).move_to((2.2,2.8,0)),\n                        Text('Curve parameter',font_size=24).move_to((2.2,-2.8,0)))\n        phase = ValueTracker(0)\n        ring = always_redraw(lambda:DashedVMobject(loop,num_dashes=12,\n                              dashed_ratio=.55,dash_offset=phase.get_value()))\n        even = DashedVMobject(curve.copy().set_color(YELLOW),num_dashes=8).shift(UP*.65)\n        legacy = DashedVMobject(curve,num_dashes=8,equal_lengths=False).shift(DOWN*.65)\n        self.add(references,labels)\n        self.play(Create(ring),Create(even),Create(legacy),run_time=2)\n        self.play(phase.animate.set_value(1.25),run_time=3)\n        denser = DashedVMobject(curve.copy().set_color(RED),num_dashes=16,dashed_ratio=.8).shift(UP*.65)\n        self.play(Transform(even,denser),run_time=2)\n        self.play(FadeOut(ring),FadeOut(even),FadeOut(legacy),run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "guides",
    "label": "Follow dashed coordinate guides",
    "path": "examples/guides_scene.py",
    "type": "manim",
    "cover": "gallery/previews/guides.png",
    "video": "gallery/previews/guides.mp4",
    "editorURL": "./?example=guides&url=examples%2Fguides_scene.py",
    "title": "Follow dashed coordinate guides",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Dashed coordinate projections follow a graph and a rotating frame.\"\"\"\nfrom manim import *\n\n\nclass GuidesScene(Scene):\n    def construct(self):\n        axes = NumberPlane([-2,3],[-1,3],x_length=8,y_length=4,\n                           background_line_style=dict(stroke_opacity=.25)).add_coordinates()\n        curve = axes.plot(lambda x:.4*x*x+.2,x_range=[-2,3,.15],color=BLUE)\n        value = ValueTracker(-1.5)\n        marker = always_redraw(lambda:Dot(axes.i2gp(value.get_value(),curve),color=YELLOW))\n        guides = always_redraw(lambda:axes.get_lines_to_point(axes.i2gp(value.get_value(),curve),color=GREEN,\n                               line_config=dict(dash_length=.15,dashed_ratio=.6)))\n        # Redraw callbacks read the axes, so they join once the axes are drawn (as in Community).\n        self.play(Create(axes),Create(curve),run_time=1)\n        self.play(FadeIn(guides),FadeIn(marker),run_time=1)\n        self.play(value.animate.set_value(2),run_time=3)\n        self.play(axes.animate.rotate(PI/6),curve.animate.rotate(PI/6,about_point=axes.get_center()),run_time=2)\n        self.play(FadeOut(guides),FadeOut(marker),run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "area",
    "label": "Fill changing graph regions",
    "path": "examples/area_scene.py",
    "type": "manim",
    "cover": "gallery/previews/area.png",
    "video": "gallery/previews/area.mp4",
    "editorURL": "./?example=area&url=examples%2Farea_scene.py",
    "title": "Fill changing graph regions",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Expand a gradient area, then fill the region between two functions.\"\"\"\nfrom manim import *\n\n\nclass AreaScene(Scene):\n    def construct(self):\n        axes = Axes([-2,3],[-1,3],x_length=8,y_length=4).add_coordinates()\n        curve = axes.plot(lambda x:.5*x*x-.4,x_range=[-2,3,.12],color=BLUE)\n        lower = axes.plot(lambda x:-.3*x-.4,x_range=[-1.5,2,.12],color=YELLOW)\n        end = ValueTracker(-.5)\n        area = always_redraw(lambda:axes.get_area(curve,[-1.5,end.get_value()],\n                              color=[BLUE,GREEN],opacity=.5,stroke_width=0).set_z_index(-1))\n        self.play(Create(axes),Create(curve),FadeIn(area),run_time=2)\n        self.play(end.animate.set_value(2),run_time=3)\n        area.clear_updaters()\n        between = axes.get_area(curve,[-1.5,2],bounded_graph=lower,\n                                color=[RED,YELLOW],opacity=.5,stroke_width=0).set_z_index(-1)\n        self.play(Create(lower),Transform(area,between),run_time=2)\n        self.play(FadeOut(area),FadeOut(lower),run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "secant",
    "label": "Follow a labeled secant",
    "path": "examples/secant_scene.py",
    "type": "manim",
    "cover": "gallery/previews/secant.png",
    "video": "gallery/previews/secant.mp4",
    "editorURL": "./?example=secant&url=examples%2Fsecant_scene.py",
    "title": "Follow a labeled secant",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"A labeled secant triangle follows a changing interval and graph input.\"\"\"\nfrom manim import *\n\n\nclass SecantScene(Scene):\n    def construct(self):\n        axes = NumberPlane([-2,3],[-2,3],x_length=8,y_length=4,\n                           background_line_style=dict(stroke_opacity=.3)).add_coordinates()\n        graph = axes.plot(lambda x:.5*x*x-.7,x_range=[-2,3,.15],color=BLUE)\n        start = ValueTracker(0)\n        interval = ValueTracker(1.5)\n        secant = always_redraw(lambda: axes.get_secant_slope_group(start.get_value(),graph,\n                              dx=interval.get_value(),dx_label='dx',dy_label='df',\n                              dy_line_color=RED,secant_line_length=6))\n        # The secant reads the axes, so it joins once they are drawn (as in Community).\n        self.play(Create(axes),Create(graph),run_time=1)\n        self.play(FadeIn(secant),run_time=1)\n        self.play(interval.animate.set_value(.25),run_time=3)\n        self.play(start.animate.set_value(1),run_time=2)\n        self.play(FadeOut(secant),run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "riemann",
    "label": "Refine signed area estimates",
    "path": "examples/riemann_scene.py",
    "type": "manim",
    "cover": "gallery/previews/riemann.png",
    "video": "gallery/previews/riemann.mp4",
    "editorURL": "./?example=riemann&url=examples%2Friemann_scene.py",
    "title": "Refine signed area estimates",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Refine signed area estimates, then compare the region between two functions.\"\"\"\nfrom manim import *\n\n\nclass RiemannScene(Scene):\n    def construct(self):\n        axes = NumberPlane([-2,2],[-2,2],x_length=8,y_length=4,\n                           background_line_style=dict(stroke_opacity=.3)).add_coordinates()\n        graph = axes.plot(lambda x:.5*x*x-.7,x_range=[-2,2,.1],color=WHITE)\n        rectangles = axes.get_riemann_rectangles(graph,dx=.5,input_sample_type='center',\n                                                fill_opacity=.65,color=[BLUE,GREEN])\n        fine = axes.get_riemann_rectangles(graph,dx=.125,input_sample_type='center',\n                                          fill_opacity=.65,color=[BLUE,GREEN])\n        bound = axes.plot(lambda x:.3*x-.4,x_range=[-2,2,.1],color=YELLOW)\n        between = axes.get_riemann_rectangles(graph,bounded_graph=bound,dx=.25,\n                                             input_sample_type='center',fill_opacity=.65,\n                                             color=[BLUE,GREEN])\n        self.play(Create(axes),Create(graph),FadeIn(rectangles),run_time=2)\n        self.play(Transform(rectangles,fine),run_time=2)\n        self.play(Create(bound),Transform(rectangles,between),run_time=2)\n        self.play(FadeOut(rectangles),FadeOut(bound),run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "calculus",
    "label": "Follow a tangent and derivative",
    "path": "examples/calculus_scene.py",
    "type": "manim",
    "cover": "gallery/previews/calculus.png",
    "video": "gallery/previews/calculus.mp4",
    "editorURL": "./?example=calculus&url=examples%2Fcalculus_scene.py",
    "title": "Follow a tangent and derivative",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"A function, its numerical derivative and a tangent tracking a changing input.\"\"\"\nfrom manim import *\nfrom math import sin\n\n\nclass CalculusScene(Scene):\n    def construct(self):\n        axes = NumberPlane([-3,3],[-2,2],x_length=8,y_length=4,\n                           background_line_style=dict(stroke_opacity=.3)).add_coordinates()\n        graph = axes.plot(sin,x_range=[-3,3,.15],color=BLUE)\n        derivative = axes.plot_derivative_graph(graph,x_range=[-3,3,.15],color=GREEN)\n        recovered = axes.plot_antiderivative_graph(derivative,samples=30,x_range=[-3,3,.15],\n                                                  color=RED,stroke_width=1)\n        value = ValueTracker(-2)\n        point = Dot(axes.i2gp(-2,graph),color=YELLOW)\n        point.add_updater(lambda mob: mob.move_to(axes.i2gp(value.get_value(),graph)))\n        def tangent():\n            x = value.get_value()\n            y = axes.i2gc(x,graph)[1]\n            slope = axes.slope_of_tangent(x,graph)\n            return Line(axes.c2p(x-.6,y-.6*slope),axes.c2p(x+.6,y+.6*slope),color=YELLOW)\n        line = always_redraw(tangent)\n        readout = DecimalNumber(axes.slope_of_tangent(-2,graph),num_decimal_places=2,color=GREEN).shift(UP*2.5)\n        readout.add_updater(lambda mob: mob.set_value(axes.slope_of_tangent(value.get_value(),graph)))\n        self.play(Create(axes),Create(graph),Create(derivative),Create(recovered),run_time=2)\n        self.play(FadeIn(point),FadeIn(line),FadeIn(readout),run_time=1)\n        self.play(value.animate.set_value(2),run_time=4,rate_func=linear)\n        self.play(FadeOut(point),FadeOut(line),FadeOut(readout),run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "complex",
    "label": "Animate complex coordinates",
    "path": "examples/complex_scene.py",
    "type": "manim",
    "cover": "gallery/previews/complex.png",
    "video": "gallery/previews/complex.mp4",
    "editorURL": "./?example=complex&url=examples%2Fcomplex_scene.py",
    "title": "Animate complex coordinates",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"A complex value and its conjugate follow a rotating, labeled complex plane.\"\"\"\nfrom manim import *\nfrom cmath import exp\n\n\nclass ComplexScene(Scene):\n    def construct(self):\n        plane = ComplexPlane(x_range=[-3,3],y_range=[-2,2],x_length=8,y_length=4,\n                             background_line_style=dict(stroke_opacity=.4)).add_coordinates()\n        plane.save_state()\n        angle = ValueTracker(0)\n        value = lambda: 2*exp(1j*angle.get_value())\n        marker = Dot(plane.n2p(value()),color=YELLOW)\n        marker.add_updater(lambda mob: mob.move_to(plane.n2p(value())))\n        conjugate = Dot(plane.n2p(value().conjugate()),color=GREEN)\n        conjugate.add_updater(lambda mob: mob.move_to(plane.n2p(value().conjugate())))\n        vector = always_redraw(lambda: plane.get_vector([value().real,value().imag],color=YELLOW))\n        self.play(Create(plane),FadeIn(marker),FadeIn(conjugate),FadeIn(vector),run_time=2)\n        self.play(angle.animate.set_value(PI/2),run_time=3,rate_func=linear)\n        self.play(plane.animate.rotate(PI/6).scale(.8),run_time=2)\n        self.play(Restore(plane),run_time=2)\n        self.play(FadeOut(vector),run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "plane",
    "label": "Move a Cartesian grid",
    "path": "examples/plane_scene.py",
    "type": "manim",
    "cover": "gallery/previews/plane.png",
    "video": "gallery/previews/plane.mp4",
    "editorURL": "./?example=plane&url=examples%2Fplane_scene.py",
    "title": "Move a Cartesian grid",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Cartesian grids, plotted functions and moving vectors on a transformed plane.\"\"\"\nfrom manim import *\n\n\nclass PlaneScene(Scene):\n    def construct(self):\n        plane = NumberPlane([-3,3],[-2,2],x_length=8,y_length=4,faded_line_ratio=2,\n                            background_line_style=dict(stroke_width=2,stroke_opacity=.5)).add_coordinates()\n        plane.save_state()\n        value = ValueTracker(-2)\n        function = lambda x: .3*x*x-1\n        graph = always_redraw(lambda: plane.plot(function,x_range=[-3,3,.15],color=RED))\n        marker = Dot(plane.i2gp(value.get_value(),graph),color=YELLOW)\n        marker.add_updater(lambda mob: mob.move_to(plane.i2gp(value.get_value(),graph)))\n        vector = always_redraw(lambda: plane.get_vector([value.get_value(),function(value.get_value())],\n                                                       color=YELLOW))\n        self.play(Create(plane),Create(graph),FadeIn(marker),FadeIn(vector),run_time=2)\n        self.play(value.animate.set_value(2),run_time=3,rate_func=linear)\n        self.play(plane.animate.rotate(PI/6).scale(.8).shift(UP*.3),run_time=2)\n        self.play(Restore(plane),run_time=2)\n        self.play(FadeOut(marker),FadeOut(vector),run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "plot",
    "label": "Plot smooth functions",
    "path": "examples/plot_scene.py",
    "type": "manim",
    "cover": "gallery/previews/plot.png",
    "video": "gallery/previews/plot.mp4",
    "editorURL": "./?example=plot&url=examples%2Fplot_scene.py",
    "title": "Plot smooth functions",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Smooth function plots, exact graph-input queries and a closed parametric curve.\"\"\"\nfrom manim import *\nfrom math import cos, sin\n\n\nclass PlotScene(Scene):\n    def construct(self):\n        axes = Axes([-3,3],[-2,3],x_length=8,y_length=4,\n                    axis_config=dict(font_size=22,line_to_number_buff=.4)).add_coordinates()\n        coefficient = ValueTracker(1/3)\n        function = lambda x: coefficient.get_value()*x*x-1\n        graph = always_redraw(lambda: axes.plot(function,x_range=[-3,3,.15],color=BLUE))\n        value = ValueTracker(-2)\n        marker = Dot(axes.i2gp(value.get_value(),graph),color=YELLOW)\n        marker.add_updater(lambda mob: mob.move_to(axes.i2gp(value.get_value(),graph)))\n        loop = axes.plot_parametric_curve(lambda t: (2*cos(t),.6+.6*sin(t)),\n                                          t_range=[0,TAU,.2],color=RED)\n        self.play(Create(axes),Create(graph),FadeIn(marker),run_time=2)\n        self.play(value.animate.set_value(2),run_time=3,rate_func=linear)\n        self.play(coefficient.animate.set_value(.15),run_time=2,rate_func=linear)\n        self.play(ShowPassingFlash(graph.copy().set_stroke(color=YELLOW,width=7),time_width=.3),\n                  Create(loop),run_time=2)\n        self.play(FadeOut(marker),FadeOut(loop),run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "rounded",
    "label": "Rounded and concave corners",
    "path": "examples/rounded_rectangle_scene.py",
    "type": "manim",
    "cover": "gallery/previews/rounded.png",
    "video": "gallery/previews/rounded.mp4",
    "editorURL": "./?example=rounded&url=examples%2Frounded_rectangle_scene.py",
    "title": "Rounded and concave corners",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Follow rounded corners, morph concave cuts, and restore the original outline.\"\"\"\nfrom manim import *\n\n\nclass RoundedRectangleScene(Scene):\n    def construct(self):\n        box = RoundedRectangle(width=5, height=3, corner_radius=.6,\n                               color=BLUE, fill_opacity=.25).save_state()\n        self.play(Create(box), run_time=2)\n        dot = Dot(color=YELLOW).move_to(box.get_start())\n        self.add(dot)\n        self.play(MoveAlongPath(dot, box), run_time=4, rate_func=linear)\n        target = RoundedRectangle(width=5, height=3,\n                                  corner_radius=[-.8, .2, -.8, .2],\n                                  color=GREEN, fill_opacity=.4)\n        self.play(FadeOut(dot), Transform(box, target), run_time=2)\n        self.play(Restore(box), run_time=2)\n        self.wait(1)\n"
    }
  },
  {
    "id": "sectors",
    "label": "Circular and ring sectors",
    "path": "examples/sector_scene.py",
    "type": "manim",
    "cover": "gallery/previews/sectors.png",
    "video": "gallery/previews/sectors.mp4",
    "editorURL": "./?example=sectors&url=examples%2Fsector_scene.py",
    "title": "Circular and ring sectors",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Create and morph connected circular and annular sector outlines.\"\"\"\nfrom manim import *\n\n\nclass SectorScene(Scene):\n    def construct(self):\n        wedge = Sector(radius=1.5, angle=PI/2, color=BLUE,\n                       stroke_width=2).move_to(LEFT * 2)\n        ring = AnnularSector(inner_radius=.7, outer_radius=1.5,\n                             angle=-3*PI/2, color=YELLOW,\n                             stroke_width=2).move_to(RIGHT * 2)\n        ring.save_state()\n        self.play(Create(wedge), Create(ring), run_time=2)\n        dot = Dot(color=WHITE).move_to(wedge.get_start())\n        self.add(dot)\n        self.play(MoveAlongPath(dot, wedge), run_time=3, rate_func=linear)\n        self.play(FadeOut(dot), Transform(ring, Sector(radius=1.5, angle=PI,\n                  color=GREEN).move_to(RIGHT * 2)), run_time=2)\n        self.play(Restore(ring), wedge.animate.rotate(PI/2), run_time=2)\n        self.wait(1)\n"
    }
  },
  {
    "id": "ellipse",
    "label": "Follow an ellipse",
    "path": "examples/ellipse_scene.py",
    "type": "manim",
    "cover": "gallery/previews/ellipse.png",
    "video": "gallery/previews/ellipse.mp4",
    "editorURL": "./?example=ellipse&url=examples%2Fellipse_scene.py",
    "title": "Follow an ellipse",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Trace a rotated ellipse, follow its outline and morph to a circle.\"\"\"\nfrom manim import *\n\n\nclass EllipseScene(Scene):\n    def construct(self):\n        ellipse = Ellipse(width=4, height=2, color=BLUE).rotate(PI / 6)\n        ellipse.save_state()\n        dot = Dot(color=YELLOW).move_to(ellipse.point_from_proportion(0))\n        self.play(Create(ellipse), run_time=1)\n        self.add(dot)\n        self.play(MoveAlongPath(dot, ellipse), run_time=4, rate_func=linear)\n        self.play(FadeOut(dot), Transform(ellipse, Circle(radius=1.5, color=GREEN)), run_time=2)\n        self.play(Restore(ellipse), run_time=2)\n        self.wait(1)\n"
    }
  },
  {
    "id": "trace",
    "label": "Trace moving points",
    "path": "examples/trace_scene.py",
    "type": "manim",
    "cover": "gallery/previews/trace.png",
    "video": "gallery/previews/trace.mp4",
    "editorURL": "./?example=trace&url=examples%2Ftrace_scene.py",
    "title": "Trace moving points",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Compare a complete point trail with a short dissipating trail.\"\"\"\nfrom manim import *\n\n\nclass TraceScene(Scene):\n    def construct(self):\n        full_dot = Dot(LEFT * 3 + RIGHT, color=BLUE)\n        tail_dot = Dot(RIGHT * 3 + RIGHT, color=YELLOW)\n        full = TracedPath(full_dot.get_center, stroke_color=BLUE, stroke_width=4)\n        tail = TracedPath(tail_dot.get_center, dissipating_time=1,\n                          stroke_color=YELLOW, stroke_width=4)\n        self.add(full_dot, tail_dot, full, tail)\n        self.play(Rotate(full_dot, TAU, about_point=LEFT * 3),\n                  Rotate(tail_dot, TAU, about_point=RIGHT * 3),\n                  run_time=4, rate_func=linear)\n        full.clear_updaters()\n        self.wait(2)\n        self.play(FadeOut(full_dot), FadeOut(tail_dot), FadeOut(full), FadeOut(tail))\n"
    }
  },
  {
    "id": "numbers",
    "label": "Show changing numbers",
    "path": "examples/numeric_scene.py",
    "type": "manim",
    "cover": "gallery/previews/numbers.png",
    "video": "gallery/previews/numbers.mp4",
    "editorURL": "./?example=numbers&url=examples%2Fnumeric_scene.py",
    "title": "Show changing numbers",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Display sampled tracker values; animating set_value morphs the glyphs, as in Manim.\"\"\"\nfrom manim import *\n\n\nclass NumericScene(Scene):\n    def construct(self):\n        value = ValueTracker(-2)\n        dot = Dot(color=BLUE)\n        dot.add_updater(lambda m: m.move_to(RIGHT * value.get_value()))\n        decimal = DecimalNumber(-2, include_sign=True, font_size=36, color=BLUE)\n        decimal.add_updater(lambda m: m.set_value(value.get_value()).move_to(dot.get_center() + UP))\n        integer = Integer(-2, font_size=36, color=YELLOW)\n        integer.add_updater(lambda m: m.set_value(value.get_value()).move_to(dot.get_center() + DOWN))\n        total = DecimalNumber(1000, num_decimal_places=0, unit=' points', font_size=32, color=GREEN)\n        total.shift(DOWN * 2.5).save_state()\n        self.add(value, dot, decimal, integer, total)\n        self.play(value.animate.set_value(2), run_time=4, rate_func=linear)\n        self.play(total.animate.set_value(2500), run_time=2, rate_func=linear)\n        self.play(Restore(total), run_time=2, rate_func=linear)\n        self.wait(1)\n"
    }
  },
  {
    "id": "redraw",
    "label": "Rebuild shapes each frame",
    "path": "examples/redraw_scene.py",
    "type": "manim",
    "cover": "gallery/previews/redraw.png",
    "video": "gallery/previews/redraw.mp4",
    "editorURL": "./?example=redraw&url=examples%2Fredraw_scene.py",
    "title": "Rebuild shapes each frame",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Regenerate a circle and shape family from an animated parameter.\"\"\"\nfrom manim import *\n\n\nclass RedrawScene(Scene):\n    def construct(self):\n        size = ValueTracker(.5)\n        circle = always_redraw(lambda: Circle(radius=size.get_value(), color=BLUE, fill_opacity=.2).shift(LEFT*2))\n        family = always_redraw(lambda: VGroup(\n            Square(side_length=size.get_value(), color=YELLOW).shift(RIGHT*2),\n            Triangle(color=RED).scale(size.get_value()).shift(RIGHT*2+UP*2)\n        ))\n        self.add(size, circle, family)\n        self.play(size.animate.set_value(1.5), run_time=3, rate_func=linear)\n        circle.suspend_updating()\n        self.play(size.animate.set_value(.5), run_time=2, rate_func=linear)\n        circle.resume_updating()\n        family.clear_updaters()\n        self.play(size.animate.set_value(1), run_time=2, rate_func=linear)\n        self.wait(1)\n"
    }
  },
  {
    "id": "tracker",
    "label": "Animate a shared value",
    "path": "examples/value_tracker_scene.py",
    "type": "manim",
    "cover": "gallery/previews/tracker.png",
    "video": "gallery/previews/tracker.mp4",
    "editorURL": "./?example=tracker&url=examples%2Fvalue_tracker_scene.py",
    "title": "Animate a shared value",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Drive two objects and their connector from one animated real parameter.\"\"\"\nfrom manim import *\n\n\nclass TrackedValueScene(Scene):\n    def construct(self):\n        value = ValueTracker(-2)\n        dot = Dot(color=BLUE)\n        square = Square(side_length=.6, color=YELLOW)\n        connector = Line(color=GREEN)\n        dot.add_updater(lambda m: m.move_to(RIGHT * value.get_value() + DOWN))\n        square.add_updater(lambda m: m.move_to(LEFT * value.get_value() + UP))\n        connector.add_updater(lambda m: m.put_start_and_end_on(dot.get_center(), square.get_center()))\n        self.add(value, dot, square, connector)\n        self.play(value.animate.set_value(2), run_time=4, rate_func=linear)\n        self.play(value.animate.increment_value(-1))\n        self.play(value.animate.increment_value(-1))\n        self.wait(1)\n"
    }
  },
  {
    "id": "updaters",
    "label": "Follow objects each frame",
    "path": "examples/updater_scene.py",
    "type": "manim",
    "cover": "gallery/previews/updaters.png",
    "video": "gallery/previews/updaters.mp4",
    "editorURL": "./?example=updaters&url=examples%2Fupdater_scene.py",
    "title": "Follow objects each frame",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"A timed spinner and a follower/camera that track an animated dot.\"\"\"\nfrom manim import *\n\n\nclass UpdaterScene(MovingCameraScene):\n    def construct(self):\n        dot = Dot(color=BLUE).shift(LEFT * 2)\n        follower = Square(side_length=.5, color=YELLOW)\n        follower.add_updater(lambda m: m.move_to(dot.get_center() + UP), call_updater=True)\n        spinner = Square(color=RED).shift(DOWN * 2)\n        spinner.add_updater(lambda m, dt: m.rotate(dt * PI / 2))\n        self.camera.frame.add_updater(lambda m: m.move_to(dot), call_updater=True)\n        self.add(dot, follower, spinner, self.camera.frame)\n        self.wait(1)\n        self.play(dot.animate.shift(RIGHT * 4), run_time=4, rate_func=linear)\n        spinner.clear_updaters()\n        self.camera.frame.clear_updaters()\n        self.wait(1)\n"
    }
  },
  {
    "id": "autozoom",
    "label": "Fit shapes in the view",
    "path": "examples/auto_zoom_scene.py",
    "type": "manim",
    "cover": "gallery/previews/autozoom.png",
    "video": "gallery/previews/autozoom.mp4",
    "editorURL": "./?example=autozoom&url=examples%2Fauto_zoom_scene.py",
    "title": "Fit shapes in the view",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Fit several shapes, focus on one, and restore the saved camera view.\"\"\"\nfrom manim import *\n\n\nclass AutoZoomScene(MovingCameraScene):\n    def construct(self):\n        frame = self.camera.frame.save_state()\n        circle = Circle(color=BLUE, fill_opacity=.2).shift(LEFT * 2)\n        square = Square(color=RED, fill_opacity=.2).shift(RIGHT * 2)\n        self.play(Create(circle), Create(square), run_time=2)\n        self.play(self.camera.auto_zoom([circle, square], margin=2), run_time=2)\n        self.wait(1)\n        self.play(self.camera.auto_zoom(circle, margin=1), run_time=2)\n        self.play(Restore(frame), run_time=2)\n"
    }
  },
  {
    "id": "movingcamera",
    "label": "Pan and zoom the view",
    "path": "examples/moving_camera_scene.py",
    "type": "manim",
    "cover": "gallery/previews/movingcamera.png",
    "video": "gallery/previews/movingcamera.mp4",
    "editorURL": "./?example=movingcamera&url=examples%2Fmoving_camera_scene.py",
    "title": "Pan and zoom the view",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Pan and zoom into a shape, follow a new focus, then restore the full view.\"\"\"\nfrom manim import *\n\n\nclass MovingViewScene(MovingCameraScene):\n    def construct(self):\n        frame = self.camera.frame.save_state()\n        circle = Circle(color=BLUE, fill_opacity=.2).shift(LEFT * 2)\n        square = Square(color=RED, fill_opacity=.2).shift(RIGHT * 2)\n        title = Text(\"Pan, zoom, and restore\", font_size=30).shift(UP * 2.7)\n        self.play(Create(circle), Create(square), FadeIn(title), run_time=2)\n        self.play(frame.animate.move_to(square).scale(.5), run_time=2)\n        self.wait(1)\n        self.play(frame.animate.move_to(circle), run_time=1)\n        self.play(Restore(frame), run_time=2)\n        self.wait(1)\n"
    }
  },
  {
    "id": "camera",
    "label": "Configure the canvas",
    "path": "examples/camera_scene.py",
    "type": "manim",
    "cover": "gallery/previews/camera.png",
    "video": "gallery/previews/camera.mp4",
    "editorURL": "./?example=camera&url=examples%2Fcamera_scene.py",
    "title": "Configure the canvas",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Use a square canvas and preserve changing backgrounds in exported frames.\"\"\"\nfrom manim import *\n\nconfig.pixel_width = 600\nconfig.pixel_height = 600\nconfig.frame_width = 8\nconfig.background_color = WHITE\n\n\nclass CameraScene(Scene):\n    def construct(self):\n        title = Text(\"A square canvas\", color=BLACK, font_size=30).shift(UP * 2.7)\n        shapes = VGroup(Circle(color=BLUE, fill_opacity=.25),\n                        Square(color=RED, fill_opacity=.15)).arrange(RIGHT, buff=.6).scale(.7)\n        self.play(FadeIn(title), Create(shapes), run_time=2)\n        self.camera.background_color = \"#E8EEF7\"\n        self.play(shapes.animate.rotate(PI / 2), run_time=2)\n        self.wait(1)\n"
    }
  },
  {
    "id": "family",
    "label": "Build and edit a group",
    "path": "examples/group_family_scene.py",
    "type": "manim",
    "cover": "gallery/previews/family.png",
    "video": "gallery/previews/family.mp4",
    "editorURL": "./?example=family&url=examples%2Fgroup_family_scene.py",
    "title": "Build and edit a group",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Select, reorder, and edit children while keeping a scene-added group intact.\"\"\"\nfrom manim import *\n\n\nclass GroupFamilyScene(Scene):\n    def construct(self):\n        title = Text(\"Build and edit a group\", font_size=30).shift(UP * 2.5)\n        row = VGroup(Circle(radius=.6, color=BLUE),\n                     Square(side_length=1.2, color=RED),\n                     Triangle(color=GREEN).scale(2)).arrange(RIGHT, buff=.7)\n        self.add(title, row)\n        self.wait(1)\n        row[::2].set_color(YELLOW)\n        self.wait(1)\n        middle = row[1]\n        row.remove(middle)\n        self.wait(1)\n        row.add_to_back(middle)\n        self.play(row.animate.rotate(PI / 2), run_time=2)\n        self.play(FadeOut(row), run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "groupmorph",
    "label": "Morph nested groups",
    "path": "examples/group_morph_scene.py",
    "type": "manim",
    "cover": "gallery/previews/groupmorph.png",
    "video": "gallery/previews/groupmorph.mp4",
    "editorURL": "./?example=groupmorph&url=examples%2Fgroup_morph_scene.py",
    "title": "Morph nested groups",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Morph unequal nested families, restore the checkpoint, and erase the group.\"\"\"\nfrom manim import *\n\n\nclass GroupMorphScene(Scene):\n    def construct(self):\n        title = Text(\"Morph nested groups\", font_size=30).shift(UP * 2.5)\n        shapes = VGroup(\n            Circle(radius=.65, color=BLUE, fill_opacity=.2).shift(LEFT * 1.5),\n            VGroup(Square(side_length=1.1, color=YELLOW).shift(RIGHT * 1.5))\n        ).rotate(PI / 12).save_state()\n        target = VGroup(\n            Square(side_length=1.2, color=RED).shift(LEFT * 2),\n            Triangle(color=GREEN).scale(2),\n            VGroup(Circle(radius=.65, color=PURPLE).shift(RIGHT * 2),\n                   Line((1.4,-1,0), (2.6,-1,0), color=ORANGE))\n        ).rotate(-PI / 12)\n        self.play(FadeIn(title), Create(shapes), run_time=2)\n        self.play(Transform(shapes, target), run_time=2)\n        self.wait(1)\n        self.play(Restore(shapes), run_time=3)\n        self.wait(1)\n        self.play(Uncreate(shapes), run_time=1)\n        self.wait(1)\n"
    }
  },
  {
    "id": "shapemorph",
    "label": "Morph built-in shapes",
    "path": "examples/shape_morph_scene.py",
    "type": "manim",
    "cover": "gallery/previews/shapemorph.png",
    "video": "gallery/previews/shapemorph.mp4",
    "editorURL": "./?example=shapemorph&url=examples%2Fshape_morph_scene.py",
    "title": "Morph built-in shapes",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Morph primitive outlines, restore a circle, and finish as a cubic curve.\"\"\"\nfrom manim import *\n\n\nclass ShapeMorphScene(Scene):\n    def construct(self):\n        shape = Circle(color=BLUE, fill_opacity=0.15).scale(1.2).save_state()\n        title = Text(\"Morph built-in shapes\", font_size=30).shift(UP * 2.5)\n        self.play(Create(shape), FadeIn(title), run_time=2)\n        self.play(Transform(shape, Square(color=RED, fill_opacity=0.2)), run_time=2)\n        self.play(Transform(shape, Triangle(color=GREEN, fill_opacity=0.3).scale(3)), run_time=2)\n        self.play(Restore(shape), run_time=2)\n        curve = CubicBezier((-3,-1,0), (-1,3,0), (1,-3,0), (3,1,0), color=PURPLE)\n        self.play(Transform(shape, curve), run_time=2)\n        self.wait(1)\n"
    }
  },
  {
    "id": "morph",
    "label": "Morph aligned paths",
    "path": "examples/morph_scene.py",
    "type": "manim",
    "cover": "gallery/previews/morph.png",
    "video": "gallery/previews/morph.mp4",
    "editorURL": "./?example=morph&url=examples%2Fmorph_scene.py",
    "title": "Morph aligned paths",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Morph unequal path counts, restore a curve, and close an outline.\"\"\"\nfrom manim import *\n\n\nclass MorphScene(Scene):\n    def construct(self):\n        path = CubicBezier((-3,0,0), (-1,3,0), (1,-3,0), (3,0,0), color=BLUE)\n        path.scale(0.8).rotate(PI / 12).save_state()\n        corners = VMobject(color=GREEN).set_points_as_corners([(-3,-1,0), (-1,1,0), (1,-1,0), (3,1,0)])\n        title = Text(\"Morph aligned paths\", font_size=30).shift(UP * 2.5)\n        self.play(Create(path), FadeIn(title), run_time=2)\n        self.play(Transform(path, corners), run_time=2, rate_func=linear)\n        self.play(Restore(path), run_time=2, rate_func=linear)\n        polygon = Polygon((-3,-1,0), (-1,1,0), (1,1,0), (3,-1,0), color=PURPLE, fill_opacity=0.2)\n        self.play(Transform(path, polygon), run_time=3, rate_func=linear)\n        self.wait(1)\n"
    }
  },
  {
    "id": "bezier",
    "label": "Cubic Bezier paths",
    "path": "examples/bezier_scene.py",
    "type": "manim",
    "cover": "gallery/previews/bezier.png",
    "video": "gallery/previews/bezier.mp4",
    "editorURL": "./?example=bezier&url=examples%2Fbezier_scene.py",
    "title": "Cubic Bezier paths",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Trace a cubic curve, follow it, deform it, and draw a mixed path.\"\"\"\nfrom manim import *\n\n\nclass BezierScene(Scene):\n    def construct(self):\n        curve = CubicBezier((-3,-1,0), (-2,3,0), (2,-3,0), (3,1,0), color=BLUE)\n        curve.scale(0.8).rotate(PI / 12).save_state()\n        marker = Dot(curve.get_start(), color=YELLOW)\n        title = Text(\"Cubic Bezier paths\", font_size=30).shift(UP * 2.5)\n        self.play(Create(curve), FadeIn(marker), FadeIn(title), run_time=2)\n        self.play(MoveAlongPath(marker, curve), run_time=3, rate_func=linear)\n        target = CubicBezier((-3,0,0), (-1,3,0), (1,3,0), (3,0,0), color=GREEN)\n        self.play(Transform(curve, target), run_time=2)\n        self.play(Restore(curve), FadeOut(marker))\n        mixed = VMobject(color=PURPLE).set_points_as_corners([(-3,-1,0), (-1,-1,0)])\n        mixed.add_cubic_bezier_curve_to(LEFT+UP*2, RIGHT+UP*2, RIGHT+DOWN).add_line_to(RIGHT*3+DOWN)\n        self.play(Uncreate(curve), Create(mixed), run_time=2)\n        self.wait(1)\n"
    }
  },
  {
    "id": "corners",
    "label": "Connected corner paths",
    "path": "examples/corner_path_scene.py",
    "type": "manim",
    "cover": "gallery/previews/corners.png",
    "video": "gallery/previews/corners.mp4",
    "editorURL": "./?example=corners&url=examples%2Fcorner_path_scene.py",
    "title": "Connected corner paths",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Trace, follow, and deform a connected path built from corners.\"\"\"\nfrom manim import *\n\n\nclass CornerPathScene(Scene):\n    def construct(self):\n        path = VMobject(color=BLUE).set_points_as_corners([\n            (-3, -1, 0), (-1, 1, 0), (1, -1, 0), (3, 1, 0)\n        ]).scale(0.8).rotate(PI / 12).shift(DOWN * 0.3)\n        marker = Dot(path.get_start(), color=YELLOW)\n        title = Text(\"Connected corner path\", font_size=30).shift(UP * 2.5)\n        self.play(Create(path), FadeIn(marker), FadeIn(title), run_time=2)\n        self.play(MoveAlongPath(marker, path), run_time=3, rate_func=linear)\n        target = path.copy().set_points_as_corners([\n            (-3, 0, 0), (-1, 1.5, 0), (1, 0.5, 0), (3, -1, 0)\n        ]).set_color(GREEN)\n        self.play(Transform(path, target), run_time=2)\n        self.play(Uncreate(path), FadeOut(marker))\n        self.wait(1)\n"
    }
  },
  {
    "id": "path",
    "label": "Follow a path",
    "path": "examples/path_scene.py",
    "type": "manim",
    "cover": "gallery/previews/path.png",
    "video": "gallery/previews/path.mp4",
    "editorURL": "./?example=path&url=examples%2Fpath_scene.py",
    "title": "Follow a path",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "from manim import *\n\n\nclass PathScene(Scene):\n    def construct(self):\n        circle = Circle(radius=1.2, color=BLUE).scale(0.8).shift(LEFT * 2)\n        polygon = Polygon((0, 0, 0), (2, 0, 0), (2, 1, 0), (0, 1, 0), color=GREEN)\n        polygon.rotate(PI / 6).shift(RIGHT * 2)\n        line = Line(LEFT * 3, RIGHT * 3, color=GRAY).rotate(-PI / 12).shift(DOWN * 2)\n        dot = Dot(radius=0.15, color=YELLOW)\n        square = Square(side_length=0.3, color=RED, fill_opacity=1).rotate(PI / 4)\n        self.play(Create(circle), Create(polygon), Create(line))\n        self.play(LaggedStart(\n            MoveAlongPath(dot, circle, run_time=4, rate_func=linear),\n            MoveAlongPath(square, polygon, run_time=4, rate_func=linear),\n            lag_ratio=0.25,\n        ))\n        self.play(MoveAlongPath(dot, line), square.animate.shift(UP), run_time=2, rate_func=linear)\n        self.wait(1)\n"
    }
  },
  {
    "id": "arc",
    "label": "Circular arcs",
    "path": "examples/arc_scene.py",
    "type": "manim",
    "cover": "gallery/previews/arc.png",
    "video": "gallery/previews/arc.mp4",
    "editorURL": "./?example=arc&url=examples%2Farc_scene.py",
    "title": "Circular arcs",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "from manim import *\n\n\nclass ArcScene(Scene):\n    def construct(self):\n        upper = Arc(radius=1.4, start_angle=0, angle=PI, arc_center=LEFT * 2, color=BLUE)\n        clockwise = Arc(radius=1.4, start_angle=PI, angle=-PI, arc_center=RIGHT * 2, color=GREEN)\n        clockwise.scale(0.8).rotate(PI / 6)\n        yellow = Dot(radius=0.13, color=YELLOW)\n        red = Dot(radius=0.13, color=RED)\n        self.play(Create(upper), Create(clockwise), run_time=2)\n        self.play(\n            MoveAlongPath(yellow, upper),\n            MoveAlongPath(red, clockwise),\n            run_time=4,\n            rate_func=linear,\n        )\n        self.wait(1)\n"
    }
  },
  {
    "id": "growth",
    "label": "Grow and shrink",
    "path": "examples/growth_scene.py",
    "type": "manim",
    "cover": "gallery/previews/growth.png",
    "video": "gallery/previews/growth.mp4",
    "editorURL": "./?example=growth&url=examples%2Fgrowth_scene.py",
    "title": "Grow and shrink",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "from manim import *\n\n\nclass GrowthScene(Scene):\n    def construct(self):\n        origin = LEFT * 4 + DOWN\n        marker = Dot(origin, color=YELLOW)\n        square = Square(color=BLUE, fill_opacity=0.4).rotate(PI / 6).shift(LEFT * 2)\n        group = VGroup(Circle(radius=0.6, color=GREEN),\n                       Triangle(color=RED)).arrange(RIGHT, buff=0.4).shift(RIGHT * 2)\n        self.add(marker)\n        self.play(GrowFromPoint(square, origin), GrowFromCenter(group),\n                  run_time=3, rate_func=linear)\n        self.wait(1)\n        self.play(LaggedStart(ShrinkToCenter(square, remover=True),\n                             ShrinkToCenter(group, remover=True),\n                             lag_ratio=0.5), run_time=3)\n        self.wait(1)\n"
    }
  },
  {
    "id": "lifecycle",
    "label": "Scene setup and time",
    "path": "examples/lifecycle_scene.py",
    "type": "manim",
    "cover": "gallery/previews/lifecycle.png",
    "video": "gallery/previews/lifecycle.mp4",
    "editorURL": "./?example=lifecycle&url=examples%2Flifecycle_scene.py",
    "title": "Scene setup and time",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Scene setup, elapsed time, and a visible teardown animation.\"\"\"\nfrom manim import *\n\n\nclass LifecycleScene(Scene):\n    def setup(self):\n        self.shape = Square(color=BLUE)\n        self.title = Text(\"Initialized in setup\", font_size=30).shift(UP * 2.5)\n        self.add(self.shape, self.title)\n        self.wait(1)\n\n    def construct(self):\n        self.play(Rotate(self.shape, PI / 2), run_time=2)\n        self.play(Indicate(self.shape))\n        self.wait(1)\n\n    def tear_down(self):\n        summary = Text(f\"Finished at {self.time:.1f}s\", font_size=28).shift(DOWN * 2.5)\n        self.play(FadeIn(summary))\n        self.wait(1)\n"
    }
  },
  {
    "id": "foreground",
    "label": "Keep an overlay in front",
    "path": "examples/foreground_scene.py",
    "type": "manim",
    "cover": "gallery/previews/foreground.png",
    "video": "gallery/previews/foreground.mp4",
    "editorURL": "./?example=foreground&url=examples%2Fforeground_scene.py",
    "title": "Keep an overlay in front",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Keep a grouped overlay in front, release it, and remove it cleanly.\"\"\"\nfrom manim import *\n\n\nclass ForegroundScene(Scene):\n    def construct(self):\n        badge = VGroup(\n            Circle(radius=0.7, color=YELLOW, fill_opacity=1),\n            Text(\"Overlay\", color=BLACK, font_size=20),\n        )\n        blue = Square(side_length=2.8, color=BLUE, fill_opacity=1)\n        red = Square(side_length=2.2, color=RED, fill_opacity=1)\n        title = Text(\"Foreground overlay\", font_size=30).shift(UP * 2.5).set_z_index(10)\n        self.add(title)\n        self.add_foreground_mobject(badge)\n        self.play(Create(blue), run_time=2)\n        self.wait(1)\n        self.remove_foreground_mobject(badge)\n        self.play(Create(red))\n        self.add_foreground_mobject(badge)\n        self.play(Rotate(badge, PI / 6))\n        self.play(FadeOut(badge))\n        self.clear()\n        self.wait(1)\n        self.add(title)\n        self.wait(1)\n"
    }
  },
  {
    "id": "order",
    "label": "Reorder and clear a scene",
    "path": "examples/order_scene.py",
    "type": "manim",
    "cover": "gallery/previews/order.png",
    "video": "gallery/previews/order.mp4",
    "editorURL": "./?example=order&url=examples%2Forder_scene.py",
    "title": "Reorder and clear a scene",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Reorder equal-depth roots, clear the display, and reuse an object.\"\"\"\nfrom manim import *\n\n\nclass OrderScene(Scene):\n    def construct(self):\n        square = Square(color=BLUE, fill_opacity=1).shift(LEFT * 0.5)\n        triangle = Triangle(color=GREEN, fill_opacity=1).scale(2).shift(RIGHT * 0.5)\n        group = VGroup(square, triangle)\n        circle = Circle(color=RED, fill_opacity=1, radius=0.8).shift(DOWN * 0.3)\n        title = Text(\"Scene draw order\", font_size=30).shift(UP * 2.5)\n        self.add(group, circle, title)\n        self.wait(1)\n        self.bring_to_front(group)\n        self.play(Rotate(group, PI / 6), run_time=2)\n        self.bring_to_back(group)\n        self.wait(1)\n        self.clear()\n        self.wait(1)\n        self.play(FadeIn(title))\n        self.wait(1)\n"
    }
  },
  {
    "id": "layers",
    "label": "Layer overlapping shapes",
    "path": "examples/layer_scene.py",
    "type": "manim",
    "cover": "gallery/previews/layers.png",
    "video": "gallery/previews/layers.mp4",
    "editorURL": "./?example=layers&url=examples%2Flayer_scene.py",
    "title": "Layer overlapping shapes",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "\"\"\"Change depth across group boundaries while retaining group geometry.\"\"\"\nfrom manim import *\n\n\nclass LayerScene(Scene):\n    def construct(self):\n        back = Square(color=BLUE, fill_opacity=1, z_index=-2).shift(LEFT * 0.65)\n        front = Square(color=RED, fill_opacity=1, z_index=2).shift(RIGHT * 0.65)\n        pair = VGroup(back, front).scale(1.2).shift(UP * 0.2).save_state()\n        middle = Circle(radius=0.8, color=YELLOW, fill_opacity=1).shift(DOWN * 0.4)\n        title = Text(\"Layers across groups\", font_size=30, z_index=10).shift(UP * 2.5)\n        self.add(pair, middle, title)\n        self.wait(1)\n        self.play(pair.animate.set_z_index(-3), run_time=2, rate_func=linear)\n        self.wait(1)\n        self.play(Restore(pair), run_time=2, rate_func=linear)\n        self.wait(1)\n"
    }
  },
  {
    "id": "style",
    "label": "Fill and outline styles",
    "path": "examples/style_scene.py",
    "type": "manim",
    "cover": "gallery/previews/style.png",
    "video": "gallery/previews/style.mp4",
    "editorURL": "./?example=style&url=examples%2Fstyle_scene.py",
    "title": "Fill and outline styles",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "from manim import *\n\n\nclass StyleScene(Scene):\n    def construct(self):\n        shapes = VGroup(Square(), Circle(), Triangle().scale(2))\n        shapes.arrange(RIGHT, buff=0.6)\n        shapes.set_fill(BLUE, opacity=0.6).set_stroke(YELLOW, width=4)\n        title = Text(\"Fill and outline\", font_size=32).shift(UP * 2)\n        self.play(Create(shapes), Write(title), run_time=2)\n        self.play(shapes.animate.set_fill(RED, opacity=0.8)\n                  .set_stroke(GREEN, width=6, opacity=0.7), run_time=2)\n        self.play(shapes.animate.set_opacity(0.2), run_time=2)\n        self.play(shapes.animate.set_opacity(1), run_time=2)\n        self.wait(1)\n"
    }
  },
  {
    "id": "restore",
    "label": "Save and restore",
    "path": "examples/restore_scene.py",
    "type": "manim",
    "cover": "gallery/previews/restore.png",
    "video": "gallery/previews/restore.mp4",
    "editorURL": "./?example=restore&url=examples%2Frestore_scene.py",
    "title": "Save and restore",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "from manim import *\n\n\nclass RestoreScene(Scene):\n    def construct(self):\n        shapes = VGroup(Square(), Circle()).arrange(RIGHT, buff=0.6)\n        shapes.set_fill(BLUE, 0.5).set_stroke(YELLOW, width=4)\n        shapes.save_state()\n        title = Text(\"Change and restore\", font_size=32).shift(UP * 2.5)\n        self.add(title)\n        self.play(Create(shapes), run_time=2)\n        self.play(shapes.animate.shift(DOWN).scale(0.6).rotate(PI / 4)\n                  .set_fill(RED, 0.8).set_stroke(GREEN, width=6), run_time=2)\n        self.play(Restore(shapes), run_time=3)\n        self.play(ShrinkToCenter(shapes), run_time=1)\n        self.play(shapes.animate.restore(), run_time=2)\n        self.wait(1)\n"
    }
  },
  {
    "id": "indicate",
    "label": "Highlight objects",
    "path": "examples/indicate_scene.py",
    "type": "manim",
    "cover": "gallery/previews/indicate.png",
    "video": "gallery/previews/indicate.mp4",
    "editorURL": "./?example=indicate&url=examples%2Findicate_scene.py",
    "title": "Highlight objects",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "from manim import *\n\n\nclass IndicateScene(Scene):\n    def construct(self):\n        square = Square(fill_color=BLUE, fill_opacity=0.5, stroke_color=PURPLE)\n        square.rotate(PI / 6).shift(LEFT * 2.5)\n        group = VGroup(Circle(radius=0.6, color=GREEN),\n                       Triangle(color=RED)).arrange(RIGHT, buff=0.4).shift(RIGHT * 2)\n        title = Text(\"Highlight and return\", font_size=32).shift(UP * 2.5)\n        self.add(square, group, title)\n        self.play(Indicate(square, scale_factor=1.5),\n                  Indicate(group, scale_factor=1.4, color=ORANGE), run_time=4)\n        self.wait(1)\n        self.play(LaggedStart(Indicate(square), Indicate(group),\n                             lag_ratio=0.5), run_time=3)\n        self.wait(1)\n"
    }
  },
  {
    "id": "copy",
    "label": "Transform a copy",
    "path": "examples/copy_scene.py",
    "type": "manim",
    "cover": "gallery/previews/copy.png",
    "video": "gallery/previews/copy.mp4",
    "editorURL": "./?example=copy&url=examples%2Fcopy_scene.py",
    "title": "Transform a copy",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "from manim import *\n\n\nclass CopyScene(Scene):\n    def construct(self):\n        source = Square(fill_color=BLUE, fill_opacity=0.5, stroke_color=PURPLE)\n        source.shift(LEFT * 3)\n        target = source.copy().set_color(GREEN).shift(RIGHT * 6)\n        title = Text(\"Copy, transform, keep the original\", font_size=28).shift(UP * 2.5)\n        self.add(source, title)\n        self.play(TransformFromCopy(source, target), run_time=4, rate_func=linear)\n        self.wait(1)\n        circle = Circle(color=ORANGE, fill_opacity=0.4).shift(DOWN * 1.5)\n        self.play(TransformFromCopy(target, circle), run_time=2)\n        self.play(Indicate(source), Indicate(target), Indicate(circle), run_time=2)\n        self.play(FadeOut(target), FadeOut(circle))\n        self.wait(1)\n"
    }
  },
  {
    "id": "connector",
    "label": "Move connector endpoints",
    "path": "examples/connector_scene.py",
    "type": "manim",
    "cover": "gallery/previews/connector.png",
    "video": "gallery/previews/connector.mp4",
    "editorURL": "./?example=connector&url=examples%2Fconnector_scene.py",
    "title": "Move connector endpoints",
    "tags": [
      "manim"
    ],
    "description": "Browser Manim-lite animation. Pre-rendered preview available.",
    "document": {
      "src": "from manim import *\n\n\nclass ConnectorScene(Scene):\n    def construct(self):\n        connector = Arrow(LEFT * 3 + DOWN, RIGHT * 3 + DOWN, color=BLUE)\n        connector.rotate(PI / 6).scale(0.8).save_state()\n        start = Dot(connector.get_start(), color=GREEN)\n        end = Dot(connector.get_end(), color=RED)\n        title = Text(\"Move the connector endpoints\", font_size=30).shift(UP * 3)\n        self.add(connector, start, end, title)\n        new_start, new_end = LEFT * 3 + UP, RIGHT * 2 + DOWN * 2\n        self.play(connector.animate.put_start_and_end_on(new_start, new_end),\n                  start.animate.move_to(new_start), end.animate.move_to(new_end),\n                  run_time=4, rate_func=linear)\n        self.wait(1)\n        self.play(Restore(connector), FadeOut(start), FadeOut(end), run_time=2)\n        self.wait(1)\n"
    }
  },
  {
    "id": "dot",
    "label": "Graphviz diagram",
    "path": "examples/basic_graph.dot",
    "type": "graphviz",
    "cover": "gallery/previews/dot.png",
    "video": null,
    "editorURL": "./?example=dot&url=examples%2Fbasic_graph.dot",
    "title": "Graphviz diagram",
    "tags": [
      "graphviz"
    ],
    "description": "Editable graphviz diagram.",
    "document": {
      "src": "digraph {\n  rankdir=LR;\n  node [shape=box, style=rounded];\n  Editor -> Render -> Preview;\n}\n"
    }
  },
  {
    "id": "dotdecision",
    "label": "Decision flowchart",
    "path": "examples/decision_flow.dot",
    "type": "graphviz",
    "cover": "gallery/previews/dotdecision.png",
    "video": null,
    "editorURL": "./?example=dotdecision&url=examples%2Fdecision_flow.dot",
    "title": "Decision flowchart",
    "tags": [
      "graphviz"
    ],
    "description": "Editable graphviz diagram.",
    "document": {
      "src": "// Diamonds, labeled branches, and a loop back for revisions.\ndigraph Review {\n  graph [bgcolor=\"#f8fafc\", pad=0.25];\n  node [shape=box, style=\"rounded,filled\", fillcolor=\"#dbeafe\", color=\"#3b82f6\", fontname=\"Arial\"];\n  edge [color=\"#64748b\", fontname=\"Arial\", fontsize=11];\n  draft [label=\"Draft\"];\n  review [label=\"Ready?\", shape=diamond, fillcolor=\"#fef3c7\", color=\"#d97706\"];\n  revise [label=\"Revise\"];\n  publish [label=\"Publish\", fillcolor=\"#dcfce7\", color=\"#16a34a\"];\n  draft -> review;\n  review -> publish [label=\"Yes\"];\n  review -> revise [label=\"No\"];\n  revise -> draft;\n}\n"
    }
  },
  {
    "id": "dotservices",
    "label": "Service architecture with clusters",
    "path": "examples/service_architecture.dot",
    "type": "graphviz",
    "cover": "gallery/previews/dotservices.png",
    "video": null,
    "editorURL": "./?example=dotservices&url=examples%2Fservice_architecture.dot",
    "title": "Service architecture with clusters",
    "tags": [
      "graphviz"
    ],
    "description": "Editable graphviz diagram.",
    "document": {
      "src": "// Subgraphs whose names start with cluster_ draw grouped boundaries.\ndigraph Services {\n  graph [rankdir=LR, bgcolor=\"#f8fafc\", pad=0.2];\n  node [shape=box, style=\"rounded,filled\", fillcolor=\"#dbeafe\", color=\"#3b82f6\", fontname=\"Arial\"];\n  edge [color=\"#64748b\", fontname=\"Arial\", fontsize=10];\n  browser [label=\"Browser\"];\n  subgraph cluster_app {\n    label=\"Application\"; fontname=\"Arial\"; color=\"#93c5fd\"; style=rounded;\n    api [label=\"API\"];\n    worker [label=\"Worker\"];\n  }\n  subgraph cluster_storage {\n    label=\"Storage\"; fontname=\"Arial\"; color=\"#86efac\"; style=rounded;\n    database [label=\"Database\", shape=cylinder, fillcolor=\"#dcfce7\", color=\"#16a34a\"];\n    queue [label=\"Queue\", fillcolor=\"#dcfce7\", color=\"#16a34a\"];\n  }\n  browser -> api [label=\"Request\"];\n  api -> database;\n  api -> queue [label=\"Job\"];\n  queue -> worker;\n  worker -> database [label=\"Result\"];\n}\n"
    }
  },
  {
    "id": "dotdependencies",
    "label": "Build dependency graph",
    "path": "examples/build_dependencies.dot",
    "type": "graphviz",
    "cover": "gallery/previews/dotdependencies.png",
    "video": null,
    "editorURL": "./?example=dotdependencies&url=examples%2Fbuild_dependencies.dot",
    "title": "Build dependency graph",
    "tags": [
      "graphviz"
    ],
    "description": "Editable graphviz diagram.",
    "document": {
      "src": "// Nodes on the same rank stay aligned; shared prerequisites merge paths.\ndigraph Build {\n  graph [rankdir=LR, bgcolor=\"#f8fafc\", pad=0.2];\n  node [shape=box, style=\"rounded,filled\", fillcolor=\"#ede9fe\", color=\"#8b5cf6\", fontname=\"Arial\"];\n  edge [color=\"#64748b\"];\n  source [label=\"Source\"];\n  assets [label=\"Assets\"];\n  compile [label=\"Compile\"];\n  tests [label=\"Tests\"];\n  bundle [label=\"Bundle\"];\n  release [label=\"Release\", fillcolor=\"#dcfce7\", color=\"#16a34a\"];\n  { rank=same; source; assets; }\n  { rank=same; compile; tests; }\n  source -> compile;\n  source -> tests;\n  compile -> bundle;\n  assets -> bundle;\n  bundle -> release;\n  tests -> release [style=dashed, label=\"Pass\", fontname=\"Arial\", fontsize=10];\n}\n"
    }
  },
  {
    "id": "dottables",
    "label": "Data tables with record ports",
    "path": "examples/data_tables.dot",
    "type": "graphviz",
    "cover": "gallery/previews/dottables.png",
    "video": null,
    "editorURL": "./?example=dottables&url=examples%2Fdata_tables.dot",
    "title": "Data tables with record ports",
    "tags": [
      "graphviz"
    ],
    "description": "Editable graphviz diagram.",
    "document": {
      "src": "// Record fields with named ports let edges connect to specific columns.\ndigraph Tables {\n  graph [rankdir=LR, bgcolor=\"#f8fafc\", pad=0.25, nodesep=0.4];\n  node [shape=record, style=filled, fillcolor=\"#e0f2fe\", color=\"#0284c7\", fontname=\"Arial\", fontsize=12];\n  edge [color=\"#64748b\", arrowsize=0.8];\n  customer [label=\"Customer|<id> id|name\"];\n  order [label=\"Order|<id> id|<customer> customer_id|date\"];\n  item [label=\"Order item|<order> order_id|product|quantity\"];\n  customer:id -> order:customer;\n  order:id -> item:order;\n}\n"
    }
  },
  {
    "id": "dotstates",
    "label": "Order state machine",
    "path": "examples/order_states.dot",
    "type": "graphviz",
    "cover": "gallery/previews/dotstates.png",
    "video": null,
    "editorURL": "./?example=dotstates&url=examples%2Forder_states.dot",
    "title": "Order state machine",
    "tags": [
      "graphviz"
    ],
    "description": "Editable graphviz diagram.",
    "document": {
      "src": "// A point marks the start; double circles mark final states.\ndigraph OrderStates {\n  graph [rankdir=LR, bgcolor=\"#f8fafc\", pad=0.25];\n  node [shape=circle, style=filled, fillcolor=\"#dbeafe\", color=\"#3b82f6\", fontname=\"Arial\", fontsize=12];\n  edge [color=\"#64748b\", fontname=\"Arial\", fontsize=10];\n  start [shape=point, color=\"#64748b\"];\n  new [label=\"New\"];\n  paid [label=\"Paid\"];\n  sent [label=\"Sent\", shape=doublecircle, fillcolor=\"#dcfce7\", color=\"#16a34a\"];\n  cancelled [label=\"Cancelled\", shape=doublecircle, fillcolor=\"#fee2e2\", color=\"#ef4444\"];\n  start -> new;\n  new -> paid [label=\"Pay\"];\n  paid -> sent [label=\"Ship\"];\n  new -> cancelled [label=\"Cancel\"];\n  paid -> cancelled [label=\"Refund\"];\n}\n"
    }
  }
];
