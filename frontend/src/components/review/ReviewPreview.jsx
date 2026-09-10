import React, { useState } from 'react';
import { Check, X, Edit3, ShieldCheck, CheckCircle2, Sparkles, FileCode, AlertCircle } from 'lucide-react';

export default function ReviewPreview() {
  const [actionStatus, setActionStatus] = useState(null);

  const baseCode = `# Base Ancestor (main)
def verify_token(token: str) -> dict:
    claims = jwt.decode(
        token, 
        SECRET_KEY, 
        algorithms=["HS256"]
    )
    return claims`;

  const localCode = `# LOCAL (feature/pkce-auth)
def verify_token(token: str, code_verifier: str) -> dict:
    if not validate_pkce(code_verifier):
        raise InvalidPKCEError()
    claims = jwt.decode(
        token, 
        SECRET_KEY, 
        algorithms=["HS256"]
    )
    return claims`;

  const remoteCode = `# REMOTE (hotfix/rate-limit)
@rate_limiter(max_per_min=60)
def verify_token(token: str) -> dict:
    claims = jwt.decode(
        token, 
        SECRET_KEY, 
        algorithms=["HS256"]
    )
    audit_log(claims["sub"], "verify")
    return claims`;

  const mergedCode = `# AI-MERGED (Proposed & Verified)
@rate_limiter(max_per_min=60)
def verify_token(token: str, code_verifier: str) -> dict:
    if not validate_pkce(code_verifier):
        raise InvalidPKCEError()
    claims = jwt.decode(
        token, 
        SECRET_KEY, 
        algorithms=["HS256"]
    )
    audit_log(claims["sub"], "verify")
    return claims`;

  const handleAction = (type) => {
    setActionStatus(type);
    setTimeout(() => {
      setActionStatus(null);
    }, 3500);
  };

  return (
    <section id="review" className="py-20 sm:py-28 relative z-10">
      <div className="max-w-7xl mx-auto px-6 sm:px-8">
        
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto mb-14 sm:mb-16">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full neu-recessed text-xs font-mono uppercase tracking-wider text-sky-400 mb-4 border border-sky-500/20">
            Human-in-the-Loop
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-white tracking-tight">
            You Stay in Control.
          </h2>
          <p className="mt-4 text-base sm:text-lg text-slate-400">
            MergeMind never silently accepts an AI-generated merge. Every proposed resolution is verified and presented for developer approval.
          </p>
        </div>

        {/* Monaco-Style Neumorphic 4-Way Review Mockup */}
        <div className="neu-panel rounded-2xl overflow-hidden border border-white/[0.08] shadow-[0_20px_50px_rgba(0,0,0,0.8)]">
          
          {/* Top IDE Window Header */}
          <div className="px-5 py-3.5 bg-[#0a0d14] border-b border-white/[0.06] flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              {/* Window dots */}
              <div className="flex items-center gap-1.5">
                <div className="w-3 h-3 rounded-full bg-rose-500/80" />
                <div className="w-3 h-3 rounded-full bg-amber-500/80" />
                <div className="w-3 h-3 rounded-full bg-emerald-500/80" />
              </div>
              <div className="h-4 w-[1px] bg-white/10 mx-1" />
              <div className="flex items-center gap-2 font-mono text-xs text-slate-300">
                <FileCode className="w-4 h-4 text-sky-400" />
                <span className="font-semibold text-white">auth_service.py</span>
                <span className="text-slate-500">•</span>
                <span className="text-slate-400">feature/pkce-auth ➔ main</span>
              </div>
            </div>

            {/* Verification Status Badges */}
            <div className="flex items-center gap-3 text-xs font-mono">
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Docker: 8/8 tests passed</span>
              </div>
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Semgrep: 0 issues</span>
              </div>
            </div>
          </div>

          {/* 4 Code Panels Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 divide-y lg:divide-y-0 lg:divide-x divide-white/[0.06] bg-[#070a10]">
            
            {/* Panel 1: BASE */}
            <div className="flex flex-col">
              <div className="px-4 py-2 bg-[#0a0d15] text-xs font-mono text-slate-400 border-b border-white/[0.04] flex items-center justify-between">
                <span>BASE (Ancestor)</span>
                <span className="text-[10px] text-slate-500">v1.2</span>
              </div>
              <pre className="p-4 font-mono text-[11px] leading-relaxed text-slate-400 overflow-x-auto select-none min-h-[190px]">
                <code>{baseCode}</code>
              </pre>
            </div>

            {/* Panel 2: LOCAL */}
            <div className="flex flex-col">
              <div className="px-4 py-2 bg-[#0a0d15] text-xs font-mono text-sky-300 border-b border-white/[0.04] flex items-center justify-between">
                <span>LOCAL (Our branch)</span>
                <span className="text-[10px] text-sky-400/70">+PKCE</span>
              </div>
              <pre className="p-4 font-mono text-[11px] leading-relaxed text-slate-300 overflow-x-auto select-none min-h-[190px] bg-sky-950/10">
                <code>{localCode}</code>
              </pre>
            </div>

            {/* Panel 3: REMOTE */}
            <div className="flex flex-col">
              <div className="px-4 py-2 bg-[#0a0d15] text-xs font-mono text-purple-300 border-b border-white/[0.04] flex items-center justify-between">
                <span>REMOTE (Their branch)</span>
                <span className="text-[10px] text-purple-400/70">+RateLimit</span>
              </div>
              <pre className="p-4 font-mono text-[11px] leading-relaxed text-slate-300 overflow-x-auto select-none min-h-[190px] bg-purple-950/10">
                <code>{remoteCode}</code>
              </pre>
            </div>

            {/* Panel 4: AI-MERGED (Hero Panel) */}
            <div className="flex flex-col bg-[#0b101a] ring-1 ring-inset ring-sky-400/30">
              <div className="px-4 py-2 bg-[#0e1524] text-xs font-mono text-sky-200 border-b border-sky-400/20 flex items-center justify-between">
                <span className="flex items-center gap-1.5 font-bold">
                  <Sparkles className="w-3.5 h-3.5 text-sky-400" /> AI-MERGED
                </span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-sky-500/20 text-sky-300 font-semibold">
                  Verified
                </span>
              </div>
              <pre className="p-4 font-mono text-[11px] leading-relaxed text-sky-100 overflow-x-auto select-none min-h-[190px]">
                <code>{mergedCode}</code>
              </pre>
            </div>

          </div>

          {/* AI Reasoning & Action Bar */}
          <div className="p-5 sm:p-6 bg-[#0a0e16] border-t border-white/[0.06] flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
            
            {/* Reasoning Panel */}
            <div className="flex items-start gap-3 max-w-2xl">
              <div className="w-8 h-8 rounded-lg neu-recessed flex items-center justify-center flex-shrink-0 mt-0.5 text-sky-400">
                <Sparkles className="w-4 h-4" />
              </div>
              <div>
                <div className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-400">
                  MergeMind Agent Reasoning
                </div>
                <p className="text-xs sm:text-sm text-slate-300 mt-1 leading-relaxed">
                  Both branches modified <code className="text-sky-300 font-mono">verify_token()</code> for orthogonal concerns. The resolution applies Remote’s <code className="text-sky-300 font-mono">@rate_limiter</code> decorator while preserving Local’s PKCE challenge verification and audit logging.
                </p>
              </div>
            </div>

            {/* Action Buttons: Accept / Edit / Reject */}
            <div className="flex items-center gap-3 w-full md:w-auto justify-end">
              {actionStatus ? (
                <div className="px-4 py-2 rounded-xl bg-sky-500/10 border border-sky-500/30 text-xs font-mono text-sky-300 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-sky-400" />
                  <span>
                    {actionStatus === 'accept' && 'Resolution approved & merged into working branch!'}
                    {actionStatus === 'edit' && 'Opening 4-way editor mode...'}
                    {actionStatus === 'reject' && 'AI proposal dismissed. Falling back to manual resolution.'}
                  </span>
                </div>
              ) : (
                <>
                  <button
                    onClick={() => handleAction('reject')}
                    className="neu-button px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-rose-300 hover:border-rose-500/30 flex items-center gap-1.5 transition-colors"
                  >
                    <X className="w-3.5 h-3.5" />
                    <span>Reject</span>
                  </button>

                  <button
                    onClick={() => handleAction('edit')}
                    className="neu-button px-4 py-2 rounded-xl text-xs font-medium text-slate-300 hover:text-white flex items-center gap-1.5 transition-colors"
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                    <span>Edit</span>
                  </button>

                  <button
                    onClick={() => handleAction('accept')}
                    className="neu-glow-btn px-5 py-2 rounded-xl text-xs font-semibold text-white flex items-center gap-1.5"
                  >
                    <Check className="w-3.5 h-3.5 text-sky-300" />
                    <span>Accept Resolution</span>
                  </button>
                </>
              )}
            </div>

          </div>

        </div>

      </div>
    </section>
  );
}
