import React, { useEffect, useMemo, useState } from "react";
import {
  AreaChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

// -------------------------------
//  Types
// -------------------------------
type Scenario = {
  change: string;
  score: number;
  action: string;
};

type SnapshotReport = {
  next_open_regime: string;
  next_open_score: number;
  next_open_confidence: number;
  scenarios: Scenario[];
};

type ModelSignal = {
  name: string;
  signal: number | null;
  confidence: number | null;
};

type SigmaSignal = {
  timestamp: string;
  symbol: string;
  regime: string;
  score: number | null;
  confidence: number | null;
  market_closed?: boolean;
  snapshot?: SnapshotReport;
  models: ModelSignal[];
};

const WS_URL = "ws://localhost:8000/ws";
const REST_SIGNALS = "http://localhost:8000/signals";

export default function MarketDashboard() {
  const [connected, setConnected] = useState(false);
  const [history, setHistory] = useState<SigmaSignal[]>([]);
  const [latest, setLatest] = useState<SigmaSignal | null>(null);

  const wsRef = React.useRef<WebSocket | null>(null);

  const safeFixed = (v: number | null | undefined, d: number) =>
    typeof v === "number" ? v.toFixed(d) : "-";

  const safePercent = (v: number | null | undefined) =>
    typeof v === "number" ? `${(v * 100).toFixed(1)}%` : "-";

  // -----------------------------
  // Initial Load
  // -----------------------------
  useEffect(() => {
    async function load() {
      try {
        const r = await fetch(`${REST_SIGNALS}?limit=120`);
        const arr = (await r.json()) as SigmaSignal[];
        setHistory(arr);
        setLatest(arr[arr.length - 1] ?? null);
      } catch (e) {
        console.warn("initial fetch error", e);
      }
    }
    load();
  }, []);

  // -----------------------------
  // WebSocket
  // -----------------------------
  useEffect(() => {
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);

    ws.onmessage = (ev) => {
      try {
        const payload = JSON.parse(ev.data) as SigmaSignal;
        setLatest(payload);
        setHistory((h) => [...h.slice(-400), payload]);
      } catch (e) {
        console.warn("ws parse error", e);
      }
    };

    return () => ws.close();
  }, []);

  // -----------------------------
  // Chart Data
  // -----------------------------
  const chartData = useMemo(
    () =>
      history.slice(-80).map((s) => ({
        timestamp: new Date(s.timestamp).toLocaleTimeString(),
        score: typeof s.score === "number" ? s.score : 0,
        confidence:
          typeof s.confidence === "number"
            ? Number(s.confidence.toFixed(2))
            : 0,
      })),
    [history]
  );

  // ============================================================
  //      🔥 Market Phase Classification (5단계 시장 분류)
  // ============================================================
  function classifyMarketPhase(score: number | null) {
    if (score == null) return { phase: "-", desc: "-", action: "-" };

    if (score >= 0.6)
      return {
        phase: "강한 상승(Strong Bull)",
        desc: "시장이 강한 상승 레짐에 있음. 추세 지속 확률 높음.",
        action: "BUY",
      };

    if (score >= 0.2)
      return {
        phase: "완만한 상승(Weak Bull)",
        desc: "상승세지만 변동성이 존재. 눌림 매수 구간일 수 있음.",
        action: "Buy on dips",
      };

    if (score > -0.2)
      return {
        phase: "중립(Neutral)",
        desc: "명확한 방향성이 없는 상태. 관망 필요.",
        action: "HOLD",
      };

    if (score > -0.6)
      return {
        phase: "완만한 하락(Weak Bear)",
        desc: "약세가 조금씩 강화되는 구간. 보수적 접근 필요.",
        action: "Light sell",
      };

    return {
      phase: "강한 하락(Strong Bear)",
      desc: "명확한 하락 추세. 리스크 높은 구간.",
      action: "SELL",
    };
  }

  const phaseInfo = classifyMarketPhase(latest?.score ?? null);

  // -----------------------------
  // Market Summary (기존 1단계)
  // -----------------------------
  const marketSummary = useMemo(() => {
    if (!latest)
      return { title: "데이터 부족", desc: "신호 데이터를 기다리는 중" };

    const { regime, score, confidence } = latest;
    const title =
      regime === "bull" ? "상승 우세" : regime === "bear" ? "하락 우세" : "중립";

    return {
      title,
      desc: `스코어 ${safeFixed(score, 2)} · 신뢰도 ${
        confidence !== null ? `${Math.round(confidence * 100)}%` : "-"
      }`,
    };
  }, [latest]);

  // ============================================================
  //      🔥 Market Closed Mode
  // ============================================================
  if (latest?.market_closed) {
    const snap = latest.snapshot;

    return (
      <div className="px-4 py-10 text-gray-100">
        <header className="mb-10 flex items-center justify-between">
          <h2 className="text-4xl font-extrabold gradient-text">
            📉 Market Closed - Snapshot Report
          </h2>
          <span className="px-4 py-1 rounded-full bg-red-500/20 text-red-400 font-semibold">
            MARKET CLOSED
          </span>
        </header>

        {/* Next Opening Prediction */}
        <div className="glass-card p-6 mb-10">
          <div className="text-sm text-slate-400">다음 개장 예측</div>
          <div className="mt-3">
            <div className="text-3xl font-bold">{snap?.next_open_regime}</div>
            <div className="mt-2 text-slate-300">
              Score: {safeFixed(snap?.next_open_score, 3)}
            </div>
            <div className="text-slate-300">
              Confidence: {safePercent(snap?.next_open_confidence)}
            </div>
          </div>
        </div>

        {/* Scenario Cards */}
        <div className="glass-card p-6">
          <div className="text-sm text-slate-400 mb-4">시나리오 분석</div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {(snap?.scenarios ?? []).map((s, idx) => (
              <div key={idx} className="glass-card p-4 text-sm">
                <div className="text-slate-400">{s.change} 변동 시</div>
                <div className="mt-2 font-semibold">
                  Score {safeFixed(s.score, 3)}
                </div>
                <div
                  className={`mt-1 font-bold ${
                    s.action === "BUY"
                      ? "text-blue-400"
                      : s.action === "SELL"
                      ? "text-rose-400"
                      : "text-slate-300"
                  }`}
                >
                  {s.action}
                </div>
              </div>
            ))}
          </div>
        </div>

        <footer className="mt-12 text-center text-slate-600">
          시장 재개 전까지 Snapshot Report가 유지됩니다.
        </footer>
      </div>
    );
  }

  // ============================================================
  //      🔥 Market OPEN — Real-Time Monitoring
  // ============================================================
  return (
    <div className="px-4 py-10 text-gray-100">
      {/* HEADER */}
      <header className="mb-10 flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-extrabold gradient-text">
            시장상황 분석
          </h1>
          <p className="mt-2 text-slate-400">
            KOSPI200 실시간 레짐 · 스코어 · 시장 단계 분석
          </p>
        </div>

        <span
          className={`px-4 py-1 rounded-full text-sm font-semibold ${
            connected
              ? "bg-green-500/20 text-green-400"
              : "bg-red-500/20 text-red-400"
          }`}
        >
          {connected ? "실시간 연결됨" : "연결 끊김"}
        </span>
      </header>

      {/* SUMMARY CARDS (4개로 확대) */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-10">
        {/* 1) 기본 시장 레짐 */}
        <div className="glass-card p-6">
          <div className="text-sm text-slate-400">현재 레짐</div>
          <div className="mt-3 text-2xl font-bold">
            {marketSummary.title}
          </div>
          <div className="mt-1 text-slate-300">{marketSummary.desc}</div>
        </div>

        {/* 2) 종합 스코어 */}
        <div className="glass-card p-6">
          <div className="text-sm text-slate-400">종합 스코어</div>
          <div className="mt-3 text-4xl font-extrabold">
            {safeFixed(latest?.score, 2)}
          </div>
          <div className="mt-1 text-slate-300">
            신뢰도:{" "}
            {latest?.confidence !== null
              ? `${Math.round((latest?.confidence ?? 0) * 100)}%`
              : "-"}
          </div>
        </div>

        {/* 3) 모델/심볼 정보 */}
        <div className="glass-card p-6">
          <div className="text-sm text-slate-400">상세</div>
          <div className="mt-3 space-y-1 text-slate-300">
            <div>모델 수: {latest?.models.length ?? "-"}</div>
            <div>심볼: {latest?.symbol ?? "-"}</div>
          </div>
        </div>

        {/* ⭐ 4) 시장 단계 분석 */}
        <div className="glass-card p-6">
          <div className="text-sm text-slate-400">시장 단계 분석</div>
          <div className="mt-3 text-xl font-bold">{phaseInfo.phase}</div>
          <div className="text-slate-300 text-sm mt-1">{phaseInfo.desc}</div>
          <div className="mt-2 font-semibold text-indigo-300">
            매매 신호: {phaseInfo.action}
          </div>
        </div>
      </div>

      {/* CHART */}
      <div className="glass-card p-5 mb-10">
        <div className="flex justify-between mb-4">
          <h3 className="text-lg font-semibold">실시간 시그널 추세</h3>
          <span className="text-slate-400 text-sm">
            최근 {chartData.length}개
          </span>
        </div>

        <div style={{ height: 320 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="score" x1="0" y1="0" x2="0" y2="1">
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
                }}
              />
              <Area
                type="monotone"
                dataKey="score"
                stroke="#3B82F6"
                fill="url(#score)"
                strokeWidth={2}
              />
              <Line
                type="monotone"
                dataKey="confidence"
                stroke="#F59E0B"
                strokeWidth={2}
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* MODEL 안내 */}
      <div className="mt-12 text-center text-slate-400 text-sm">
        모델별 신호는{" "}
        <span className="text-indigo-400 font-semibold">
          “모델 개별 성능”
        </span>{" "}
        페이지에서 확인하세요.
      </div>
    </div>
  );
}
