import React from 'react';
import { Code2, Brain, ShieldCheck, Users } from 'lucide-react';

export default function Features() {
  const features = [
    {
      icon: Code2,
      title: "Understands Code",
      description: "Uses ASTs to detect real semantic conflicts.",
      detail: "Goes beyond textual line diffs with Tree-sitter AST classification across Python, JS, and Java.",
    },
    {
      icon: Brain,
      title: "AI-Powered Resolution",
      description: "Leverages LLMs to propose intelligent merges.",
      detail: "Orchestrated via LangGraph with multi-provider LiteLLM access, generating syntactically sound unions.",
    },
    {
      icon: ShieldCheck,
      title: "Verified & Secure",
      description: "Runs tests in a sandbox and scans with Semgrep before suggesting.",
      detail: "Executes in isolated Docker containers with automated test suites and OWASP vulnerability scans.",
    },
    {
      icon: Users,
      title: "Human in the Loop",
      description: "Provides a 4-way diff UI with clear reasoning. You stay in control.",
      detail: "Full transparency with Base, Local, Remote, and Merged code views alongside step-by-step reasoning.",
    },
  ];

  return (
    <section id="features" className="py-16 sm:py-24 relative z-10">
      <div className="max-w-7xl mx-auto px-6 sm:px-8">
        
        {/* Section Divider / Subhead */}
        <div className="flex items-center justify-center gap-6 mb-16 sm:mb-20">
          <div className="h-[1px] flex-1 max-w-xs bg-gradient-to-r from-transparent via-slate-700/60 to-slate-700/30" />
          <h2 className="text-xs sm:text-sm font-mono tracking-[0.25em] uppercase text-slate-400 font-semibold text-center select-none">
            TURNING MERGE CONFLICTS INTO PROGRESS
          </h2>
          <div className="h-[1px] flex-1 max-w-xs bg-gradient-to-l from-transparent via-slate-700/60 to-slate-700/30" />
        </div>

        {/* 4 Feature Cards Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 sm:gap-7">
          {features.map((feature, idx) => {
            const Icon = feature.icon;
            return (
              <div
                key={idx}
                className="neu-panel neu-panel-hover rounded-2xl p-7 flex flex-col items-start text-left relative overflow-hidden group"
              >
                {/* Top ambient highlight line */}
                <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-sky-400/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

                {/* Circular Recessed Icon Well */}
                <div className="w-14 h-14 rounded-full neu-recessed flex items-center justify-center mb-6 relative">
                  <div className="absolute inset-0 rounded-full bg-sky-400/5 blur-sm" />
                  <Icon className="w-6 h-6 text-sky-300 relative z-10 stroke-[1.8] transition-transform duration-300 group-hover:scale-110" />
                </div>

                {/* Title */}
                <h3 className="text-lg font-bold text-white tracking-tight mb-2.5">
                  {feature.title}
                </h3>

                {/* Core Description */}
                <p className="text-sm text-slate-300 leading-relaxed font-normal mb-3">
                  {feature.description}
                </p>

                {/* Extended subtle technical detail */}
                <p className="text-xs text-slate-500 leading-relaxed mt-auto pt-3 border-t border-white/[0.04] w-full">
                  {feature.detail}
                </p>
              </div>
            );
          })}
        </div>

      </div>
    </section>
  );
}
