import React, { useState, useEffect } from 'react';
import Navbar from './components/layout/Navbar';
import Hero from './components/layout/Hero';
import Stats from './components/layout/Stats';
import Features from './components/layout/Features';
import HowItWorks from './components/layout/HowItWorks';
import ReviewPreview from './components/review/ReviewPreview';
import Team from './components/layout/Team';
import CTA from './components/layout/CTA';
import Footer from './components/layout/Footer';

export default function App() {
  const [activeSection, setActiveSection] = useState('home');

  useEffect(() => {
    const handleScroll = () => {
      const sections = ['home', 'about', 'features', 'how-it-works', 'review', 'team'];
      const scrollPosition = window.scrollY + 180;

      for (const sectionId of sections) {
        const el = document.getElementById(sectionId);
        if (el) {
          const top = el.offsetTop;
          const height = el.offsetHeight;
          if (scrollPosition >= top && scrollPosition < top + height) {
            setActiveSection(sectionId);
            break;
          }
        }
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const handleNavigate = (href) => {
    const targetId = href.replace('#', '');
    const element = document.getElementById(targetId);
    if (element) {
      const navOffset = 80;
      const elementPosition = element.getBoundingClientRect().top;
      const offsetPosition = elementPosition + window.pageYOffset - navOffset;

      window.scrollTo({
        top: offsetPosition,
        behavior: 'smooth'
      });
      setActiveSection(targetId);
    }
  };

  return (
    <div className="min-h-screen bg-[#07090e] text-slate-100 flex flex-col relative selection:bg-sky-500/20 selection:text-sky-200">
      {/* Background subtle noise and gradient spots */}
      <div className="fixed inset-0 bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(120,119,198,0.06),rgba(255,255,255,0))] pointer-events-none" />

      {/* Top Navigation */}
      <Navbar activeSection={activeSection} onNavigate={handleNavigate} />

      {/* Main Content Sections */}
      <main className="flex-grow">
        <Hero />
        <Stats />
        <Features />
        <HowItWorks />
        <ReviewPreview />
        <Team />
        <CTA />
      </main>

      {/* Footer */}
      <Footer />
    </div>
  );
}
