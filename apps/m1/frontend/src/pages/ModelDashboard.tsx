import React, { useEffect, useMemo, useState } from "react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
} from "recharts";

type ModelSignal = { name: string; signal: number; confidence: number };
type SigmaSignal = {
  timestamp: string;
  models: ModelSignal[];
};

const REST_SIGNALS = "http://localhost:8000/signals";

const COLORS = [
  "#3B82F6",
  "#60A5FA",
  "#7C3AED",
  "#F59E0B",
  "#10B981",
  "#EF4444",
  "#8B5CF6",
];

export default function ModelDashboard() {
  const [history, setHistory] = useState<SigmaSignal[]>([]);
  const latest = history[history.length - 1] ?? null;

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`${REST_SIGNALS}?limit=200`);
        if (!res.ok) throw new Error("fetch failed");
        const arr: SigmaSignal[] = await res.json();
        setHistory(arr);
      } catch (e) {
        console.warn(e);
      }
    }
    load();
  }, []);

  // --------------------------------------------------------------------
  // 평균 Confidence 기반 모델 가중치
  // --------------------------------------------------------------------
  const modelWeights = useMemo(() => {
    const map = new Map<string, { sum: number; cnt: number }>();

    history.forEach((h) =>
      h.models.forEach((m) => {
        const cur = map.get(m.name) ?? { sum: 0, cnt: 0 };
        cur.sum += m.confidence;
        cur.cnt += 1;
        map.set(m.name, cur);
      })
    );

    const arr = Array.from(map.entries()).map(([name, v]) => ({
      name,
      weight: v.sum / Math.max(1, v.cnt),
    }));

    arr.sort((a, b) => b.weight - a.weight);
    return arr;
  }, [history]);

  // --------------------------------------------------------------------
  // 최근 트렌드 (Top 5 모델)
  // --------------------------------------------------------------------
  const topModels = modelWeights.slice(0, 5).map((m) => m.name);

  const confidenceTrend = useMemo(() => {
    const recent = history.slice(-20);
    return recent.map((s) => {
      const obj: any = {
        t: new Date(s.timestamp).toLocaleTimeString(),
      };
      s.models.forEach((m) => {
        if (topModels.includes(m.name))
          obj[m.name] = Number((m.confidence * 100).toFixed(1));
      });
      return obj;
    });
  }, [history, topModels]);

  const safeFixed = (v: number | null | undefined, d: number) =>
    typeof v === "number" ? v.toFixed(d) : "-";

  const safePercent = (v: number | null | undefined) =>
    typeof v === "number" ? `${(v * 100).toFixed(1)}%` : "-";

  return (
    <div>
      <header className="mb-8">
        <h2 className="text-3xl font-bold gradient-text">모델 개별 성능</h2>
        <div className="text-slate-400 mt-1">
          각 모델의 신호·신뢰도·트렌드 및 앙상블 기여도 분석
        </div>
      </header>

      {/* ----------------------------------
          PIE: 모델 가중치
      ----------------------------------- */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass-card p-6">
          <h3 className="text-lg font-semibold mb-4">
            모델 가중치 (평균 Confidence)
          </h3>
          <div style={{ height: 300 }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={modelWeights.map((m) => ({
                    name: m.name,
                    value: Number((m.weight * 100).toFixed(2)),
                  }))}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={50}
                  outerRadius={90}
                  paddingAngle={4}
                >
                  {modelWeights.map((_, idx) => (
                    <Cell key={idx} fill={COLORS[idx % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* ----------------------------------
            BAR: Top 모델 Confidence Trend
        ----------------------------------- */}
        <div className="glass-card p-6">
          <h3 className="text-lg font-semibold mb-4">
            상위 모델 신뢰도 추세 (최근)
          </h3>
          <div style={{ height: 300 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={confidenceTrend}>
                <XAxis dataKey="t" tick={{ fill: "#94a3b8" }} />
                <YAxis tick={{ fill: "#94a3b8" }} />
                <Tooltip />
                <Legend />
                {topModels.map((mName, idx) => (
                  <Bar
                    key={mName}
                    dataKey={mName}
                    stackId="a"
                    fill={COLORS[idx % COLORS.length]}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* ----------------------------------
          LEADERBOARD
      ----------------------------------- */}
      <div className="mt-8 glass-card p-4">
        <h4 className="font-semibold mb-3">
          모델 Leaderboard (평균 Confidence 기준)
        </h4>
        <ul className="space-y-2">
          {modelWeights.map((m, i) => (
            <li key={m.name} className="flex justify-between items-center">
              <div className="text-sm">
                {i + 1}. {m.name}
              </div>
              <div className="text-sm text-slate-300">
                {(m.weight * 100).toFixed(1)}%
              </div>
            </li>
          ))}
        </ul>
      </div>

      {/* ----------------------------------
          MODEL DETAIL CARDS (Moved from MarketDashboard)
      ----------------------------------- */}
      <div className="mt-10">
        <h3 className="text-lg font-semibold mb-4">모델 개별 신호</h3>

        {!latest && (
          <div className="text-slate-400">데이터를 불러오는 중...</div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {latest?.models.map((m, idx) => (
            <div key={idx} className="glass-card p-4 text-sm">
              <div className="text-slate-400">{m.name}</div>
              <div className="mt-2 font-semibold">
                Signal: {safeFixed(m.signal, 3)}
              </div>
              <div className="text-slate-300">
                Confidence: {safePercent(m.confidence)}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
