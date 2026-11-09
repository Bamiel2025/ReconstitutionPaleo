"""Comparaison chiffrée original / reconstitution via Craft Anything."""
import json, os, subprocess

ROOT = r"D:/IA/ReconstitutionPaleoTerre/_outils"
CLI = r"C:/Users/brice/AppData/Local/Temp/kilo/craft-anything-target/release/craft-anything-cli.exe"
PROJECT = ROOT + "/verification-cany"
ORIGINAL = ROOT + "/capture-original"
REBUILD = ROOT + "/capture-reconstitution"

proc = subprocess.Popen(
    [CLI, "--deep", "--allow-run", "--project", PROJECT, "mcp"],
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
        line = proc.stdout.readline().strip()
        if not line:
            raise RuntimeError("MCP fermé")
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if data.get("id") == n:
            return data


def call(name, args):
    r = send("tools/call", {"name": name, "arguments": args})
    if "error" in r:
        return {"_error": r["error"]}
    raw = "\n".join(c.get("text", "") for c in r.get("result", {}).get("content", []) if c.get("type") == "text")
    try:
        return json.loads(raw)
    except Exception:
        return {"_text": raw}


send("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                    "clientInfo": {"name": "linne-compare", "version": "1.0"}})
send("notifications/initialized", {}, notify=True)

out = {}
for largeur in (1440, 900, 390):
    avant = os.path.join(ORIGINAL, "screenshot-%d.png" % largeur).replace("\\", "/")
    apres = os.path.join(REBUILD, "screenshot-%d.png" % largeur).replace("\\", "/")
    out[str(largeur)] = call("web_pixels_compare", {
        "before": {"path": avant},
        "after": {"path": apres},
        "tolerance": 24,
        "common_area": True,
    })

with open(ROOT + "/comparaison_mcp.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

try:
    proc.stdin.close()
    proc.terminate()
except Exception:
    pass

for k, v in out.items():
    if "result" in v:
        r = v["result"]
        print(k, "px ->", json.dumps({a: r.get(a) for a in
              ("comparable", "layout_similarity", "perceptual_similarity", "difference_fraction",
               "changed_bounding_box", "width", "height")}, ensure_ascii=False))
    else:
        print(k, "px ->", json.dumps(v, ensure_ascii=False)[:500])
