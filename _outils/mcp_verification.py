"""Phase « Check » avec Craft Anything : capture de l'application reconstruite."""
import json, os, subprocess, sys, time, urllib.request

ROOT = r"D:/IA/ReconstitutionPaleoTerre/_outils"
CLI = r"C:/Users/brice/AppData/Local/Temp/kilo/craft-anything-target/release/craft-anything-cli.exe"
PROJECT = ROOT + "/verification-cany"
CAPTURE = ROOT + "/capture-reconstitution"
URL = "http://127.0.0.1:8765/index.html#460"

# Craft Anything n'accepte que http/https : serveur loopback temporaire, sans accès réseau externe.
serveur = subprocess.Popen(
    [sys.executable, "-m", "http.server", "8765", "--bind", "127.0.0.1",
     "--directory", r"D:/IA/ReconstitutionPaleoTerre"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)
for _ in range(40):
    try:
        urllib.request.urlopen("http://127.0.0.1:8765/index.html", timeout=1).read(64)
        break
    except Exception:
        time.sleep(.15)

proc = subprocess.Popen(
    [CLI, "--deep", "--allow-run", "--project", PROJECT, "mcp"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True, encoding="utf-8", errors="replace", bufsize=1,
)
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
            raise RuntimeError("serveur MCP fermé")
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if data.get("id") == rid:
            return data


def call(name, args):
    r = send("tools/call", {"name": name, "arguments": args})
    if "error" in r:
        return {"_error": r["error"]}
    res = r.get("result", {})
    raw = "\n".join(c.get("text", "") for c in res.get("content", []) if c.get("type") == "text")
    try:
        return json.loads(raw)
    except Exception:
        return {"_text": raw}


out = {}
send("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                    "clientInfo": {"name": "linne-check", "version": "1.0"}})
send("notifications/initialized", {}, notify=True)

sch = send("tools/list", {}).get("result", {}).get("tools", [])
out["schemas"] = {t["name"]: t.get("inputSchema", {}) for t in sch
                  if t["name"] in ("web_site_open", "web_site_capture", "web_pixels_compare", "web_browser_connect")}

out["open"] = call("web_site_open", {
    "url": URL, "width": 1440, "height": 900, "settle_ms": 3500, "headless": True,
})
if os.path.isdir(CAPTURE):
    out["capture"] = {"_skipped": "dossier déjà présent"}
else:
    out["capture"] = call("web_site_capture", {
        "output_directory": CAPTURE, "widths": [1440, 900, 390],
        "include_html": True, "timeout_secs": 120,
    })
out["close"] = call("web_site_close", {})

with open(ROOT + "/verification_mcp.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

try:
    proc.stdin.close()
    proc.terminate()
except Exception:
    pass
serveur.terminate()

for k in ("open", "capture", "close"):
    v = out.get(k, {})
    print(k, "->", str(v.get("status", v.get("summary", v.get("_error", v.get("_text", "ok")))))[:300])
print("Schémas :", json.dumps(out["schemas"], ensure_ascii=False)[:1200])
print("Résultats :", ROOT + "/verification_mcp.json")
