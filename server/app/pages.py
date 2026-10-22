"""Server-rendered HTML: the public live-tracking page and the admin incident dashboard."""

import datetime as dt
from html import escape

LEAFLET = "https://unpkg.com/leaflet@1.9.4/dist"

_BASE_CSS = """
:root { --primary:#D32F2F; --primary-dark:#B71C1C; --bg:#F3F5F9; --card:#FFFFFF; --text:#111827;
        --muted:#4B5563; --border:#E2E8F0; --safe:#2E7D32; }
* { box-sizing:border-box; }
body { margin:0; font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; background:var(--bg); color:var(--text); }
header { background:var(--primary); color:#fff; padding:14px 16px; display:flex; align-items:center; justify-content:space-between; gap:12px; }
header h1 { font-size:18px; margin:0; font-weight:600; }
.pill { font-size:12px; font-weight:600; padding:4px 10px; border-radius:999px; background:rgba(255,255,255,.2); }
a.button { display:inline-block; padding:10px 14px; border-radius:8px; background:var(--primary); color:#fff; text-decoration:none; font-weight:600; font-size:14px; }
a.button.secondary { background:#fff; color:var(--text); border:1px solid var(--border); }
"""


def render_tracking_page(session_id: str) -> str:
    sid = escape(session_id)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Live location · SurakshaX</title>
<link rel="stylesheet" href="{LEAFLET}/leaflet.css">
<style>
{_BASE_CSS}
html, body {{ height:100%; }}
body {{ display:flex; flex-direction:column; }}
#map {{ flex:1; min-height:300px; }}
.panel {{ background:var(--card); border-top:1px solid var(--border); padding:12px 16px; display:grid; gap:10px; }}
.row {{ display:flex; justify-content:space-between; font-size:14px; gap:12px; }}
.row span:first-child {{ color:var(--muted); }}
.actions {{ display:flex; gap:8px; flex-wrap:wrap; }}
.ended {{ background:#FFF3E0; color:#8a4b00; padding:10px 16px; font-size:14px; display:none; }}
</style>
</head>
<body>
<header><h1 id="title">Live location</h1><span class="pill" id="status">Connecting…</span></header>
<div class="ended" id="ended">Location sharing has ended. The last known position is shown.</div>
<div id="map"></div>
<div class="panel">
  <div class="row"><span>Last update</span><span id="updated">–</span></div>
  <div class="row"><span>Accuracy</span><span id="accuracy">–</span></div>
  <div class="row"><span>Battery</span><span id="battery">–</span></div>
  <div class="actions">
    <a class="button" href="tel:112">Call 112</a>
    <a class="button secondary" id="gmaps" href="#" target="_blank" rel="noopener">Open in Google Maps</a>
  </div>
</div>
<script src="{LEAFLET}/leaflet.js"></script>
<script>
const sessionId = "{sid}";
const map = L.map("map").setView([22.97, 78.66], 5);
L.tileLayer("https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png", {{
  maxZoom: 19, attribution: "&copy; OpenStreetMap contributors"
}}).addTo(map);
let marker = null, trail = null, centred = false;

function ago(iso) {{
  if (!iso) return "–";
  const s = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000));
  if (s < 60) return s + " s ago";
  if (s < 3600) return Math.round(s / 60) + " min ago";
  return new Date(iso).toLocaleString();
}}

async function refresh() {{
  try {{
    const res = await fetch("../tracking/" + encodeURIComponent(sessionId), {{ cache: "no-store" }});
    if (res.status === 404) {{
      document.getElementById("status").textContent = "Link not found";
      return;
    }}
    const data = await res.json();
    document.getElementById("title").textContent = (data.user_name || "Live location");
    document.getElementById("status").textContent = data.is_active ? (data.is_emergency ? "SOS active" : "Sharing") : "Ended";
    document.getElementById("ended").style.display = data.is_active ? "none" : "block";
    const loc = data.latest_location;
    if (!loc) {{ document.getElementById("status").textContent = "Waiting for GPS…"; return; }}
    const pos = [loc.latitude, loc.longitude];
    if (!marker) marker = L.marker(pos).addTo(map); else marker.setLatLng(pos);
    const path = (data.location_history || []).map(p => [p.latitude, p.longitude]);
    if (!trail) trail = L.polyline(path, {{ color: "#D32F2F", weight: 4 }}).addTo(map); else trail.setLatLngs(path);
    if (!centred) {{ map.setView(pos, 16); centred = true; }}
    document.getElementById("updated").textContent = ago(loc.updated_at);
    document.getElementById("accuracy").textContent = loc.accuracy_meters ? Math.round(loc.accuracy_meters) + " m" : "–";
    document.getElementById("battery").textContent = loc.battery_level || "–";
    document.getElementById("gmaps").href = "https://www.google.com/maps?q=" + pos[0] + "," + pos[1];
  }} catch (e) {{
    document.getElementById("status").textContent = "Reconnecting…";
  }}
}}
refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>"""


def _fmt_time(value: dt.datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.timezone.utc)
    ist = value.astimezone(dt.timezone(dt.timedelta(hours=5, minutes=30)))
    return ist.strftime("%d %b %Y, %I:%M %p IST")


def render_dashboard(incidents, base_url: str) -> str:
    rows = []
    for inc in incidents:
        station = (inc.nearest_stations or [{}])[0] if inc.nearest_stations else {}
        station_txt = (
            f"{escape(str(station.get('name', '')))} · {station.get('distance_km', '?')} km"
            if station else "None mapped nearby"
        )
        contacts = ", ".join(escape(c.get("name") or c.get("phone", "")) for c in (inc.contacts or [])) or "–"
        rows.append(f"""
<tr>
  <td><strong>{escape(inc.code)}</strong><br><span class="muted">{_fmt_time(inc.created_at)}</span></td>
  <td>{escape(inc.user_name)}<br><span class="muted">{escape(inc.trigger)}</span></td>
  <td>{inc.lat:.5f}, {inc.lon:.5f}</td>
  <td>{station_txt}</td>
  <td>{contacts}</td>
  <td class="actions">
    <a class="button" href="{escape(base_url)}/track/{escape(inc.session_id or '')}" target="_blank" rel="noopener">Live map</a>
    <a class="button secondary" href="https://www.google.com/maps?q={inc.lat},{inc.lon}" target="_blank" rel="noopener">Maps</a>
  </td>
</tr>""")
    body = "".join(rows) or '<tr><td colspan="6" class="empty">No SOS alerts yet.</td></tr>'
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="20">
<title>SOS alerts · SurakshaX</title>
<style>
{_BASE_CSS}
main {{ padding:16px; overflow-x:auto; }}
table {{ width:100%; border-collapse:collapse; background:var(--card); border:1px solid var(--border); border-radius:12px; overflow:hidden; font-size:14px; }}
th, td {{ text-align:left; padding:12px; border-bottom:1px solid var(--border); vertical-align:top; }}
th {{ background:#F8FAFC; font-size:12px; text-transform:uppercase; letter-spacing:.04em; color:var(--muted); }}
.muted {{ color:var(--muted); font-size:12px; }}
.actions {{ white-space:nowrap; }}
.actions a {{ padding:6px 10px; font-size:13px; }}
.empty {{ text-align:center; color:var(--muted); padding:32px; }}
</style>
</head>
<body>
<header><h1>SOS alerts</h1><span class="pill">{len(incidents)} shown</span></header>
<main>
<table>
<thead><tr><th>Alert</th><th>Person</th><th>Location</th><th>Nearest police</th><th>Contacts</th><th></th></tr></thead>
<tbody>{body}</tbody>
</table>
</main>
</body>
</html>"""
