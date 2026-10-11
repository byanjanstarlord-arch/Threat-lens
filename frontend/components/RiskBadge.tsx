import React from "react";

interface RiskBadgeProps {
  level: string;
  score?: number;
  showScore?: boolean;
  className?: string;
}

export default function RiskBadge({ level, score, showScore = false, className = "" }: RiskBadgeProps) {
  const norm = (level || "LOW").toUpperCase();
  
  const getStyles = () => {
    switch (norm) {
      case "CRITICAL":
        return "bg-rose-950/60 text-rose-400 border-rose-800/80 shadow-[0_0_12px_rgba(244,63,94,0.3)]";
      case "HIGH":
        return "bg-amber-950/60 text-amber-400 border-amber-800/80 shadow-[0_0_12px_rgba(245,158,11,0.3)]";
      case "MEDIUM":
        return "bg-yellow-950/50 text-yellow-300 border-yellow-800/60";
      case "LOW":
        return "bg-emerald-950/50 text-emerald-400 border-emerald-800/60";
      default:
        return "bg-slate-800 text-slate-400 border-slate-700";
    }
  };

  const getDotColor = () => {
    switch (norm) {
      case "CRITICAL": return "bg-rose-500 animate-ping";
      case "HIGH": return "bg-amber-500 animate-pulse";
      case "MEDIUM": return "bg-yellow-400";
      case "LOW": return "bg-emerald-400";
      default: return "bg-slate-400";
    }
  };

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider border ${getStyles()} ${className}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${getDotColor()}`} />
      {norm}
      {showScore && score !== undefined && (
        <span className="opacity-75 font-mono ml-0.5">({(score * 100).toFixed(1)}%)</span>
      )}
    </span>
  );
}
