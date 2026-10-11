import React from "react";
import { Database, AlertCircle } from "lucide-react";

interface EmptyStateProps {
  title?: string;
  message?: string;
  className?: string;
}

export default function EmptyState({
  title = "NO DATA AVAILABLE",
  message = "No real data has been ingested or generated yet. Run the dataset replay or trigger prediction to populate.",
  className = ""
}: EmptyStateProps) {
  return (
    <div className={`flex flex-col items-center justify-center p-8 text-center border border-dashed border-slate-800 rounded-xl bg-slate-900/30 ${className}`}>
      <div className="w-12 h-12 rounded-full bg-slate-800/60 border border-slate-700 flex items-center justify-center mb-3 text-slate-400">
        <Database className="w-5 h-5" />
      </div>
      <h4 className="text-sm font-semibold tracking-wider uppercase text-slate-300 mb-1 flex items-center gap-1.5">
        <AlertCircle className="w-4 h-4 text-amber-500" />
        {title}
      </h4>
      <p className="text-xs text-slate-500 max-w-sm">
        {message}
      </p>
    </div>
  );
}
