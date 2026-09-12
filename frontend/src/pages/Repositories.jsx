import React from 'react';
import { Link } from 'react-router-dom';
import Logo from '../components/common/Logo';
import { CheckCircle2, ArrowLeft, GitFork } from 'lucide-react';

export default function Repositories() {
  return (
    <div className="min-h-screen bg-[#07090e] text-slate-100 flex flex-col justify-between relative overflow-hidden selection:bg-sky-500/20 selection:text-sky-200">
      {/* Ambient background lighting */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[700px] h-[350px] bg-sky-500/5 rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-80 h-80 bg-emerald-500/5 rounded-full blur-[120px] pointer-events-none" />

      {/* Header Navigation */}
      <header className="py-6 px-6 sm:px-10 border-b border-white/[0.04] bg-[#07090e]/70 backdrop-blur-md relative z-20">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <Link to="/" className="focus:outline-none" aria-label="MergeMind Home">
            <Logo />
          </Link>

          <Link
            to="/"
            className="neu-button px-4 py-2 rounded-full text-xs font-medium text-slate-300 hover:text-white flex items-center gap-1.5 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5 text-sky-400" />
            <span>Back to Home</span>
          </Link>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 flex items-center justify-center px-4 sm:px-6 py-16 relative z-10">
        <div className="max-w-lg w-full mx-auto text-center">
          
          {/* Card Container */}
          <div className="neu-panel rounded-2xl p-8 sm:p-10 border border-white/[0.08] shadow-[0_20px_50px_rgba(0,0,0,0.8)] flex flex-col items-center">
            
            {/* Success Icon Recessed Well */}
            <div className="w-16 h-16 rounded-full neu-recessed flex items-center justify-center mb-6 relative">
              <div className="absolute inset-0 rounded-full bg-emerald-500/10 blur-sm" />
              <CheckCircle2 className="w-8 h-8 text-emerald-400 relative z-10" />
            </div>

            {/* Status Pill */}
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full neu-recessed text-xs font-mono uppercase tracking-wider text-emerald-400 mb-4 border border-emerald-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              INSTALLATION COMPLETE
            </div>

            {/* Required Primary Heading */}
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight mb-3">
              GitHub Connected
            </h1>

            {/* Required Secondary Notice */}
            <p className="text-sm sm:text-base text-slate-300 leading-relaxed font-normal mb-8">
              MergeMind has been installed successfully.
            </p>

            {/* Next Steps / Info Callout */}
            <div className="w-full neu-recessed rounded-xl p-4 border border-white/[0.03] text-left mb-6">
              <div className="flex items-start gap-3">
                <GitFork className="w-4 h-4 text-sky-400 flex-shrink-0 mt-0.5" />
                <p className="text-xs text-slate-400 leading-relaxed font-mono">
                  Your GitHub App installation was verified securely. Repository dashboards and active PR conflict tracking will be enabled in the next phase.
                </p>
              </div>
            </div>

            {/* Return Link */}
            <Link
              to="/"
              className="neu-glow-btn w-full py-3 rounded-xl text-sm font-semibold text-white flex items-center justify-center gap-2"
            >
              <span>Return to Dashboard</span>
            </Link>
          </div>

        </div>
      </main>

      {/* Footer */}
      <footer className="py-6 px-6 border-t border-white/[0.04] text-center text-[11px] font-mono text-slate-600 relative z-10">
        MergeMind Developer Workspace • GitHub App Installation Verified
      </footer>
    </div>
  );
}
