import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import Logo from '../components/common/Logo';
import {
  GitPullRequest,
  ArrowLeft,
  ArrowRight,
  ExternalLink,
  RefreshCw,
  AlertCircle,
  Loader2,
  FolderGit2,
  GitBranch,
  CheckCircle2,
} from 'lucide-react';

export default function Repository() {
  const { owner, repo } = useParams();
  const navigate = useNavigate();
  const [repository, setRepository] = useState({ owner, name: repo, full_name: `${owner}/${repo}` });
  const [pullRequests, setPullRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchPullRequests = async () => {
    setLoading(true);
    setError(null);

    try {
      const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';
      const apiUrl = `${backendUrl}/api/github/repositories/${owner}/${repo}/pulls`;

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
        if (response.status === 403) {
          throw new Error(`Repository '${owner}/${repo}' is not accessible to this installation.`);
        }
        if (response.status === 404) {
          throw new Error(`Repository '${owner}/${repo}' was not found on GitHub.`);
        }
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Unable to load pull requests.');
      }

      const data = await response.json();
      setRepository(data.repository || { owner, name: repo, full_name: `${owner}/${repo}` });
      setPullRequests(data.pull_requests || []);
    } catch (err) {
      setError(err.message || 'Unable to load pull requests.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPullRequests();
  }, [owner, repo]);

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
              onClick={fetchPullRequests}
              disabled={loading}
              className="neu-button p-2 sm:px-3.5 sm:py-2 rounded-full text-xs font-medium text-slate-300 hover:text-white flex items-center gap-1.5 transition-colors disabled:opacity-50"
              title="Refresh pull requests"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-sky-400 ${loading ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">Refresh</span>
            </button>

            <Link
              to="/repositories"
              className="neu-button px-4 py-2 rounded-full text-xs font-medium text-slate-300 hover:text-white flex items-center gap-1.5 transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5 text-sky-400" />
              <span>Back to Repositories</span>
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 py-10 sm:py-14 relative z-10">
        
        {/* Repository Header Card */}
        <div className="neu-panel rounded-2xl p-6 sm:p-8 border border-white/[0.07] mb-10 shadow-[0_15px_40px_rgba(0,0,0,0.6)]">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-xl neu-recessed flex items-center justify-center text-sky-400 flex-shrink-0 mt-1">
                <FolderGit2 className="w-6 h-6" />
              </div>
              <div>
                <div className="inline-flex items-center gap-2 px-3 py-0.5 rounded-full neu-recessed text-[11px] font-mono uppercase tracking-wider text-sky-400 mb-2 border border-sky-500/20">
                  <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-pulse" />
                  REPOSITORY
                </div>
                <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                  {repo}
                </h1>
                <p className="text-xs sm:text-sm font-mono text-slate-400 mt-1">
                  {owner}/{repo}
                </p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <a
                href={`https://github.com/${owner}/${repo}`}
                target="_blank"
                rel="noopener noreferrer"
                className="neu-button px-4 py-2 rounded-xl text-xs font-medium text-slate-300 hover:text-white flex items-center gap-1.5 transition-colors"
              >
                <span>View on GitHub</span>
                <ExternalLink className="w-3.5 h-3.5 text-sky-400" />
              </a>
            </div>
          </div>
        </div>

        {/* Section Heading: Pull Requests */}
        <div className="flex items-center justify-between pb-4 mb-6 border-b border-white/[0.04]">
          <div className="flex items-center gap-2.5">
            <GitPullRequest className="w-5 h-5 text-sky-400" />
            <h2 className="text-xl font-bold text-white tracking-tight">
              Pull Requests
            </h2>
          </div>
          {!loading && !error && (
            <div className="neu-recessed px-3 py-1 rounded-lg border border-white/[0.04]">
              <span className="text-xs font-mono text-slate-400">Open PRs: </span>
              <span className="text-xs font-mono font-bold text-sky-300">{pullRequests.length}</span>
            </div>
          )}
        </div>

        {/* State 1: Loading State */}
        {loading && (
          <div className="neu-panel rounded-2xl p-12 sm:p-16 border border-white/[0.08] shadow-[0_20px_50px_rgba(0,0,0,0.8)] flex flex-col items-center justify-center text-center my-8">
            <div className="w-14 h-14 rounded-full neu-recessed flex items-center justify-center mb-5 relative">
              <Loader2 className="w-6 h-6 text-sky-400 animate-spin" />
            </div>
            <h3 className="text-lg font-semibold text-white tracking-tight mb-2">
              Loading pull requests...
            </h3>
            <p className="text-xs sm:text-sm text-slate-400 max-w-sm">
              Retrieving open pull requests from GitHub for {owner}/{repo}.
            </p>
          </div>
        )}

        {/* State 2: Error State */}
        {!loading && error && (
          <div className="neu-panel rounded-2xl p-8 sm:p-12 border border-rose-500/20 shadow-[0_20px_50px_rgba(0,0,0,0.8)] flex flex-col items-center justify-center text-center my-8">
            <div className="w-14 h-14 rounded-full neu-recessed flex items-center justify-center mb-5 border border-rose-500/20">
              <AlertCircle className="w-6 h-6 text-rose-400" />
            </div>
            <h3 className="text-xl font-bold text-white tracking-tight mb-2">
              Unable to load pull requests.
            </h3>
            <p className="text-xs sm:text-sm text-slate-400 max-w-md mb-6 leading-relaxed">
              {error}
            </p>
            <div className="flex flex-wrap items-center justify-center gap-3">
              <button
                onClick={fetchPullRequests}
                className="neu-button px-5 py-2.5 rounded-xl text-xs font-medium text-slate-300 hover:text-white flex items-center gap-2"
              >
                <RefreshCw className="w-3.5 h-3.5 text-sky-400" />
                <span>Try Again</span>
              </button>
              <Link
                to="/repositories"
                className="neu-glow-btn px-5 py-2.5 rounded-xl text-xs font-semibold text-white flex items-center gap-2"
              >
                <span>Back to Repositories</span>
              </Link>
            </div>
          </div>
        )}

        {/* State 3: Empty State */}
        {!loading && !error && pullRequests.length === 0 && (
          <div className="neu-panel rounded-2xl p-10 sm:p-16 border border-white/[0.08] shadow-[0_20px_50px_rgba(0,0,0,0.8)] flex flex-col items-center justify-center text-center my-8">
            <div className="w-16 h-16 rounded-2xl neu-recessed flex items-center justify-center mb-5 text-slate-500">
              <GitPullRequest className="w-8 h-8 text-slate-400" />
            </div>
            <h3 className="text-xl font-bold text-white tracking-tight mb-2">
              No open pull requests found.
            </h3>
            <p className="text-xs sm:text-sm text-slate-400 max-w-md mb-6 leading-relaxed">
              There are currently no open pull requests in {owner}/{repo}. Create a pull request on GitHub to analyze merge conflicts.
            </p>
            <a
              href={`https://github.com/${owner}/${repo}/pulls`}
              target="_blank"
              rel="noopener noreferrer"
              className="neu-glow-btn px-6 py-3 rounded-xl text-xs font-semibold text-white flex items-center gap-2"
            >
              <span>Open on GitHub</span>
              <ExternalLink className="w-3.5 h-3.5 text-sky-300" />
            </a>
          </div>
        )}

        {/* State 4: Success State (PR Cards) */}
        {!loading && !error && pullRequests.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-stretch">
            {pullRequests.map((pr) => (
              <div
                key={pr.number}
                onClick={() => navigate(`/repositories/${owner}/${repo}/pulls/${pr.number}`)}
                className="neu-panel neu-panel-hover rounded-2xl p-6 flex flex-col justify-between border border-white/[0.07] relative group cursor-pointer transition-all duration-200"
              >
                {/* Top highlight glow */}
                <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-sky-400/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

                <div>
                  {/* PR Number & Status Badges */}
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <span className="text-xs font-mono font-bold text-sky-400">
                      #{pr.number}
                    </span>
                    <div className="flex items-center gap-2">
                      {pr.draft && (
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
                          Draft
                        </span>
                      )}
                      <span className="text-[10px] font-mono uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                        OPEN
                      </span>
                    </div>
                  </div>

                  {/* PR Title */}
                  <Link
                    to={`/repositories/${owner}/${repo}/pulls/${pr.number}`}
                    className="text-lg font-bold text-white tracking-tight leading-snug mb-2 hover:text-sky-300 transition-colors block"
                  >
                    {pr.title}
                  </Link>

                  {/* Author */}
                  <p className="text-xs font-mono text-slate-400 mb-4">
                    by <span className="text-slate-200 font-medium">{pr.user?.login || 'unknown'}</span>
                  </p>

                  {/* Branch Diff Flow: Source branch → Target branch */}
                  <div className="flex items-center gap-2 px-3 py-2 rounded-xl neu-recessed text-xs font-mono border border-white/[0.03]">
                    <span className="text-sky-300 truncate max-w-[140px]" title={pr.head?.ref}>
                      {pr.head?.ref || 'head'}
                    </span>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-500 flex-shrink-0" />
                    <span className="text-slate-300 truncate max-w-[140px]" title={pr.base?.ref}>
                      {pr.base?.ref || 'base'}
                    </span>
                  </div>
                </div>

                {/* Footer Controls: Analyze Pull Request & View on GitHub */}
                <div className="mt-6 pt-4 border-t border-white/[0.05] flex flex-wrap items-center justify-between gap-3">
                  <Link
                    to={`/repositories/${owner}/${repo}/pulls/${pr.number}`}
                    className="neu-glow-btn flex-1 py-2.5 px-4 rounded-xl text-xs font-semibold text-white flex items-center justify-center gap-2 group/btn transition-all"
                  >
                    <span>Analyze Pull Request</span>
                    <ArrowRight className="w-3.5 h-3.5 text-sky-300 group-hover/btn:translate-x-1 transition-transform" />
                  </Link>

                  <a
                    href={pr.html_url}
                    onClick={(e) => e.stopPropagation()}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="neu-button px-3 py-2.5 rounded-xl text-xs font-medium text-slate-300 hover:text-white inline-flex items-center gap-1.5 transition-colors group/btn flex-shrink-0"
                    title="View on GitHub"
                  >
                    <span>View on GitHub</span>
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
        MergeMind Developer Workspace • Repository Pull Request Viewer
      </footer>
    </div>
  );
}
