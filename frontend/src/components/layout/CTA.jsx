import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Terminal } from 'lucide-react';

export default function CTA() {
  return (
    <section className="py-20 sm:py-28 relative z-10">
      <div className="max-w-5xl mx-auto px-6 sm:px-8 text-center">
        
        <div className="neu-panel rounded-3xl p-10 sm:p-16 border border-white/[0.08] relative overflow-hidden shadow-[0_20px_50px_rgba(0,0,0,0.8)]">
          {/* Subtle background ambient light */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-sky-500/10 rounded-full blur-3xl pointer-events-none" />

          <div className="relative z-10 flex flex-col items-center">
            
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-white tracking-tight max-w-2xl leading-tight mb-4">
              Ready to resolve conflicts differently?
            </h2>

            <p className="text-base sm:text-lg text-slate-300 max-w-xl font-normal mb-10">
              Understand the code. Verify the merge. Keep control.
            </p>

            <div className="flex flex-wrap items-center justify-center gap-4">
              <Link
                to="/connect"
                className="neu-glow-btn px-8 py-4 rounded-full text-base font-semibold text-white flex items-center gap-3 group"
              >
                <span>Get Started</span>
                <ArrowRight className="w-4 h-4 text-sky-300 transition-transform duration-200 group-hover:translate-x-1" />
              </Link>

              <a
                href="#review"
                className="neu-button px-7 py-4 rounded-full text-base font-medium text-slate-300 hover:text-white flex items-center gap-2"
              >
                <span>Inspect 4-Way Review</span>
              </a>
            </div>

            {/* Git Driver quick command placeholder */}
            <div className="mt-10 inline-flex items-center gap-2 px-4 py-2 rounded-xl neu-recessed text-xs font-mono text-slate-400 border border-white/[0.04]">
              <Terminal className="w-3.5 h-3.5 text-sky-400" />
              <span>git config merge.mergemind.driver "mergemind-driver %O %A %B %L %P"</span>
            </div>

          </div>
        </div>

      </div>
    </section>
  );
}
