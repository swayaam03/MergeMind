import React, { useState } from 'react';
import { GitMerge, FileCode, Network, Sparkles, Box, ShieldAlert, UserCheck, ArrowRight, CheckCircle2 } from 'lucide-react';

export default function HowItWorks() {
  const [activeStep, setActiveStep] = useState(0);

  const steps = [
    {
      num: "01",
      title: "Conflict Detection",
      subtitle: "Git Driver Hook",
      icon: GitMerge,
      desc: "MergeMind's custom Git merge driver intercepts conflicting files during rebase or merge before standard text-level failure markers pollute the codebase.",
      tech: "Custom .gitattributes driver + GitPython",
      badge: "Deterministic",
    },
    {
      num: "02",
      title: "AST Analysis",
      subtitle: "Tree-sitter Parser",
      icon: FileCode,
      desc: "Generates Concrete Syntax Trees for Python, JavaScript, and Java. Classifies whether the conflict is lexical, non-overlapping AST nodes, or semantic collision.",
      tech: "Tree-sitter AST Grammar",
      badge: "Deterministic",
    },
    {
      num: "03",
      title: "Context Extraction",
      subtitle: "Dependency Graph",
      icon: Network,
      desc: "Traverses surrounding scope, imports, dependent callers, class hierarchies, and relevant test files to build a rich semantic context window.",
      tech: "Graph analysis + Scope resolver",
      badge: "Deterministic",
    },
    {
      num: "04",
      title: "AI Resolution",
      subtitle: "Merge Agent",
      icon: Sparkles,
      desc: "LangGraph agent formulates a unified AST resolution preserving the semantic intent of both branch authors using LiteLLM swappable models.",
      tech: "LangGraph + LiteLLM (OpenRouter/Qwen)",
      badge: "Agentic LLM",
    },
    {
      num: "05",
      title: "Sandbox Verification",
      subtitle: "Docker Isolation",
      icon: Box,
      desc: "Spins up an ephemeral, resource-constrained container to run the repository's test suite and compiler against the proposed merge patch.",
      tech: "Docker SDK + Pytest/Jest/JUnit",
      badge: "Deterministic",
    },
    {
      num: "06",
      title: "Security Audit",
      subtitle: "Semgrep Scan",
      icon: ShieldAlert,
      desc: "Runs automated static application security testing (SAST) to ensure the AI resolution introduces zero secrets leaks, injection flaws, or OWASP risks.",
      tech: "Semgrep Ruleset",
      badge: "Deterministic",
    },
    {
      num: "07",
      title: "Human Review",
      subtitle: "4-Way Diff UI",
      icon: UserCheck,
      desc: "Presents side-by-side Base, Local, Remote, and Merged code along with concise reasoning and verification metrics for final engineer approval.",
      tech: "React 18 + Monaco 4-way UI",
      badge: "Human-in-the-Loop",
    },
  ];

  return (
    <section id="how-it-works" className="py-20 sm:py-28 relative z-10">
      <div className="max-w-7xl mx-auto px-6 sm:px-8">
        
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto mb-16 sm:mb-20">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full neu-recessed text-xs font-mono uppercase tracking-wider text-sky-400 mb-4 border border-sky-500/20">
            Pipeline Architecture
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-white tracking-tight">
            How MergeMind Works
          </h2>
          <p className="mt-4 text-base sm:text-lg text-slate-400">
            Deterministic AST analysis meets sandboxed agent orchestration — an unverified merge is never silently applied.
          </p>
        </div>

        {/* Timeline Pipeline Nodes: Horizontal scrollable on large screens, vertical on mobile */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3 sm:gap-4 mb-10">
          {steps.map((s, idx) => {
            const Icon = s.icon;
            const isSelected = activeStep === idx;
            return (
              <button
                key={s.num}
                onClick={() => setActiveStep(idx)}
                className={`flex flex-col items-start p-4 rounded-xl text-left transition-all duration-200 relative ${
                  isSelected
                    ? 'neu-panel border-sky-400/40 shadow-[0_0_20px_rgba(56,189,248,0.15)] ring-1 ring-sky-400/30'
                    : 'bg-[#0a0e16]/60 border border-white/[0.04] hover:border-white/10 hover:bg-[#0e131d]'
                }`}
              >
                {/* Step indicator */}
                <div className="flex items-center justify-between w-full mb-3">
                  <span className={`text-xs font-mono font-bold ${isSelected ? 'text-sky-300' : 'text-slate-500'}`}>
                    {s.num}
                  </span>
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                    isSelected ? 'neu-recessed text-sky-300' : 'bg-black/30 text-slate-400'
                  }`}>
                    <Icon className="w-4 h-4 stroke-[1.8]" />
                  </div>
                </div>

                <div className="text-xs font-bold text-white tracking-tight leading-tight line-clamp-1">
                  {s.title}
                </div>
                <div className="text-[11px] text-slate-400 font-mono mt-0.5 line-clamp-1">
                  {s.subtitle}
                </div>
              </button>
            );
          })}
        </div>

        {/* Active Step Detailed Card */}
        <div className="neu-panel rounded-2xl p-6 sm:p-10 border border-white/[0.08] relative overflow-hidden">
          <div className="absolute top-0 right-0 w-80 h-80 bg-sky-500/5 rounded-full blur-3xl pointer-events-none" />

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center relative z-10">
            {/* Left detail */}
            <div className="lg:col-span-8 flex flex-col items-start">
              <div className="flex flex-wrap items-center gap-3 mb-4">
                <span className="text-xl sm:text-2xl font-mono font-extrabold text-sky-400">
                  {steps[activeStep].num}
                </span>
                <h3 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
                  {steps[activeStep].title}
                </h3>
                <span className="px-3 py-0.5 rounded-full text-xs font-mono font-semibold uppercase bg-sky-500/10 text-sky-300 border border-sky-500/20">
                  {steps[activeStep].badge}
                </span>
              </div>

              <p className="text-base sm:text-lg text-slate-300 leading-relaxed max-w-2xl font-normal mb-6">
                {steps[activeStep].desc}
              </p>

              <div className="flex items-center gap-2 text-xs sm:text-sm font-mono text-slate-400 neu-recessed px-4 py-2 rounded-xl">
                <span className="text-sky-400 font-semibold">Engine:</span>
                <span>{steps[activeStep].tech}</span>
              </div>
            </div>

            {/* Right Pipeline Flowchart snippet */}
            <div className="lg:col-span-4 neu-recessed rounded-xl p-5 font-mono text-xs text-slate-300 space-y-3">
              <div className="text-slate-500 text-[11px] uppercase tracking-wider font-semibold border-b border-white/[0.05] pb-2">
                Pipeline Sequence
              </div>
              <div className="space-y-1.5 text-xs">
                {steps.map((s, idx) => (
                  <div
                    key={s.num}
                    className={`flex items-center gap-2 py-1 px-2 rounded-lg transition-colors ${
                      activeStep === idx
                        ? 'bg-sky-500/15 text-sky-200 font-medium'
                        : 'text-slate-500'
                    }`}
                  >
                    <span className="text-[10px] w-4">{s.num}</span>
                    <span className="truncate">{s.title}</span>
                    {activeStep === idx && (
                      <CheckCircle2 className="w-3.5 h-3.5 ml-auto text-sky-400" />
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

      </div>
    </section>
  );
}
