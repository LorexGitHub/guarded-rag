import { useState } from "react";
import { scenarios } from "../fixtures";
import { FilePick, Marked, StatusIcon, useRag } from "../shared";
import { MIN_SCORE } from "../types";
import "./C.css";

type Stage = "question" | "retrieve" | "threshold" | "generate" | "answer";

// Variant C: Blueprint-style pipeline. The guardrail is a diagram; click a stage to inspect it.
export function VariantC() {
  const { id, setId, scenario, res, busy, ask, docs, upload, error } = useRag();
  const [stage, setStage] = useState<Stage>("threshold");
  const [showDocs, setShowDocs] = useState(false);
  const t = res?.trace;
  const passed = t?.hits.filter((h) => h.passed).length ?? 0;
  const nodes: { k: Stage; name: string; stat: string; dim?: boolean }[] = [
    { k: "question", name: "Scan question", stat: t ? `${t.findings_in.length} found` : "-" },
    { k: "retrieve", name: "Retrieve", stat: t ? `${t.hits.length} chunks` : "-" },
    { k: "threshold", name: `Score ≥ ${MIN_SCORE.toFixed(2)}`, stat: t ? `${passed} kept` : "-" },
    { k: "generate", name: "Generate", stat: res ? (res.refused ? "skipped" : "called") : "-", dim: res?.refused },
    { k: "answer", name: "Scan answer", stat: t ? `${t.findings_out.length} found` : "-" },
  ];

  return (
    <div className="vC">
      <header className="vC-top">
        <b>Guarded RAG</b>
        <button className="vC-btn" onClick={() => setShowDocs((s) => !s)} aria-expanded={showDocs}>Documents ({docs.length})</button>
      </header>

      {showDocs && (
        <div className="vC-docs" role="region" aria-label="Documents">
          <ul>{docs.map((d) => <li key={d.doc_id} className={`is-${d.status}`}><StatusIcon status={d.status} />{d.filename}<small>{d.status === "ready" ? `${d.chunks} chunks` : d.status === "pending" ? "ingesting" : "failed"}</small></li>)}</ul>
          <FilePick onFile={upload} className="vC-btn">Upload .txt or .md</FilePick>
          {error && <p className="vC-err" role="alert">{error}</p>}
        </div>
      )}

      <main className="vC-main">
        <form className="vC-ask" onSubmit={(e) => { e.preventDefault(); ask(); }}>
          <label htmlFor="vCq" className="vC-lab">Question</label>
          <input id="vCq" value={scenario.question} readOnly />
          <div className="vC-pick" role="radiogroup" aria-label="Fixture">
            {scenarios.map((s) => <button type="button" key={s.id} role="radio" aria-checked={id === s.id} onClick={() => setId(s.id)}>{s.label}</button>)}
          </div>
          <button className="vC-btn vC-go" disabled={busy} aria-busy={busy}>{busy ? "Asking" : "Ask"}</button>
        </form>

        <ol className="vC-pipe" aria-label="Pipeline">
          {nodes.map((n, i) => (
            <li key={n.k}>
              <button className={`vC-node${stage === n.k ? " on" : ""}${n.dim ? " dim" : ""}`} aria-pressed={stage === n.k} onClick={() => setStage(n.k)}>
                <span className="vC-name">{n.name}</span><span className="vC-stat">{n.stat}</span>
              </button>
              {i < nodes.length - 1 && <span className={`vC-link${n.dim || nodes[i + 1].dim ? " dim" : ""}`} aria-hidden />}
            </li>
          ))}
        </ol>

        <div className="vC-lower">
          <section className="vC-inspect" aria-label="Stage detail">
            {!res && <p className="vC-empty">Ask a question, then pick a stage to inspect it.</p>}
            {res && stage === "question" && <Findings title="Found in the question" items={t!.findings_in} />}
            {res && stage === "answer" && <Findings title="Found in the answer" items={t!.findings_out} />}
            {res && stage === "generate" && (
              <>
                <h2>Generate</h2>
                <p>{res.refused ? "Skipped. Nothing reached the threshold, so the model was never called and the fixed refusal was returned." : "Called with the chunks that reached the threshold."}</p>
              </>
            )}
            {res && stage === "retrieve" && (
              <>
                <h2>Top {t!.hits.length} chunks</h2>
                <ul className="vC-hits">{t!.hits.map((h) => <li key={h.doc_id + h.chunk_index} className={h.passed ? "pass" : ""}><span className="vC-id">{h.source} #{h.chunk_index}</span><span><Marked text={h.text} /></span></li>)}</ul>
              </>
            )}
            {res && stage === "threshold" && (
              <>
                <h2>Scores against {MIN_SCORE.toFixed(2)}</h2>
                <div className="vC-plot" role="img" aria-label="Score dot plot">
                  <div className="vC-axis" style={{ left: `${MIN_SCORE * 100}%` }}><span>{MIN_SCORE.toFixed(2)}</span></div>
                  {t!.hits.map((h, i) => <span key={i} className={`vC-dot${h.passed ? " pass" : ""}`} style={{ left: `${h.score * 100}%`, top: `${12 + i * 22}px` }} title={`${h.source} #${h.chunk_index}: ${h.score}`}><em>{h.score.toFixed(2)}</em></span>)}
                </div>
                <ul className="vC-hits">{t!.hits.map((h) => <li key={h.doc_id + h.chunk_index} className={h.passed ? "pass" : ""}><span className="vC-id">{h.score.toFixed(2)}</span><span>{h.source} #{h.chunk_index}, {h.passed ? "kept" : "dropped"}</span></li>)}</ul>
              </>
            )}
          </section>

          <section className={`vC-out${res?.refused ? " refused" : ""}`} aria-live="polite" aria-label="Answer">
            {!res ? <p className="vC-empty">The answer appears here.</p> : (
              <>
                <h2>{res.refused ? "Refused" : "Answer"}</h2>
                <p className="vC-ans"><Marked text={res.answer} /></p>
                {res.sources.length > 0 && <ul className="vC-srcs">{res.sources.map((s) => <li key={s.doc_id + s.chunk_index}>{s.source}<small>chunk {s.chunk_index}</small></li>)}</ul>}
              </>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}

function Findings({ title, items }: { title: string; items: { entity_type: string; placeholder: string }[] }) {
  return (
    <>
      <h2>{title}</h2>
      {items.length === 0 ? <p>None found.</p> : <ul className="vC-find">{items.map((f) => <li key={f.placeholder}><mark>{f.placeholder}</mark><span>{f.entity_type}</span></li>)}</ul>}
    </>
  );
}
