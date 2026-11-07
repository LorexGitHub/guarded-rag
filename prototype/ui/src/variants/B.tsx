import { Fragment } from "react";
import { scenarios } from "../fixtures";
import { FilePick, Marked, StatusIcon, useRag } from "../shared";
import { MIN_SCORE } from "../types";
import "./B.css";

// Variant B: Wayfind-style ledger. One column, read top to bottom, trace as a table under the answer.
export function VariantB() {
  const { id, setId, scenario, res, busy, ask, docs, upload, error } = useRag();
  const passed = res?.trace.hits.filter((h) => h.passed).length ?? 0;
  return (
    <div className="vB">
      <div className="vB-wrap">
        <header className="vB-top">
          <b>guarded-rag</b>
          <span>{docs.filter((d) => d.status === "ready").length} documents searchable</span>
        </header>

        <section className="vB-docs" aria-label="Documents">
          <ul>
            {docs.map((d) => (
              <li key={d.doc_id} className={`is-${d.status}`}>
                <StatusIcon status={d.status} />
                <span>{d.filename}</span>
                <small>{d.status === "ready" ? `${d.chunks} chunks` : d.status === "pending" ? "ingesting" : "failed"}</small>
              </li>
            ))}
            <li className="vB-add"><FilePick onFile={upload} className="vB-btn">Add .txt or .md</FilePick></li>
          </ul>
          {error && <p className="vB-err" role="alert">{error}</p>}
        </section>

        <form className="vB-ask" onSubmit={(e) => { e.preventDefault(); ask(); }}>
          <label htmlFor="vBq">Ask your documents</label>
          <div className="vB-line"><span aria-hidden>&gt;</span><textarea id="vBq" rows={2} value={scenario.question} readOnly /></div>
          <div className="vB-row">
            <div className="vB-pick" role="radiogroup" aria-label="Fixture">
              {scenarios.map((s) => (
                <Fragment key={s.id}><button type="button" role="radio" aria-checked={id === s.id} onClick={() => setId(s.id)}>{s.label}</button></Fragment>
              ))}
            </div>
            <button className="vB-btn vB-go" disabled={busy} aria-busy={busy}>{busy ? "Asking" : "Ask"}</button>
          </div>
        </form>

        {res && (
          <>
            <section className={`vB-answer${res.refused ? " is-refused" : ""}`} aria-live="polite">
              <h2>{res.refused ? "Refused" : "Answer"}</h2>
              <p><Marked text={res.answer} /></p>
              {res.refused && <p className="vB-note">No chunk reached {MIN_SCORE.toFixed(2)}. The model was not called.</p>}
              {res.sources.length > 0 && (
                <ol className="vB-src">
                  {res.sources.map((s) => <li key={`${s.doc_id}${s.chunk_index}`}>{s.source}, chunk {s.chunk_index}</li>)}
                </ol>
              )}
            </section>

            <section className="vB-trace" aria-label="Guardrail trace">
              <h2>Guardrail trace</h2>
              <ol className="vB-steps">
                <li>
                  <h3>1. Question scanned</h3>
                  <p>{res.trace.findings_in.length ? res.trace.findings_in.map((f) => <mark key={f.placeholder}>{f.placeholder}</mark>) : "No personal data found."}</p>
                </li>
                <li>
                  <h3>2. Retrieved 5 chunks, {passed} reached {MIN_SCORE.toFixed(2)}</h3>
                  <table>
                    <thead><tr><th>Chunk</th><th>Score</th><th /><th>Result</th></tr></thead>
                    <tbody>
                      {res.trace.hits.map((h) => (
                        <tr key={`${h.doc_id}${h.chunk_index}`} className={h.passed ? "pass" : "fail"}>
                          <td>
                            <details><summary>{h.source} #{h.chunk_index}</summary><p><Marked text={h.text} /></p></details>
                          </td>
                          <td className="num">{h.score.toFixed(2)}</td>
                          <td className="bar"><i style={{ width: `${h.score * 100}%` }} /><b style={{ left: `${MIN_SCORE * 100}%` }} /></td>
                          <td>{h.passed ? "kept" : "dropped"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </li>
                <li>
                  <h3>3. Answer scanned</h3>
                  <p>{res.trace.findings_out.length ? res.trace.findings_out.map((f) => <mark key={f.placeholder}>{f.placeholder}</mark>) : "No personal data found."}</p>
                </li>
              </ol>
            </section>
          </>
        )}
      </div>
    </div>
  );
}
