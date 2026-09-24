# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["pygame==2.6.1", "pillow==11.3.0", "numpy==2.2.6"]
# ///

"""Draw the cached forecast as a 12-frame WebP and PNG: uv run plot.py.

No network calls. --still renders just the cover. Every frame represents one
forecast timestamp; replay from 22:00 to 00:00 repeats this same day.
"""

import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, features
from humidity import (OUT, HOURS, FRAME_MS, MAP_SIZE, PAPER, INK, MAP_CREDIT,
                      load_data, report, load_basemap, to_pixel, draw_ink)

CANVAS = (1600, 1050)
MAP_ORIGIN = (360, 160)


def font(size, serif=False):
    """Installed fonts when available; Pillow's bundled font otherwise."""
    candidates = (["/System/Library/Fonts/Supplemental/Georgia.ttf",
                   "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"] if serif else
                  ["/System/Library/Fonts/Supplemental/Arial.ttf",
                   "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"])
    for path in candidates:
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def frame(index, stations, basemap):
    """One forecast hour: fixed map positions and data-dependent ink."""
    image = Image.new("RGBA", CANVAS, PAPER + (255,))
    draw = ImageDraw.Draw(image)
    draw.text((40,26), "A Bit Damp", font=font(53,True), fill=INK)
    draw.text((43,99), "HONG KONG  /  RELATIVE HUMIDITY IN INK", font=font(15), fill=(90,111,125))
    draw.text((1560,43), "25 September 2026", font=font(25,True), fill=INK, anchor="ra")
    draw.text((1560,84), f"FORECAST  ·  {HOURS[index]:02d}:00 HKT", font=font(19), fill=INK, anchor="ra")
    draw.line((40,137,1560,137), fill=(186,197,202), width=1)
    image.alpha_composite(basemap.convert("RGBA"), MAP_ORIGIN)
    for station in stations:
        x, y = to_pixel(station["lon"], station["lat"])
        x, y = round(x+MAP_ORIGIN[0]), round(y+MAP_ORIGIN[1])
        ink = draw_ink(station["code"], station["values"][index])
        image.alpha_composite(ink, (x-ink.width//2, y-ink.height//2))
    draw = ImageDraw.Draw(image)
    for station in stations:
        x, y = to_pixel(station["lon"], station["lat"])
        x, y = x+MAP_ORIGIN[0], y+MAP_ORIGIN[1]
        draw.ellipse((x-1.5,y-1.5,x+1.5,y+1.5), fill=(242,246,247))
    draw.text((42,177), "Weather, made visible.", font=font(23,True), fill=INK)
    for n, text in enumerate(("A day of forecast humidity,", "seen through the spread of ink.",
                              "", "Darker ink. Wider diffusion.", "Higher relative humidity.")):
        draw.text((42,226+n*26), text, font=font(17), fill=(81,102,115))
    draw.text((42,393), "RELATIVE HUMIDITY", font=font(13), fill=(90,111,125))
    for n, value in enumerate((60,80,95)):
        y = 460+n*96
        ink = draw_ink("legend",value)
        image.alpha_composite(ink, (95-ink.width//2,y-ink.height//2))
        draw.text((166,y-12), f"{value}%", font=font(24,True), fill=INK)
    values = [station["values"][index] for station in stations]
    draw.text((42,751), f"{len(stations)} stations", font=font(27,True), fill=INK)
    draw.text((42,794), f"{min(values):.1f}% — {max(values):.1f}%", font=font(22), fill=INK)
    draw.text((42,830), "Range across displayed stations", font=font(13), fill=(90,111,125))
    draw.text((42,906), "Snapshot saved 17 Sep 2026", font=font(14), fill=(90,111,125))
    draw.line((40,972,1560,972), fill=(186,197,202), width=1)
    draw.text((42,990), "Ink extent is symbolic, not geographic coverage.", font=font(13), fill=(90,111,125))
    draw.text((42,1013), "Forecast: Hong Kong Observatory  ·  Map: " + MAP_CREDIT,
              font=font(12), fill=(90,111,125))
    for j, hour in enumerate(HOURS):
        x, y = 1050+j*45, 994
        draw.ellipse((x-4,y-4,x+4,y+4), fill=INK if j == index else (191,204,211))
        if j % 2 == 0:
            draw.text((x,1008), f"{hour:02d}", anchor="ma", font=font(11), fill=(90,111,125))
    return image.convert("RGB")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--still", action="store_true", help="render only the 00:00 PNG")
    args = parser.parse_args()
    stations, omitted = load_data()
    report(stations,omitted)
    basemap = load_basemap().resize(MAP_SIZE,Image.Resampling.LANCZOS)
    OUT.mkdir(exist_ok=True)
    cover = frame(0,stations,basemap)
    cover.save(OUT / "humidity.png")
    if not args.still:
        if not features.check("webp_anim"):
            raise RuntimeError("This Pillow installation lacks animated WebP support")
        frames = [cover]
        for i in range(1,len(HOURS)):
            frames.append(frame(i,stations,basemap))
        cover.save(OUT / "humidity.webp", save_all=True, append_images=frames[1:],
                   duration=FRAME_MS, loop=0, lossless=True, method=4)
        print(f"Saved out/humidity.webp: {len(frames)} frames, {FRAME_MS} ms each.")
    print("Saved out/plot.png")


    main()
