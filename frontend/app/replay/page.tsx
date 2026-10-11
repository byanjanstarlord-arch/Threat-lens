"use client";

import React, { useEffect, useState } from "react";
import { FastForward, Play, Pause, RotateCcw, Activity, ShieldAlert, Radar, CheckCircle2 } from "lucide-react";
import RiskBadge from "@/components/RiskBadge";
import EmptyState from "@/components/EmptyState";

export default function ReplayPage() {
  const [status, setStatus] = useState<any>(null);
  const [speed, setSpeed] = useState<number>(2.0);
  const [lastStepResult, setLastStepResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const fetchStatus = async () => {
    try {
      const res = await fetch("/api/replay/status");
      if (res.ok) setStatus(await res.json());
    } catch (e) {}
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 1500);
    return () => clearInterval(interval);
  }, []);

  const handleStart = async () => {
    setLoading(true);
    await fetch(`/api/replay/start?speed=${speed}`, { method: "POST" });
    setLoading(false);
    fetchStatus();
  };

  const handleStop = async () => {
    setLoading(true);
    await fetch("/api/replay/stop", { method: "POST" });
    setLoading(false);
    fetchStatus();
  };

  const handleReset = async () => {
    setLoading(true);
    await fetch("/api/replay/reset", { method: "POST" });
    setLastStepResult(null);
    setLoading(false);
    fetchStatus();
  };

  const handleStep = async () => {
    setLoading(true);
    const res = await fetch("/api/replay/step", { method: "POST" });
    if (res.ok) {
      const data = await res.json();
      setLastStepResult(data);
    }
    setLoading(false);
    fetchStatus();
  };

  const progressPct = status?.total_windows
    ? Math.min(100, (status.current_window_index / status.total_windows) * 100)
    : 0;

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto">
      {/* Header Banner */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5">
        <div className="flex items-center gap-2 mb-1">
          <FastForward className="w-5 h-5 text-cyan-400" />
          <h1 className="text-base font-bold tracking-wider uppercase text-white font-mono">
            Historical Dataset Replay Deck
          </h1>
        </div>
        <p className="text-xs text-slate-400">
          Chronologically streams real historical capture windows from the test partition (Friday sessions) through the production inference pipeline.
        </p>
        <div className="mt-3 inline-block px-2.5 py-1 rounded text-xs font-mono bg-cyan-950/60 text-cyan-300 border border-cyan-800/80">
          Mode: Historical Dataset Replay (Zero Fake Telemetry)
        </div>
      </div>

      {/* Control Console */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          {/* Action Buttons */}
          <div className="flex items-center gap-3">
            {status?.is_running ? (
              <button
                onClick={handleStop}
                disabled={loading}
                className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-xs font-bold bg-amber-950 text-amber-300 border border-amber-800 hover:bg-amber-900 transition-all"
              >
                <Pause className="w-4 h-4" /> Pause Replay
              </button>
            ) : (
              <button
                onClick={handleStart}
                disabled={loading}
                className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-xs font-bold bg-cyan-500 text-slate-950 hover:bg-cyan-400 transition-all shadow-[0_0_15px_rgba(6,182,212,0.4)]"
              >
                <Play className="w-4 h-4 fill-slate-950" /> Start Replay
              </button>
            )}

            <button
              onClick={handleStep}
              disabled={loading || status?.is_running}
              className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs font-bold bg-slate-800 text-slate-200 border border-slate-700 hover:bg-slate-700 disabled:opacity-50 transition-all"
            >
              <FastForward className="w-4 h-4" /> Step 1 Window
            </button>

            <button
              onClick={handleReset}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs font-bold bg-slate-900 text-slate-400 border border-slate-800 hover:text-white transition-all"
            >
              <RotateCcw className="w-4 h-4" /> Reset
            </button>
          </div>

          {/* Speed Selector */}
          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="text-slate-400">Replay Speed:</span>
            {[0.5, 1.0, 2.0, 5.0, 10.0].map((s) => (
              <button
                key={s}
                onClick={() => setSpeed(s)}
                className={`px-2.5 py-1 rounded text-xs transition-colors ${
                  speed === s
                    ? "bg-cyan-950 text-cyan-300 font-bold border border-cyan-800"
                    : "bg-slate-800 text-slate-400 hover:text-slate-200"
                }`}
              >
                {s}x
              </button>
            ))}
          </div>
        </div>

        {/* Progress Bar */}
        <div>
          <div className="flex justify-between text-xs font-mono text-slate-400 mb-2">
            <span>Timeline Progression</span>
            <span>
              Window <strong className="text-white">{status?.current_window_index ?? 0}</strong> / {status?.total_windows ?? 743} ({progressPct.toFixed(1)}%)
            </span>
          </div>
          <div className="w-full h-2.5 rounded-full bg-slate-950 border border-slate-800 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-300"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>
      </div>

      {/* Latest Replayed Window Details Card */}
      {lastStepResult ? (
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold tracking-wider uppercase text-slate-200 font-mono flex items-center gap-2">
              <Activity className="w-4 h-4 text-cyan-400" />
              Latest Replayed Window #{lastStepResult.window_id} Telemetry & Inference Output
            </h3>
            <RiskBadge level={lastStepResult.prediction?.risk_level} />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
            {/* Window Telemetry */}
            <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800 space-y-1.5">
              <span className="text-slate-400 uppercase font-bold block mb-2">Input Telemetry</span>
              <div className="flex justify-between">
                <span className="text-slate-500">Flow Count:</span>
                <strong className="text-slate-200">{lastStepResult.traffic?.flow_count}</strong>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Byte Rate:</span>
                <strong className="text-slate-200">{(lastStepResult.traffic?.byte_rate / 1024).toFixed(1)} KB/s</strong>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Packet Rate:</span>
                <strong className="text-slate-200">{lastStepResult.traffic?.packet_rate?.toFixed(1)} pkts/s</strong>
              </div>
            </div>

            {/* AI Predictions */}
            <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800 space-y-1.5">
              <span className="text-slate-400 uppercase font-bold block mb-2">Multi-Model AI Output</span>
              <div className="flex justify-between">
                <span className="text-slate-500">Classification:</span>
                <strong className={lastStepResult.prediction?.predicted_class !== "BENIGN" ? "text-rose-400 font-bold" : "text-emerald-400"}>
                  {lastStepResult.prediction?.predicted_class}
                </strong>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Anomaly Score:</span>
                <strong className="text-amber-400">
                  {(lastStepResult.prediction?.anomaly_score * 100).toFixed(1)}%
                </strong>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">5-Min Forecast Prob:</span>
                <strong className="text-cyan-400 font-bold">
                  {(lastStepResult.forecast?.forecast_attack_probability * 100).toFixed(1)}%
                </strong>
              </div>
            </div>

            {/* Real Observed Ground Truth */}
            <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800 space-y-1.5">
              <span className="text-slate-400 uppercase font-bold block mb-2">Dataset Ground Truth</span>
              <div className="flex justify-between">
                <span className="text-slate-500">Attack Occurred in Horizon:</span>
                <strong className={lastStepResult.actual_ground_truth?.attack_occurred ? "text-rose-400" : "text-emerald-400"}>
                  {lastStepResult.actual_ground_truth?.attack_occurred ? "YES" : "NO"}
                </strong>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Actual Category:</span>
                <strong className="text-slate-200">{lastStepResult.actual_ground_truth?.category}</strong>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Actual Advance Lead:</span>
                <strong className="text-emerald-400 font-bold">
                  {lastStepResult.actual_ground_truth?.lead_time_sec ? `+${lastStepResult.actual_ground_truth.lead_time_sec.toFixed(1)}s` : "—"}
                </strong>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <EmptyState title="REPLAY IDLE" message="Click 'Start Replay' or 'Step 1 Window' to stream historical network traffic." />
      )}
    </div>
  );
}
