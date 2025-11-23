import React from "react";
import { NavLink } from "react-router-dom";

export default function Sidebar() {
  return (
    <aside className="w-64 bg-glassLight backdrop-blur-md shadow-glass border-r border-white/10 p-6 flex flex-col">
      {/* SIGMA 로고 + 전시 페이지 버튼 */}
      <div className="flex items-center justify-between mb-10">
        <h1 className="text-2xl font-bold gradient-text">SIGMA</h1>
        <button
          onClick={() => (window.location.href = "/demo")}
          className="bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1 rounded text-sm"
        >
          전시
        </button>
      </div>

      <nav className="flex flex-col gap-4">
        <NavLink
          to="/"
          className={({ isActive }) =>
            `sidebar-link ${isActive ? "sidebar-active" : ""}`
          }
        >
          시장상황 분석
        </NavLink>

        <NavLink
          to="/models"
          className={({ isActive }) =>
            `sidebar-link ${isActive ? "sidebar-active" : ""}`
          }
        >
          모델 개별 성능
        </NavLink>

        <NavLink
          to="/signals"
          className={({ isActive }) =>
            `sidebar-link ${isActive ? "sidebar-active" : ""}`
          }
        >
          신호 이력
        </NavLink>

        {/* 새로 추가되는 최종 모델 페이지 */}
        <NavLink
          to="/champion"
          className={({ isActive }) =>
            `sidebar-link ${isActive ? "sidebar-active" : ""}`
          }
        >
          최종 모델
        </NavLink>
      </nav>
    </aside>
  );
}
