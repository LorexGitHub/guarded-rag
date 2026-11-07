import json, os, socket, urllib.request


def _get(url):
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return {"status": r.status, "body": r.read(300).decode("utf-8", "replace")}
    except Exception as e:
        return {"error": repr(e)}


def handler(event, context):
    ollama = os.environ.get("OLLAMA_URL", "http://ollama:11434")
    opensearch = os.environ.get("OPENSEARCH_URL", "")
    host = ollama.split("//")[1].split(":")[0]
    try:
        resolved = socket.gethostbyname(host)
    except Exception as e:
        resolved = repr(e)
    out = {
        "event": event,
        "ollama_host_resolves_to": resolved,
        "ollama": _get(ollama + "/api/tags"),
        "opensearch": _get(opensearch) if opensearch else "OPENSEARCH_URL unset",
    }
    print("PROBE " + json.dumps(out))
    return out
