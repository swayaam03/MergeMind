import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import Logo from '../components/common/Logo';
import { User, Lock, Mail, ArrowRight, Loader2, AlertCircle, CheckCircle2, Shield } from 'lucide-react';
import { loginUser, registerUser } from '../services/auth';

export default function AuthPage() {
  const navigate = useNavigate();
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (isRegister) {
        if (!email.includes('@')) {
          throw new Error('Please enter a valid email address.');
        }
        await registerUser(username, email, password);
      } else {
        await loginUser(username, password);
      }
      navigate('/connect');
    } catch (err) {
      setError(err.message || 'Authentication failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#07090e] text-slate-100 flex flex-col justify-between relative overflow-hidden selection:bg-sky-500/20 selection:text-sky-200">
      {/* Background ambient lighting */}
      <div className="absolute top-[-10%] left-1/2 -translate-x-1/2 w-[700px] h-[350px] bg-sky-500/10 rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-5%] w-[500px] h-[500px] bg-indigo-600/5 rounded-full blur-[140px] pointer-events-none" />

      {/* Header */}
      <header className="py-6 px-6 sm:px-10 border-b border-white/[0.04] bg-[#07090e]/70 backdrop-blur-md relative z-20">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <Link to="/" className="focus:outline-none">
            <Logo />
          </Link>
          <span className="text-xs font-mono text-slate-400">
            {isRegister ? 'Already have an account?' : "Don't have an account?"}{' '}
            <button
              onClick={() => {
                setIsRegister(!isRegister);
                setError(null);
              }}
              className="text-sky-400 hover:text-sky-300 font-semibold underline underline-offset-4 ml-1"
            >
              {isRegister ? 'Sign In' : 'Sign Up'}
            </button>
          </span>
        </div>
      </header>

      {/* Main Login / Register Card */}
      <main className="flex-1 flex items-center justify-center px-4 sm:px-6 py-12 relative z-10">
        <div className="max-w-md w-full mx-auto">
          {/* Title Header */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full neu-recessed text-[11px] font-mono uppercase tracking-wider text-sky-400 mb-3 border border-sky-500/20">
              <Shield className="w-3.5 h-3.5 text-sky-400" />
              <span>MergeMind Account</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              {isRegister ? 'Create your account' : 'Welcome back'}
            </h1>
            <p className="mt-2 text-xs sm:text-sm text-slate-400">
              {isRegister
                ? 'Sign up to manage connected repositories and monitor merge conflicts.'
                : 'Sign in to access your connected repositories and conflict resolver.'}
            </p>
          </div>

          {/* Form Card */}
          <div className="neu-panel rounded-2xl p-6 sm:p-8 border border-white/[0.08] shadow-[0_20px_50px_rgba(0,0,0,0.8)]">
            {/* Tab switch */}
            <div className="flex rounded-xl neu-recessed p-1 mb-6 border border-white/[0.04]">
              <button
                type="button"
                onClick={() => {
                  setIsRegister(false);
                  setError(null);
                }}
                className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all ${
                  !isRegister
                    ? 'bg-sky-500 text-white shadow-lg shadow-sky-500/20'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Sign In
              </button>
              <button
                type="button"
                onClick={() => {
                  setIsRegister(true);
                  setError(null);
                }}
                className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all ${
                  isRegister
                    ? 'bg-sky-500 text-white shadow-lg shadow-sky-500/20'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Create Account
              </button>
            </div>

            {/* Error Banner */}
            {error && (
              <div className="mb-5 p-3.5 rounded-xl bg-rose-950/30 border border-rose-500/30 flex items-start gap-3">
                <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
                <p className="text-xs text-rose-300 leading-relaxed">{error}</p>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Username Input */}
              <div>
                <label className="block text-xs font-mono text-slate-300 mb-1.5">
                  {isRegister ? 'Username' : 'Username or Email'}
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                    <User className="w-4 h-4" />
                  </div>
                  <input
                    type="text"
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder={isRegister ? 'e.g. swayaam03' : 'Enter username or email'}
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-white/[0.03] border border-white/[0.08] focus:border-sky-500/60 focus:ring-1 focus:ring-sky-500/60 text-xs sm:text-sm text-white placeholder-slate-500 outline-none transition-all font-mono"
                  />
                </div>
              </div>

              {/* Email Input (only on register) */}
              {isRegister && (
                <div>
                  <label className="block text-xs font-mono text-slate-300 mb-1.5">
                    Email Address
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                      <Mail className="w-4 h-4" />
                    </div>
                    <input
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="you@example.com"
                      className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-white/[0.03] border border-white/[0.08] focus:border-sky-500/60 focus:ring-1 focus:ring-sky-500/60 text-xs sm:text-sm text-white placeholder-slate-500 outline-none transition-all font-mono"
                    />
                  </div>
                </div>
              )}

              {/* Password Input */}
              <div>
                <label className="block text-xs font-mono text-slate-300 mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-white/[0.03] border border-white/[0.08] focus:border-sky-500/60 focus:ring-1 focus:ring-sky-500/60 text-xs sm:text-sm text-white placeholder-slate-500 outline-none transition-all font-mono"
                  />
                </div>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={loading}
                className="w-full mt-2 neu-glow-btn py-3 px-4 rounded-xl text-xs sm:text-sm font-semibold text-white flex items-center justify-center gap-2 group disabled:opacity-60 transition-all"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin text-sky-200" />
                    <span>Processing...</span>
                  </>
                ) : (
                  <>
                    <span>{isRegister ? 'Create Account' : 'Sign In'}</span>
                    <ArrowRight className="w-4 h-4 text-sky-200 group-hover:translate-x-0.5 transition-transform" />
                  </>
                )}
              </button>
            </form>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="py-4 text-center text-[11px] font-mono text-slate-600 border-t border-white/[0.03]">
        MergeMind Workspace • Secure GitHub Integration
      </footer>
    </div>
  );
}
