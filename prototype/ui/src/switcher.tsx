import { useCallback, useEffect, useState } from "react";

export function useVariant(keys: string[]) {
  const read = () => { const v = new URLSearchParams(location.search).get("variant"); return v && keys.includes(v) ? v : keys[0]; };
  const [v, setV] = useState(read);
  const set = useCallback((k: string) => {
    const u = new URL(location.href); u.searchParams.set("variant", k); history.replaceState(null, "", u); setV(k);
  }, []);
  return [v, set] as const;
}

export function PrototypeSwitcher({ variants, current, onChange }: { variants: { key: string; name: string }[]; current: string; onChange: (k: string) => void }) {
  const i = variants.findIndex((x) => x.key === current);
  const go = (d: number) => onChange(variants[(i + d + variants.length) % variants.length].key);
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement;
      if (t.closest("input, textarea, [contenteditable]")) return;
      if (e.key === "ArrowLeft") go(-1); if (e.key === "ArrowRight") go(1);
    };
    addEventListener("keydown", h); return () => removeEventListener("keydown", h);
  });
  if (!import.meta.env.DEV) return null;
  return (
    <div className="proto-switch" role="group" aria-label="Prototype variant">
      <button onClick={() => go(-1)} aria-label="Previous variant">←</button>
      <span>{current} ({variants[i].name})</span>
      <button onClick={() => go(1)} aria-label="Next variant">→</button>
    </div>
  );
}
