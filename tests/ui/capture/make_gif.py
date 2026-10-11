"""Builds docs/assets/demo.gif from the frames `npm run docs:capture` filmed.

That script runs it as:  uv run --with pillow python tests/ui/capture/make_gif.py
Pillow is needed only here, so it is not a project dependency.
"""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
FRAMES = ROOT / "test-results" / "capture-frames"
TARGET = ROOT / "docs" / "assets" / "demo.gif"
WIDTH = 960
COLOURS = 256
LAST_FRAME_MS = 2500
MAX_FRAME_MS = 3000
PALETTE_SAMPLES = 8


def _shared_palette(frames: list[Image.Image]) -> Image.Image:
    """One palette for every frame, so unchanged pixels stay identical between frames."""
    step = max(1, len(frames) // PALETTE_SAMPLES)
    samples = frames[::step]
    sheet = Image.new("RGB", (WIDTH, sum(frame.height for frame in samples)))
    top = 0
    for frame in samples:
        sheet.paste(frame, (0, top))
        top += frame.height
    # Octree keeps the small areas of status colour (green, amber, blue) that
    # median cut gives up to the large white and dark areas.
    return sheet.quantize(colors=COLOURS, method=Image.Quantize.FASTOCTREE)


def main() -> None:
    paths = sorted(FRAMES.glob("*.png"))
    if len(paths) < 2:
        raise SystemExit(f"No frames in {FRAMES}. Run: npm run docs:capture")
    times = [int(path.stem) for path in paths] + [int(paths[-1].stem) + LAST_FRAME_MS]

    frames: list[Image.Image] = []
    durations: list[int] = []
    for index, path in enumerate(paths):
        shown_ms = times[index + 1] - times[index]
        with Image.open(path) as image:
            height = round(image.height * WIDTH / image.width)
            frame = image.convert("RGB").resize(
                (WIDTH, height), Image.Resampling.LANCZOS
            )
        if frames and frame.tobytes() == frames[-1].tobytes():
            # Nothing moved: show the last frame for longer instead of storing it again.
            durations[-1] = min(durations[-1] + shown_ms, MAX_FRAME_MS)
            continue
        frames.append(frame)
        durations.append(shown_ms)

    palette = _shared_palette(frames)
    indexed = [
        frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames
    ]
    indexed[0].save(
        TARGET,
        save_all=True,
        append_images=indexed[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    size_kb = TARGET.stat().st_size / 1024
    print(f"{TARGET.relative_to(ROOT)}: {len(indexed)} frames, {size_kb:.0f} KB")


if __name__ == "__main__":
    main()
