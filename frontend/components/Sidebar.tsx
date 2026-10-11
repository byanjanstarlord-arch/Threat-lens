"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Radar,
  Activity,
  ShieldAlert,
  AlertTriangle,
  BellRing,
  Cpu,
  BarChart3,
  FastForward,
  Settings
} from "lucide-react";

const NAV_ITEMS = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Attack Forecast", href: "/forecast", icon: Radar, highlight: true },
  { label: "Traffic Telemetry", href: "/traffic", icon: Activity },
  { label: "Attack Events", href: "/attacks", icon: ShieldAlert },
  { label: "Anomaly Detection", href: "/anomalies", icon: AlertTriangle },
  { label: "Alert Queue", href: "/alerts", icon: BellRing },
  { label: "Model Registry", href: "/models", icon: Cpu },
  { label: "Evaluation", href: "/evaluation", icon: BarChart3 },
  { label: "Dataset Replay", href: "/replay", icon: FastForward },
  { label: "Settings", href: "/settings", icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 border-r border-slate-800/80 bg-slate-950/60 flex flex-col justify-between shrink-0 min-h-[calc(100vh-4rem)]">
      <div className="p-4 space-y-1">
        <div className="px-3 py-2 text-[10px] font-bold uppercase tracking-widest text-slate-500 font-mono">
          Security Operations
        </div>
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
                isActive
                  ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 shadow-[0_0_15px_rgba(6,182,212,0.15)] font-semibold"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/60"
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? "text-cyan-400" : "text-slate-500"}`} />
              <span className="truncate">{item.label}</span>
              {item.highlight && (
                <span className="ml-auto w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
              )}
            </Link>
          );
        })}
      </div>

      {/* Footer info */}
      <div className="p-4 border-t border-slate-900 text-[11px] text-slate-500 font-mono">
        <div className="flex items-center justify-between text-slate-400 mb-1">
          <span>Engine Status</span>
          <span className="text-emerald-400 font-bold">READY</span>
        </div>
        <div>Model Version: v1</div>
        <div>Dataset: CIC-IDS2017</div>
      </div>
    </aside>
  );
}
