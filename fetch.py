# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["pillow==11.3.0", "requests==2.32.5"]
# ///

"""Cache source responses and a Hong Kong basemap: uv run fetch.py.

Existing files are never replaced. Forecast URLs roll forward: a missing
September 17 response must be restored from git if the server version changed.
Basemap approach: https://github.com/sd5913/tidal-streams/blob/main/currents.py
"""

import io
import json
import time
from datetime import datetime, timezone

import requests
from PIL import Image

from humidity import DATA, STATIONS, MODEL_TIME, TILES, MAP_CREDIT, ZOOM, map_extent

SOURCE = "https://www.hko.gov.hk/wxinfo/awsgis/forecast/{station}.xml"


def fetch_forecasts(session):
    """Save unchanged response bytes, only if they match our frozen snapshot."""
    for station in STATIONS:
        path = DATA / f"{station}.json"
        if path.exists():
            continue
        reply = session.get(SOURCE.format(station=station), timeout=30)
        reply.raise_for_status()
        record = reply.json()
        if (record.get("StationCode") != station
                or record.get("ModelTime") != MODEL_TIME
                or not str(record.get("LastModified", "")).startswith("20260917")):
            raise ValueError(
                f"{station}: live forecast changed. Restore data/{station}.json "
                "from git; do not mix a new forecast with the September 17 snapshot."
            )
        with path.open("xb") as handle:
            handle.write(reply.content)
        print(f"Saved original response: {path.name}")
        time.sleep(0.5)


def fetch_basemap(session):
    """Keep original tiles plus a stitched crop and its exact pixel extent."""
    x0, y0, x1, y1 = map_extent()
    tile_dir = DATA / "map-tiles"
    tile_dir.mkdir(exist_ok=True)
    tx0, ty0 = x0//256, y0//256
    tx1, ty1 = (x1-1)//256, (y1-1)//256
    sheet = Image.new("RGB", ((tx1-tx0+1)*256, (ty1-ty0+1)*256))
    sources = []
    for ty in range(ty0, ty1+1):
        for tx in range(tx0, tx1+1):
            path = tile_dir / f"{ZOOM}-{tx}-{ty}.png"
            url = TILES.format(z=ZOOM, x=tx, y=ty)
            if not path.exists():
                reply = session.get(url, timeout=30)
                reply.raise_for_status()
                image = Image.open(io.BytesIO(reply.content))
                if image.size != (256, 256):
                    raise ValueError(f"Unexpected tile dimensions: {url}")
                image.verify()
                with path.open("xb") as handle:
                    handle.write(reply.content)
                print(f"Cached tile {path.name}")
                time.sleep(0.5)
            with Image.open(path) as image:
                sheet.paste(image.convert("RGB"), ((tx-tx0)*256, (ty-ty0)*256))
            sources.append({"file": str(path.relative_to(DATA)), "url": url})
    target = DATA / "basemap.png"
    if not target.exists():
        sheet.crop((x0-tx0*256, y0-ty0*256, x1-tx0*256, y1-ty0*256)).save(target)
    metadata = DATA / "basemap-source.json"
    if not metadata.exists():
        metadata.write_text(json.dumps({
            "credit": MAP_CREDIT,
            "source_example": "https://github.com/sd5913/tidal-streams/blob/main/currents.py",
            "cached_at_utc": datetime.now(timezone.utc).isoformat(),
            "projection": "EPSG:3857", "zoom": ZOOM,
            "pixel_extent": [x0,y0,x1,y1],
            "description": "basemap.png is a stitched crop; map-tiles/ preserves original responses.",
            "tiles": sources,
        }, indent=2) + "\n", encoding="utf-8")
    print(f"Basemap ready: {len(sources)} cached tiles; drawing now works offline.")


def main():
    DATA.mkdir(exist_ok=True)
    with requests.Session() as session:
        session.headers["User-Agent"] = "A-Bit-Damp / SD5913 student data visualisation"
        fetch_forecasts(session)
        fetch_basemap(session)
    print(f"{len(STATIONS)} original forecast files retained; no existing responses overwritten.")


if __name__ == "__main__":
    main()
