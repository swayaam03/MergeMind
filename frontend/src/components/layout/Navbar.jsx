import React, { useState, useEffect } from 'react';
import Logo from '../common/Logo';
import { ArrowRight, Menu, X } from 'lucide-react';

export default function Navbar({ activeSection, onNavigate }) {
  const [isScrolled, setIsScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const navItems = [
    { label: 'Home', href: '#home' },
    { label: 'About', href: '#about' },
    { label: 'Features', href: '#features' },
    { label: 'How It Works', href: '#how-it-works' },
    { label: 'Team', href: '#team' },
  ];

  const handleLinkClick = (e, href) => {
    e.preventDefault();
    setMobileMenuOpen(false);
    if (onNavigate) {
      onNavigate(href);
    } else {
      const target = document.querySelector(href);
      if (target) {
        target.scrollIntoView({ behavior: 'smooth' });
      }
    }
  };

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        isScrolled
          ? 'bg-[#07090e]/85 backdrop-blur-md border-b border-white/[0.05] py-3.5 shadow-[0_8px_30px_rgba(0,0,0,0.6)]'
          : 'bg-transparent py-5'
      }`}
    >
      <div className="max-w-7xl mx-auto px-6 sm:px-8 flex items-center justify-between">
        {/* Left: Logo */}
        <a
          href="#home"
          onClick={(e) => handleLinkClick(e, '#home')}
          className="focus:outline-none"
          aria-label="MergeMind Home"
        >
          <Logo />
        </a>

        {/* Center: Desktop Nav Links with subtle neumorphic capsule styling */}
        <nav className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#0b0f17]/60 border border-white/[0.03] shadow-[inset_1px_1px_3px_rgba(255,255,255,0.02),_3px_3px_10px_rgba(0,0,0,0.4)]">
          {navItems.map((item) => {
            const isActive = activeSection === item.href.replace('#', '');
            return (
              <a
                key={item.label}
                href={item.href}
                onClick={(e) => handleLinkClick(e, item.href)}
                className={`px-4 py-1.5 text-sm font-medium rounded-full transition-all duration-200 ${
                  isActive
                    ? 'neu-nav-active text-sky-100 font-semibold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.03]'
                }`}
              >
                {item.label}
              </a>
            );
          })}
        </nav>

        {/* Right: CTA Button */}
        <div className="hidden md:flex items-center gap-4">
          <a
            href="#how-it-works"
            onClick={(e) => handleLinkClick(e, '#how-it-works')}
            className="neu-button px-5 py-2 rounded-full text-sm font-medium text-slate-200 flex items-center gap-2 group"
          >
            <span>Get Started</span>
            <ArrowRight className="w-3.5 h-3.5 text-sky-400 transition-transform duration-200 group-hover:translate-x-0.5" />
          </a>
        </div>

        {/* Mobile menu trigger */}
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="md:hidden p-2 rounded-xl neu-button text-slate-300"
          aria-label="Toggle navigation menu"
        >
          {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden px-6 pt-4 pb-6 bg-[#0c1018]/95 backdrop-blur-xl border-b border-white/[0.08] shadow-2xl animate-in fade-in slide-in-from-top-4 duration-200">
          <nav className="flex flex-col gap-2">
            {navItems.map((item) => {
              const isActive = activeSection === item.href.replace('#', '');
              return (
                <a
                  key={item.label}
                  href={item.href}
                  onClick={(e) => handleLinkClick(e, item.href)}
                  className={`px-4 py-2.5 text-sm rounded-xl font-medium transition-all ${
                    isActive
                      ? 'bg-sky-500/10 text-sky-200 border border-sky-500/20'
                      : 'text-slate-400 hover:text-white hover:bg-white/[0.04]'
                  }`}
                >
                  {item.label}
                </a>
              );
            })}
            <div className="pt-3 mt-1 border-t border-white/[0.06]">
              <a
                href="#how-it-works"
                onClick={(e) => handleLinkClick(e, '#how-it-works')}
                className="w-full neu-glow-btn py-2.5 rounded-xl text-sm font-medium text-white flex items-center justify-center gap-2"
              >
                <span>Get Started</span>
                <ArrowRight className="w-3.5 h-3.5 text-sky-300" />
              </a>
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}
