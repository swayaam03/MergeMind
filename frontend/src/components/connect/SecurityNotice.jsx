import React from 'react';
import { Lock, ShieldCheck } from 'lucide-react';

export default function SecurityNotice() {
  return (
    <div className="w-full neu-recessed rounded-xl p-4 border border-white/[0.04] mt-6">
      <div className="flex items-center gap-2 text-xs font-mono font-medium text-slate-300 mb-1">
        <Lock className="w-3.5 h-3.5 text-sky-400" />
        <span>Secure GitHub connection</span>
      </div>
      <p className="text-[11px] text-slate-400 leading-relaxed">
        Your GitHub credentials are handled through GitHub's authorization flow. MergeMind only requests the access required for its workflow.
      </p>
    </div>
  );
}
