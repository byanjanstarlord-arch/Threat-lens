"use client";

import React, { useState } from "react";
import { Settings, Sliders, Database, Shield, Server } from "lucide-react";

export default function SettingsPage() {
  const [weights, setWeights] = useState({
    classifier: 45,
    anomaly: 25,
    forecast: 30
  });

  const [thresholds, setThresholds] = useState({
    medium: 30,
    high: 60,
    critical: 85
  });

  return (
    <div className="space-y-6 max-w-[1200px] mx-auto">
      <div>
        <h1 className="text-base font-bold tracking-wider uppercase text-white font-mono flex items-center gap-2">
          <Settings className="w-5 h-5 text-cyan-400" />
          ThreatLens Configuration & Policy Engine
        </h1>
        <p className="text-xs text-slate-400">
          Centralized parameter management for Risk Engine weights, alert thresholds, and temporal windowing.
        </p>
      </div>

      {/* Risk Engine Weights */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
        <h3 className="text-sm font-bold tracking-wider uppercase text-slate-200 flex items-center gap-2">
          <Sliders className="w-4 h-4 text-cyan-400" />
          Multi-Factor Risk Weights
        </h3>
        <p className="text-xs text-slate-400">
          Weights used by the composite Risk Engine to combine classifier confidence, Isolation Forest anomaly score, and temporal forecast probability.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs font-mono">
          <div className="p-4 rounded-lg bg-slate-950/60 border border-slate-800">
            <span className="text-slate-400 block mb-1">Classifier Signal Weight</span>
            <span className="text-2xl font-bold text-cyan-400">{weights.classifier}%</span>
            <p className="text-[10px] text-slate-500 mt-1">Supervised attack category probability</p>
          </div>
          <div className="p-4 rounded-lg bg-slate-950/60 border border-slate-800">
            <span className="text-slate-400 block mb-1">Anomaly Signal Weight</span>
            <span className="text-2xl font-bold text-amber-400">{weights.anomaly}%</span>
            <p className="text-[10px] text-slate-500 mt-1">Unsupervised statistical distance</p>
          </div>
          <div className="p-4 rounded-lg bg-slate-950/60 border border-slate-800">
            <span className="text-slate-400 block mb-1">Forecast Signal Weight</span>
            <span className="text-2xl font-bold text-rose-400">{weights.forecast}%</span>
            <p className="text-[10px] text-slate-500 mt-1">5-minute future horizon probability</p>
          </div>
        </div>
      </div>

      {/* Risk Level Categorization Thresholds */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
        <h3 className="text-sm font-bold tracking-wider uppercase text-slate-200 flex items-center gap-2">
          <Shield className="w-4 h-4 text-amber-500" />
          Alert Severity Thresholds
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 text-xs font-mono">
          <div className="p-3.5 rounded-lg bg-slate-950/60 border border-emerald-900/40">
            <span className="text-emerald-400 block mb-1 font-bold">LOW RISK</span>
            <span className="text-lg font-bold text-white">&lt; {thresholds.medium}%</span>
            <span className="text-[10px] text-slate-500 block mt-1">Telemetry log only</span>
          </div>
          <div className="p-3.5 rounded-lg bg-slate-950/60 border border-yellow-900/40">
            <span className="text-yellow-400 block mb-1 font-bold">MEDIUM RISK</span>
            <span className="text-lg font-bold text-white">&ge; {thresholds.medium}%</span>
            <span className="text-[10px] text-slate-500 block mt-1">Elevated attention</span>
          </div>
          <div className="p-3.5 rounded-lg bg-slate-950/60 border border-amber-900/40">
            <span className="text-amber-400 block mb-1 font-bold">HIGH RISK</span>
            <span className="text-lg font-bold text-white">&ge; {thresholds.high}%</span>
            <span className="text-[10px] text-amber-400 block mt-1">Triggers SOC alert</span>
          </div>
          <div className="p-3.5 rounded-lg bg-slate-950/60 border border-rose-900/40">
            <span className="text-rose-400 block mb-1 font-bold">CRITICAL RISK</span>
            <span className="text-lg font-bold text-white">&ge; {thresholds.critical}%</span>
            <span className="text-[10px] text-rose-400 block mt-1">High priority incident</span>
          </div>
        </div>
      </div>

      {/* System & Hardware Environment */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-3">
        <h3 className="text-sm font-bold tracking-wider uppercase text-slate-200 flex items-center gap-2">
          <Server className="w-4 h-4 text-slate-400" />
          Runtime Environment & Storage
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono">
          <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 space-y-1">
            <div className="text-slate-500">Database Engine:</div>
            <div className="text-slate-200">SQLite / PostgreSQL (SQLAlchemy ORM)</div>
          </div>
          <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 space-y-1">
            <div className="text-slate-500">Temporal Parameters:</div>
            <div className="text-slate-200">Window: 60s | Horizon: 300s (5 min)</div>
          </div>
        </div>
      </div>
    </div>
  );
}
