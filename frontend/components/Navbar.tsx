"use client";

import React, { useEffect, useState } from "react";
import { ShieldAlert, Play, Pause, FastForward, Activity, RefreshCw } from "lucide-react";

export default function Navbar() {
  const [health, setHealth] = useState<any>(null);
  const [replayStatus, setReplayStatus] = useState<any>(null);

  const fetchStatus = async () => {
    try {
      const [hRes, rRes] = await Promise.all([
        fetch("/api/health"),
        fetch("/api/replay/status")
      ]);
      if (hRes.ok) setHealth(await hRes.json());
      if (rRes.ok) setReplayStatus(await rRes.json());
    } catch (e) {
      // Backend not ready
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleToggleReplay = async () => {
    try {
      if (replayStatus?.is_running) {
        await fetch("/api/replay/stop", { method: "POST" });
      } else {
        await fetch("/api/replay/start?speed=2.0", { method: "POST" });
      }
      fetchStatus();
    } catch (e) {}
  };

  const handleStepReplay = async () => {
    try {
      await fetch("/api/replay/step", { method: "POST" });
      fetchStatus();
    } catch (e) {}
  };

  return (
    <header className="h-16 border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-50">
      {/* Brand */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-[0_0_15px_rgba(6,182,212,0.4)]">
          <ShieldAlert className="w-5 h-5 text-slate-950 font-bold" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-extrabold tracking-wider text-base bg-gradient-to-r from-white via-slate-200 to-cyan-400 bg-clip-text text-transparent">
              THREATLENS AI
            </span>
            <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-cyan-950 text-cyan-400 border border-cyan-800/50">
              {health?.active_model_version || "v1"}
            </span>
          </div>
          <p className="text-[10px] text-slate-400 tracking-wide font-mono">
            &quot;See the Threat Before It Strikes.&quot;
          </p>
        </div>
      </div>

      {/* Mode & Replay Controls */}
      <div className="flex items-center gap-4">
        {/* Replay Deck Indicator */}
        <div className="hidden md:flex items-center gap-2 bg-slate-900/90 border border-slate-800 px-3 py-1.5 rounded-lg text-xs font-mono">
          <span className="flex items-center gap-1.5 text-cyan-400 font-semibold">
            <Activity className="w-3.5 h-3.5 animate-pulse text-cyan-400" />
            Dataset Replay Mode
          </span>
          <span className="text-slate-600">|</span>
          <span className="text-slate-400">
            Window: <strong className="text-slate-200">{replayStatus?.current_window_index ?? 0}</strong> / {replayStatus?.total_windows ?? 743}
          </span>
          <span className="text-slate-600">|</span>
          <button
            onClick={handleToggleReplay}
            className={`flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-sans font-medium transition-colors ${
              replayStatus?.is_running
                ? "bg-amber-950/80 text-amber-300 border border-amber-800 hover:bg-amber-900"
                : "bg-cyan-950/80 text-cyan-300 border border-cyan-800 hover:bg-cyan-900"
            }`}
          >
            {replayStatus?.is_running ? (
              <>
                <Pause className="w-3 h-3" /> Pause
              </>
            ) : (
              <>
                <Play className="w-3 h-3" /> Play
              </>
            )}
          </button>
          <button
            onClick={handleStepReplay}
            title="Step 1 Window"
            className="p-1 rounded bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white"
          >
            <FastForward className="w-3 h-3" />
          </button>
        </div>

        {/* Backend Connectivity Status */}
        <div className="flex items-center gap-2 text-xs font-mono">
          <div className={`w-2 h-2 rounded-full ${health ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]" : "bg-rose-500 animate-ping"}`} />
          <span className="text-slate-400 hidden sm:inline">
            {health ? "SOC ONLINE" : "CONNECTING..."}
          </span>
        </div>
      </div>
    </header>
  );
}
