# Offline use

Application files, gallery covers and documentation use Fragment Kit's hash-verified atomic cache. Gallery MP4 previews load only when requested and remain outside offline readiness.

Python and MathJax remain deferred: opening a gallery animation on a phone plays its MP4 without downloading Python. After a live render, ManimOnline saves the pinned runtime in a separate verified cache. More → Save Python offline also prepares it. “Diagrams ready offline” means the application is saved but Python is still incomplete. “Available offline” requires both the application and every required Python/math asset.

NumPy, Pillow, Pygments and networkx wheels are cached after actual use and excluded from readiness. External resources requested by user scenes are not made offline automatically.

Cache reads and carry-over from older versions verify every byte against the pinned hashes. Repair retries incomplete files. Updates wait for activation; Update and reload preserves source and all preview settings before reloading.
