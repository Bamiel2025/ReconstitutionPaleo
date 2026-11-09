"""Client MCP minimal pour piloter Craft Anything en une seule session navigateur.

Écrit les réponses dans _outils/etude_resultats.json et les captures PNG à côté.
"""
import json, os, subprocess, sys, base64, time

ROOT = r"D:/IA/ReconstitutionPaleoTerre/_outils"
CLI = r"C:/Users/brice/AppData/Local/Temp/kilo/craft-anything-target/release/craft-anything-cli.exe"
PROJECT = ROOT + "/etude.cany"
CAPTURE = ROOT + "/capture-original"

proc = subprocess.Popen(
    [CLI, "--allow-run", "--project", PROJECT, "mcp"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True, encoding="utf-8", errors="replace", bufsize=1,
)
pending = {}
counter = [0]


def send(method, params=None, notify=False):
    counter[0] += 1
    rid = counter[0]
    msg = {"jsonrpc": "2.0", "method": method, "params": params or {}}
    if not notify:
        msg["id"] = rid
    proc.stdin.write(json.dumps(msg, ensure_ascii=False) + "\n")
    proc.stdin.flush()
    if notify:
        return None
    while True:
        line = proc.stdout.readline()
        if not line:
            raise RuntimeError("serveur MCP fermé: " + proc.stderr.read()[-2000:])
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if data.get("id") == rid:
            return data
        pending[data.get("id")] = data


def call(name, args):
    r = send("tools/call", {"name": name, "arguments": args})
    if "error" in r:
        return {"_error": r["error"]}
    res = r.get("result", {})
    texts = [c.get("text", "") for c in res.get("content", []) if c.get("type") == "text"]
    raw = "\n".join(texts)
    try:
        return json.loads(raw)
    except Exception:
        return {"_text": raw}


results = {}
init = send("initialize", {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {"name": "linne-study", "version": "1.0"},
})
results["initialize"] = init
send("notifications/initialized", {}, notify=True)

tools = send("tools/list", {})
names = [t["name"] for t in tools.get("result", {}).get("tools", [])]
results["tools_web"] = [n for n in names if n.startswith("web_")]

# 1. Ouverture du site (hash 460 = Ordovicien moyen)
results["open"] = call("web_site_open", {
    "url": "https://dinosaurpictures.org/ancient-earth#460",
    "width": 1440, "height": 900, "settle_ms": 4000, "headless": True,
})

# 2. Observation passive du DOM et des ressources
results["page_show"] = call("web_page_show", {
    "watch_ms": 1500,
    "with_accessibility_text": True,
    "with_body_outlines": True,
})

# 3. Capture complète (3 largeurs)
if not os.path.exists(CAPTURE):
    results["capture"] = call("web_site_capture", {
        "output_directory": CAPTURE,
        "widths": [1440, 900, 390],
        "include_html": True,
        "timeout_secs": 120,
    })
else:
    results["capture"] = {"_skipped": "dossier déjà présent"}

# 4. Parcours scripté : réglages ouverts, navigation temporelle, recherche
walk = {
    "environment": {"width": 1440, "height": 900, "locale": "fr-FR", "timezone": "Europe/Paris", "color_scheme": "dark"},
    "launch": True,
    "headless": True,
    "screenshot_each_step": False,
    "capture_network": True,
    "capture": {"at_end": ["screenshot", "accessibility", "dom"]},
    "actions": [
        {"type": "goto", "url": "https://dinosaurpictures.org/ancient-earth#460"},
        {"type": "wait", "ms": 3500},
        {"step_id": "settings", "type": "click", "selector": "#settings-toggle"},
        {"type": "wait", "ms": 500},
        {"step_id": "periode", "type": "press", "key": "ArrowRight"},
        {"type": "wait", "ms": 600},
    ],
}
results["walkthrough"] = call("web_walkthrough_record", walk)

results["close"] = call("web_site_close", {})

with open(ROOT + "/etude_resultats.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

# Extraire les captures PNG renvoyées en base64 par le walkthrough
try:
    blob = json.dumps(results.get("walkthrough", {}))
    print("walkthrough bytes:", len(blob))
except Exception:
    pass

try:
    proc.stdin.close()
    proc.terminate()
except Exception:
    pass

print("MCP OK — outils web:", len(results["tools_web"]))
for k, v in results.items():
    if isinstance(v, dict):
        print(k, "->", str(v.get("summary", v.get("_error", v.get("_text", "ok"))))[:220])
print("Résultats:", ROOT + "/etude_resultats.json")
