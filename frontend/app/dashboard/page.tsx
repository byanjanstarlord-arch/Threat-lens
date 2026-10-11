"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  ShieldAlert,
  Radar,
  Activity,
  BellRing,
  TrendingUp,
  AlertTriangle,
  ArrowUpRight,
  Play,
  Pause,
  FastForward,
  Cpu
} from "lucide-react";
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid
} from "recharts";
import RiskBadge from "@/components/RiskBadge";
import EmptyState from "@/components/EmptyState";

const PIE_COLORS = ["#10b981", "#06b6d4", "#3b82f6", "#f59e0b", "#f43f5e", "#8b5cf6", "#ec4899", "#64748b"];

export default function DashboardPage() {
  const [summary, setSummary] = useState<any>(null);
  const [timeline, setTimeline] = useState<any[]>([]);
  const [forecastTimeline, setForecastTimeline] = useState<any[]>([]);
  const [attacksDist, setAttacksDist] = useState<any[]>([]);
  const [recentAlerts, setRecentAlerts] = useState<any[]>([]);
  const [replayStatus, setReplayStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const loadDashboardData = async () => {
    try {
      const [sumRes, timeRes, fcRes, distRes, alertRes, repRes] = await Promise.all([
        fetch("/api/traffic/summary"),
        fetch("/api/traffic/timeline?limit=30"),
        fetch("/api/forecast/timeline?limit=30"),
        fetch("/api/analytics/attack-distribution"),
        fetch("/api/alerts?limit=5"),
        fetch("/api/replay/status")
      ]);

      if (sumRes.ok) setSummary(await sumRes.ok ? await sumRes.json() : null);
      if (timeRes.ok) setTimeline(await timeRes.json());
      if (fcRes.ok) setForecastTimeline(await fcRes.json());
      if (distRes.ok) setAttacksDist(await distRes.json());
      if (alertRes.ok) setRecentAlerts(await alertRes.json());
      if (repRes.ok) setReplayStatus(await repRes.json());
    } catch (e) {
      console.error("Failed to load dashboard data:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
    const interval = setInterval(loadDashboardData, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleStep = async () => {
    try {
      await fetch("/api/replay/step", { method: "POST" });
      loadDashboardData();
    } catch (e) {}
  };

  const latestForecast = forecastTimeline.length > 0 ? forecastTimeline[forecastTimeline.length - 1] : null;

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto">
      {/* Top Banner: Dataset Replay Mode Context */}
      <div className="bg-gradient-to-r from-slate-900/90 via-slate-900/50 to-slate-900/90 border border-slate-800 rounded-xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
            <h2 className="text-sm font-bold tracking-wider uppercase text-cyan-400 font-mono">
              Dataset Replay Telemetry
            </h2>
            <span className="text-slate-600">|</span>
            <span className="text-xs text-slate-400 font-mono">
              Replaying historical traffic windows in chronological sequence
            </span>
          </div>
          <p className="text-xs text-slate-500">
            Every metric, probability, and alert is computed live through the trained ML inference pipeline.
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={handleStep}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 hover:bg-cyan-500/30 transition-all"
          >
            <FastForward className="w-3.5 h-3.5" />
            Step Window
          </button>
          <Link
            href="/replay"
            className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700 transition-all"
          >
            Replay Deck
          </Link>
        </div>
      </div>

      {/* 4 Core SOC KPI Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Current Network Risk */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 relative overflow-hidden">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-mono font-medium text-slate-400 uppercase tracking-wider">
              Current ThreatLens Risk Score
            </span>
            <ShieldAlert className="w-4 h-4 text-slate-500" />
          </div>
          {summary ? (
            <div>
              <div className="flex items-baseline gap-3 mb-2">
                <span className="text-3xl font-extrabold font-mono text-white">
                  {(summary.current_risk_score * 100).toFixed(1)}%
                </span>
                <RiskBadge level={summary.current_risk_level} />
              </div>
              <p className="text-[11px] text-slate-500">
                Composite assessment from classifier & anomaly engines
              </p>
            </div>
          ) : (
            <EmptyState title="NO DATA" message="Awaiting network flow events." className="p-3" />
          )}
        </div>

        {/* Forecast Attack Risk (5-Minute Horizon) */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 relative overflow-hidden">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-mono font-medium text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
              5-Min Attack Forecast
            </span>
            <Radar className="w-4 h-4 text-cyan-400" />
          </div>
          {latestForecast ? (
            <div>
              <div className="flex items-baseline gap-3 mb-2">
                <span className="text-3xl font-extrabold font-mono text-cyan-400">
                  {(latestForecast.forecast_attack_prob * 100).toFixed(1)}%
                </span>
                <RiskBadge level={latestForecast.risk_level} />
              </div>
              <p className="text-[11px] text-slate-500">
                {latestForecast.predicted_category === "ATTACK_LIKELY"
                  ? "Early Warning: Malicious onset predicted"
                  : "Normal horizon: Low attack probability"}
              </p>
            </div>
          ) : (
            <EmptyState title="NO FORECAST" message="Replay a window to generate forecast." className="p-3" />
          )}
        </div>

        {/* Active Alerts */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 relative overflow-hidden">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-mono font-medium text-slate-400 uppercase tracking-wider">
              Active Security Alerts
            </span>
            <BellRing className="w-4 h-4 text-amber-500" />
          </div>
          {summary ? (
            <div>
              <div className="flex items-baseline gap-3 mb-2">
                <span className="text-3xl font-extrabold font-mono text-white">
                  {summary.active_alerts_count}
                </span>
                <span className="text-xs text-amber-400 font-medium">Pending Triage</span>
              </div>
              <p className="text-[11px] text-slate-500">
                Generated from confirmed model risk triggers
              </p>
            </div>
          ) : (
            <EmptyState title="NO DATA" message="No alerts triggered." className="p-3" />
          )}
        </div>

        {/* Total Analyzed / Attacks Detected */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 relative overflow-hidden">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-mono font-medium text-slate-400 uppercase tracking-wider">
              Analyzed Telemetry
            </span>
            <Activity className="w-4 h-4 text-slate-500" />
          </div>
          {summary ? (
            <div>
              <div className="flex items-baseline gap-3 mb-2">
                <span className="text-2xl font-extrabold font-mono text-white">
                  {summary.total_flows_analyzed} <span className="text-xs text-slate-400 font-sans">flows</span>
                </span>
                <span className="text-xs text-rose-400 font-mono font-bold">
                  {summary.total_attacks_detected} attacks
                </span>
              </div>
              <p className="text-[11px] text-slate-500 font-mono">
                Avg: {(summary.average_byte_rate / 1024).toFixed(1)} KB/s ({summary.average_packet_rate.toFixed(1)} pkts/s)
              </p>
            </div>
          ) : (
            <EmptyState title="NO DATA" message="No telemetry stream." className="p-3" />
          )}
        </div>
      </div>

      {/* Main Visualizations Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Network Telemetry Byte Rate Over Time */}
        <div className="lg:col-span-2 bg-slate-900/60 border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold tracking-wider uppercase text-slate-200">
                Network Telemetry Throughput
              </h3>
              <p className="text-xs text-slate-500">
                Real byte and packet arrival rates across 1-minute historical windows
              </p>
            </div>
            <Link href="/traffic" className="text-xs text-cyan-400 hover:underline flex items-center gap-1">
              Details <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>
          {timeline.length > 0 ? (
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={timeline}>
                  <defs>
                    <linearGradient id="byteRateGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="window_id" stroke="#64748b" tick={{ fontSize: 10 }} />
                  <YAxis stroke="#64748b" tick={{ fontSize: 10 }} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", fontSize: "12px" }}
                  />
                  <Area
                    type="monotone"
                    dataKey="byte_rate"
                    stroke="#06b6d4"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#byteRateGrad)"
                    name="Byte Rate (B/s)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState title="NO TRAFFIC DATA" message="Start replay to stream network telemetry." className="h-64" />
          )}
        </div>

        {/* Attack Category Breakdown */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold tracking-wider uppercase text-slate-200">
                Attack Taxonomy Distribution
              </h3>
              <p className="text-xs text-slate-500">
                Detected incidents mapped to ThreatLens taxonomy
              </p>
            </div>
            <Link href="/attacks" className="text-xs text-cyan-400 hover:underline flex items-center gap-1">
              Incidents <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>
          {attacksDist.length > 0 ? (
            <div className="h-64 w-full flex flex-col items-center justify-center">
              <ResponsiveContainer width="100%" height="80%">
                <PieChart>
                  <Pie
                    data={attacksDist}
                    dataKey="count"
                    nameKey="attack_type"
                    cx="50%"
                    cy="50%"
                    outerRadius={75}
                    innerRadius={45}
                    paddingAngle={3}
                  >
                    {attacksDist.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", fontSize: "12px" }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex flex-wrap gap-2 justify-center text-[10px] text-slate-400">
                {attacksDist.slice(0, 4).map((d, i) => (
                  <span key={d.attack_type} className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full" style={{ backgroundColor: PIE_COLORS[i % PIE_COLORS.length] }} />
                    {d.attack_type}: {d.count}
                  </span>
                ))}
              </div>
            </div>
          ) : (
            <EmptyState title="NO ATTACKS DETECTED" message="No attack events recorded yet." className="h-64" />
          )}
        </div>
      </div>

      {/* Forecast Timeline & Live Alert Feed Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Forecast Probability Radar Timeline */}
        <div className="lg:col-span-2 bg-slate-900/60 border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold tracking-wider uppercase text-slate-200 flex items-center gap-2">
                <Radar className="w-4 h-4 text-cyan-400" />
                Forecast Attack Probability Timeline
              </h3>
              <p className="text-xs text-slate-500">
                Model-estimated attack likelihood over upcoming 5-minute horizon per window
              </p>
            </div>
            <Link href="/forecast" className="text-xs text-cyan-400 hover:underline flex items-center gap-1">
              Forecast Radar <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>
          {forecastTimeline.length > 0 ? (
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={forecastTimeline}>
                  <defs>
                    <linearGradient id="fcGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="window_id" stroke="#64748b" tick={{ fontSize: 10 }} />
                  <YAxis domain={[0, 1]} stroke="#64748b" tick={{ fontSize: 10 }} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", fontSize: "12px" }}
                    formatter={(val: any) => [`${(Number(val) * 100).toFixed(1)}%`, "Forecast Attack Prob"]}
                  />
                  <Area
                    type="monotone"
                    dataKey="forecast_attack_prob"
                    stroke="#f43f5e"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#fcGrad)"
                    name="Attack Probability"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState title="NO FORECAST TIMELINE" message="Step through replay windows to build forecast history." className="h-64" />
          )}
        </div>

        {/* Live Active Alert Feed */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold tracking-wider uppercase text-slate-200">
                Recent SOC Alerts
              </h3>
              <Link href="/alerts" className="text-xs text-cyan-400 hover:underline flex items-center gap-1">
                View All <ArrowUpRight className="w-3.5 h-3.5" />
              </Link>
            </div>
            {recentAlerts.length > 0 ? (
              <div className="space-y-2.5">
                {recentAlerts.map((alt) => (
                  <div
                    key={alt.id}
                    className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800 hover:border-slate-700 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-semibold text-slate-200 truncate max-w-[180px]">
                        {alt.title}
                      </span>
                      <RiskBadge level={alt.severity} />
                    </div>
                    <p className="text-[11px] text-slate-400 line-clamp-1">{alt.message}</p>
                    <span className="text-[10px] text-slate-500 font-mono mt-1 block">
                      Status: {alt.status}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState title="NO ACTIVE ALERTS" message="No alerts in queue." className="h-64" />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
