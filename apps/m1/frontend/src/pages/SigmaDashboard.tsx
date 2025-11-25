// frontend/src/pages/SigmaDashboard.tsx
import React, { useEffect, useMemo, useState } from "react";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
  Line,
} from "recharts";

type Scenario = {
  change: string;       // +1%, -1%, 0%
  score: number;
  action: string;       // BUY / SELL / HOLD
};

type Snapshot = {
  next_open_regime: string;
  next_open_score: number;
  next_open_confidence: number;
  scenarios: Scenario[];
};

type ModelInfo = {
  name: string;
  signal: number;
  confidence: number;
};

type SigmaSignal = {
  timestamp: string;
  symbol: string;
  regime: string;
  score: number | null;
  confidence: number | null;
  strength?: number | null;
  models: ModelInfo[];
  raw_preds?: Record<string, number>;
  market_closed?: boolean;
  snapshot?: Snapshot;
};

const WS_URL = "ws://localhost:8001/ws";

export default function SigmaDashboard() {
  const [connected, setConnected] = useState(false);
  const [history, setHistory] = useState<SigmaSignal[]>([]);
  const [latest, setLatest] = useState<SigmaSignal | null>(null);

  const safeFixed = (v: number | null | undefined, d: number) =>
    typeof v === "number" && !isNaN(v) ? v.toFixed(d) : "-";

  const safePercent = (v: number | null | undefined) =>
    typeof v === "number" && !isNaN(v) ? `${(v * 100).toFixed(1)}%` : "-";

  // WebSocket 연결
  useEffect(() => {
    const ws = new WebSocket(WS_URL);

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);

    ws.onmessage = (e) => {
      try {
        const json = JSON.parse(e.data) as SigmaSignal;
        setLatest(json);
        setHistory((prev) => [...prev.slice(-200), json]);
      } catch (err) {
        console.error("SigmaDashboard WS parse error", err);
      }
    };

    return () => {
      try {
        ws.close();
      } catch {}
    };
  }, []);

  // Ensemble / Confidence 타임시리즈
  const chartData = useMemo(
    () =>
      history.slice(-80).map((s) => ({
        timestamp: new Date(s.timestamp).toLocaleTimeString(),
        ensemble:
          typeof s.score === "number" && !isNaN(s.score) ? s.score : 0,
        confidence:
          typeof s.confidence === "number" && !isNaN(s.confidence)
            ? Number(s.confidence.toFixed(2))
            : 0,
        strength:
          typeof s.strength === "number" && !isNaN(s.strength)
            ? Number(s.strength.toFixed(2))
            : 0,
      })),
    [history]
  );

  // 최신 모델 시그널 바차트용 데이터
  const modelBarData = useMemo(() => {
    if (!latest) return [];
    return (latest.models ?? []).map((m) => ({
      name: m.name,
      signal: m.signal,
      confidence: m.confidence,
    }));
  }, [latest]);

  // 모델 평균 신뢰도
  const avgModelConf = useMemo(() => {
    if (!latest || !latest.models?.length) return null;
    const s = latest.models.reduce((acc, m) => acc + (m.confidence ?? 0), 0);
    return s / latest.models.length;
  }, [latest]);

  // ======================================================
  // 📉 시장 닫힘 : 모델 중심 Snapshot 모드
  // ======================================================
  if (latest?.market_closed && latest.snapshot) {
    const snap = latest.snapshot;

    return (
      <div className="min-h-screen bg-bgDark text-gray-100 px-6 py-10">
        {/* 헤더 */}
        <header className="mb-10 flex justify-between items-center">
          <div>
            <h1 className="text-4xl font-extrabold gradient-text">
              SIGMA 모델 분석 대시보드
            </h1>
            <p className="mt-2 text-slate-400">
              시장 닫힘 상태 — 마지막 모델 스냅샷 및 다음 개장 예측
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="px-3 py-1 rounded-full text-sm font-semibold bg-red-500/20 text-red-400">
              MARKET CLOSED
            </span>
          </div>
        </header>

        {/* Snapshot 요약 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
          <div className="glass-card p-6">
            <div className="text-sm text-slate-400">예상 개장 레짐</div>
            <div className="mt-3 text-2xl font-bold">
              {snap.next_open_regime}
            </div>
          </div>

          <div className="glass-card p-6">
            <div className="text-sm text-slate-400">예상 Score</div>
            <div className="mt-3 text-3xl font-extrabold">
              {snap.next_open_score.toFixed(3)}
            </div>
          </div>

          <div className="glass-card p-6">
            <div className="text-sm text-slate-400">예상 Confidence</div>
            <div className="mt-3 text-3xl font-extrabold">
              {(snap.next_open_confidence * 100).toFixed(1)}%
            </div>
          </div>
        </div>

        {/* 시나리오 테이블 */}
        <div className="glass-card p-6 mb-12">
          <h2 className="text-xl font-semibold mb-4">📊 시나리오 분석</h2>
          <table className="w-full text-sm">
            <thead className="text-slate-400 border-b border-slate-700">
              <tr>
                <th className="py-2">변화량</th>
                <th>Score</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {snap.scenarios.map((sc, idx) => (
                <tr key={idx} className="border-b border-slate-800">
                  <td className="py-2">{sc.change}</td>
                  <td>{sc.score.toFixed(3)}</td>
                  <td
                    className={
                      sc.action === "BUY"
                        ? "text-blue-400"
                        : sc.action === "SELL"
                        ? "text-rose-400"
                        : "text-slate-300"
                    }
                  >
                    {sc.action}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* 모델별 스냅샷 */}
        <h2 className="text-xl font-semibold mb-4">📡 최근 모델 상태</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {(latest.models ?? []).map((m) => (
            <div key={m.name} className="glass-card p-5">
              <h3 className="font-semibold mb-2 text-lg">{m.name}</h3>
              <p className="text-sm text-slate-400">
                Signal:{" "}
                <span
                  className={
                    m.signal >= 0 ? "text-blue-400 font-semibold" : "text-rose-400 font-semibold"
                  }
                >
                  {m.signal.toFixed(2)}
                </span>
              </p>
              <p className="mt-2 text-sm text-slate-400">
                Confidence:{" "}
                <span className="text-yellow-400 font-semibold">
                  {(m.confidence * 100).toFixed(1)}%
                </span>
              </p>
              <div className="mt-3 w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className={`h-full ${
                    m.signal >= 0 ? "bg-blue-500" : "bg-rose-500"
                  }`}
                  style={{ width: `${Math.min(Math.abs(m.signal) * 100, 100)}%` }}
                />
              </div>
            </div>
          ))}
        </div>

        <footer className="mt-16 text-slate-600 text-center text-xs">
          시장 재개 시 자동으로 실시간 모델 분석 모드로 전환됩니다.
        </footer>
      </div>
    );
  }

  // ======================================================
  // 📈 시장 열림 : 실시간 모델 분석 모드
  // ======================================================
  return (
    <div className="min-h-screen bg-bgDark text-gray-100 px-6 py-10">
      {/* 헤더 */}
      <header className="mb-10 flex justify-between items-center">
        <div>
          <h1 className="text-4xl font-extrabold gradient-text">
            SIGMA 모델 분석 대시보드
          </h1>
          <p className="mt-2 text-slate-400">
            개별 딥러닝 모델 신호와 Ensemble 결과를 실시간으로 분석합니다.
          </p>
        </div>
        <div>
          <span
            className={`px-3 py-1 rounded-full text-sm font-semibold ${
              connected
                ? "bg-green-500/20 text-green-400"
                : "bg-red-500/20 text-red-400"
            }`}
          >
            {connected ? "WebSocket 연결됨" : "연결 없음"}
          </span>
        </div>
      </header>

      {/* 상단 요약 카드 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
        <div className="glass-card p-6">
          <div className="text-sm text-slate-400">현재 Ensemble Score</div>
          <div className="mt-3 text-3xl font-extrabold">
            {safeFixed(latest?.score, 3)}
          </div>
          <div className="mt-1 text-sm text-slate-300">
            Confidence: {safePercent(latest?.confidence)}
          </div>
        </div>

        <div className="glass-card p-6">
          <div className="text-sm text-slate-400">모델 평균 신뢰도</div>
          <div className="mt-3 text-3xl font-extrabold">
            {avgModelConf !== null ? (avgModelConf * 100).toFixed(1) + "%" : "-"}
          </div>
          <div className="mt-1 text-sm text-slate-300">
            Models: {latest?.models.length ?? 0}
          </div>
        </div>

        <div className="glass-card p-6">
          <div className="text-sm text-slate-400">Signal Strength</div>
          <div className="mt-3 text-3xl font-extrabold">
            {safeFixed(latest?.strength ?? null, 2)}
          </div>
          <div className="mt-1 text-sm text-slate-300">
            {latest?.regime === "bull"
              ? "상승 우세"
              : latest?.regime === "bear"
              ? "하락 우세"
              : "중립 영역"}
          </div>
        </div>
      </div>

      {/* Ensemble 타임시리즈 차트 */}
      <div className="glass-card p-5 mb-10">
        <div className="flex justify-between mb-4">
          <h2 className="text-lg font-semibold">Ensemble Score / Confidence 추세</h2>
          <span className="text-slate-400 text-sm">
            최근 {chartData.length}개 샘플
          </span>
        </div>

        <div style={{ height: 280 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="ensemble" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#0f1724" />
              <XAxis dataKey="timestamp" tick={{ fill: "#94a3b8" }} />
              <YAxis domain={[-1, 1]} tick={{ fill: "#94a3b8" }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#0b1220",
                  border: "none",
                  color: "white",
                }}
              />
              <Area
                type="monotone"
                dataKey="ensemble"
                stroke="#3B82F6"
                fill="url(#ensemble)"
                strokeWidth={2}
                name="Ensemble Score"
              />
              <Line
                type="monotone"
                dataKey="confidence"
                stroke="#F59E0B"
                strokeWidth={2}
                dot={false}
                name="Confidence"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 모델별 BarChart */}
      <div className="glass-card p-5 mb-10">
        <div className="flex justify-between mb-4">
          <h2 className="text-lg font-semibold">모델별 Signal / Confidence</h2>
          <span className="text-slate-400 text-sm">
            최신 Snapshot 기준
          </span>
        </div>

        <div style={{ height: 260 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={modelBarData}
              margin={{ top: 10, right: 10, left: 0, bottom: 40 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#0f1724" />
              <XAxis
                dataKey="name"
                tick={{ fill: "#94a3b8", fontSize: 11 }}
                angle={-20}
                textAnchor="end"
                interval={0}
              />
              <YAxis tick={{ fill: "#94a3b8" }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#0b1220",
                  border: "none",
                  color: "white",
                }}
              />
              <Legend />
              <Bar dataKey="signal" name="Signal" fill="#3B82F6" />
              <Bar dataKey="confidence" name="Confidence" fill="#F59E0B" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 모델 카드 리스트 */}
      <h2 className="text-lg font-semibold mb-4">개별 모델 상세</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {(latest?.models ?? []).map((m) => (
          <div key={m.name} className="glass-card p-5">
            <div className="flex justify-between items-center mb-2">
              <div className="font-semibold">{m.name}</div>
              <div
                className={`text-sm ${
                  m.signal >= 0 ? "text-blue-400" : "text-rose-400"
                }`}
              >
                {m.signal >= 0 ? "UP" : "DOWN"}
              </div>
            </div>
            <p className="text-sm text-slate-300">
              Signal:{" "}
              <span
                className={
                  m.signal >= 0 ? "text-blue-400 font-semibold" : "text-rose-400 font-semibold"
                }
              >
                {m.signal.toFixed(2)}
              </span>
            </p>
            <p className="mt-2 text-sm text-slate-300">
              Confidence:{" "}
              <span className="text-yellow-400 font-semibold">
                {(m.confidence * 100).toFixed(1)}%
              </span>
            </p>
            <div className="mt-3 w-full h-2 bg-slate-800 rounded-full overflow-hidden">
              <div
                className={`h-full ${
                  m.signal >= 0 ? "bg-blue-500" : "bg-rose-500"
                }`}
                style={{
                  width: `${Math.min(Math.abs(m.signal) * 100, 100)}%`,
                }}
              />
            </div>
          </div>
        ))}
      </div>

      <footer className="mt-16 text-slate-600 text-center text-xs">
        © 2025 SIGMA — Model Insight Dashboard
      </footer>
    </div>
  );
}
