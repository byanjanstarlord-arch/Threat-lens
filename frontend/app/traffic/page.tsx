"use client";

import React, { useEffect, useState } from "react";
import { Activity, ArrowDownUp, BarChart2, ShieldCheck } from "lucide-react";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend
} from "recharts";
import EmptyState from "@/components/EmptyState";

export default function TrafficPage() {
  const [timeline, setTimeline] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchTraffic = async () => {
    try {
      const res = await fetch("/api/traffic/timeline?limit=50");
      if (res.ok) setTimeline(await res.json());
    } catch (e) {
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTraffic();
    const interval = setInterval(fetchTraffic, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto">
      <div>
        <h1 className="text-base font-bold tracking-wider uppercase text-white font-mono flex items-center gap-2">
          <Activity className="w-5 h-5 text-cyan-400" />
          Network Traffic Telemetry
        </h1>
        <p className="text-xs text-slate-400">
          Real-time flow volume, byte rates, packet rates, and TCP control flag dynamics.
        </p>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Byte Rate & Packet Rate */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
          <h3 className="text-sm font-bold tracking-wider uppercase text-slate-200 mb-1">
            Throughput (Byte Rate vs Packet Rate)
          </h3>
          <p className="text-xs text-slate-500 font-mono mb-4">
            Flow throughput per 1-minute window
          </p>
          {timeline.length > 0 ? (
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={timeline}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="window_id" stroke="#64748b" tick={{ fontSize: 10 }} />
                  <YAxis stroke="#64748b" tick={{ fontSize: 10 }} />
                  <Tooltip contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", fontSize: "12px" }} />
                  <Legend wrapperStyle={{ fontSize: "11px" }} />
                  <Area type="monotone" dataKey="byte_rate" stroke="#06b6d4" fill="#06b6d4" fillOpacity={0.2} name="Byte Rate (B/s)" />
                  <Area type="monotone" dataKey="packet_rate" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.2} name="Packet Rate (pkts/s)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState title="NO TELEMETRY" message="Awaiting traffic windows." className="h-64" />
          )}
        </div>

        {/* TCP Flags Activity */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
          <h3 className="text-sm font-bold tracking-wider uppercase text-slate-200 mb-1">
            TCP Control Flags Distribution
          </h3>
          <p className="text-xs text-slate-500 font-mono mb-4">
            SYN vs ACK flag activity indicates connection initiation vs acknowledgment
          </p>
          {timeline.length > 0 ? (
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={timeline}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="window_id" stroke="#64748b" tick={{ fontSize: 10 }} />
                  <YAxis stroke="#64748b" tick={{ fontSize: 10 }} />
                  <Tooltip contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", fontSize: "12px" }} />
                  <Legend wrapperStyle={{ fontSize: "11px" }} />
                  <Bar dataKey="syn_flag_count" fill="#f59e0b" name="SYN Flags" />
                  <Bar dataKey="ack_flag_count" fill="#10b981" name="ACK Flags" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState title="NO FLAG DATA" message="Awaiting traffic windows." className="h-64" />
          )}
        </div>
      </div>
    </div>
  );
}
