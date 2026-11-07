import { Fragment } from "react";
import type { Doc } from "./types";
const PLACEHOLDER = /(<[A-Z_]+_\d+>)/g;

export function Marked({ text }: { text: string }) {
  return (
    <>
      {text.split(PLACEHOLDER).map((part, i) =>
        i % 2 ? <mark key={i}>{part}</mark> : <Fragment key={i}>{part}</Fragment>,
      )}
    </>
  );
}

export function StatusIcon({ status }: { status: Doc["status"] | "refused" }) {
  const common = { width: 16, height: 16, viewBox: "0 0 16 16", fill: "none", stroke: "currentColor", strokeWidth: 1.6, "aria-hidden": true } as const;
  if (status === "ready") return <svg {...common}><path d="M3 8.5l3.2 3L13 4.5" /></svg>;
  if (status === "failed" || status === "refused") return <svg {...common}><path d="M4 4l8 8M12 4l-8 8" /></svg>;
  return <svg {...common} className="spin"><path d="M8 2a6 6 0 1 0 6 6" /></svg>;
}


import { useEffect, useRef, useState } from "react";
import { initialDocs, scenarios } from "./fixtures";
import type { QueryResponse } from "./types";

export function useRag() {
  const [id, setId] = useState(new URLSearchParams(location.search).get("fx") ?? scenarios[0].id);
  const [res, setRes] = useState<QueryResponse | null>(() => {
    const fx = new URLSearchParams(location.search).get("fx");
    return fx ? scenarios.find((s) => s.id === fx)?.res ?? null : null;
  });
  const [busy, setBusy] = useState(false);
  const [docs, setDocs] = useState<Doc[]>(() =>
    new URLSearchParams(location.search).has("states")
      ? [
          { doc_id: "q3-report-md", filename: "q3-report.md", status: "pending", chunks: null },
          { doc_id: "bad-notes-txt", filename: "bad-notes.txt", status: "failed", chunks: null },
          ...initialDocs.slice(0, 2),
        ]
      : initialDocs);
  const [error, setError] = useState<string | null>(null);
  const timers = useRef<number[]>([]);
  useEffect(() => () => timers.current.forEach(clearTimeout), []);
  const scenario = scenarios.find((s) => s.id === id)!;

  function ask() {
    setBusy(true);
    timers.current.push(window.setTimeout(() => { setRes(scenario.res); setBusy(false); }, 700));
  }
  function upload(file: File) {
    if (!/\.(txt|md)$/i.test(file.name)) { setError("Only .txt and .md files are accepted."); return; }
    setError(null);
    const doc_id = file.name.replace(/[^a-z0-9]+/gi, "-").toLowerCase();
    setDocs((d) => [{ doc_id, filename: file.name, status: "pending", chunks: null }, ...d.filter((x) => x.doc_id !== doc_id)]);
    const failed = /bad/i.test(file.name);
    timers.current.push(window.setTimeout(() => {
      setDocs((d) => d.map((x) => x.doc_id === doc_id ? { ...x, status: failed ? "failed" : "ready", chunks: failed ? null : 9 } : x));
    }, 2200));
  }
  return { id, setId, scenario, res, busy, ask, docs, upload, error };
}

export function FilePick({ onFile, className, children }: { onFile: (f: File) => void; className?: string; children: React.ReactNode }) {
  const input = useRef<HTMLInputElement>(null);
  return (
    <>
      <button type="button" className={className} onClick={() => input.current?.click()}>{children}</button>
      <input ref={input} type="file" accept=".txt,.md" hidden onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); e.target.value = ""; }} />
    </>
  );
}
