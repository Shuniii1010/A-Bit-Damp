# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["pygame==2.6.1", "pillow==11.3.0", "numpy==2.2.6"]
# ///

"""Shared data, projection and ink functions for the film and the Folium map.

uv run humidity.py prints a data summary. Drawing imports are lazy so fetch.py
can reuse the geographic constants without installing the drawing libraries.
"""

import hashlib
import json
import math
import os
from datetime import datetime, timezone, timedelta
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = HERE / "out"
DATE = "20260925"
MODEL_TIME = 2026091612  # Publisher's identifier; do not infer its timezone.
HKT = timezone(timedelta(hours=8))
HOURS = tuple(range(0, 24, 2))
FRAME_MS = 800
ZOOM = 11
BOUNDS = (113.80, 22.14, 114.43, 22.56)  # west, south, east, north
MAP_SIZE = (1200, 790)
PAPER = (247, 248, 246)
INK = (22, 50, 72)
TILES = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}"
MAP_CREDIT = "Esri, HERE, Garmin, © OpenStreetMap contributors"

# Names: HKO's irwip-station-config-aws.js. Positions come from each original
# forecast JSON's Latitude/Longitude, not hand-placed screen points.
STATIONS = {
    "CCH": "Cheung Chau", "CWB": "Clear Water Bay", "HKA": "Chek Lap Kok",
    "HKO": "Hong Kong Observatory", "HKP": "Hong Kong Park", "HKS": "Wong Chuk Hang",
    "JKB": "Tseung Kwan O", "KLT": "Kowloon City", "KP": "King's Park",
    "KSC": "Kau Sai Chau", "LFS": "Lau Fau Shan", "PEN": "Peng Chau",
    "PLC": "Tai Mei Tuk", "SE1": "Kai Tak Runway Park", "SEK": "Shek Kong",
    "SHA": "Sha Tin", "SKG": "Sai Kung", "SKW": "Shau Kei Wan", "SSH": "Sheung Shui",
    "TKL": "Ta Kwu Ling", "TLS": "Tai Lung", "TW": "Tsuen Wan Shing Mun Valley",
    "TWN": "Tsuen Wan Ho Koon", "TY1": "Tsing Yi", "TYW": "Pak Tam Chung",
    "WGL": "Waglan Island", "WLP": "Wetland Park", "YLP": "Yuen Long Park",
}


def load_data():
    """Validate the snapshot; report and omit stations missing any selected hour."""
    stations, omitted = [], []
    for code, name in STATIONS.items():
        path = DATA / f"{code}.json"
        if not path.is_file():
            raise FileNotFoundError(f"Restore {path} from the saved snapshot or git.")
        record = json.loads(path.read_bytes())
        if (record.get("StationCode") != code or record.get("ModelTime") != MODEL_TIME
                or not str(record.get("LastModified", "")).startswith("20260917")):
            raise ValueError(f"{path.name}: incompatible forecast version or station code")
        lon, lat = float(record["Longitude"]), float(record["Latitude"])
        if not (BOUNDS[0] <= lon <= BOUNDS[2] and BOUNDS[1] <= lat <= BOUNDS[3]):
            raise ValueError(f"{code}: station lies outside our Hong Kong map")
        hours = {}
        for row in record["HourlyWeatherForecast"]:
            when = str(row["ForecastHour"])
            if when.startswith(DATE):
                hour = int(when[8:10])
                if hour in hours:
                    raise ValueError(f"{code}: duplicated forecast hour {when}")
                value = row.get("ForecastRelativeHumidity")
                if value in (None, "", "M"):
                    hours[hour] = None
                elif (not isinstance(value, (int, float)) or isinstance(value, bool)
                      or not math.isfinite(value) or not 0 <= value <= 100):
                    raise ValueError(f"{code}: invalid humidity {value!r} at {when}")
                else:
                    hours[hour] = float(value)
        missing = [h for h in HOURS if hours.get(h) is None]
        if missing:
            omitted.append({"code": code, "name": name, "hours": missing})
            continue
        stations.append({"code": code, "name": name, "lon": lon, "lat": lat,
                         "values": [hours[h] for h in HOURS],
                         "last_modified": record["LastModified"]})
    if not stations:
        raise ValueError("No stations have the complete 12-frame sequence")
    return stations, omitted


def report(stations, omitted):
    print(f"{len(stations)} stations × {len(HOURS)} frames; {DATE}, Hong Kong time.")
    for item in omitted:
        print(f"Omitted {item['code']} ({item['name']}): missing humidity, "
              f"{len(item['hours'])} selected hours. Original response retained.")


def timestamp(hour):
    return datetime.strptime(f"{DATE}{hour:02d}", "%Y%m%d%H").replace(tzinfo=HKT).isoformat()


def world_pixel(lon, lat):
    """Web Mercator pixels at ZOOM, matching the Esri tile grid."""
    size = 256 * 2 ** ZOOM
    phi = math.radians(lat)
    return ((lon + 180) / 360 * size,
            (1 - math.asinh(math.tan(phi)) / math.pi) / 2 * size)


def pixel_lnglat(x, y):
    size = 256 * 2 ** ZOOM
    return x / size * 360 - 180, math.degrees(math.atan(math.sinh(math.pi * (1 - 2*y/size))))


def map_extent():
    """Expand the geographical bounds to the picture's aspect ratio, then round."""
    west, south, east, north = BOUNDS
    x0, y0 = world_pixel(west, north)
    x1, y1 = world_pixel(east, south)
    cx, cy = (x0+x1)/2, (y0+y1)/2
    width = max(x1-x0, (y1-y0) * MAP_SIZE[0]/MAP_SIZE[1])
    height = width * MAP_SIZE[1]/MAP_SIZE[0]
    return math.floor(cx-width/2), math.floor(cy-height/2), math.ceil(cx+width/2), math.ceil(cy+height/2)


def to_pixel(lon, lat):
    """Coordinates inside the static map panel (before its page offset)."""
    x, y = world_pixel(lon, lat)
    x0, y0, x1, y1 = map_extent()
    return (x-x0)/(x1-x0)*MAP_SIZE[0], (y-y0)/(y1-y0)*MAP_SIZE[1]


def load_basemap():
    from PIL import Image
    path = DATA / "basemap.png"
    metadata = DATA / "basemap-source.json"
    if not path.exists() or not metadata.exists():
        raise FileNotFoundError("Run uv run fetch.py once to cache the basemap.")
    info = json.loads(metadata.read_text(encoding="utf-8"))
    if info["pixel_extent"] != list(map_extent()) or info["zoom"] != ZOOM:
        raise ValueError("The cached basemap does not match this projection/extent.")
    with Image.open(path) as image:
        x0, y0, x1, y1 = map_extent()
        if image.size != (x1-x0, y1-y0):
            raise ValueError("Unexpected basemap image size")
        return image.convert("RGB")


def humidity_to_style(humidity):
    """Fixed display scale across ALL stations and frames; never per-frame scaling.

    The 50–100% display range emphasizes this snapshot's range. This artistic
    encoding does not represent geographic spread or proportional area.
    """
    t = max(0.0, min(1.0, (humidity - 50) / 50))
    return {"diameter": round(30 + 78*t), "opacity": 0.22 + 0.76*t,
            "blur": 0.5 + 1.4*t}


@lru_cache(maxsize=64)
def ink_mask(station):
    """Pygame draws uneven polygons; layered masks and grain form a soft ink bloom.

    The station seed is fixed, so revisiting a frame produces identical texture.
    Separate surfaces avoid draw calls replacing earlier alpha values.
    """
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    import numpy as np
    import pygame
    from PIL import Image, ImageFilter

    size = 256
    seed = int.from_bytes(hashlib.sha256(station.encode()).digest()[:8], "big")
    rng = np.random.default_rng(seed)
    theta = np.linspace(0, 2*math.pi, 180, endpoint=False)
    outline = np.ones(theta.shape)
    for frequency, amplitude in ((3,.11), (5,.10), (9,.08), (17,.045), (31,.025)):
        outline += amplitude*np.sin(frequency*theta + rng.uniform(0, 2*math.pi))
    density = np.zeros((size, size), dtype=np.float32)
    for radius, weight, blur in ((91,.055,9), (82,.075,6), (73,.10,4),
                                 (65,.11,3), (56,.12,2), (47,.15,2),
                                 (38,.18,1.5), (28,.19,1.5), (17,.15,2)):
        surface = pygame.Surface((size, size), flags=pygame.SRCALPHA)
        r = radius*outline + rng.uniform(-2.5, 2.5, len(theta))
        points = list(zip(128 + r*np.cos(theta), 128 + r*np.sin(theta)))
        pygame.draw.polygon(surface, (255, 255, 255, 255), points)
        mask = Image.frombytes("RGBA", (size, size), pygame.image.tobytes(surface, "RGBA")).getchannel("A")
        density += weight*np.asarray(mask.filter(ImageFilter.GaussianBlur(blur)))/255
    grain = np.zeros_like(density)
    for cells, weight in ((7,.42), (19,.32), (48,.18), (128,.08)):
        noise = Image.fromarray(rng.integers(0, 256, (cells, cells), dtype=np.uint8))
        grain += weight*np.asarray(noise.resize((size, size), Image.Resampling.BICUBIC))/255
    density *= .58 + .75*grain
    return Image.fromarray(np.uint8(np.clip(density, 0, 1)*255))


def draw_ink(station, humidity):
    """Transparent PNG-ready stamp: both output formats call this function."""
    from PIL import Image, ImageFilter
    style = humidity_to_style(humidity)
    mask = ink_mask(station).filter(ImageFilter.GaussianBlur(style["blur"]))
    alpha = mask.point(lambda value: round(value*style["opacity"]))
    stamp = Image.new("RGBA", mask.size, INK + (0,))
    stamp.putalpha(alpha)
    side = style["diameter"]
    return stamp.resize((side, side), Image.Resampling.LANCZOS)


if __name__ == "__main__":
    report(*load_data())
