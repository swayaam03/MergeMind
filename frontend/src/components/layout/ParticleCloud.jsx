import React, { useEffect, useRef } from 'react';

export default function ParticleCloud({ className = "" }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    let animationFrameId;
    let width = (canvas.width = canvas.parentElement.offsetWidth);
    let height = (canvas.height = canvas.parentElement.offsetHeight);

    const handleResize = () => {
      if (!canvas.parentElement) return;
      width = canvas.width = canvas.parentElement.offsetWidth;
      height = canvas.height = canvas.parentElement.offsetHeight;
    };

    window.addEventListener('resize', handleResize);

    // Number of particles for dense cosmic ring
    const PARTICLE_COUNT = 1400;
    const particles = [];

    // Tilted torus / orbital cloud parameters
    const ringRadiusX = Math.min(width, height) * 0.42;
    const ringRadiusY = ringRadiusX * 0.58;
    const tiltAngle = -0.45; // ~ -25 degrees tilt
    const cosTilt = Math.cos(tiltAngle);
    const sinTilt = Math.sin(tiltAngle);

    for (let i = 0; i < PARTICLE_COUNT; i++) {
      // Angle along the orbital loop
      const theta = Math.random() * Math.PI * 2;
      // Dispersion around the ring core
      const spread = (Math.random() - 0.5) * (Math.random() - 0.5) * 85;
      const rX = ringRadiusX + spread;
      const rY = ringRadiusY + spread * 0.6;

      // Particle position in ring plane
      const px = Math.cos(theta) * rX;
      const py = Math.sin(theta) * rY;
      const pz = (Math.random() - 0.5) * 60; // thickness in z

      // Apply tilt rotation
      const x = px * cosTilt - py * sinTilt;
      const y = px * sinTilt + py * cosTilt;
      const z = pz;

      particles.push({
        baseX: x,
        baseY: y,
        baseZ: z,
        theta,
        speed: 0.0015 + Math.random() * 0.002,
        rX,
        rY,
        size: Math.random() * 1.6 + 0.3,
        alpha: Math.random() * 0.7 + 0.2,
        twinkleSpeed: 0.02 + Math.random() * 0.04,
        twinklePhase: Math.random() * Math.PI * 2,
        colorType: Math.random() > 0.85 ? 'blue' : 'white',
      });
    }

    // Additional background ambient stars
    const ambientStars = [];
    for (let i = 0; i < 90; i++) {
      ambientStars.push({
        x: Math.random() * width,
        y: Math.random() * height,
        size: Math.random() * 1.2 + 0.2,
        alpha: Math.random() * 0.4 + 0.1,
        twinkle: Math.random() * 0.02,
      });
    }

    let mouseX = 0;
    let mouseY = 0;
    let targetMouseX = 0;
    let targetMouseY = 0;

    const handleMouseMove = (e) => {
      const rect = canvas.getBoundingClientRect();
      targetMouseX = ((e.clientX - rect.left) / width - 0.5) * 30;
      targetMouseY = ((e.clientY - rect.top) / height - 0.5) * 30;
    };

    window.addEventListener('mousemove', handleMouseMove);

    let time = 0;

    const render = () => {
      time += 1;
      ctx.clearRect(0, 0, width, height);

      // Smooth mouse follow
      mouseX += (targetMouseX - mouseX) * 0.05;
      mouseY += (targetMouseY - mouseY) * 0.05;

      const centerX = width * 0.52 + mouseX;
      const centerY = height * 0.5 + mouseY;

      // Draw faint celestial background glow
      const radialGlow = ctx.createRadialGradient(
        centerX,
        centerY,
        10,
        centerX,
        centerY,
        ringRadiusX * 1.2
      );
      radialGlow.addColorStop(0, 'rgba(56, 189, 248, 0.04)');
      radialGlow.addColorStop(0.5, 'rgba(30, 58, 138, 0.025)');
      radialGlow.addColorStop(1, 'rgba(0, 0, 0, 0)');
      ctx.fillStyle = radialGlow;
      ctx.beginPath();
      ctx.arc(centerX, centerY, ringRadiusX * 1.2, 0, Math.PI * 2);
      ctx.fill();

      // Draw ambient stars
      ambientStars.forEach((star) => {
        const starAlpha =
          star.alpha + Math.sin(time * star.twinkle) * 0.15;
        ctx.fillStyle = `rgba(224, 242, 254, ${Math.max(0, starAlpha)})`;
        ctx.beginPath();
        ctx.arc(star.x, star.y, star.size, 0, Math.PI * 2);
        ctx.fill();
      });

      // Draw orbital stardust
      particles.forEach((p) => {
        p.theta += p.speed;

        const px = Math.cos(p.theta) * p.rX;
        const py = Math.sin(p.theta) * p.rY;

        // Tilted coordinates
        const x = px * cosTilt - py * sinTilt + centerX;
        const y = px * sinTilt + py * cosTilt + centerY;

        // Twinkle factor
        const twinkle = Math.sin(time * p.twinkleSpeed + p.twinklePhase);
        const currentAlpha = Math.min(
          1,
          Math.max(0.1, p.alpha + twinkle * 0.25)
        );

        // Z-depth color & size modulation
        const depth = (py / ringRadiusY + 1) / 2; // 0 to 1
        const size = p.size * (0.8 + depth * 0.5);

        if (p.colorType === 'blue') {
          ctx.fillStyle = `rgba(125, 211, 252, ${currentAlpha * 0.9})`;
        } else {
          ctx.fillStyle = `rgba(248, 250, 252, ${currentAlpha * 0.85})`;
        }

        ctx.beginPath();
        ctx.arc(x, y, size, 0, Math.PI * 2);
        ctx.fill();

        // Extra glowing core for brighter particles
        if (size > 1.2 && Math.random() > 0.6) {
          ctx.fillStyle = `rgba(186, 230, 253, ${currentAlpha * 0.2})`;
          ctx.beginPath();
          ctx.arc(x, y, size * 2.4, 0, Math.PI * 2);
          ctx.fill();
        }
      });

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('mousemove', handleMouseMove);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className={`w-full h-full pointer-events-none ${className}`}
    />
  );
}
