// frontend/src/pages/SignalHistory.tsx
import React, { useEffect, useMemo, useState } from "react";

type ModelSignal = { name: string; signal: number; confidence: number };
type SigmaSignal = {
  timestamp: string;
  symbol: string;
  regime: string;
  score: number | null;
  confidence: number | null;
  models: ModelSignal[] | null;
};

const REST_SIGNALS = "http://localhost:8000/signals";

function toCSV(arr: SigmaSignal[]) {
  const rows = [
    ["timestamp", "symbol", "regime", "score", "confidence", "model_count"].join(","),
    ...arr.map((r) =>
      [
        r.timestamp,
        r.symbol,
        r.regime,
        r.score ?? "",
        r.confidence ?? "",
        r.models?.length ?? 0,
      ].join(",")
    ),
  ];
  return rows.join("\n");
}

export default function SignalHistory() {
  const [list, setList] = useState<SigmaSignal[]>([]);
  const [limit, setLimit] = useState(100);
  const [minConf, setMinConf] = useState(0);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`${REST_SIGNALS}?limit=${limit}`);
        if (!res.ok) throw new Error("fetch failed");
        const arr: SigmaSignal[] = await res.json();
        setList(arr.reverse()); // 최신이 위로
      } catch (e) {
        console.warn(e);
      }
    }
    load();
  }, [limit]);

  // confidence가 null일 때 필터 불가 → 자동 제외
  const filtered = useMemo(
    () => list.filter((s) => (s.confidence ?? 0) >= minConf),
    [list, minConf]
  );

  return (
    <div>
      <header className="mb-6">
        <h2 className="text-3xl font-bold gradient-text">신호 이력</h2>
        <div className="text-slate-400 mt-1">최근 생성된 신호와 신뢰도 로그</div>
      </header>

      <div className="mb-4 flex items-center gap-4">
        <label className="text-sm text-slate-300">표시 수</label>
        <select
          value={limit}
          onChange={(e) => setLimit(Number(e.target.value))}
          className="bg-slate-800 px-3 py-1 rounded"
        >
          <option value={50}>50</option>
          <option value={100}>100</option>
          <option value={200}>200</option>
        </select>

        <label className="text-sm text-slate-300 ml-4">최소 신뢰도</label>
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={minConf}
          onChange={(e) => setMinConf(Number(e.target.value))}
        />
        <div className="text-sm text-slate-300 ml-2">{Math.round(minConf * 100)}%</div>

        <button
          className="ml-auto btn-primary"
          onClick={() => {
            const csv = toCSV(list);
            const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `signals_${new Date().toISOString()}.csv`;
            a.click();
            URL.revokeObjectURL(url);
          }}
        >
          CSV 다운로드
        </button>
      </div>

      <div className="glass-card p-4">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-300">
              <th className="p-2">시간</th>
              <th className="p-2">심볼</th>
              <th className="p-2">레짐</th>
              <th className="p-2">스코어</th>
              <th className="p-2">신뢰도</th>
              <th className="p-2">모델수</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((s, i) => (
              <tr key={i} className="border-t border-white/5 hover:bg-white/5">
                <td className="p-2">{new Date(s.timestamp).toLocaleString()}</td>
                <td className="p-2">{s.symbol}</td>
                <td className="p-2">{s.regime}</td>

                {/* score null-safe */}
                <td className="p-2">
                  {s.score != null ? s.score.toFixed(3) : "-"}
                </td>

                {/* confidence null-safe */}
                <td className="p-2">
                  {s.confidence != null
                    ? Math.round(s.confidence * 100) + "%"
                    : "-"}
                </td>

                <td className="p-2">{s.models?.length ?? 0}</td>
              </tr>
            ))}
          </tbody>
        </table>

        {filtered.length === 0 && (
          <div className="text-slate-400 p-6">조건에 맞는 신호가 없습니다.</div>
        )}
      </div>
    </div>
  );
}
