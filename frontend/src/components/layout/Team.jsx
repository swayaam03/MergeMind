import React, { useState } from 'react';
import { GraduationCap, ArrowRight, BookOpen, Layers, Cpu, Shield } from 'lucide-react';

export default function Team() {
  const [showDetails, setShowDetails] = useState(false);

  const teamMembers = [
    { name: "Aarushi Arora", role: "Pipeline & AST Analysis" },
    { name: "Dhvani Mistry", role: "Docker Sandbox & Verification" },
    { name: "Prishita Mali", role: "Security Scanning & Semgrep" },
    { name: "Swayam Kandarkar", role: "Orchestration & 4-Way Review UI" },
  ];

  return (
    <section id="team" className="py-16 sm:py-20 relative z-10">
      <div className="max-w-7xl mx-auto px-6 sm:px-8">
        
        {/* Main Team Neumorphic Bar (Exact match to reference image bottom card) */}
        <div className="neu-panel rounded-2xl p-6 sm:p-8 border border-white/[0.08] shadow-[0_12px_36px_rgba(0,0,0,0.6)]">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-8">
            
            {/* Left: Department & Institution */}
            <div className="flex flex-col">
              <span className="text-[11px] font-mono uppercase tracking-[0.2em] text-slate-400 font-semibold mb-1">
                FINAL YEAR PROJECT
              </span>
              <h3 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
                Department of Information Technology
              </h3>
              <p className="text-sm text-slate-400 mt-0.5">
                St. Francis Institute of Technology
              </p>
            </div>

            {/* Middle divider on desktop */}
            <div className="hidden lg:block w-[1px] h-16 bg-white/[0.08]" />

            {/* Center: Team & Guide */}
            <div className="flex flex-col">
              <span className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-400 mb-2">
                Project Team
              </span>
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm font-medium text-slate-200">
                <span>Aarushi Arora</span>
                <span className="text-slate-600">|</span>
                <span>Dhvani Mistry</span>
                <span className="text-slate-600">|</span>
                <span>Prishita Mali</span>
                <span className="text-slate-600">|</span>
                <span className="text-sky-300">Swayam Kandarkar</span>
              </div>
              <div className="text-xs text-slate-400 font-mono mt-2">
                <span className="text-slate-500">Guide:</span> Shree Jaswal, Assistant Professor
              </div>
            </div>

            {/* Right: Learn More CTA */}
            <div className="flex items-center">
              <button
                onClick={() => setShowDetails(!showDetails)}
                className="neu-button px-6 py-3 rounded-full text-sm font-medium text-slate-200 hover:text-white flex items-center gap-2 group w-full sm:w-auto justify-center"
              >
                <span>{showDetails ? 'Hide Details' : 'Learn More'}</span>
                <ArrowRight className={`w-4 h-4 text-sky-400 transition-transform duration-200 ${
                  showDetails ? 'rotate-90' : 'group-hover:translate-x-1'
                }`} />
              </button>
            </div>

          </div>

          {/* Expandable Project Details Drawer */}
          {showDetails && (
            <div className="mt-8 pt-8 border-t border-white/[0.06] animate-in fade-in duration-300">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                
                <div className="neu-recessed p-5 rounded-xl">
                  <div className="flex items-center gap-2 text-sky-400 text-sm font-semibold mb-2">
                    <BookOpen className="w-4 h-4" />
                    <span>Academic Scope</span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    Designed as an undergraduate research capstone tackling the limits of textual 3-way merge algorithms (`diff3` and `ort`) through syntax-aware Tree-sitter AST classification.
                  </p>
                </div>

                <div className="neu-recessed p-5 rounded-xl">
                  <div className="flex items-center gap-2 text-sky-400 text-sm font-semibold mb-2">
                    <Layers className="w-4 h-4" />
                    <span>Core Guarantees</span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    Strict separation between deterministic stages (AST analysis, Docker test runs, Semgrep SAST) and swappable LiteLLM agents ensures unverified code never reaches production.
                  </p>
                </div>

                <div className="neu-recessed p-5 rounded-xl">
                  <div className="flex items-center gap-2 text-sky-400 text-sm font-semibold mb-2">
                    <Shield className="w-4 h-4" />
                    <span>Language Support</span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    Focused first-class support for Python, JavaScript, and Java with tailored sandbox test harnesses, AST grammars, and security rule profiles.
                  </p>
                </div>

              </div>
            </div>
          )}

        </div>

      </div>
    </section>
  );
}
