"use client";

import React, { useEffect, useState } from "react";
import { BellRing, Check, ShieldCheck, Clock, AlertCircle } from "lucide-react";
import RiskBadge from "@/components/RiskBadge";
import EmptyState from "@/components/EmptyState";

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [tab, setTab] = useState<string>("ALL");
  const [loading, setLoading] = useState(true);

  const fetchAlerts = async () => {
    try {
      const url = tab === "ALL" ? "/api/alerts?limit=100" : `/api/alerts?status_filter=${tab}&limit=100`;
      const res = await fetch(url);
      if (res.ok) setAlerts(await res.json());
    } catch (e) {
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 3000);
    return () => clearInterval(interval);
  }, [tab]);

  const handleAcknowledge = async (id: number) => {
    await fetch(`/api/alerts/${id}/acknowledge`, { method: "PATCH" });
    fetchAlerts();
  };

  const handleResolve = async (id: number) => {
    await fetch(`/api/alerts/${id}/resolve`, { method: "PATCH" });
    fetchAlerts();
  };

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-base font-bold tracking-wider uppercase text-white font-mono flex items-center gap-2">
            <BellRing className="w-5 h-5 text-amber-500" />
            Security Operations Alert Queue
          </h1>
          <p className="text-xs text-slate-400">
            Real-time alerts triggered by high-risk early warning forecasts and confirmed attack classifications.
          </p>
        </div>

        {/* Status Tabs */}
        <div className="flex items-center gap-1 bg-slate-900 border border-slate-800 p-1 rounded-lg text-xs font-mono">
          {["ALL", "UNRESOLVED", "ACKNOWLEDGED", "RESOLVED"].map((s) => (
            <button
              key={s}
              onClick={() => setTab(s)}
              className={`px-3 py-1 rounded transition-colors ${
                tab === s ? "bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/30" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Alert List */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
        {alerts.length > 0 ? (
          <div className="space-y-3">
            {alerts.map((alt) => (
              <div
                key={alt.id}
                className="p-4 rounded-lg bg-slate-950/70 border border-slate-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 hover:border-slate-700 transition-colors"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-white font-mono">#{alt.id}</span>
                    <span className="text-xs font-bold text-slate-200">{alt.title}</span>
                    <RiskBadge level={alt.severity} />
                    <span className="text-[10px] px-2 py-0.5 rounded font-mono bg-slate-800 text-slate-400">
                      {alt.source_event_type}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">{alt.message}</p>
                  <span className="text-[10px] text-slate-500 font-mono block">
                    {alt.timestamp?.replace("T", " ").slice(0, 19)} | Status:{" "}
                    <strong className={alt.status === "UNRESOLVED" ? "text-amber-400" : "text-emerald-400"}>
                      {alt.status}
                    </strong>
                  </span>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {alt.status === "UNRESOLVED" && (
                    <button
                      onClick={() => handleAcknowledge(alt.id)}
                      className="px-3 py-1.5 rounded text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
                    >
                      Acknowledge
                    </button>
                  )}
                  {alt.status !== "RESOLVED" && (
                    <button
                      onClick={() => handleResolve(alt.id)}
                      className="px-3 py-1.5 rounded text-xs font-medium bg-emerald-950 text-emerald-400 border border-emerald-800 hover:bg-emerald-900 transition-colors flex items-center gap-1"
                    >
                      <Check className="w-3.5 h-3.5" /> Resolve
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title="NO ALERTS IN QUEUE" message={`No alerts with status ${tab}.`} />
        )}
      </div>
    </div>
  );
}
