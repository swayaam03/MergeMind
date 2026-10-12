import React, { useState } from 'react';
import {
  GitMerge,
  Workflow,
  Sparkles,
  RefreshCw,
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ArrowRight,
  ChevronDown,
  ChevronUp,
  FileText,
  ShieldAlert,
  ListChecks,
  Loader2,
  GitCompare,
  Code2,
  Layers,
} from 'lucide-react';

export default function WorkflowPanel({
  workflowData,
  running,
  onRunWorkflow,
  maxRetries = 2,
  onChangeMaxRetries,
  error,
}) {
  const [expandedAttempt, setExpandedAttempt] = useState(null);
  const [showEvents, setShowEvents] = useState(false);

  const status = workflowData?.status;
  const history = workflowData?.history || [];
  const explanation = workflowData?.explanation;
  const events = workflowData?.events || [];
  const retryCount = workflowData?.retry_count ?? 0;

  const toggleAttempt = (idx) => {
    setExpandedAttempt(expandedAttempt === idx ? null : idx);
  };

  return (
    <div className="rounded-2xl neu-panel p-6 border border-white/[0.08] relative overflow-hidden space-y-6">
      {/* Background ambient glow */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-500/5 rounded-full blur-[120px] pointer-events-none" />

      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-white/[0.04]">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono uppercase tracking-wider bg-violet-500/10 text-violet-400 border border-violet-500/20">
              <Workflow className="w-3 h-3 text-violet-400" />
              Autonomous LangGraph Workflow
            </span>
            <span className="text-[10px] font-mono text-slate-500">
              StateGraph • Automated Retry • Explanation
            </span>
          </div>
          <h3 className="text-base sm:text-lg font-bold text-white flex items-center gap-2">
            <span>Adaptive Retry & Resolution Engine</span>
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Iterates through merge proposal generation and deterministic Docker verification until verified or safely escalated.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-3 self-start sm:self-auto flex-wrap">
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl neu-recessed border border-white/[0.05] text-xs font-mono text-slate-400">
            <span>Max Retries:</span>
            <select
              value={maxRetries}
              onChange={(e) => onChangeMaxRetries && onChangeMaxRetries(Number(e.target.value))}
              disabled={running}
              className="bg-transparent text-sky-400 font-bold focus:outline-none cursor-pointer"
            >
              <option value={1} className="bg-slate-900 text-white">1</option>
              <option value={2} className="bg-slate-900 text-white">2</option>
              <option value={3} className="bg-slate-900 text-white">3</option>
            </select>
          </div>

          <button
            type="button"
            onClick={onRunWorkflow}
            disabled={running}
            className="neu-glow-btn px-5 py-2.5 rounded-xl text-xs font-semibold text-white flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {running ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin text-sky-300" />
                <span>Running StateGraph...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-3.5 h-3.5 text-sky-300" />
                <span>{workflowData ? 'Re-run Workflow' : 'Start Autonomous Workflow'}</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Running Banner */}
      {running && (
        <div className="p-6 rounded-xl neu-recessed border border-sky-500/20 bg-sky-950/10 text-center space-y-3">
          <div className="flex items-center justify-center gap-2 text-sky-400">
            <Loader2 className="w-5 h-5 animate-spin" />
            <span className="text-sm font-bold font-mono">LangGraph Workflow in Progress</span>
          </div>
          <p className="text-xs text-slate-300 max-w-lg mx-auto">
            Executing state nodes: generating proposal via LiteLLM ➔ executing sandbox tests & security audit ➔ evaluating feedback for retry...
          </p>
          <div className="flex items-center justify-center gap-2 text-[11px] font-mono text-slate-400 pt-1">
            <span className="w-2 h-2 rounded-full bg-sky-400 animate-ping" />
            <span>Deterministic verification loop active</span>
          </div>
        </div>
      )}

      {/* Error Notice */}
      {!running && error && (
        <div className="p-4 rounded-xl bg-rose-950/30 border border-rose-500/30 flex items-start gap-3">
          <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-xs font-bold text-rose-300 font-mono">Workflow Execution Error</p>
            <p className="text-xs text-rose-400/90 mt-0.5 leading-relaxed">{error}</p>
          </div>
          <button
            onClick={onRunWorkflow}
            className="text-xs text-rose-300 hover:text-white underline font-medium"
          >
            Retry
          </button>
        </div>
      )}

      {/* Workflow Output Results */}
      {!running && workflowData && (
        <div className="space-y-6">

          {/* Status Banner */}
          <div
            className={`p-4 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${
              status === 'verified'
                ? 'bg-emerald-950/20 border-emerald-500/30 text-emerald-300'
                : status === 'escalated'
                ? 'bg-amber-950/20 border-amber-500/30 text-amber-300'
                : 'bg-rose-950/20 border-rose-500/30 text-rose-300'
            }`}
          >
            <div className="flex items-start sm:items-center gap-3">
              {status === 'verified' ? (
                <CheckCircle2 className="w-6 h-6 text-emerald-400 flex-shrink-0" />
              ) : status === 'escalated' ? (
                <ShieldAlert className="w-6 h-6 text-amber-400 flex-shrink-0" />
              ) : (
                <AlertTriangle className="w-6 h-6 text-rose-400 flex-shrink-0" />
              )}
              <div>
                <div className="flex items-center gap-2">
                  <h4 className="text-sm font-bold uppercase tracking-wider font-mono">
                    {status === 'verified'
                      ? 'Merge Resolution Verified'
                      : status === 'escalated'
                      ? 'Escalated to Human Review'
                      : 'Conflict Unresolved'}
                  </h4>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/10 text-white">
                    {status}
                  </span>
                </div>
                <p className="text-xs text-slate-300 mt-0.5">
                  {status === 'verified'
                    ? `Passed all sandbox verification stages after ${retryCount} attempt${retryCount > 1 ? 's' : ''}.`
                    : status === 'escalated'
                    ? `Retries exhausted (${retryCount}/${workflowData.max_retries || 2}). Explanation report generated below.`
                    : 'Merge Agent could not safely synthesize a proposal.'}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 text-xs font-mono text-slate-400 self-end sm:self-auto">
              <span>Attempts:</span>
              <span className="text-white font-bold px-2 py-0.5 rounded bg-white/[0.06] border border-white/10">
                {retryCount} / {workflowData.max_retries || 2}
              </span>
            </div>
          </div>

          {/* ============================================================ */}
          {/* Explanation Report Card (Displayed when escalated or available) */}
          {/* ============================================================ */}
          {explanation && (
            <div className="neu-panel rounded-xl p-5 border border-amber-500/30 bg-amber-950/10 space-y-5">
              <div className="flex items-start gap-3 pb-3 border-b border-amber-500/20">
                <div className="w-9 h-9 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 flex-shrink-0">
                  <FileText className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-white flex items-center gap-2">
                    <span>Explanation Agent Briefing</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                      Human Review Package
                    </span>
                  </h4>
                  <p className="text-xs text-slate-300 mt-0.5 leading-relaxed">
                    {explanation.summary}
                  </p>
                </div>
              </div>

              {/* Conflicting Intents Breakdown (3-column comparison) */}
              {explanation.conflicting_intents && (
                <div className="space-y-2">
                  <h5 className="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono flex items-center gap-1.5">
                    <GitCompare className="w-3.5 h-3.5 text-sky-400" />
                    <span>Conflicting Architectural Intents</span>
                  </h5>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <div className="p-3.5 rounded-xl neu-recessed border border-white/[0.05] space-y-1">
                      <div className="text-[11px] font-mono font-bold text-slate-400 flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-slate-500" />
                        <span>Base (Ancestor) Intent</span>
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed">
                        {explanation.conflicting_intents.base || 'Original baseline implementation.'}
                      </p>
                    </div>

                    <div className="p-3.5 rounded-xl neu-recessed border border-sky-500/20 bg-sky-950/10 space-y-1">
                      <div className="text-[11px] font-mono font-bold text-sky-400 flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-sky-400" />
                        <span>Local (Target Branch) Intent</span>
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed">
                        {explanation.conflicting_intents.local || 'Target branch changes.'}
                      </p>
                    </div>

                    <div className="p-3.5 rounded-xl neu-recessed border border-violet-500/20 bg-violet-950/10 space-y-1">
                      <div className="text-[11px] font-mono font-bold text-violet-400 flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-violet-400" />
                        <span>Remote (PR Head) Intent</span>
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed">
                        {explanation.conflicting_intents.remote || 'Pull request incoming changes.'}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Failure Root Causes & Recommended Actions */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Failure Reasons */}
                {explanation.failure_reasons && explanation.failure_reasons.length > 0 && (
                  <div className="p-4 rounded-xl neu-recessed border border-rose-500/20 bg-rose-950/10 space-y-2">
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 text-rose-400" />
                      <h5 className="text-xs font-bold uppercase tracking-wider text-rose-300 font-mono">
                        Verification Blockers
                      </h5>
                    </div>
                    <ul className="space-y-1.5 text-xs text-slate-300">
                      {explanation.failure_reasons.map((reason, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <span className="text-rose-400 select-none font-mono">✕</span>
                          <span>{reason}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Recommended Actions */}
                {explanation.recommended_actions && explanation.recommended_actions.length > 0 && (
                  <div className="p-4 rounded-xl neu-recessed border border-emerald-500/20 bg-emerald-950/10 space-y-2">
                    <div className="flex items-center gap-2">
                      <ListChecks className="w-4 h-4 text-emerald-400" />
                      <h5 className="text-xs font-bold uppercase tracking-wider text-emerald-300 font-mono">
                        Recommended Next Steps
                      </h5>
                    </div>
                    <ul className="space-y-1.5 text-xs text-slate-300">
                      {explanation.recommended_actions.map((act, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <span className="text-emerald-400 select-none font-mono">➔</span>
                          <span>{act}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ============================================================ */}
          {/* Attempt History Accordion                                    */}
          {/* ============================================================ */}
          {history.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono flex items-center gap-2">
                  <Clock className="w-3.5 h-3.5 text-sky-400" />
                  <span>Attempt History & Diagnostics ({history.length})</span>
                </h4>
                <span className="text-[11px] text-slate-500 font-mono">
                  Feedback was fed into next prompt
                </span>
              </div>

              <div className="space-y-2">
                {history.map((att, idx) => {
                  const isExpanded = expandedAttempt === idx;
                  const vStatus = att.verification?.overall_status || 'UNKNOWN';
                  const isPass = String(vStatus).toUpperCase() === 'PASSED';

                  return (
                    <div
                      key={idx}
                      className="rounded-xl neu-recessed border border-white/[0.04] overflow-hidden transition-all"
                    >
                      <button
                        type="button"
                        onClick={() => toggleAttempt(idx)}
                        className="w-full p-3.5 flex items-center justify-between text-left hover:bg-white/[0.02] transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-white/[0.06] text-white">
                            Attempt #{att.attempt_number || idx + 1}
                          </span>
                          <span
                            className={`text-[11px] font-mono px-2 py-0.5 rounded border ${
                              isPass
                                ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                                : 'bg-rose-500/15 text-rose-300 border-rose-500/30'
                            }`}
                          >
                            {vStatus}
                          </span>
                          <span className="text-xs text-slate-300 truncate max-w-md hidden sm:inline-block">
                            {att.proposal?.explanation || 'Merge proposal produced'}
                          </span>
                        </div>

                        <div className="flex items-center gap-2 text-slate-400">
                          {isExpanded ? (
                            <ChevronUp className="w-4 h-4 text-slate-400" />
                          ) : (
                            <ChevronDown className="w-4 h-4 text-slate-400" />
                          )}
                        </div>
                      </button>

                      {isExpanded && (
                        <div className="p-4 border-t border-white/[0.04] bg-slate-950/40 space-y-3">
                          {att.proposal?.explanation && (
                            <div>
                              <span className="text-[10px] font-mono uppercase text-slate-400 font-bold">
                                Proposal Explanation:
                              </span>
                              <p className="text-xs text-slate-300 mt-0.5 leading-relaxed">
                                {att.proposal.explanation}
                              </p>
                            </div>
                          )}

                          {att.verification?.summary && (
                            <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                              <span className="text-[10px] font-mono uppercase text-slate-400 font-bold">
                                Verification Diagnostic:
                              </span>
                              <p className="text-xs text-slate-300 mt-0.5 leading-relaxed font-mono">
                                {att.verification.summary}
                              </p>
                            </div>
                          )}

                          {att.proposal?.merged_code && (
                            <div>
                              <div className="flex items-center justify-between mb-1">
                                <span className="text-[10px] font-mono uppercase text-slate-400 font-bold">
                                  Resolved Code for Attempt #{att.attempt_number}:
                                </span>
                              </div>
                              <pre className="p-3 rounded-lg bg-slate-950 border border-white/[0.04] text-[11px] font-mono text-slate-300 max-h-48 overflow-y-auto overflow-x-auto whitespace-pre leading-relaxed">
                                {att.proposal.merged_code}
                              </pre>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Workflow Events Timeline Toggle */}
          {events.length > 0 && (
            <div className="pt-2">
              <button
                type="button"
                onClick={() => setShowEvents(!showEvents)}
                className="text-xs font-mono text-slate-400 hover:text-sky-400 flex items-center gap-1.5 transition-colors"
              >
                <Layers className="w-3.5 h-3.5" />
                <span>{showEvents ? 'Hide Workflow Execution Trace' : 'View Workflow Execution Trace'} ({events.length} events)</span>
              </button>

              {showEvents && (
                <div className="mt-3 p-3 rounded-xl neu-recessed border border-white/[0.04] space-y-2">
                  {events.map((ev, idx) => (
                    <div key={idx} className="flex items-start gap-2.5 text-[11px] font-mono">
                      <span className="text-slate-500 select-none">[{idx + 1}]</span>
                      <span className="text-sky-400">{ev.event_type}:</span>
                      <span className="text-slate-300">{ev.message}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

        </div>
      )}
    </div>
  );
}
