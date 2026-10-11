"use client";

import React, { useEffect, useState } from "react";
import { ShieldAlert, Terminal, ArrowRight, Filter } from "lucide-react";
import RiskBadge from "@/components/RiskBadge";
import EmptyState from "@/components/EmptyState";

export default function AttacksPage() {
  const [attacks, setAttacks] = useState<any[]>([]);
  const [filter, setFilter] = useState<string>("ALL");
  const [loading, setLoading] = useState(true);

  const fetchAttacks = async () => {
    try {
      const res = await fetch("/api/attacks?limit=100");
      if (res.ok) setAttacks(await res.json());
    } catch (e) {
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAttacks();
    const interval = setInterval(fetchAttacks, 3000);
    return () => clearInterval(interval);
  }, []);

  const filtered = filter === "ALL" ? attacks : attacks.filter((a) => a.attack_type === filter);
  const categories = Array.from(new Set(attacks.map((a) => a.attack_type)));

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-base font-bold tracking-wider uppercase text-white font-mono flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-rose-500" />
            Detected Attack Incidents
          </h1>
          <p className="text-xs text-slate-400">
            Confirmed malicious flows classified by the production AI model with SHAP feature explanations.
          </p>
        </div>

        {/* Filter */}
        <div className="flex items-center gap-2 text-xs font-mono">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="bg-slate-900 border border-slate-700 text-slate-200 rounded px-2.5 py-1 text-xs outline-none"
          >
            <option value="ALL">All Categories ({attacks.length})</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {c} ({attacks.filter((a) => a.attack_type === c).length})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Incidents Table */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
        {filtered.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-3">ID</th>
                  <th className="py-2.5 px-3">Timestamp</th>
                  <th className="py-2.5 px-3">Attack Category</th>
                  <th className="py-2.5 px-3">Dest Port</th>
                  <th className="py-2.5 px-3">Confidence</th>
                  <th className="py-2.5 px-3">Risk Level</th>
                  <th className="py-2.5 px-3">SHAP Top Drivers</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filtered.map((att) => (
                  <tr key={att.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-2 px-3 font-semibold text-slate-400">#{att.id}</td>
                    <td className="py-2 px-3 text-slate-400">{att.timestamp?.slice(11, 19) || "—"}</td>
                    <td className="py-2 px-3 font-bold text-rose-400">{att.attack_type}</td>
                    <td className="py-2 px-3 text-slate-300">{att.destination_port || "—"}</td>
                    <td className="py-2 px-3 text-cyan-400">{(att.confidence * 100).toFixed(1)}%</td>
                    <td className="py-2 px-3">
                      <RiskBadge level={att.risk_level} />
                    </td>
                    <td className="py-2 px-3">
                      <div className="flex flex-wrap gap-1">
                        {(att.details?.shap_drivers || []).map((driver: string, i: number) => (
                          <span
                            key={i}
                            className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 border border-slate-700"
                          >
                            {driver}
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="NO ATTACK EVENTS" message="No confirmed attacks detected in current session." />
        )}
      </div>
    </div>
  );
}
