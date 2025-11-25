import React from "react";
import { Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import MarketDashboard from "./pages/MarketDashboard";
import ModelDashboard from "./pages/ModelDashboard";
import SignalHistory from "./pages/SignalHistory";
import ChampionModel from "./pages/ChampionModel";   // ⭐ 새 페이지 추가
import DemoPage from "./pages/DemoPage";             // ⭐ 전시 페이지 라우팅

export default function App() {
  return (
    <div className="flex min-h-screen bg-bgDark text-gray-200">
      {/* Sidebar */}
      <Sidebar />

      {/* Content */}
      <main className="flex-1 p-10 overflow-auto">
        <Routes>
          <Route path="/" element={<MarketDashboard />} />
          <Route path="/models" element={<ModelDashboard />} />
          <Route path="/signals" element={<SignalHistory />} />

          {/* ⭐ 챔피언 모델 페이지 */}
          <Route path="/champion" element={<ChampionModel />} />

          {/* ⭐ 전시 페이지 라우팅 */}
          <Route path="/demo" element={<DemoPage />} />
        </Routes>
      </main>
    </div>
  );
}
