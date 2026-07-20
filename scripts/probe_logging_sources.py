#!/usr/bin/env python3
"""Quick probe for logging concession data sources."""
import requests

base = "http://gis-gfw.wri.org/arcgis/rest/services/land_use/MapServer/3/query"
queries = [
    "country='Brazil'",
    "group_coun='Brazil'",
    "province LIKE '%Par%'",
]
for where in queries:
    url = f"{base}?where={requests.utils.quote(where)}&returnCountOnly=true&f=json"
    r = requests.get(url, timeout=60)
    print(where, "->", r.status_code, r.text.strip())
