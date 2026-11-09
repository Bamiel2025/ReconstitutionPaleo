"""Étude Deep (privée) : états d'interface du site via le navigateur de Craft Anything."""
import json, subprocess, os, base64

ROOT = r"D:/IA/ReconstitutionPaleoTerre/_outils"
CLI = r"C:/Users/brice/AppData/Local/Temp/kilo/craft-anything-target/release/craft-anything-cli.exe"
proc = subprocess.Popen(
    [CLI, "--deep", "--allow-run", "--project", ROOT + "/etude-deep.cany", "mcp"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True, encoding="utf-8", errors="replace", bufsize=1,
)
rid = [0]


def send(method, params=None, notify=False):
    rid[0] += 1
    n = rid[0]
    msg = {"jsonrpc": "2.0", "method": method, "params": params or {}}
    if not notify:
        msg["id"] = n
    proc.stdin.write(json.dumps(msg, ensure_ascii=False) + "\n")
    proc.stdin.flush()
    if notify:
        return None
    while True:
        line = proc.stdout.readline()
        if not line:
            raise RuntimeError("MCP fermé: " + proc.stderr.read()[-1500:])
        try:
            d = json.loads(line.strip())
        except Exception:
            continue
        if d.get("id") == n:
            return d


def call(name, args):
    r = send("tools/call", {"name": name, "arguments": args})
    if "error" in r:
        return {"_error": r["error"]}
    txt = "\n".join(c.get("text", "") for c in r.get("result", {}).get("content", []) if c.get("type") == "text")
    try:
        return json.loads(txt)
    except Exception:
        return {"_text": txt[:4000]}


out = {}
send("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                    "clientInfo": {"name": "linne-deep", "version": "1.0"}})
send("notifications/initialized", {}, notify=True)

out["open"] = call("web_site_open", {
    "url": "https://dinosaurpictures.org/ancient-earth#460",
    "width": 1440, "height": 900, "settle_ms": 3500, "headless": True})

out["page_show"] = call("web_page_show", {
    "watch_ms": 1200, "with_accessibility_text": True, "with_body_outlines": True,
    "with_script_text": False})

out["walkthrough"] = call("web_walkthrough_record", {
    "launch": True, "headless": True, "screenshot_each_step": True,
    "environment": {"width": 1440, "height": 900, "locale": "en-US", "timezone": "UTC", "color_scheme": "dark"},
    "capture_network": True,
    "capture": {"at_end": ["screenshot", "accessibility", "dom"]},
    "actions": [
        {"kind": "goto", "url": "https://dinosaurpictures.org/ancient-earth#460", "wait_ms": 3000},
        {"step_id": "reglages", "kind": "click", "selector": "#settings-toggle"},
        {"kind": "wait", "ms": 400},
        {"step_id": "navigation", "kind": "press", "selector": "body", "key": "ArrowLeft"},
        {"kind": "wait", "ms": 900},
    ],
})

# Sauvegarde des images base64 éventuellement renvoyées
blob = json.dumps(out)
import re
imgs = re.findall(r'"(?:data|image|png|screenshot)"\s*:\s*"([A-Za-z0-9+/=]{500,})"', blob)
for i, b in enumerate(imgs[:6]):
    try:
        raw = base64.b64decode(b)
        with open(ROOT + f"/etat_{i}.png", "wb") as f:
            f.write(raw)
    except Exception:
        pass

with open(ROOT + "/etude_deep.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

for k, v in out.items():
    print(k, "->", str(v.get("summary", v.get("_error", "ok")))[:260])
print("images extraites:", len(imgs), "taille json:", len(blob))
proc.stdin.close()
proc.terminate()
