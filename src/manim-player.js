/** SVG frame player. Export always reflects the currently displayed frame. */
class ManimPlayer {
  constructor(container, sceneData, onFrame) {
    this.frames = sceneData.frames;
    this.mathGlyphs = sceneData.mathGlyphs;
    this.fps = sceneData.fps;
    this.index = 0;
    this.playing = false;
    this.root = document.createElement('div');
    this.root.className = 'manim-player';
    this.stage = document.createElement('div');
    this.stage.className = 'manim-stage';
    const controls = document.createElement('div');
    controls.className = 'manim-controls';
    this.playButton = document.createElement('button');
    this.playButton.type = 'button';
    this.playButton.textContent = 'Play';
    const replay = document.createElement('button');
    replay.type = 'button';
    replay.textContent = 'Replay';
    this.seek = document.createElement('input');
    this.seek.type = 'range';
    this.seek.min = 0;
    this.seek.max = this.frames.length - 1;
    this.seek.value = 0;
    this.seek.step = 1;
    this.seek.setAttribute('aria-label', 'Animation position');
    this.time = document.createElement('span');
    controls.append(this.playButton, replay, this.seek, this.time);
    this.root.append(this.stage, controls);
    container.appendChild(this.root);
    this.onFrame = onFrame;
    this.playButton.onclick = () => this.playing ? this.pause() : this.play();
    replay.onclick = () => { this.pause(); this.draw(0); this.play(); };
    this.seek.oninput = () => { this.pause(); this.draw(Number(this.seek.value)); };
    this.draw(0);
    this.play();
  }

  draw(index) {
    this.index = index;
    const svg = ManimRenderer.render(this.frames[index], this.mathGlyphs);
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', 'Manim animation preview');
    this.stage.replaceChildren(svg);
    this.seek.value = index;
    this.time.textContent = `${(index / this.fps).toFixed(1)} / ${((this.frames.length - 1) / this.fps).toFixed(1)}s`;
    this.onFrame(svg);
  }

  play() {
    if (this.playing || this.frames.length < 2) return;
    if (this.index === this.frames.length - 1) this.draw(0);
    this.playing = true;
    this.playButton.textContent = 'Pause';
    const started = performance.now() - this.index / this.fps * 1000;
    const tick = now => {
      if (!this.playing) return;
      const index = Math.min(this.frames.length - 1, Math.max(0, Math.floor((now - started) * this.fps / 1000)));
      if (index !== this.index) this.draw(index);
      if (index === this.frames.length - 1) this.pause();
      else this.animationId = requestAnimationFrame(tick);
    };
    this.animationId = requestAnimationFrame(tick);
  }

  pause() {
    this.playing = false;
    cancelAnimationFrame(this.animationId);
    this.playButton.textContent = 'Play';
  }

  destroy() { this.pause(); this.root.remove(); }
}
window.ManimPlayer = ManimPlayer;
