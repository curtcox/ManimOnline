/** Template detection/debounce plus Sheets' abortable asynchronous result contract. */
export class RenderScheduler {
  constructor({ detect = () => {}, render, onResult, onStatus = () => {}, timers = globalThis, delay = 300, detectionDelay = 300, renderDelay = 1000 }) {
    Object.assign(this, { detect, render, onResult, onStatus, timers, delay, detectionDelay, renderDelay });
    this.revision = 0;
  }
  cancel() {
    this.revision++;
    for (const timer of [this.timer, this.detectionTimer]) this.timers.clearTimeout(timer);
    this.controller?.abort();
  }
  schedule(source, context = {}, immediate = false) {
    this.cancel();
    const revision = this.revision, controller = this.controller = new AbortController();
    const legacy = !this.onResult;
    if (legacy && source?.detect !== false) this.detectionTimer = this.timers.setTimeout(() => {
      if (revision === this.revision) this.detect();
    }, this.detectionDelay);
    this.onStatus('waiting');
    this.timer = this.timers.setTimeout(async () => {
      if (revision !== this.revision) return;
      this.onStatus('rendering');
      try {
        const result = await this.render(source, { ...context, signal: controller.signal, revision });
        if (revision !== this.revision || controller.signal.aborted) return;
        await this.onResult?.(result, revision);
        if (revision === this.revision) this.onStatus('done', result?.diagnostics ?? []);
      } catch (error) { if (revision === this.revision && !controller.signal.aborted) this.onStatus('error', error); }
    }, immediate ? 0 : legacy ? this.renderDelay : this.delay);
    return revision;
  }
}
