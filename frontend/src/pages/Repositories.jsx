import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Logo from '../components/common/Logo';
import {
  FolderGit2,
  Lock,
  Globe,
  GitBranch,
  ExternalLink,
  RefreshCw,
  AlertCircle,
  ArrowLeft,
  Loader2,
  PlusCircle,
} from 'lucide-react';

export default function Repositories() {
  const [repositories, setRepositories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchRepositories = async () => {
    setLoading(true);
    setError(null);

    try {
      const apiUrl = import.meta.env.VITE_BACKEND_URL
        ? `${import.meta.env.VITE_BACKEND_URL}/api/github/repositories`
        : '/api/github/repositories';

      const response = await fetch(apiUrl, {
        method: 'GET',
        headers: {
          Accept: 'application/json',
        },
        credentials: 'include',
      });

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Missing installation context. Please connect your GitHub account.');
        }
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Unable to load repositories.');
      }

      const data = await response.json();
      setRepositories(data.repositories || []);
    } catch (err) {
      setError(err.message || 'Unable to load repositories.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRepositories();
  }, []);

  return (
    <div className="min-h-screen bg-[#07090e] text-slate-100 flex flex-col justify-between relative overflow-hidden selection:bg-sky-500/20 selection:text-sky-200">
      {/* Background ambient lighting */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[850px] h-[400px] bg-sky-500/5 rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-96 h-96 bg-blue-600/5 rounded-full blur-[140px] pointer-events-none" />

      {/* Header Navigation */}
      <header className="py-5 px-6 sm:px-10 border-b border-white/[0.04] bg-[#07090e]/70 backdrop-blur-md relative z-20">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <Link to="/" className="focus:outline-none" aria-label="MergeMind Home">
            <Logo />
          </Link>

          <div className="flex items-center gap-3">
            <button
              onClick={fetchRepositories}
              disabled={loading}
              className="neu-button p-2 sm:px-3.5 sm:py-2 rounded-full text-xs font-medium text-slate-300 hover:text-white flex items-center gap-1.5 transition-colors disabled:opacity-50"
              title="Refresh repository list"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-sky-400 ${loading ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">Refresh</span>
            </button>

            <Link
              to="/connect"
              className="neu-button px-4 py-2 rounded-full text-xs font-medium text-slate-300 hover:text-white flex items-center gap-1.5 transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5 text-sky-400" />
              <span>Back to Connect</span>
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 py-10 sm:py-14 relative z-10">
        
        {/* Page Title & Context Header */}
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8 sm:mb-10 pb-6 border-b border-white/[0.04]">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full neu-recessed text-xs font-mono uppercase tracking-wider text-sky-400 mb-3 border border-sky-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-pulse" />
              GITHUB APP WORKSPACE
            </div>
            <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
              Connected Repositories
            </h1>
            <p className="mt-2 text-sm text-slate-400 leading-relaxed font-normal max-w-xl">
              Repositories accessible to the MergeMind GitHub App. These repositories are monitored for semantic conflicts.
            </p>
          </div>

          {!loading && !error && repositories.length > 0 && (
            <div className="neu-recessed px-4 py-2 rounded-xl border border-white/[0.04] self-start sm:self-auto">
              <span className="text-xs font-mono text-slate-400">Total Connected: </span>
              <span className="text-xs font-mono font-bold text-sky-300">{repositories.length}</span>
            </div>
          )}
        </div>

        {/* State 1: Loading State */}
        {loading && (
          <div className="neu-panel rounded-2xl p-12 sm:p-16 border border-white/[0.08] shadow-[0_20px_50px_rgba(0,0,0,0.8)] flex flex-col items-center justify-center text-center my-8">
            <div className="w-14 h-14 rounded-full neu-recessed flex items-center justify-center mb-5 relative">
              <Loader2 className="w-6 h-6 text-sky-400 animate-spin" />
            </div>
            <h2 className="text-lg font-semibold text-white tracking-tight mb-2">
              Loading repositories...
            </h2>
            <p className="text-xs sm:text-sm text-slate-400 max-w-sm">
              Retrieving accessible repositories from your GitHub App installation.
            </p>
          </div>
        )}

        {/* State 2: Error State */}
        {!loading && error && (
          <div className="neu-panel rounded-2xl p-8 sm:p-12 border border-rose-500/20 shadow-[0_20px_50px_rgba(0,0,0,0.8)] flex flex-col items-center justify-center text-center my-8">
            <div className="w-14 h-14 rounded-full neu-recessed flex items-center justify-center mb-5 border border-rose-500/20">
              <AlertCircle className="w-6 h-6 text-rose-400" />
            </div>
            <h2 className="text-xl font-bold text-white tracking-tight mb-2">
              Unable to load repositories.
            </h2>
            <p className="text-xs sm:text-sm text-slate-400 max-w-md mb-6 leading-relaxed">
              {error}
            </p>
            <div className="flex flex-wrap items-center justify-center gap-3">
              <button
                onClick={fetchRepositories}
                className="neu-button px-5 py-2.5 rounded-xl text-xs font-medium text-slate-300 hover:text-white flex items-center gap-2"
              >
                <RefreshCw className="w-3.5 h-3.5 text-sky-400" />
                <span>Try Again</span>
              </button>
              <Link
                to="/connect"
                className="neu-glow-btn px-5 py-2.5 rounded-xl text-xs font-semibold text-white flex items-center gap-2"
              >
                <span>Connect GitHub</span>
              </Link>
            </div>
          </div>
        )}

        {/* State 3: Empty State */}
        {!loading && !error && repositories.length === 0 && (
          <div className="neu-panel rounded-2xl p-10 sm:p-16 border border-white/[0.08] shadow-[0_20px_50px_rgba(0,0,0,0.8)] flex flex-col items-center justify-center text-center my-8">
            <div className="w-16 h-16 rounded-2xl neu-recessed flex items-center justify-center mb-5 text-slate-500">
              <FolderGit2 className="w-8 h-8 text-slate-400" />
            </div>
            <h2 className="text-xl font-bold text-white tracking-tight mb-2">
              No repositories are connected to MergeMind.
            </h2>
            <p className="text-xs sm:text-sm text-slate-400 max-w-md mb-6 leading-relaxed">
              Either your GitHub App installation has no selected repositories, or permissions have not been granted.
            </p>
            <Link
              to="/connect"
              className="neu-glow-btn px-6 py-3 rounded-xl text-xs font-semibold text-white flex items-center gap-2"
            >
              <PlusCircle className="w-4 h-4 text-sky-300" />
              <span>Configure GitHub Repositories</span>
            </Link>
          </div>
        )}

        {/* State 4: Success State (Display Repository Cards) */}
        {!loading && !error && repositories.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 items-stretch">
            {repositories.map((repo) => (
              <div
                key={repo.id}
                className="neu-panel neu-panel-hover rounded-2xl p-6 flex flex-col justify-between border border-white/[0.07] relative group overflow-hidden"
              >
                {/* Top Subtle Glow Line */}
                <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-sky-400/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

                {/* Card Content Top */}
                <div>
                  <div className="flex items-start justify-between gap-3 mb-4">
                    {/* Repository Icon Recessed Well */}
                    <div className="w-11 h-11 rounded-xl neu-recessed flex items-center justify-center text-sky-400 flex-shrink-0">
                      <FolderGit2 className="w-5 h-5" />
                    </div>

                    {/* Private / Public Status Pill */}
                    {repo.private ? (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-500/10 text-amber-300 text-[11px] font-mono border border-amber-500/20">
                        <Lock className="w-3 h-3" />
                        <span>Private</span>
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 text-[11px] font-mono border border-emerald-500/20">
                        <Globe className="w-3 h-3" />
                        <span>Public</span>
                      </span>
                    )}
                  </div>

                  {/* Repository Name */}
                  <h3 className="text-base sm:text-lg font-bold text-white tracking-tight break-words group-hover:text-sky-300 transition-colors">
                    {repo.name}
                  </h3>

                  {/* Owner / Full Name */}
                  <p className="text-xs font-mono text-slate-400 mt-1 truncate">
                    {repo.full_name}
                  </p>

                  {/* Description (if present) */}
                  {repo.description ? (
                    <p className="text-xs text-slate-400 mt-3 line-clamp-2 leading-relaxed font-normal">
                      {repo.description}
                    </p>
                  ) : (
                    <p className="text-xs text-slate-500 mt-3 italic font-normal">
                      No description provided.
                    </p>
                  )}
                </div>

                {/* Card Footer / Bottom Controls */}
                <div className="mt-6 pt-4 border-t border-white/[0.05] space-y-3">
                  {/* Default Branch Tag */}
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="text-slate-500">Branch:</span>
                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md neu-recessed text-slate-300 border border-white/[0.03]">
                      <GitBranch className="w-3 h-3 text-sky-400" />
                      <span>{repo.default_branch || 'main'}</span>
                    </span>
                  </div>

                  {/* Open Repository External Action */}
                  <a
                    href={repo.html_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="neu-button w-full py-2.5 px-4 rounded-xl text-xs font-medium text-slate-300 hover:text-white flex items-center justify-center gap-2 group/btn transition-colors"
                  >
                    <span>Open Repository</span>
                    <ExternalLink className="w-3.5 h-3.5 text-sky-400 group-hover/btn:translate-x-0.5 group-hover/btn:-translate-y-0.5 transition-transform" />
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}

      </main>

      {/* Footer */}
      <footer className="py-6 px-6 border-t border-white/[0.04] text-center text-[11px] font-mono text-slate-600 relative z-10">
        MergeMind Developer Workspace • Autonomous Git Conflict Driver
      </footer>
    </div>
  );
}
