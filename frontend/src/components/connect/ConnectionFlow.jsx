import React from 'react';
import { GitBranch, GitPullRequest, GitMerge, FolderGit2, Sparkles } from 'lucide-react';

function GithubIcon({ className = "w-5 h-5" }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
    </svg>
  );
}

export default function ConnectionFlow() {
  const flowSteps = [
    {
      title: "GitHub",
      subtitle: "Identity & Auth",
      icon: GithubIcon,
      active: true,
    },
    {
      title: "MergeMind",
      subtitle: "Developer Workspace",
      icon: Sparkles,
      active: true,
    },
    {
      title: "Repositories",
      subtitle: "Selective Access",
      icon: FolderGit2,
      active: false,
    },
    {
      title: "Pull Requests",
      subtitle: "Automated Tracking",
      icon: GitPullRequest,
      active: false,
    },
    {
      title: "Conflict Resolution",
      subtitle: "AST + Sandboxed LLM",
      icon: GitMerge,
      active: false,
    },
  ];

  return (
    <div className="neu-panel rounded-2xl p-6 sm:p-7 border border-white/[0.08] relative overflow-hidden h-full flex flex-col justify-between">
      {/* Ambient background glow */}
      <div className="absolute top-0 right-0 w-48 h-48 bg-sky-500/5 rounded-full blur-3xl pointer-events-none" />

      <div>
        <div className="flex items-center justify-between mb-6 pb-3 border-b border-white/[0.05]">
          <span className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-400">
            Lifecycle Workflow
          </span>
          <span className="text-[11px] font-mono text-sky-400/80 px-2 py-0.5 rounded-md bg-sky-500/10 border border-sky-500/20">
            Step 1 of 5
          </span>
        </div>

        <p className="text-xs text-slate-400 leading-relaxed mb-6 font-normal">
          Connecting GitHub initiates the autonomous workspace pipeline while preserving granular repository boundaries.
        </p>

        {/* Vertical Connected Node Sequence */}
        <div className="relative pl-6 space-y-6">
          {/* Vertical connecting line */}
          <div className="absolute left-[33px] top-4 bottom-6 w-[2px] bg-gradient-to-b from-sky-400/50 via-sky-500/20 to-slate-800" />

          {flowSteps.map((step, idx) => {
            const Icon = step.icon;
            const isFirst = idx === 0;
            const isSecond = idx === 1;

            return (
              <div key={step.title} className="relative flex items-center gap-4 group">
                {/* Node circle */}
                <div
                  className={`relative z-10 w-9 h-9 rounded-full flex items-center justify-center transition-all duration-300 ${
                    isFirst
                      ? 'bg-sky-400 text-slate-950 ring-4 ring-sky-400/20 shadow-[0_0_15px_rgba(56,189,248,0.5)]'
                      : isSecond
                      ? 'neu-glow-btn text-sky-300 ring-2 ring-sky-400/30'
                      : 'neu-recessed text-slate-500 border border-white/[0.04]'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                </div>

                {/* Node info card */}
                <div
                  className={`flex-1 p-3 rounded-xl border transition-all duration-200 ${
                    isFirst || isSecond
                      ? 'bg-[#0f1420]/80 border-sky-400/20 shadow-[2px_2px_8px_rgba(0,0,0,0.5)]'
                      : 'bg-[#090c13]/40 border-white/[0.03] opacity-60'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span
                      className={`text-xs font-semibold ${
                        isFirst || isSecond ? 'text-white' : 'text-slate-400'
                      }`}
                    >
                      {step.title}
                    </span>
                    <span className="text-[10px] font-mono text-slate-500">
                      0{idx + 1}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                    {step.subtitle}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="mt-8 pt-4 border-t border-white/[0.05] text-[11px] font-mono text-slate-500 flex items-center justify-between">
        <span>Zero-push guarantee</span>
        <span className="text-emerald-400/80 flex items-center gap-1">
          ● Read-first scoped
        </span>
      </div>
    </div>
  );
}
