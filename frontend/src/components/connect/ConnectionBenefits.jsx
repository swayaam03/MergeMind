import React from 'react';
import { Check } from 'lucide-react';

export default function ConnectionBenefits() {
  const benefits = [
    "Choose which repositories MergeMind can access",
    "Review conflicts before accepting any resolution",
    "MergeMind never silently pushes AI-generated changes",
  ];

  return (
    <div className="w-full pt-6 border-t border-white/[0.06]">
      <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-300 mb-3 flex items-center gap-2">
        <span className="w-1.5 h-1.5 rounded-full bg-sky-400" />
        Your code stays under your control.
      </h4>

      <ul className="space-y-2.5">
        {benefits.map((benefit, idx) => (
          <li key={idx} className="flex items-start gap-2.5 text-xs text-slate-300 leading-snug">
            <div className="w-4 h-4 rounded-full bg-sky-500/10 border border-sky-400/30 flex items-center justify-center flex-shrink-0 mt-0.5">
              <Check className="w-2.5 h-2.5 text-sky-300 stroke-[2.5]" />
            </div>
            <span>{benefit}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
