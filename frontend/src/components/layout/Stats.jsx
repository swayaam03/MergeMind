import React from 'react';
import { Clock, BarChart3, Shield } from 'lucide-react';

export default function Stats() {
  const stats = [
    {
      icon: Clock,
      value: "15 – 25%",
      label: "of developer time lost to merge conflicts",
      citation: "IEEE, 2025",
    },
    {
      icon: BarChart3,
      value: "$2.3B / yr",
      label: "in lost productivity worldwide",
      citation: "Gartner, 2026",
    },
    {
      icon: Shield,
      value: "41%",
      label: "of breaches linked to merge errors",
      citation: "OWASP, 2025",
    },
  ];

  return (
    <section id="about" className="py-12 sm:py-16 relative z-10">
      <div className="max-w-7xl mx-auto px-6 sm:px-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 sm:gap-8">
          {stats.map((stat, idx) => {
            const Icon = stat.icon;
            return (
              <div
                key={idx}
                className="neu-panel neu-panel-hover rounded-2xl p-7 sm:p-8 flex items-center gap-6"
              >
                {/* Circular recessed well icon */}
                <div className="flex-shrink-0 w-16 h-16 rounded-full neu-recessed flex items-center justify-center relative group">
                  <div className="absolute inset-0 rounded-full bg-sky-400/5 blur-sm" />
                  <Icon className="w-7 h-7 text-sky-300 relative z-10 stroke-[1.8]" />
                </div>

                {/* Content */}
                <div className="flex flex-col">
                  <div className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                    {stat.value}
                  </div>
                  <div className="text-sm text-slate-300 font-normal mt-1 leading-snug">
                    {stat.label}
                  </div>
                  <div className="text-[11px] font-mono uppercase tracking-wider text-slate-500 mt-2 font-medium">
                    {stat.citation}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
