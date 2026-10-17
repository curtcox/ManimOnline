"""Render every Manim QR snippet natively through manim-lite and report problems.

Usage: python3 video-series/tools/check_snippets.py [snippet-path-substring ...]

Each snippet runs in its own subprocess (with a deadline, like the browser's) so a
runaway scene cannot stall the check. The manifest's `expect` field marks snippets
that are meant to fail ("error") or never finish ("timeout"). NumPy snippets need a
Python with NumPy; Pillow/networkx snippets need those packages too.

A native pass is necessary but not sufficient: it does not prove Pyodide loading,
MathJax measurement or browser playback. Load the links in a browser as well.
"""
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

SERIES = Path(__file__).resolve().parents[1]
ROOT = SERIES.parent
MANIFEST = SERIES / 'qr-manifest.json'
DEADLINE = 90        # seconds; matches the editor's render deadline
MAX_FRAMES = 1800    # 120 s at 15 fps
MAX_BYTES = 32 * 1024 * 1024


def render_one(path, scene):
    spec = importlib.util.spec_from_file_location('manim_lite', ROOT / 'src/manim-lite.py')
    lite = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lite)
    source = Path(path).read_text()
    started = time.time()
    try:
        output = lite.render_scene(source, scene or None, compact=True)
    except Exception as error:  # noqa: BLE001 - report every failure kind
        print(json.dumps({'status': 'error', 'message': f'{type(error).__name__}: {error}'}))
        return
    result = json.loads(output)
    frames = result.get('frames') or []
    print(json.dumps({
        'status': 'ok',
        'frames': len(frames),
        'seconds': round(len(frames) / 15, 2),
        'bytes': len(output),
        'scenes': result.get('scenes'),
        'math_estimated': len(result.get('math_estimated') or []),
        'elapsed': round(time.time() - started, 1),
    }))


def main(filters):
    manifest = json.loads(MANIFEST.read_text())['snippets']
    failures = 0
    for entry in manifest:
        if entry['type'] != 'manim':
            continue
        if filters and not any(f in entry['file'] for f in filters):
            continue
        expect = entry.get('expect', 'ok')
        path = SERIES / entry['file']
        try:
            run = subprocess.run([sys.executable, __file__, '--one', str(path), entry.get('scene', '')],
                                 capture_output=True, text=True, timeout=DEADLINE)
            report = json.loads(run.stdout.strip().splitlines()[-1]) if run.stdout.strip() else {
                'status': 'error', 'message': run.stderr.strip()[-500:]}
        except subprocess.TimeoutExpired:
            report = {'status': 'timeout'}
        problems = []
        if report['status'] != expect:
            problems.append(f"expected {expect}, got {report['status']}")
        if report['status'] == 'ok':
            if report['frames'] > MAX_FRAMES + 1:
                problems.append('longer than the 120 s preview limit')
            if report['bytes'] > MAX_BYTES:
                problems.append('frame data over 32 MiB')
        failures += bool(problems)
        mark = 'FAIL' if problems else 'ok  '
        detail = report.get('message') or (
            f"{report.get('seconds')} s, {report.get('frames')} frames, "
            f"{report.get('bytes', 0) // 1024} KiB, {report.get('elapsed')} s to render" if report['status'] == 'ok' else report['status'])
        print(f"{mark} {entry['id']:<8} {entry['file']:<45} {detail}{' — ' + '; '.join(problems) if problems else ''}")
    print(f"\n{failures} problem(s)")
    return 1 if failures else 0


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--one':
        render_one(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else '')
    else:
        sys.exit(main(sys.argv[1:]))
