import React from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  Terminal,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Loader2,
  Cpu,
  Layers,
  Check,
  ExternalLink,
  Lock,
} from 'lucide-react';

export default function VerificationCard({
  report,
  verifying,
  onVerify,
  error,
}) {
  return (
    <div className="mt-6 rounded-2xl neu-panel p-6 border border-white/[0.08] relative overflow-hidden">
      {/* Background ambient subtle glow */}
      <div className="absolute top-0 right-0 w-80 h-80 bg-sky-500/5 rounded-full blur-[100px] pointer-events-none" />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-white/[0.04]">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono uppercase tracking-wider bg-sky-500/10 text-sky-400 border border-sky-500/20">
              <Lock className="w-3 h-3 text-sky-400" />
              Docker Sandbox Verification
            </span>
            <span className="text-[10px] font-mono text-slate-500">
              --network none • No Host Secrets
            </span>
          </div>
          <h3 className="text-base sm:text-lg font-bold text-white flex items-center gap-2">
            <span>Deterministic Verification Pipeline</span>
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Strict zero-LLM validation: syntax parsing, build checking, test suite execution, and Semgrep security audit.
          </p>
        </div>

        <button
          type="button"
          onClick={onVerify}
          disabled={verifying}
          className="neu-glow-btn px-5 py-2.5 rounded-xl text-xs font-semibold text-white flex items-center justify-center gap-2 self-start sm:self-auto disabled:opacity-50"
        >
          {verifying ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin text-sky-300" />
              <span>Verifying in Sandbox...</span>
            </>
          ) : (
            <>
              <ShieldCheck className="w-3.5 h-3.5 text-sky-300" />
              <span>{report ? 'Re-verify Proposal' : 'Verify Merge Proposal'}</span>
            </>
          )}
        </button>
      </div>

      {/* Error state if verification request failed */}
      {error && (
        <div className="mt-4 p-4 rounded-xl bg-rose-950/20 border border-rose-500/20 flex items-center gap-3">
          <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0" />
          <p className="text-xs text-rose-300">{error}</p>
        </div>
      )}

      {/* Loading animation state */}
      {verifying && (
        <div className="py-10 flex flex-col items-center justify-center text-center">
          <div className="w-12 h-12 rounded-2xl neu-recessed flex items-center justify-center mb-4 border border-sky-500/30">
            <Loader2 className="w-6 h-6 text-sky-400 animate-spin" />
          </div>
          <h4 className="text-sm font-semibold text-white">Running Isolated Verification</h4>
          <p className="text-xs text-slate-400 max-w-sm mt-1">
            Applying proposed merge to ephemeral container workspace and running deterministic checks...
          </p>
        </div>
      )}

      {/* Verification Results Dashboard */}
      {!verifying && report && (
        <div className="mt-5 space-y-5 animate-in fade-in duration-300">
          {/* Overall Verdict Banner */}
          <div
            className={`p-4 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
              report.overall_status === 'PASSED'
                ? 'bg-emerald-950/20 border-emerald-500/30 text-emerald-300'
                : report.overall_status === 'FAILED'
                ? 'bg-rose-950/20 border-rose-500/30 text-rose-300'
                : 'bg-amber-950/20 border-amber-500/30 text-amber-300'
            }`}
          >
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl neu-recessed flex items-center justify-center flex-shrink-0">
                {report.overall_status === 'PASSED' ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                ) : (
                  <ShieldAlert className="w-5 h-5 text-rose-400" />
                )}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-bold tracking-wider uppercase">
                    Verification Verdict: {report.overall_status}
                  </span>
                  <span className="text-[10px] font-mono text-slate-400">
                    ({report.total_duration_seconds}s)
                  </span>
                </div>
                <p className="text-xs text-slate-300 mt-0.5">
                  {report.overall_status === 'PASSED'
                    ? 'All deterministic stages passed. Code is structurally sound and free of security risks.'
                    : 'Regressions or security warnings detected. Review failing items before applying.'}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
              <span className="px-2 py-1 rounded bg-black/40 border border-white/5">
                Lang: {report.language}
              </span>
              <span className="px-2 py-1 rounded bg-black/40 border border-white/5">
                Docker: {report.docker_used ? 'Isolated' : 'In-Process'}
              </span>
            </div>
          </div>

          {/* 4 Stage Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            
            {/* Stage 1: Syntax Validation */}
            <div className="p-4 rounded-xl neu-recessed border border-white/[0.04] flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Terminal className="w-4 h-4 text-sky-400" />
                    <span className="text-xs font-semibold text-white">1. Syntax Validation</span>
                  </div>
                  <span
                    className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                      report.syntax.status === 'PASS'
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                    }`}
                  >
                    {report.syntax.status}
                  </span>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  {report.syntax.summary}
                </p>
                {report.syntax.failing_items && report.syntax.failing_items.length > 0 && (
                  <div className="mt-2.5 p-2 rounded bg-black/40 border border-rose-500/20 text-[11px] font-mono text-rose-300 max-h-24 overflow-y-auto">
                    {report.syntax.failing_items.map((item, i) => (
                      <div key={i}>• {item}</div>
                    ))}
                  </div>
                )}
              </div>
              <div className="mt-3 pt-2 border-t border-white/[0.03] text-[10px] font-mono text-slate-500">
                Duration: {report.syntax.duration_seconds}s
              </div>
            </div>

            {/* Stage 2: Build / Compilation */}
            <div className="p-4 rounded-xl neu-recessed border border-white/[0.04] flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Cpu className="w-4 h-4 text-indigo-400" />
                    <span className="text-xs font-semibold text-white">2. Build Check</span>
                  </div>
                  <span
                    className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                      report.build.status === 'PASS'
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : report.build.status === 'SKIPPED'
                        ? 'bg-slate-500/10 text-slate-400 border border-slate-500/20'
                        : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                    }`}
                  >
                    {report.build.status}
                  </span>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  {report.build.summary}
                </p>
                {report.build.failing_items && report.build.failing_items.length > 0 && (
                  <div className="mt-2.5 p-2 rounded bg-black/40 border border-rose-500/20 text-[11px] font-mono text-rose-300 max-h-24 overflow-y-auto">
                    {report.build.failing_items.map((item, i) => (
                      <div key={i}>• {item}</div>
                    ))}
                  </div>
                )}
              </div>
              <div className="mt-3 pt-2 border-t border-white/[0.03] text-[10px] font-mono text-slate-500">
                Duration: {report.build.duration_seconds}s
              </div>
            </div>

            {/* Stage 3: Test Suite Execution */}
            <div className="p-4 rounded-xl neu-recessed border border-white/[0.04] flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Layers className="w-4 h-4 text-cyan-400" />
                    <span className="text-xs font-semibold text-white">3. Tests Execution</span>
                  </div>
                  <span
                    className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                      report.tests.status === 'PASS'
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : report.tests.status === 'SKIPPED'
                        ? 'bg-slate-500/10 text-slate-400 border border-slate-500/20'
                        : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                    }`}
                  >
                    {report.tests.status}
                  </span>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  {report.tests.summary}
                </p>
                {report.tests.failing_items && report.tests.failing_items.length > 0 && (
                  <div className="mt-2.5 p-2 rounded bg-black/40 border border-rose-500/20 text-[11px] font-mono text-rose-300 max-h-24 overflow-y-auto">
                    {report.tests.failing_items.map((item, i) => (
                      <div key={i}>• {item}</div>
                    ))}
                  </div>
                )}
              </div>
              <div className="mt-3 pt-2 border-t border-white/[0.03] text-[10px] font-mono text-slate-500">
                Duration: {report.tests.duration_seconds}s
              </div>
            </div>

            {/* Stage 4: Security Audit */}
            <div className="p-4 rounded-xl neu-recessed border border-white/[0.04] flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-violet-400" />
                    <span className="text-xs font-semibold text-white">4. Security Scan</span>
                  </div>
                  <span
                    className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                      report.security.status === 'PASS'
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                    }`}
                  >
                    {report.security.status}
                  </span>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  {report.security.summary}
                </p>
                {report.security.failing_items && report.security.failing_items.length > 0 && (
                  <div className="mt-2.5 p-2 rounded bg-black/40 border border-rose-500/20 text-[11px] font-mono text-rose-300 max-h-24 overflow-y-auto">
                    {report.security.failing_items.map((item, i) => (
                      <div key={i}>• {item}</div>
                    ))}
                  </div>
                )}
              </div>
              <div className="mt-3 pt-2 border-t border-white/[0.03] text-[10px] font-mono text-slate-500">
                Duration: {report.security.duration_seconds}s
              </div>
            </div>

          </div>

          {/* Sandbox Metadata Footer */}
          <div className="p-3 rounded-lg bg-black/30 border border-white/[0.03] flex flex-wrap items-center justify-between gap-3 text-[11px] font-mono text-slate-500">
            <div>Target File: <code className="text-slate-300">{report.target_file}</code></div>
            <div>Workspace ID: <code className="text-slate-400">{report.sandbox_details?.workspace_id || 'isolated'}</code></div>
            <div className="flex items-center gap-1.5 text-emerald-400">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              Clean Workspace Exited
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
