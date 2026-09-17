import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Logo from '../components/common/Logo';
import GitHubConnectCard from '../components/connect/GitHubConnectCard';
import ConnectionFlow from '../components/connect/ConnectionFlow';
import { ArrowLeft, ArrowRight, CheckCircle2 } from 'lucide-react';
import { checkGitHubStatus } from '../services/github';

export default function ConnectPage() {
  const [alreadyConnected, setAlreadyConnected] = useState(false);
  const [repoCount, setRepoCount] = useState(null);

  useEffect(() => {
    let isMounted = true;
    checkGitHubStatus().then((status) => {
      if (isMounted && status && status.connected) {
        setAlreadyConnected(true);
        if (typeof status.repository_count === 'number') {
          setRepoCount(status.repository_count);
        }
      }
    });
    return () => {
      isMounted = false;
    };
  }, []);
  return (
    <div className="min-h-screen bg-[#07090e] text-slate-100 flex flex-col justify-between relative overflow-hidden selection:bg-sky-500/20 selection:text-sky-200">
      
      {/* Background ambient lighting */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-sky-500/5 rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-96 h-96 bg-blue-600/5 rounded-full blur-[120px] pointer-events-none" />

      {/* Minimal App Onboarding Header */}
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

      {/* Main Centered Onboarding Content */}
      <main className="flex-1 flex items-center justify-center px-4 sm:px-6 py-12 sm:py-16 relative z-10">
        <div className="max-w-5xl w-full mx-auto">
          
          {/* Header Typography */}
          <div className="text-center max-w-2xl mx-auto mb-10 sm:mb-12">
            <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full neu-recessed text-xs font-mono uppercase tracking-wider text-sky-400 mb-4 border border-sky-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-pulse" />
              GET STARTED
            </div>

            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-white tracking-tight">
              Connect your GitHub
            </h1>

            <p className="mt-3.5 text-sm sm:text-base text-slate-400 leading-relaxed max-w-xl mx-auto font-normal">
              Connect your GitHub account to let MergeMind discover your repositories, monitor pull requests, and help resolve merge conflicts.
            </p>
          </div>

          {/* Already Connected Alert Banner */}
          {alreadyConnected && (
            <div className="mb-8 p-4 sm:p-5 rounded-2xl neu-panel border border-sky-400/30 flex flex-col sm:flex-row items-center justify-between gap-4 animate-in fade-in slide-in-from-top-2 duration-300">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl neu-recessed flex items-center justify-center text-sky-400 flex-shrink-0 border border-sky-400/20">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-white">GitHub App Connected</h4>
                  <p className="text-xs text-slate-400">
                    Your session already has access to {repoCount ? `${repoCount} repositories` : 'connected repositories'}.
                  </p>
                </div>
              </div>
              <Link
                to="/repositories"
                className="neu-glow-btn px-5 py-2.5 rounded-xl text-xs font-semibold text-white flex items-center gap-2 group flex-shrink-0"
              >
                <span>Go to Repositories</span>
                <ArrowRight className="w-3.5 h-3.5 text-sky-300 group-hover:translate-x-1 transition-transform" />
              </Link>
            </div>
          )}

          {/* Balanced Two-Column Composition: Left = Connect Card, Right = Lifecycle Flow */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch">
            
            {/* Left 7 Columns: Connection Card */}
            <div className="lg:col-span-7 flex flex-col">
              <GitHubConnectCard />
            </div>

            {/* Right 5 Columns: Lifecycle Pipeline Diagram */}
            <div className="lg:col-span-5 flex flex-col">
              <ConnectionFlow />
            </div>

          </div>

          {/* Bottom Prompt: Already connected? */}
          <div className="mt-12 text-center text-xs sm:text-sm text-slate-400 flex items-center justify-center gap-2">
            <span>Already connected?</span>
            <Link
              to="/repositories"
              className="text-sky-300 hover:text-sky-200 font-medium inline-flex items-center gap-1 group transition-colors"
            >
              <span>Continue to Repositories</span>
              <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5" />
            </Link>
          </div>

        </div>
      </main>

      {/* Minimal Clean Footer */}
      <footer className="py-6 px-6 border-t border-white/[0.04] text-center text-[11px] font-mono text-slate-600 relative z-10">
        MergeMind Developer Workspace • Secure OAuth 2.0 Flow
      </footer>

    </div>
  );
}
