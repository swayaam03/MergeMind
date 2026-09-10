import React from 'react';

export default function Logo({ className = "w-8 h-8", textClassName = "text-xl font-bold text-white tracking-tight" }) {
  return (
    <div className="flex items-center gap-3 select-none">
      <div className={`relative flex items-center justify-center ${className}`}>
        {/* Soft back-glow */}
        <div className="absolute inset-0 rounded-full bg-sky-400/20 blur-md" />
        
        {/* Intertwined ring knot SVG */}
        <svg
          viewBox="0 0 40 40"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="relative w-full h-full text-white"
        >
          {/* Subtle gradient definitions */}
          <defs>
            <linearGradient id="ringGrad1" x1="0" y1="0" x2="40" y2="40" gradientUnits="userSpaceOnUse">
              <stop stopColor="#e0f2fe" />
              <stop offset="0.5" stopColor="#bae6fd" />
              <stop offset="1" stopColor="#38bdf8" />
            </linearGradient>
            <linearGradient id="ringGrad2" x1="40" y1="0" x2="0" y2="40" gradientUnits="userSpaceOnUse">
              <stop stopColor="#ffffff" />
              <stop offset="1" stopColor="#7dd3fc" />
            </linearGradient>
          </defs>
          
          {/* Loop 1 */}
          <ellipse
            cx="20"
            cy="20"
            rx="14"
            ry="9"
            transform="rotate(-28 20 20)"
            stroke="url(#ringGrad1)"
            strokeWidth="2.2"
            strokeLinecap="round"
            className="opacity-90"
          />
          {/* Loop 2 */}
          <ellipse
            cx="20"
            cy="20"
            rx="14"
            ry="9"
            transform="rotate(32 20 20)"
            stroke="url(#ringGrad2)"
            strokeWidth="2.2"
            strokeLinecap="round"
            className="opacity-80"
          />
          {/* Core nucleus star */}
          <circle cx="20" cy="20" r="1.5" fill="#f8fafc" className="drop-shadow-[0_0_6px_#38bdf8]" />
        </svg>
      </div>

      <span className={textClassName}>
        MergeMind
      </span>
    </div>
  );
}
