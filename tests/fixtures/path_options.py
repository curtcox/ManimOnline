def r(v): return [round(float(x), 4) for x in v]
out = []
class S(Scene):
    def construct(self):
        sq = Square().shift(RIGHT * 2)
        t = Transform(sq, Square().rotate(PI / 4).shift(LEFT * 2 + UP), path_arc=PI, path_arc_centers=UP)
        t.begin(); t.interpolate(0.5)
        out.append([r(sq.get_center()), r(sq.points[0])])
        c = Circle().shift(RIGHT)
        rot = Rotate(c, PI / 2, about_point=ORIGIN, path_arc=PI)
        rot.begin(); rot.interpolate(0.5)
        out.append([r(c.get_center()), r(c.points[0])])
        a = Arrow(LEFT, RIGHT)
        g = GrowArrow(a, path_arc=PI / 2)
        g.begin(); g.interpolate(0)
        out.append([r(a.get_center()), round(a.width, 4)])
        g.interpolate(0.5)
        out.append([r(a.get_center()), round(a.width, 4)])
        seen = []
        d = Dot(); self.add(d)
        self.play(AnimationGroup(FadeIn(Square()), _on_finish=lambda s: seen.append(len(s.mobjects)),
                                 reverse_rate_function=True, suspend_mobject_updating=False))
        self.play(FadeOut(d, _on_finish=lambda s: seen.append(d in s.mobjects)))
        out.append(seen)
        f = FadeIn(Square().shift(RIGHT), path_arc=PI)
        sq2 = f.mobject; f.begin(); f.interpolate(0.5)
        out.append(r(sq2.get_center()))
S().render(); result = out
