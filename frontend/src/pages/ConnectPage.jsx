import React from 'react';
import { Link } from 'react-router-dom';
import Logo from '../components/common/Logo';
import GitHubConnectCard from '../components/connect/GitHubConnectCard';
import ConnectionFlow from '../components/connect/ConnectionFlow';
import { ArrowLeft, ArrowRight } from 'lucide-react';

export default function ConnectPage() {
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
            <a
              href="#dashboard"
              onClick={(e) => {
                e.preventDefault();
                alert("Dashboard access will be enabled in the upcoming application phases!");
              }}
              className="text-sky-300 hover:text-sky-200 font-medium inline-flex items-center gap-1 group transition-colors"
            >
              <span>Continue to Dashboard</span>
              <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5" />
            </a>
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
