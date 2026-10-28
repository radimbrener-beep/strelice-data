"""Zkušební volání lokálního MCP serveru: python mcp-tests/call.py <nástroj> '<json argumenty>'
   (bez argumentů: initialize + tools/list)."""
import json
import sys
import urllib.request

URL = "http://localhost:8790/mcp"


def rpc(method, params=None, id=1):
    body = json.dumps({"jsonrpc": "2.0", "id": id, "method": method, "params": params or {}}).encode()
    req = urllib.request.Request(URL, body, {"Content-Type": "application/json",
                                             "Accept": "application/json, text/event-stream"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        print(json.dumps(rpc("initialize", {"protocolVersion": "2025-06-18", "clientInfo": {"name": "test", "version": "0"},
                                            "capabilities": {}})["result"]["protocolVersion"]))
        for t in rpc("tools/list")["result"]["tools"]:
            print(t["name"], "-", t["title"])
    else:
        r = rpc("tools/call", {"name": sys.argv[1], "arguments": json.loads(sys.argv[2] if len(sys.argv) > 2 else "{}")})
        res = r.get("result") or r
        if res.get("isError"):
            print("CHYBA:", res["content"][0]["text"])
        else:
            out = json.dumps(res.get("structuredContent", res), ensure_ascii=False, indent=1)
            print(out[: int(sys.argv[3]) if len(sys.argv) > 3 else 3000])
