import React, { useState } from 'react';
import { ArrowRight, Loader2, CheckCircle2, ShieldCheck, AlertCircle, RefreshCw } from 'lucide-react';
import ConnectionBenefits from './ConnectionBenefits';
import SecurityNotice from './SecurityNotice';

function GithubIcon({ className = "w-6 h-6" }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
    </svg>
  );
}

export default function GitHubConnectCard() {
  const [status, setStatus] = useState('idle'); // 'idle' | 'connecting' | 'connected_preview'

  const handleInitiateOAuth = () => {
    // In Phase 2, this will trigger window.location.href = `${API_URL}/api/routes/auth/github/login`
    setStatus('connecting');

    // Simulate short network handoff for UI/UX demonstration
    setTimeout(() => {
      setStatus('connected_preview');
    }, 1200);
  };

  const handleReset = () => {
    setStatus('idle');
  };

  return (
    <div className="neu-panel rounded-2xl p-6 sm:p-8 border border-white/[0.08] shadow-[0_20px_50px_rgba(0,0,0,0.8)] relative">
      
      {/* GitHub Identity Row */}
      <div className="flex items-center gap-4 mb-6">
        <div className="w-14 h-14 rounded-2xl neu-recessed flex items-center justify-center border border-white/[0.06] text-white">
          <GithubIcon className="w-7 h-7" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-bold text-white tracking-tight">GitHub</h3>
            <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded-md bg-white/[0.05] text-slate-400 border border-white/[0.05]">
              OAuth 2.0
            </span>
          </div>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            Connect your GitHub account
          </p>
        </div>
      </div>

      {/* Description */}
      <p className="text-sm text-slate-300 leading-relaxed font-normal mb-8">
        Securely connect your GitHub account to access the repositories you choose to work with.
      </p>

      {/* Interactive State Area */}
      {status === 'idle' && (
        <div className="space-y-6">
          <button
            onClick={handleInitiateOAuth}
            className="w-full neu-glow-btn py-4 px-6 rounded-xl text-sm sm:text-base font-semibold text-white flex items-center justify-center gap-3 group"
          >
            <GithubIcon className="w-5 h-5 text-sky-200" />
            <span>Continue with GitHub</span>
            <ArrowRight className="w-4 h-4 text-sky-300 transition-transform duration-200 group-hover:translate-x-1" />
          </button>

          <ConnectionBenefits />
          <SecurityNotice />
        </div>
      )}

      {status === 'connecting' && (
        <div className="neu-recessed rounded-xl p-8 flex flex-col items-center justify-center text-center space-y-4 border border-sky-500/20">
          <Loader2 className="w-8 h-8 text-sky-400 animate-spin" />
          <div>
            <div className="text-sm font-semibold text-white">
              Connecting to GitHub...
            </div>
            <p className="text-xs text-slate-400 mt-1 font-mono">
              Initializing secure handoff flow
            </p>
          </div>
        </div>
      )}

      {status === 'connected_preview' && (
        <div className="space-y-6 animate-in fade-in duration-300">
          <div className="neu-recessed rounded-xl p-6 border border-sky-400/20">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-sky-500/10 border border-sky-400/30 flex items-center justify-center flex-shrink-0 text-sky-300 mt-0.5">
                <CheckCircle2 className="w-4 h-4" />
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-bold text-white">
                    GitHub OAuth Ready (UI Placeholder)
                  </h4>
                  <span className="text-[10px] font-mono text-sky-300 px-2 py-0.5 rounded bg-sky-500/20 border border-sky-500/30">
                    Phase 2 Integration
                  </span>
                </div>
                <p className="text-xs text-slate-300 mt-1.5 leading-relaxed">
                  This button is configured and ready to invoke the backend GitHub OAuth endpoint (<code className="text-sky-300 font-mono text-[11px]">/api/routes/auth.py</code>) once backend services are connected.
                </p>
                <div className="mt-3 text-[11px] font-mono text-slate-400 flex items-center gap-1.5">
                  <span className="text-sky-400">Next step:</span> Select repositories at <code className="text-slate-300">/repositories</code>
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleReset}
              className="neu-button flex-1 py-3 px-4 rounded-xl text-xs font-medium text-slate-300 hover:text-white flex items-center justify-center gap-2"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Reset State</span>
            </button>
            <a
              href="#dashboard-placeholder"
              onClick={(e) => {
                e.preventDefault();
                alert("Repository discovery and Dashboard will be configured in the next phase!");
              }}
              className="neu-glow-btn flex-1 py-3 px-4 rounded-xl text-xs font-semibold text-white flex items-center justify-center gap-2"
            >
              <span>View Repositories →</span>
            </a>
          </div>

          <ConnectionBenefits />
        </div>
      )}

    </div>
  );
}
