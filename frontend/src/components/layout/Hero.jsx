import React, { useState } from 'react';
import ParticleCloud from './ParticleCloud';
import { ArrowRight, Play, Terminal, CheckCircle2, X, Loader2 } from 'lucide-react';
import { useGetStarted } from '../../hooks/useGetStarted';

export default function Hero() {
  const [showDemoModal, setShowDemoModal] = useState(false);
  const { handleGetStarted, checking } = useGetStarted();

  return (
    <section id="home" className="relative pt-32 pb-20 md:pt-40 md:pb-28 overflow-hidden min-h-[92vh] flex items-center">
      {/* Background celestial ambient glow */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-sky-500/5 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute top-1/3 right-1/4 w-[500px] h-[500px] bg-blue-600/5 rounded-full blur-[140px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-6 sm:px-8 w-full relative z-10">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-center">
          
          {/* Left Hero Content (7 Cols) */}
          <div className="lg:col-span-7 flex flex-col items-start text-left z-20">
            
            {/* Eyebrow Pill */}
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#0d121b] border border-white/[0.08] shadow-[inset_2px_2px_4px_rgba(0,0,0,0.6),_2px_2px_6px_rgba(0,0,0,0.3)] mb-8">
              <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-pulse" />
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                Agentic AI <span className="text-slate-500">•</span> Developer Tooling
              </span>
            </div>

            {/* Main Headline */}
            <h1 className="text-6xl sm:text-7xl lg:text-[5.75rem] leading-[1.05] font-extrabold tracking-tight text-white mb-6">
              <span className="bg-gradient-to-b from-white via-slate-100 to-sky-200 bg-clip-text text-transparent drop-shadow-[0_0_35px_rgba(186,230,253,0.35)]">
                MergeMind
              </span>
            </h1>

            {/* Sub-headline */}
            <h2 className="text-xl sm:text-2xl font-medium text-slate-300 leading-snug tracking-tight mb-5 max-w-2xl">
              Semantic Git Conflict Resolution <br className="hidden sm:inline" />
              <span className="text-slate-400">using ASTs and Sandboxed LLMs</span>
            </h2>

            {/* Description */}
            <p className="text-base sm:text-lg text-slate-400 leading-relaxed max-w-xl mb-10 font-normal">
              An AI-powered merge driver that understands code, not just text.
              Resolve conflicts intelligently, verify safely, and build with confidence.
            </p>

            {/* CTA Buttons */}
            <div className="flex flex-wrap items-center gap-4 sm:gap-5 w-full sm:w-auto">
              <button
                onClick={handleGetStarted}
                disabled={checking}
                className="neu-glow-btn px-7 py-3.5 rounded-full text-base font-semibold text-white flex items-center justify-center gap-2.5 group w-full sm:w-auto disabled:opacity-75"
              >
                {checking ? (
                  <>
                    <Loader2 className="w-4 h-4 text-sky-300 animate-spin" />
                    <span>Checking...</span>
                  </>
                ) : (
                  <>
                    <span>Get Started</span>
                    <ArrowRight className="w-4 h-4 text-sky-300 transition-transform duration-200 group-hover:translate-x-1" />
                  </>
                )}
              </button>

              <button
                onClick={() => setShowDemoModal(true)}
                className="neu-button px-6 py-3.5 rounded-full text-base font-medium text-slate-300 hover:text-white flex items-center justify-center gap-3 group w-full sm:w-auto"
              >
                <div className="w-6 h-6 rounded-full bg-[#0a0e16] shadow-[inset_2px_2px_4px_rgba(0,0,0,0.8)] border border-white/[0.05] flex items-center justify-center">
                  <Play className="w-2.5 h-2.5 text-sky-400 fill-sky-400 translate-x-0.5" />
                </div>
                <span>Watch Demo</span>
              </button>
            </div>
          </div>

          {/* Right Hero Visual: Particle Cloud + Side Tagline (5 Cols) */}
          <div className="lg:col-span-5 relative flex items-center justify-center min-h-[380px] sm:min-h-[460px] lg:min-h-[520px]">
            {/* 3D Particle Cloud Canvas */}
            <div className="absolute inset-0 flex items-center justify-center">
              <ParticleCloud className="w-full h-full" />
            </div>

            {/* Subtle vertical/side mantra from the cover slide */}
            <div className="absolute right-2 bottom-4 sm:right-6 sm:bottom-6 text-right select-none pointer-events-none opacity-40 hover:opacity-80 transition-opacity">
              <div className="w-8 h-[1px] bg-slate-500 ml-auto mb-2" />
              <p className="text-[11px] font-mono tracking-widest uppercase text-slate-400 leading-tight">
                Code<br />
                Understand<br />
                Resolve<br />
                Evolve
              </p>
            </div>
          </div>

        </div>
      </div>

      {/* Interactive Quick Demo Modal */}
      {showDemoModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
          <div className="relative w-full max-w-2xl neu-panel rounded-2xl p-6 border border-white/10 shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-white/[0.08]">
              <div className="flex items-center gap-2.5">
                <Terminal className="w-5 h-5 text-sky-400" />
                <h3 className="text-base font-semibold text-white">MergeMind Autonomous Git Driver Simulation</h3>
              </div>
              <button
                onClick={() => setShowDemoModal(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-white/[0.05]"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Mock terminal playback */}
            <div className="mt-4 neu-recessed rounded-xl p-4 font-mono text-xs sm:text-sm text-slate-300 space-y-2 overflow-hidden">
              <div className="text-slate-500">$ git merge feature/auth-refactor</div>
              <div className="text-amber-400">CONFLICT (content): Merge conflict in src/auth/token_verifier.py</div>
              <div className="text-sky-300 font-semibold mt-2">[MergeMind Driver Activated]</div>
              <div className="text-slate-400">├── Intercepted 3-way conflict (BASE: a4f10c, OURS: 8bc21e, THEIRS: 91fa02)</div>
              <div className="text-slate-400">├── Tree-sitter AST classifier: Semantic AST Overlap (Function signature & Scope)</div>
              <div className="text-slate-400">├── Context extraction: 2 caller modules + token test fixture extracted</div>
              <div className="text-slate-400">├── LangGraph Merge Agent proposing AST-compliant union...</div>
              <div className="text-emerald-400 flex items-center gap-1.5 pt-1">
                <CheckCircle2 className="w-4 h-4" /> Docker sandbox test suite passed (14/14 unit tests green)
              </div>
              <div className="text-emerald-400 flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4" /> Semgrep AST security scan passed (0 CVEs, 0 OWASP regressions)
              </div>
              <div className="text-sky-200 font-semibold pt-2">
                Resolution ready for Human-in-the-Loop review at: http://localhost:5173/review
              </div>
            </div>

            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setShowDemoModal(false)}
                className="neu-button px-5 py-2 rounded-xl text-sm font-medium text-slate-300 hover:text-white"
              >
                Close Demo
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
