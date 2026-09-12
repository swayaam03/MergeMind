import React from 'react';
import Logo from '../common/Logo';
import { FileText } from 'lucide-react';

function GithubIcon({ className = "w-4 h-4" }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
    </svg>
  );
}

export default function Footer() {
  return (
    <footer className="border-t border-white/[0.06] bg-[#07090e] py-12 relative z-10">
      <div className="max-w-7xl mx-auto px-6 sm:px-8 flex flex-col md:flex-row items-center justify-between gap-8">
        
        {/* Left: Brand info */}
        <div className="flex flex-col items-center md:items-start text-center md:text-left">
          <Logo className="w-7 h-7" textClassName="text-lg font-bold text-white tracking-tight" />
          <p className="text-xs text-slate-400 mt-2 font-medium">
            Semantic Git Conflict Resolution
          </p>
          <p className="text-[11px] text-slate-600 font-mono mt-1">
            Built with AST analysis, Docker sandbox verification & LangGraph
          </p>
        </div>

        {/* Right: Quick Links */}
        <div className="flex flex-wrap items-center justify-center gap-6 sm:gap-8 text-sm font-medium text-slate-400">
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 hover:text-sky-300 transition-colors"
          >
            <GithubIcon className="w-4 h-4" />
            <span>GitHub</span>
          </a>

          <a
            href="#how-it-works"
            className="flex items-center gap-2 hover:text-sky-300 transition-colors"
          >
            <FileText className="w-4 h-4" />
            <span>Documentation</span>
          </a>
        </div>

      </div>

      {/* Copyright Line */}
      <div className="max-w-7xl mx-auto px-6 sm:px-8 mt-8 pt-8 border-t border-white/[0.03] flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500 font-mono">
        <div>
          © 2026 MergeMind. St. Francis Institute of Technology.
        </div>
        <div className="flex items-center gap-1">
          <span>AI developer tooling research</span>
        </div>
      </div>
    </footer>
  );
}
