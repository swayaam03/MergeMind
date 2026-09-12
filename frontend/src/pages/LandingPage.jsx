import React, { useState, useEffect, useRef } from 'react';
import Navbar from '../components/layout/Navbar';
import Hero from '../components/layout/Hero';
import Stats from '../components/layout/Stats';
import Features from '../components/layout/Features';
import HowItWorks from '../components/layout/HowItWorks';
import ReviewPreview from '../components/review/ReviewPreview';
import Footer from '../components/layout/Footer';

export default function LandingPage() {
  const [activeSection, setActiveSection] = useState('home');
  const isNavigatingRef = useRef(false);
  const navTimeoutRef = useRef(null);

  useEffect(() => {
    const handleScroll = () => {
      // Prevent scroll event from fighting with smooth navigation click
      if (isNavigatingRef.current) return;

      // Bottom of page detection (activates the final section reliably)
      if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 70) {
        setActiveSection('how-it-works');
        return;
      }

      const sections = ['home', 'about', 'features', 'how-it-works', 'review'];
      const scrollPosition = window.scrollY + 200;

      for (const sectionId of sections) {
        const el = document.getElementById(sectionId);
        if (el) {
          const top = el.offsetTop;
          const height = el.offsetHeight;
          if (scrollPosition >= top && scrollPosition < top + height) {
            // Map 'review' to 'how-it-works' so navbar active state doesn't blink or disappear in review section
            const mappedSection = sectionId === 'review' ? 'how-it-works' : sectionId;
            setActiveSection(mappedSection);
            break;
          }
        }
      }
    };

    const handleUserInterrupt = () => {
      isNavigatingRef.current = false;
      if (navTimeoutRef.current) clearTimeout(navTimeoutRef.current);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    window.addEventListener('wheel', handleUserInterrupt, { passive: true });
    window.addEventListener('touchmove', handleUserInterrupt, { passive: true });

    return () => {
      window.removeEventListener('scroll', handleScroll);
      window.removeEventListener('wheel', handleUserInterrupt);
      window.removeEventListener('touchmove', handleUserInterrupt);
      if (navTimeoutRef.current) clearTimeout(navTimeoutRef.current);
    };
  }, []);

  const handleNavigate = (href) => {
    const targetId = href.replace('#', '');
    const element = document.getElementById(targetId);
    if (element) {
      isNavigatingRef.current = true;
      if (navTimeoutRef.current) clearTimeout(navTimeoutRef.current);

      setActiveSection(targetId);

      const navOffset = 80;
      const elementPosition = element.getBoundingClientRect().top;
      const offsetPosition = elementPosition + window.pageYOffset - navOffset;

      window.scrollTo({
        top: offsetPosition,
        behavior: 'smooth'
      });

      // Release navigation lock after smooth scroll finishes
      navTimeoutRef.current = setTimeout(() => {
        isNavigatingRef.current = false;
      }, 850);
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
      </main>

      {/* Footer */}
      <Footer />
    </div>
  );
}
