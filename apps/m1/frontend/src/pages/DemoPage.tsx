import React, { useEffect, useState } from "react";

export default function DemoPage() {
  const [snapshot, setSnapshot] = useState<any>(null);

  useEffect(() => {
    const scheme = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${scheme}://${window.location.host}/ws`);

    ws.onmessage = (msg) => {
      try {
        setSnapshot(JSON.parse(msg.data));
      } catch (e) {
        console.warn("WS parse error:", e);
      }
    };

    ws.onerror = () => {
      console.warn("WS error");
    };

    return () => ws.close();
  }, []);

  return (
    <div className="flex flex-col gap-10">

      {/* HERO */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
        <div>
          <h1 className="text-5xl font-bold leading-tight">
            <span className="gradient-text">시장상황 분석</span>과<br />
            옵션 스큐 분석을 통한<br />
            자동매매 시스템
          </h1>
          <p className="text-slate-400 mt-4 text-lg">
            A: 시장상황 분석 → B: 트레이딩 → C: 리스크 관리
          </p>

          <button
            className="mt-8 px-5 py-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 transition text-white font-semibold"
            onClick={() => (window.location.href = "/")}
          >
            A 프로젝트 대시보드로 이동 →
          </button>
        </div>

        {/* SNAPSHOT PANEL */}
        <div className="glass-card p-6 rounded-2xl border border-white/10">
          <h3 className="text-xl font-bold mb-4">실시간 스냅샷</h3>

          {!snapshot ? (
            <div className="text-slate-500">로드 중...</div>
          ) : (
            <div className="grid grid-cols-3 gap-4">
              {[
                { label: "시장상태", key: "regime" },
                { label: "시그널", key: "score" },
                { label: "신뢰도", key: "confidence" },
                { label: "가격", key: "price" },
                { label: "시간", key: "timestamp" },
              ].map((item) => (
                <div
                  key={item.key}
                  className="p-3 rounded-xl border border-white/10 bg-white/5"
                >
                  <div className="text-xs text-slate-400">{item.label}</div>
                  <div className="text-lg font-bold mt-1">
                    {String(snapshot[item.key] ?? "—")}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* PROJECT CARDS */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="glass-card p-6 rounded-xl border border-white/10">
          <h4 className="text-lg font-bold mb-2">시장상황분석 (A)</h4>
          <p className="text-slate-400 text-sm mb-4">
            7개 모델 + XGBoost 스태킹 기반 KOSPI200 실시간 분석.
          </p>
          <a
            href="/"
            className="text-indigo-400 hover:text-indigo-300 font-semibold"
          >
            이동하기 →
          </a>
        </div>

        <div className="glass-card p-6 rounded-xl border border-white/10">
          <h4 className="text-lg font-bold mb-2">트레이딩 (B)</h4>
          <p className="text-slate-400 text-sm mb-4">
            IV Skew + BOCPD 기반 동적 트레이딩 시스템.
          </p>
          <a
            href="/trading.html"
            className="text-indigo-400 hover:text-indigo-300 font-semibold"
          >
            이동하기 →
          </a>
        </div>

        <div className="glass-card p-6 rounded-xl border border-white/10">
          <h4 className="text-lg font-bold mb-2">리스크 관리 (C)</h4>
          <p className="text-slate-400 text-sm mb-4">
            VaR/ES · AI 매도신호 기반 종합 리스크 모듈.
          </p>
          <a
            href="/risk-management.html"
            className="text-indigo-400 hover:text-indigo-300 font-semibold"
          >
            이동하기 →
          </a>
        </div>
      </section>
    </div>
  );
}
