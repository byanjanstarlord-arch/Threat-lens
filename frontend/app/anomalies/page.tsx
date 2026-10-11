"use client";

import React, { useEffect, useState } from "react";
import { AlertTriangle, ShieldCheck, Activity } from "lucide-react";
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine
} from "recharts";
import EmptyState from "@/components/EmptyState";

export default function AnomaliesPage() {
  const [timeline, setTimeline] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      const res = await fetch("/api/analytics/risk-history?limit=50");
      if (res.ok) setTimeline(await res.json());
    } catch (e) {
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto">
      <div>
        <h1 className="text-base font-bold tracking-wider uppercase text-white font-mono flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-amber-400" />
          Behavioral Anomaly Radar (Isolation Forest)
        </h1>
        <p className="text-xs text-slate-400">
          Unsupervised detection of behavioral deviations from learned benign traffic patterns.
        </p>
      </div>

      {/* Conceptual Explanation Card */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
        <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
          <h4 className="font-semibold text-cyan-400 mb-1">Behavioral Anomaly Detection</h4>
          <p className="text-slate-400">
            Measures mathematical distance from the learned normal baseline. An anomaly indicates unexpected statistical variance, not necessarily a known signature.
          </p>
        </div>
        <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
          <h4 className="font-semibold text-rose-400 mb-1">Attack Classification</h4>
          <p className="text-slate-400">
            Supervised mapping to documented attack categories (DoS, DDoS, PortScan, BruteForce, Botnet, WebAttack).
          </p>
        </div>
      </div>

      {/* Anomaly Timeline */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
        <h3 className="text-sm font-bold tracking-wider uppercase text-slate-200 mb-1">
          Telemetry Risk & Anomaly Progression
        </h3>
        <p className="text-xs text-slate-500 font-mono mb-4">
          Continuous score timeline across evaluated network flows
        </p>
        {timeline.length > 0 ? (
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={timeline}>
                <defs>
                  <linearGradient id="anomGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="id" stroke="#64748b" tick={{ fontSize: 10 }} />
                <YAxis domain={[0, 1]} stroke="#64748b" tick={{ fontSize: 10 }} />
                <Tooltip contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", fontSize: "12px" }} />
                <ReferenceLine y={0.58} stroke="#f59e0b" strokeDasharray="3 3" label={{ value: "Anomaly Threshold (0.58)", fill: "#f59e0b", fontSize: 10 }} />
                <Area type="monotone" dataKey="composite_risk" stroke="#f59e0b" fill="url(#anomGrad)" name="Score" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <EmptyState title="NO ANOMALY DATA" message="Awaiting flow events." className="h-64" />
        )}
      </div>
    </div>
  );
}
