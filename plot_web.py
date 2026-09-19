# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["pygame==2.6.1", "pillow==11.3.0", "numpy==2.2.6", "folium==0.20.0"]
# ///

"""Generate site/index.html from cached data: uv run plot_web.py.

Folium/Leaflet handles positions, pan and zoom. Pygame supplies the exact same
ink stamps as plot.py. The browser loads its JS/CSS libraries from CDNs; all
forecast values, ink images and the default cached basemap are embedded.
Optional live Esri tiles provide extra detail when zooming.
"""

import base64
import io
import json
from html import escape

import folium
from folium.plugins import TimestampedGeoJson
from branca.element import Element, MacroElement, Template

from humidity import (HERE, HOURS, FRAME_MS, TILES, MAP_CREDIT, draw_ink,
                      load_data, report, load_basemap, map_extent, pixel_lnglat, timestamp)


def image_url(image):
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def feature(station, index):
    """One station at one forecast time, with a centred transparent ink icon."""
    humidity = station["values"][index]
    image = draw_ink(station["code"], humidity)
    hour = HOURS[index]
    popup = (f'<div class="station-popup"><small>{station["code"]} · FORECAST</small>'
             f'<h3>{escape(station["name"])}</h3><strong>{humidity:.1f}%</strong>'
             f'<p>Relative humidity<br>25 Sep 2026 · {hour:02d}:00 HKT</p></div>')
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [station["lon"], station["lat"]]},
        "properties": {
            "time": timestamp(hour), "station": station["code"], "humidity": humidity,
            "popup": popup, "icon": "marker",
            "iconstyle": {"iconUrl": image_url(image), "iconSize": [image.width,image.height],
                          "iconAnchor": [image.width/2,image.height/2],
                          "popupAnchor": [0,-image.height/3], "className": "ink-station"},
        },
    }


def add_layout(m, stations, omitted):
    legend = "".join(
        f'<div class="legend-item"><img alt="{value}% humidity" src="{image_url(draw_ink("legend",value))}" '
        f'width="{draw_ink("legend",value).width}" height="{draw_ink("legend",value).height}">'
        f'<span>{value}%</span></div>' for value in (60,80,95)
    )
    missing = ", ".join(escape(item["name"]) for item in omitted) or "None"
    m.get_root().header.add_child(Element('''
    <title>A Bit Damp — Hong Kong humidity in ink</title>
    <style>
    :root { --ink:#163248; --muted:#607888; --paper:#f7f8f6; }
    body { margin:0; background:var(--paper); color:var(--ink); font:14px/1.55 Arial,sans-serif; }
    .folium-map { position:absolute!important; left:302px!important; top:110px!important;
      width:calc(100% - 326px)!important; height:calc(100% - 134px)!important;
      border:1px solid #d8e0e3; border-radius:6px; background:#e4eaed; }
    .page-header { position:absolute; left:30px; right:30px; top:16px; height:78px;
      display:flex; justify-content:space-between; align-items:center; gap:20px; }
    .page-header h1 { margin:0; font:38px/1.15 Georgia,serif; letter-spacing:-1px; }
    .eyebrow { font-size:10px; letter-spacing:2px; color:var(--muted); margin-top:8px; }
    .date { text-align:right; font:20px Georgia,serif; }
    .date p { font:13px Arial,sans-serif; color:var(--muted); margin:8px 0 0; }
    .sidebar { position:absolute; left:30px; top:126px; bottom:22px; width:242px; overflow:auto; }
    .sidebar h2 { font:24px/1.25 Georgia,serif; margin:0 0 17px; }
    .sidebar p { color:var(--muted); margin:0 0 20px; }
    .legend { margin:22px 0; border-top:1px solid #d5dee2; border-bottom:1px solid #d5dee2; padding:16px 0; }
    .legend-item { display:flex; align-items:center; height:83px; gap:20px; font:23px Georgia,serif; }
    .legend-item img { object-fit:contain; width:100px; height:100px; }
    .legend-item:first-child img { width:46px; height:46px; margin:0 27px; }
    .legend-item:nth-child(2) img { width:77px; height:77px; margin:0 11.5px; }
    .stats { font:24px Georgia,serif; margin:17px 0 5px; }
    .sidebar details { font-size:12px; color:var(--muted); margin-top:24px; }
    .sidebar summary { cursor:pointer; color:var(--ink); }
    .sidebar a { color:var(--ink); text-decoration:underline; }
    .sidebar .hint { font-size:12px; }
    .leaflet-control-timecontrol { background:#fff; color:var(--ink); border-radius:4px; }
    .leaflet-control-layers { font-family:Arial,sans-serif; }
    .station-popup { min-width:175px; color:var(--ink); }
    .station-popup small { font-size:10px; letter-spacing:1px; }
    .station-popup h3 { margin:8px 0; font:20px Georgia,serif; }
    .station-popup strong { font:36px Georgia,serif; }
    .station-popup p { margin:8px 0!important; line-height:1.6; }
    .leaflet-marker-icon:focus { outline:2px solid #557e98; outline-offset:2px; }
    @media(max-width:700px) {
      .page-header { left:18px; right:18px; top:12px; height:68px; }
      .page-header h1 { font-size:28px; } .eyebrow { font-size:8px; letter-spacing:1px; }
      .date { font-size:15px; } .date p { font-size:11px; }
      .folium-map { left:12px!important; top:166px!important; width:calc(100% - 24px)!important;
        height:calc(100% - 180px)!important; min-height:290px; }
      .sidebar { left:18px; right:18px; top:94px; width:auto; bottom:auto; height:65px; overflow:hidden; }
      .sidebar h2,.sidebar>p,.sidebar details { display:none; }
      .legend { display:flex; align-items:center; gap:6px; margin:0; padding:0; border:0; }
      .legend-item { height:60px; font:14px Georgia,serif; gap:0; }
      .legend-item img { max-width:48px; max-height:48px; margin:0!important; }
      .stats { position:absolute; right:0; top:1px; font-size:16px; margin:0; }
      #range-label { position:absolute; right:0; top:26px; font-size:11px; }
      .legend-title { display:none; }
      .leaflet-control-timecontrol.timecontrol-slider { max-width:105px; }
    }
    </style>'''))
    m.get_root().html.add_child(Element(f'''
    <header class="page-header"><div><h1>A Bit Damp</h1>
      <div class="eyebrow">HONG KONG / RELATIVE HUMIDITY IN INK</div></div>
      <div class="date">25 September 2026<p id="forecast-clock">FORECAST · 00:00 HKT</p></div></header>
    <aside class="sidebar"><h2>A day in the air.</h2>
      <p>Watch humidity move through the day.<br>Darker ink. Wider diffusion.</p>
      <div class="legend-title eyebrow">RELATIVE HUMIDITY</div><div class="legend">{legend}</div>
      <div class="stats">{len(stations)} stations</div><p id="range-label"></p>
      <p class="hint">Click an ink spot for its forecast.<br>Play or scrub through 12 time points.</p>
      <details><summary>About this forecast</summary><p>Forecast snapshot saved on 17 Sep 2026,
      for 25 Sep 2026. Times are Hong Kong time (UTC+8).</p>
      <p>Source: <a href="https://www.hko.gov.hk/sc/wxinfo/awsgis/regional_portal.html?ele=rh"
      target="_blank" rel="noopener">Hong Kong Observatory</a>.</p>
      <p>Missing humidity: {missing}. These stations are omitted, not assigned zero.</p>
      <p>Ink size and darkness use a fixed 50–100% display scale. The ink footprint is symbolic;
      it does not describe the area influenced by a station. Overlapping spots may look darker.</p>
      <p>Each step is a forecast two hours later. Replay repeats the same day. Shapes are fixed
      per station; no intermediate humidity values are invented.</p></details>
    </aside>'''))

    # Folium's default date control uses UTC. Always display UTC+8 here, even
    # when the reader's browser is in another timezone.
    stats = {timestamp(h): [min(s["values"][i] for s in stations),
                            max(s["values"][i] for s in stations)] for i,h in enumerate(HOURS)}
    behavior = MacroElement()
    behavior._template = Template('''{% macro script(this, kwargs) %}
    (function () {
      const map = {{this._parent.get_name()}};
      const ranges = {{this.ranges | safe}};
      const byTime = Object.fromEntries(Object.entries(ranges).map(([k,v]) => [Date.parse(k),v]));
      function hkt(ms) { return new Date(ms+8*3600000).toISOString().slice(11,16); }
      timeDimensionControl._getDisplayDateFormat = function(date) {
        return '25 Sep · ' + hkt(date.getTime()) + ' HKT';
      };
      function update() {
        const t = map.timeDimension.getCurrentTime();
        document.getElementById('forecast-clock').textContent = 'FORECAST · ' + hkt(t) + ' HKT';
        const range = byTime[t];
        if (range) document.getElementById('range-label').textContent =
          range[0].toFixed(1) + '% – ' + range[1].toFixed(1) + '% across stations';
      }
      map.timeDimension.on('timeload', update);
      timeDimensionControl._update();
      update();
    })();
    {% endmacro %}''')
    behavior.ranges = json.dumps(stats)
    m.add_child(behavior)


def main():
    stations, omitted = load_data()
    report(stations,omitted)
    basemap = load_basemap()
    m = folium.Map(location=[22.35,114.12], zoom_start=11, tiles=None,
                   control_scale=True, min_zoom=9, max_zoom=16, prefer_canvas=True,
                   zoom_snap=0.1)
    x0,y0,x1,y1 = map_extent()
    west,north = pixel_lnglat(x0,y0)
    east,south = pixel_lnglat(x1,y1)
    bounds = [[south,west],[north,east]]
    folium.raster_layers.ImageOverlay(image=image_url(basemap), bounds=bounds,
        name="Saved light-grey map", attr=MAP_CREDIT, overlay=False, show=True).add_to(m)
    folium.TileLayer(tiles=TILES, attr=MAP_CREDIT, name="Detailed map (online)",
                     overlay=False, show=False, max_zoom=16).add_to(m)
    m.fit_bounds(bounds)
    m.get_root().html.add_child(Element(
        '<div style="position:fixed;right:30px;bottom:2px;font:10px Arial;color:#607888;z-index:1000">'
        + MAP_CREDIT + '</div>'))
    features = []
    for index in range(len(HOURS)):
        for station in stations:
            features.append(feature(station,index))
    TimestampedGeoJson({"type":"FeatureCollection", "features":features},
        period="PT2H", duration="PT119M", transition_time=FRAME_MS,
        auto_play=False, loop=True, loop_button=True, add_last_point=False,
        time_slider_drag_update=True, date_options="DD MMM HH:mm",
        speed_slider=False).add_to(m)
    folium.LayerControl(collapsed=True).add_to(m)
    add_layout(m,stations,omitted)
    site = HERE / "site"
    site.mkdir(exist_ok=True)
    m.save(site / "index.html")
    print(f"Saved site/index.html: {len(features)} station/time points; all forecast data embedded.")


if __name__ == "__main__":
    main()
