from manim.scene.section import Section
def r(v): return [round(float(x), 4) for x in v]
c = HSV((0.25, 0.5, 0.8))
tip = ArrowSquareTip(length=0.5); side = tip.side_length; tip.side_length = 1
line = Line(LEFT, RIGHT); t = ArrowTriangleFilledTip().move_to(RIGHT * 3)
line.reset_endpoints_based_on_tip(t, False)
a = PointCloudDot(); b = PointCloudDot(color=RED, density=4)
a.match_colors(b)
rot = Rotate(Square(), PI / 2, about_point=RIGHT).create_target()
sec = Section('default.normal', 'v.mp4', 'intro', False); sec.partial_movie_files = ['a', None, 'b']
result = [len(dir(TexFontTemplates)) >= 52, TexFontTemplates.comic_sans.description,
          TexTemplateLibrary.simple.description, [round(c.h, 4), round(c.s, 4), round(c.v, 4)],
          round(side, 4), round(tip.width, 4), r(line.get_end()),
          len(a.points) == len(b.points), a.get_color() == b.get_color(), r(rot.get_center()),
          Indicate(Square()).create_target().width, FadeIn(Dot()).create_target().width,
          sec.get_clean_partial_movie_files(), sec.get_dict(__import__('pathlib').Path('.'))['name']]
