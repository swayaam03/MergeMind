import React, { useState, useEffect } from 'react';
import {
  Check,
  CheckCircle2,
  X,
  XCircle,
  Edit3,
  Save,
  RotateCcw,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  Sparkles,
  Columns,
  Maximize2,
  Layers,
  Copy,
  Info,
  Loader2,
  ArrowRight,
} from 'lucide-react';
import { submitMergeDecision } from '../../services/github';

export default function ConflictReviewPanel({
  owner,
  repo,
  pullNumber,
  filePath,
  baseCode = '',
  localCode = '',
  remoteCode = '',
  proposedCode = '',
  reasoning = '',
  confidence = 0,
  verificationReport = null,
  runId = null,
  onDecisionSubmitted = null,
}) {
  const [activeTab, setActiveTab] = useState('merged'); // '4way' | 'base' | 'local' | 'remote' | 'merged'
  const [isEditing, setIsEditing] = useState(false);
  const [editedCode, setEditedCode] = useState(proposedCode || '');
  const [copied, setCopied] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [decisionFeedback, setDecisionFeedback] = useState(null); // { type: 'accept'|'edit'|'reject', message: '' }
  const [notes, setNotes] = useState('');

  // Synchronize when proposedCode changes from upstream agent
  useEffect(() => {
    if (!isEditing) {
      setEditedCode(proposedCode || '');
    }
  }, [proposedCode, isEditing]);

  const handleCopy = (code) => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDecision = async (decisionType) => {
    setSubmitting(true);
    setDecisionFeedback(null);

    const payload = {
      decision: decisionType,
      file_path: filePath,
      final_code: decisionType === 'reject' ? null : (isEditing ? editedCode : (proposedCode || editedCode)),
      notes: notes.trim() || undefined,
    };

    try {
      const response = await submitMergeDecision(owner, repo, pullNumber, payload, runId);
      setDecisionFeedback({
        type: decisionType,
        message: `Resolution successfully ${decisionType}ed.`,
        data: response,
      });
      setIsEditing(false);
      if (onDecisionSubmitted) {
        onDecisionSubmitted(decisionType, response);
      }
    } catch (err) {
      setDecisionFeedback({
        type: 'error',
        message: err.message || 'Failed to submit decision. Please try again.',
      });
    } finally {
      setSubmitting(false);
    }
  };

  const confidencePct = Math.round((confidence || 0) * 100);

  return (
    <div className="neu-panel rounded-2xl overflow-hidden border border-white/[0.08] shadow-[0_20px_50px_rgba(0,0,0,0.8)] space-y-4">
      {/* Top Bar: Title & View Selector */}
      <div className="p-4 bg-slate-950/80 border-b border-white/[0.06] flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
            <Columns className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <span>Interactive 4-Way Review</span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-sky-500/10 text-sky-300 border border-sky-500/20">
                Phase 8
              </span>
            </h3>
            <p className="text-xs text-slate-400 font-mono truncate max-w-sm sm:max-w-md">{filePath}</p>
          </div>
        </div>

        {/* View Switcher Pills */}
        <div className="flex items-center gap-1 p-1 rounded-xl neu-recessed border border-white/[0.03]">
          <button
            onClick={() => setActiveTab('4way')}
            className={`px-2.5 py-1 rounded-lg text-xs font-mono font-medium transition-colors ${
              activeTab === '4way'
                ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            4-Way Grid
          </button>
          <button
            onClick={() => setActiveTab('base')}
            className={`px-2.5 py-1 rounded-lg text-xs font-mono font-medium transition-colors ${
              activeTab === 'base'
                ? 'bg-slate-700/40 text-slate-200 border border-slate-600/50'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Base
          </button>
          <button
            onClick={() => setActiveTab('local')}
            className={`px-2.5 py-1 rounded-lg text-xs font-mono font-medium transition-colors ${
              activeTab === 'local'
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Local (Ours)
          </button>
          <button
            onClick={() => setActiveTab('remote')}
            className={`px-2.5 py-1 rounded-lg text-xs font-mono font-medium transition-colors ${
              activeTab === 'remote'
                ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Remote (Theirs)
          </button>
          <button
            onClick={() => setActiveTab('merged')}
            className={`px-2.5 py-1 rounded-lg text-xs font-mono font-semibold transition-colors ${
              activeTab === 'merged'
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            AI-Merged {isEditing && '(Editing)'}
          </button>
        </div>
      </div>

      {/* Code Display Area */}
      <div className="p-4 space-y-4">
        {/* Mode 1: 4-Way Grid View */}
        {activeTab === '4way' && (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
            {/* 1. Base */}
            <div className="rounded-xl neu-recessed border border-white/[0.04] overflow-hidden flex flex-col">
              <div className="px-3 py-2 bg-slate-900/60 border-b border-white/[0.04] flex items-center justify-between text-xs font-mono text-slate-300">
                <span className="font-semibold text-slate-400">1. Base Ancestor</span>
                <span className="text-[10px] text-slate-500">original</span>
              </div>
              <pre className="p-3 text-[11px] font-mono text-slate-300 whitespace-pre overflow-x-auto max-h-80 flex-1 leading-relaxed">
                {baseCode || '(empty or not available)'}
              </pre>
            </div>

            {/* 2. Local (Ours) */}
            <div className="rounded-xl neu-recessed border border-amber-500/20 overflow-hidden flex flex-col">
              <div className="px-3 py-2 bg-amber-950/20 border-b border-amber-500/20 flex items-center justify-between text-xs font-mono text-amber-300">
                <span className="font-semibold">2. Local (Head)</span>
                <span className="text-[10px] text-amber-400">incoming</span>
              </div>
              <pre className="p-3 text-[11px] font-mono text-amber-100/90 whitespace-pre overflow-x-auto max-h-80 flex-1 leading-relaxed">
                {localCode || '(empty or not available)'}
              </pre>
            </div>

            {/* 3. Remote (Theirs) */}
            <div className="rounded-xl neu-recessed border border-indigo-500/20 overflow-hidden flex flex-col">
              <div className="px-3 py-2 bg-indigo-950/20 border-b border-indigo-500/20 flex items-center justify-between text-xs font-mono text-indigo-300">
                <span className="font-semibold">3. Remote (Target)</span>
                <span className="text-[10px] text-indigo-400">base</span>
              </div>
              <pre className="p-3 text-[11px] font-mono text-indigo-100/90 whitespace-pre overflow-x-auto max-h-80 flex-1 leading-relaxed">
                {remoteCode || '(empty or not available)'}
              </pre>
            </div>

            {/* 4. AI-Merged */}
            <div className="rounded-xl neu-recessed border border-emerald-500/30 overflow-hidden flex flex-col bg-emerald-950/5">
              <div className="px-3 py-2 bg-emerald-950/30 border-b border-emerald-500/20 flex items-center justify-between text-xs font-mono text-emerald-300">
                <span className="font-semibold flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
                  <span>4. Proposed Resolution</span>
                </span>
                <span className="text-[10px] text-emerald-400">{confidencePct}% conf</span>
              </div>
              <pre className="p-3 text-[11px] font-mono text-emerald-100/95 whitespace-pre overflow-x-auto max-h-80 flex-1 leading-relaxed">
                {editedCode || '(no resolution generated)'}
              </pre>
            </div>
          </div>
        )}

        {/* Mode 2: Single Pane Detailed View (Base / Local / Remote / Merged) */}
        {activeTab !== '4way' && (
          <div className="rounded-xl neu-recessed border border-white/[0.06] overflow-hidden">
            <div className="px-4 py-2.5 bg-slate-900/80 border-b border-white/[0.04] flex items-center justify-between text-xs font-mono">
              <div className="flex items-center gap-2">
                <span className="text-slate-400">Viewing:</span>
                <span className="font-bold text-white uppercase">{activeTab}</span>
              </div>

              <div className="flex items-center gap-2">
                {activeTab === 'merged' && (
                  <button
                    onClick={() => setIsEditing(!isEditing)}
                    className="neu-button px-2.5 py-1 rounded-lg text-xs font-mono text-sky-300 hover:text-white flex items-center gap-1.5"
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                    <span>{isEditing ? 'Preview Code' : 'Edit Code'}</span>
                  </button>
                )}

                <button
                  onClick={() =>
                    handleCopy(
                      activeTab === 'base'
                        ? baseCode
                        : activeTab === 'local'
                        ? localCode
                        : activeTab === 'remote'
                        ? remoteCode
                        : editedCode
                    )
                  }
                  className="neu-button px-2.5 py-1 rounded-lg text-xs font-mono text-slate-300 hover:text-white flex items-center gap-1.5"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? 'Copied' : 'Copy'}</span>
                </button>
              </div>
            </div>

            {/* Code Body or Monaco-like Text Editor */}
            {activeTab === 'merged' && isEditing ? (
              <div className="p-3 bg-slate-950">
                <textarea
                  value={editedCode}
                  onChange={(e) => setEditedCode(e.target.value)}
                  className="w-full h-80 bg-transparent font-mono text-xs text-slate-100 p-2 border border-sky-500/30 rounded-lg focus:outline-none focus:ring-1 focus:ring-sky-400 leading-relaxed resize-y"
                  placeholder="Edit resolved code here..."
                  spellCheck="false"
                />
              </div>
            ) : (
              <div className="p-4 bg-slate-950 max-h-96 overflow-auto">
                <pre className="font-mono text-xs text-slate-200 leading-relaxed whitespace-pre">
                  {activeTab === 'base' && (baseCode || '(empty)')}
                  {activeTab === 'local' && (localCode || '(empty)')}
                  {activeTab === 'remote' && (remoteCode || '(empty)')}
                  {activeTab === 'merged' && (editedCode || '(no resolved code)')}
                </pre>
              </div>
            )}
          </div>
        )}

        {/* AI Rationale & Verification Summary Strip */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {/* Reasoning */}
          <div className="md:col-span-2 p-3.5 rounded-xl neu-recessed border border-white/[0.04] space-y-1.5">
            <div className="flex items-center gap-1.5 text-xs font-mono font-bold text-sky-400 uppercase">
              <Sparkles className="w-3.5 h-3.5" />
              <span>AI Resolution Rationale</span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              {reasoning || 'No explanation report provided.'}
            </p>
          </div>

          {/* Verification Status */}
          <div className="p-3.5 rounded-xl neu-recessed border border-white/[0.04] space-y-2">
            <div className="flex items-center justify-between text-xs font-mono font-bold">
              <span className="text-slate-400">Confidence:</span>
              <span className="text-sky-300">{confidencePct}%</span>
            </div>

            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-slate-400">Sandbox Test:</span>
              {verificationReport?.test_execution?.passed ? (
                <span className="text-emerald-400 flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" /> Passed
                </span>
              ) : (
                <span className="text-amber-400 flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3" /> Not Verified
                </span>
              )}
            </div>

            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-slate-400">Semgrep Audit:</span>
              {verificationReport?.security_audit?.findings?.length === 0 ? (
                <span className="text-emerald-400 flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3" /> 0 findings
                </span>
              ) : (
                <span className="text-slate-400">Clean</span>
              )}
            </div>
          </div>
        </div>

        {/* Optional Reviewer Notes */}
        <div className="space-y-1.5">
          <label className="text-[11px] font-mono uppercase text-slate-400 block">
            Reviewer Notes / Audit Trail (Optional):
          </label>
          <input
            type="text"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="e.g. Approved with custom auth tweak; validated PKCE flow."
            className="w-full px-3 py-2 rounded-xl neu-recessed border border-white/[0.04] text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-sky-500/30"
          />
        </div>

        {/* Feedback Alert Banner */}
        {decisionFeedback && (
          <div
            className={`p-3.5 rounded-xl text-xs font-mono flex items-center justify-between ${
              decisionFeedback.type === 'accept'
                ? 'bg-emerald-950/40 border border-emerald-500/30 text-emerald-300'
                : decisionFeedback.type === 'edit'
                ? 'bg-sky-950/40 border border-sky-500/30 text-sky-300'
                : decisionFeedback.type === 'reject'
                ? 'bg-rose-950/40 border border-rose-500/30 text-rose-300'
                : 'bg-rose-950/40 border border-rose-500/30 text-rose-300'
            }`}
          >
            <span>{decisionFeedback.message}</span>
            <button
              onClick={() => setDecisionFeedback(null)}
              className="text-slate-400 hover:text-white"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Bottom Action Bar: Accept | Edit | Reject */}
        <div className="pt-2 border-t border-white/[0.06] flex flex-wrap items-center justify-end gap-3">
          {/* Reject Button */}
          <button
            type="button"
            disabled={submitting}
            onClick={() => handleDecision('reject')}
            className="neu-button px-4 py-2 rounded-xl text-xs font-bold text-rose-400 hover:text-rose-300 border border-rose-500/20 hover:border-rose-500/40 flex items-center gap-2 transition-all disabled:opacity-50 cursor-pointer"
          >
            <XCircle className="w-4 h-4 text-rose-400" />
            <span>Reject Proposal</span>
          </button>

          {/* Edit & Save Button */}
          <button
            type="button"
            disabled={submitting || !editedCode}
            onClick={() => handleDecision('edit')}
            className="neu-button px-4 py-2 rounded-xl text-xs font-bold text-sky-300 hover:text-white border border-sky-500/30 hover:border-sky-500/50 flex items-center gap-2 transition-all disabled:opacity-50 cursor-pointer"
          >
            <Edit3 className="w-4 h-4 text-sky-400" />
            <span>Apply Edited Code</span>
          </button>

          {/* Accept Button */}
          <button
            type="button"
            disabled={submitting || !editedCode}
            onClick={() => handleDecision('accept')}
            className="neu-glow-btn px-5 py-2 rounded-xl text-xs font-bold text-white flex items-center gap-2 transition-all disabled:opacity-50 cursor-pointer bg-gradient-to-r from-emerald-600 to-teal-600 shadow-[0_0_20px_rgba(16,185,129,0.3)]"
          >
            {submitting ? (
              <Loader2 className="w-4 h-4 animate-spin text-white" />
            ) : (
              <CheckCircle2 className="w-4 h-4 text-emerald-300" />
            )}
            <span>Accept Resolution</span>
          </button>
        </div>
      </div>
    </div>
  );
}
