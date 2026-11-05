/** Coalesce edits; queued callbacks from earlier source versions cannot render. */
class RenderScheduler {
  constructor({ detect, render, timers = globalThis, detectionDelay = 300, renderDelay = 1000 }) {
    this.detect = detect;
    this.render = render;
    this.timers = timers;
    this.detectionDelay = detectionDelay;
    this.renderDelay = renderDelay;
    this.revision = 0;
  }
  cancel() {
    this.revision++;
    this.timers.clearTimeout(this.detectionTimer);
    this.timers.clearTimeout(this.renderTimer);
  }
  schedule({ detect = true } = {}) {
    this.cancel();
    const revision = this.revision;
    if (detect) this.detectionTimer = this.timers.setTimeout(() => {
      if (revision === this.revision) this.detect();
    }, this.detectionDelay);
    this.renderTimer = this.timers.setTimeout(() => {
      if (revision === this.revision) this.render();
    }, this.renderDelay);
  }
}
if (typeof module !== 'undefined') module.exports = RenderScheduler;
else globalThis.RenderScheduler = RenderScheduler;
