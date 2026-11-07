import { Fragment, useEffect, useRef, useState } from "react";
import { Marked, StatusIcon } from "./shared";
import { VariantB } from "./variants/B";
import { VariantC } from "./variants/C";
import { PrototypeSwitcher, useVariant } from "./switcher";
import { initialDocs, scenarios } from "./fixtures";
import type { Doc, Finding, Hit, QueryResponse } from "./types";
import { MIN_SCORE } from "./types";

function Ask({ onAsk, busy }: { onAsk: (id: string) => void; busy: boolean }) {
  const [id, setId] = useState(new URLSearchParams(location.search).get("fx") ?? scenarios[0].id);
  const sc = scenarios.find((s) => s.id === id)!;
  return (
    <form className="ask cut" onSubmit={(e) => { e.preventDefault(); onAsk(id); }}>
      <label htmlFor="q" className="label">Question</label>
      <textarea id="q" rows={3} value={sc.question} readOnly />
      <div className="ask-row">
        <fieldset className="seg">
          <legend>Fixture</legend>
          {scenarios.map((s) => (
            <Fragment key={s.id}>
              <input type="radio" name="fx" id={`fx-${s.id}`} checked={id === s.id} onChange={() => setId(s.id)} />
              <label htmlFor={`fx-${s.id}`}>{s.label}</label>
            </Fragment>
          ))}
        </fieldset>
        <button className="key key--primary" type="submit" aria-busy={busy} disabled={busy}>
          {busy ? "Asking" : "Ask"}
        </button>
      </div>
    </form>
  );
}

function Answer({ res }: { res: QueryResponse }) {
  return (
    <section className={`answer cut${res.refused ? " is-refused" : ""}`} aria-live="polite">
      <h2 className="label">{res.refused ? "Refused" : "Answer"}</h2>
      {res.refused ? (
        <div className="refusal">
          <StatusIcon status="refused" />
          <div>
            <p className="answer-text">{res.answer}</p>
            <p className="muted">No chunk scored at or above {MIN_SCORE.toFixed(2)}, so the model was never called.</p>
          </div>
        </div>
      ) : (
        <p className="answer-text"><Marked text={res.answer} /></p>
      )}
      {res.sources.length > 0 && (
        <>
          <h3 className="label">Sources</h3>
          <ul className="sources">
            {res.sources.map((s) => (
              <li key={`${s.doc_id}-${s.chunk_index}`}>
                <span className="src-name">{s.source}</span>
                <span className="mono">chunk {s.chunk_index}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

function FindingList({ title, items }: { title: string; items: Finding[] }) {
  return (
    <div className="findings">
      <h4>{title}</h4>
      {items.length === 0 ? (
        <p className="g-muted">None found</p>
      ) : (
        <ul>
          {items.map((f) => (
            <li key={f.placeholder}><mark>{f.placeholder}</mark><span className="g-muted">{f.entity_type}</span></li>
          ))}
        </ul>
      )}
    </div>
  );
}

function HitRow({ h }: { h: Hit }) {
  return (
    <li className={h.passed ? "hit is-pass" : "hit is-fail"}>
      <div className="hit-head">
        <span className="mono">{h.source} #{h.chunk_index}</span>
        <span className="hit-verdict">{h.passed ? "passed" : "below threshold"}</span>
      </div>
      <div className="meter" role="img" aria-label={`Score ${h.score}, threshold ${MIN_SCORE}`}>
        <span className="meter-fill" style={{ width: `${h.score * 100}%` }} />
        <span className="meter-tick" style={{ left: `${MIN_SCORE * 100}%` }} />
        <span className="meter-num mono">{h.score.toFixed(2)}</span>
      </div>
      <p className="hit-text"><Marked text={h.text} /></p>
    </li>
  );
}

function Trace({ res }: { res: QueryResponse | null }) {
  return (
    <aside className="trace graphite" aria-label="Guardrail trace">
      <header>
        <h2>Guardrail trace</h2>
        <p className="g-muted">Threshold <span className="mono">{MIN_SCORE.toFixed(2)}</span>, top 5 chunks</p>
      </header>
      {!res ? (
        <p className="g-muted trace-empty">Ask a question to see what the guardrail did with it.</p>
      ) : (
        <>
          <section>
            <h3>Retrieved chunks</h3>
            <ul className="hits">{res.trace.hits.map((h) => <HitRow key={`${h.doc_id}-${h.chunk_index}`} h={h} />)}</ul>
          </section>
          <section className="findings-pair">
            <FindingList title="In the question" items={res.trace.findings_in} />
            <FindingList title="In the answer" items={res.trace.findings_out} />
          </section>
        </>
      )}
    </aside>
  );
}

function Documents() {
  const [docs, setDocs] = useState<Doc[]>(() =>
    new URLSearchParams(location.search).has("states")
      ? [
          { doc_id: "q3-report-md", filename: "q3-report.md", status: "pending", chunks: null },
          { doc_id: "bad-notes-txt", filename: "bad-notes.txt", status: "failed", chunks: null },
          ...initialDocs.slice(0, 2),
        ]
      : initialDocs);
  const [error, setError] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const timers = useRef<number[]>([]);
  useEffect(() => () => timers.current.forEach(clearTimeout), []);

  function upload(file: File) {
    if (!/\.(txt|md)$/i.test(file.name)) { setError("Only .txt and .md files are accepted."); return; }
    setError(null);
    const doc_id = file.name.replace(/[^a-z0-9]+/gi, "-").toLowerCase();
    const next: Doc = { doc_id, filename: file.name, status: "pending", chunks: null };
    setDocs((d) => [next, ...d.filter((x) => x.doc_id !== doc_id)]);
    const failed = /bad/i.test(file.name);
    timers.current.push(window.setTimeout(() => {
      setDocs((d) => d.map((x) => x.doc_id === doc_id ? { ...x, status: failed ? "failed" : "ready", chunks: failed ? null : 9 } : x));
    }, 2200));
  }

  return (
    <section className="docs" aria-label="Documents">
      <h2 className="label">Documents</h2>
      <div className="drop cut" onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) upload(f); }}>
        <p>Drop a .txt or .md file</p>
        <button className="key" type="button" onClick={() => input.current?.click()}>Choose file</button>
        <input ref={input} type="file" accept=".txt,.md" hidden onChange={(e) => { const f = e.target.files?.[0]; if (f) upload(f); e.target.value = ""; }} />
      </div>
      {error && <p className="err" role="alert">{error}</p>}
      <ul className="doclist">
        {docs.map((d) => (
          <li key={d.doc_id} className={`doc is-${d.status}`}>
            <span className="doc-name">{d.filename}</span>
            <span className="doc-status">
              <StatusIcon status={d.status} />
              {d.status === "ready" ? `${d.chunks} chunks` : d.status === "pending" ? "Ingesting" : "Failed"}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function VariantA() {
  const [res, setRes] = useState<QueryResponse | null>(null);
  const [busy, setBusy] = useState(false);
  function ask(id: string) {
    setBusy(true);
    window.setTimeout(() => { setRes(scenarios.find((s) => s.id === id)!.res); setBusy(false); }, 700);
  }
  const first = new URLSearchParams(location.search).get("fx");
  useEffect(() => { if (first) setRes(scenarios.find((s) => s.id === first)?.res ?? null); }, [first]);

  return (
    <>
      <header className="bar">
        <div className="container bar-in"><span className="wordmark">Guarded RAG</span><span className="muted">Prototype, fixture data</span></div>
      </header>
      <main className="container grid">
        <div className="col-main">
          <Ask onAsk={ask} busy={busy} />
          {res ? <Answer res={res} /> : <p className="empty muted">The answer and its cited sources appear here.</p>}
        </div>
        <Trace res={res} />
        <Documents />
      </main>
    </>
  );
}

const variants = [
  { key: "A", name: "Workbench, three columns" },
  { key: "B", name: "Ledger, one column" },
  { key: "C", name: "Pipeline, stage inspector" },
];

export function App() {
  const [v, setV] = useVariant(variants.map((x) => x.key));
  return (
    <>
      {v === "A" && <VariantA />}
      {v === "B" && <VariantB />}
      {v === "C" && <VariantC />}
      <PrototypeSwitcher variants={variants} current={v} onChange={setV} />
    </>
  );
}
