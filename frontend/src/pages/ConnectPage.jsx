import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import Logo from '../components/common/Logo';
import GitHubConnectCard from '../components/connect/GitHubConnectCard';
import ConnectionFlow from '../components/connect/ConnectionFlow';
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  User,
  LogOut,
  LogIn,
  Link as LinkIcon,
  ShieldCheck,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { checkGitHubStatus } from '../services/github';
import {
  fetchCurrentUser,
  logoutUser,
  connectGitHubInstallation,
  disconnectGitHub,
} from '../services/auth';

function GithubIcon({ className = 'w-5 h-5' }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
      />
    </svg>
  );
}

export default function ConnectPage() {
  const navigate = useNavigate();
  const [currentUser, setCurrentUser] = useState(null);
  const [alreadyConnected, setAlreadyConnected] = useState(false);
  const [repoCount, setRepoCount] = useState(null);
  const [manualInstallId, setManualInstallId] = useState('167531148');
  const [linking, setLinking] = useState(false);
  const [linkError, setLinkError] = useState(null);

  const loadStatusAndUser = async () => {
    // 1. Check if user is logged in
    const user = await fetchCurrentUser();
    if (user) {
      setCurrentUser(user);
      if (user.is_github_connected) {
        setAlreadyConnected(true);
        setRepoCount(user.repository_count);
      }
    }

    // 2. Check general GitHub status via cookie
    const status = await checkGitHubStatus();
    if (status && status.connected) {
      setAlreadyConnected(true);
      if (typeof status.repository_count === 'number') {
        setRepoCount(status.repository_count);
      }
    }
  };

  useEffect(() => {
    // Check if GitHub redirected back with installation_id query param
    const params = new URLSearchParams(window.location.search);
    const installId = params.get('installation_id');
    if (installId) {
      const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';
      window.location.href = `${backendUrl}/api/github/setup?installation_id=${installId}`;
      return;
    }

    loadStatusAndUser();
  }, []);

  const handleManualLink = async (e) => {
    e.preventDefault();
    if (!manualInstallId) return;
    setLinking(true);
    setLinkError(null);
    try {
      if (currentUser) {
        await connectGitHubInstallation(manualInstallId);
      } else {
        // Direct setup redirect to establish cookie
        const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';
        window.location.href = `${backendUrl}/api/github/setup?installation_id=${manualInstallId}`;
        return;
      }
      await loadStatusAndUser();
      navigate('/repositories');
    } catch (err) {
      setLinkError(err.message || 'Failed to link GitHub installation.');
    } finally {
      setLinking(false);
    }
  };

  const handleDisconnect = async () => {
    if (!confirm('Are you sure you want to disconnect GitHub?')) return;
    try {
      if (currentUser) {
        await disconnectGitHub();
      }
      setAlreadyConnected(false);
      setRepoCount(null);
      await loadStatusAndUser();
    } catch (err) {
      console.error('Failed to disconnect:', err);
    }
  };

  const handleLogout = async () => {
    await logoutUser();
    setCurrentUser(null);
    setAlreadyConnected(false);
  };

  return (
    <div className="min-h-screen bg-[#07090e] text-slate-100 flex flex-col justify-between relative overflow-hidden selection:bg-sky-500/20 selection:text-sky-200">
      {/* Background ambient lighting */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-sky-500/5 rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-96 h-96 bg-blue-600/5 rounded-full blur-[120px] pointer-events-none" />

      {/* Header */}
      <header className="py-6 px-6 sm:px-10 border-b border-white/[0.04] bg-[#07090e]/70 backdrop-blur-md relative z-20">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <Link to="/" className="focus:outline-none" aria-label="MergeMind Home">
            <Logo />
          </Link>

          <div className="flex items-center gap-3">
            {currentUser ? (
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/[0.04] border border-white/[0.06] text-xs font-mono text-slate-300">
                  <User className="w-3.5 h-3.5 text-sky-400" />
                  <span>{currentUser.username}</span>
                </div>
                <button
                  onClick={handleLogout}
                  className="neu-button px-3 py-1.5 rounded-full text-xs font-mono text-slate-400 hover:text-white flex items-center gap-1.5 transition-colors"
                >
                  <LogOut className="w-3 h-3 text-rose-400" />
                  <span>Sign Out</span>
                </button>
              </div>
            ) : (
              <Link
                to="/login"
                className="neu-button px-4 py-2 rounded-full text-xs font-medium text-slate-300 hover:text-white flex items-center gap-1.5 transition-colors"
              >
                <LogIn className="w-3.5 h-3.5 text-sky-400" />
                <span>Sign In / Register</span>
              </Link>
            )}

            <Link
              to="/"
              className="hidden sm:flex neu-button px-4 py-2 rounded-full text-xs font-medium text-slate-300 hover:text-white items-center gap-1.5 transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5 text-sky-400" />
              <span>Home</span>
            </Link>
          </div>
        </div>
      </header>

      {/* Main Centered Content */}
      <main className="flex-1 flex items-center justify-center px-4 sm:px-6 py-12 sm:py-16 relative z-10">
        <div className="max-w-5xl w-full mx-auto">
          {/* Header Typography */}
          <div className="text-center max-w-2xl mx-auto mb-10 sm:mb-12">
            <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full neu-recessed text-xs font-mono uppercase tracking-wider text-sky-400 mb-4 border border-sky-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-pulse" />
              WORKSPACE INTEGRATION
            </div>

            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-white tracking-tight">
              Connect your GitHub
            </h1>

            <p className="mt-3.5 text-sm sm:text-base text-slate-400 leading-relaxed max-w-xl mx-auto font-normal">
              {currentUser
                ? `Logged in as ${currentUser.username}. Link your GitHub App to access repositories and monitor conflicts.`
                : 'Connect your GitHub account to let MergeMind discover your repositories and resolve merge conflicts.'}
            </p>
          </div>

          {/* Connected Alert Banner */}
          {alreadyConnected && (
            <div className="mb-8 p-4 sm:p-5 rounded-2xl neu-panel border border-emerald-500/30 bg-emerald-950/10 flex flex-col sm:flex-row items-center justify-between gap-4 animate-in fade-in slide-in-from-top-2 duration-300">
              <div className="flex items-center gap-3.5">
                <div className="w-10 h-10 rounded-xl neu-recessed flex items-center justify-center text-emerald-400 flex-shrink-0 border border-emerald-500/20">
                  <CheckCircle2 className="w-6 h-6 text-emerald-400" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h4 className="text-sm font-semibold text-white">GitHub App Connected</h4>
                    <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
                      Active
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {currentUser?.github_username
                      ? `Connected to GitHub account @${currentUser.github_username}`
                      : 'Installation verified'}
                    {repoCount ? ` with access to ${repoCount} repository(ies).` : '.'}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 w-full sm:w-auto">
                <button
                  type="button"
                  onClick={handleDisconnect}
                  className="neu-button px-3.5 py-2 rounded-xl text-xs font-mono text-rose-400 hover:text-rose-300 transition-colors"
                >
                  Disconnect
                </button>
                <Link
                  to="/repositories"
                  className="flex-1 sm:flex-none neu-glow-btn px-5 py-2.5 rounded-xl text-xs font-semibold text-white flex items-center justify-center gap-2 group"
                >
                  <span>Go to Repositories</span>
                  <ArrowRight className="w-3.5 h-3.5 text-sky-300 group-hover:translate-x-1 transition-transform" />
                </Link>
              </div>
            </div>
          )}

          {/* Quick Manual Installation Link Banner (for instant connection) */}
          {!alreadyConnected && (
            <div className="mb-8 p-5 rounded-2xl neu-panel border border-sky-500/20 bg-sky-950/10 flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl neu-recessed flex items-center justify-center text-sky-400 flex-shrink-0 border border-sky-400/20">
                  <Github className="w-5 h-5 text-sky-400" />
                </div>
                <div>
                  <h4 className="text-xs sm:text-sm font-semibold text-white">Already installed on GitHub?</h4>
                  <p className="text-xs text-slate-400">
                    Link your active GitHub installation ID (<code className="text-sky-300 font-mono">167531148</code>) directly to your account.
                  </p>
                </div>
              </div>

              <form onSubmit={handleManualLink} className="flex items-center gap-2 w-full sm:w-auto">
                <input
                  type="number"
                  value={manualInstallId}
                  onChange={(e) => setManualInstallId(e.target.value)}
                  placeholder="Installation ID"
                  className="px-3 py-1.5 rounded-lg bg-black/40 border border-white/10 text-xs font-mono text-white placeholder-slate-500 focus:border-sky-500 outline-none w-36"
                />
                <button
                  type="submit"
                  disabled={linking || !manualInstallId}
                  className="neu-glow-btn px-4 py-2 rounded-lg text-xs font-semibold text-white flex items-center gap-1.5 disabled:opacity-50"
                >
                  {linking ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <LinkIcon className="w-3.5 h-3.5" />}
                  <span>Link ID</span>
                </button>
              </form>
            </div>
          )}

          {linkError && (
            <div className="mb-6 p-4 rounded-xl bg-rose-950/30 border border-rose-500/30 flex items-center gap-3">
              <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
              <p className="text-xs text-rose-300">{linkError}</p>
            </div>
          )}

          {/* Left = Connect Card, Right = Lifecycle Flow */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch">
            <div className="lg:col-span-7 flex flex-col">
              <GitHubConnectCard />
            </div>
            <div className="lg:col-span-5 flex flex-col">
              <ConnectionFlow />
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="py-6 px-6 sm:px-10 border-t border-white/[0.04] bg-[#07090e]/70 backdrop-blur-md relative z-20">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-xs font-mono text-slate-500">
          <div>MergeMind Workspace • Autonomous Git Conflict Driver</div>
          <div className="flex items-center gap-4">
            <span className="inline-flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              API Online
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}
