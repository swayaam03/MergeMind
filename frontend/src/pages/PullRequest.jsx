import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import Logo from '../components/common/Logo';
import {
  GitPullRequest,
  ArrowLeft,
  ArrowRight,
  ExternalLink,
  RefreshCw,
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  GitBranch,
  User,
  ShieldAlert,
  Sparkles,
  Info,
  FileCode,
} from 'lucide-react';

export default function PullRequest() {
  const { owner, repo, pullNumber } = useParams();
  const [pullRequest, setPullRequest] = useState(null);
  const [repository, setRepository] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [errorStatus, setErrorStatus] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [conflictData, setConflictData] = useState(null);
  const [analysisError, setAnalysisError] = useState(null);

  const fetchPullRequest = async () => {
    setLoading(true);
    setError(null);
    setErrorStatus(null);
    setConflictData(null);
    setAnalysisError(null);

    try {
      const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';
      const apiUrl = `${backendUrl}/api/github/repositories/${owner}/${repo}/pulls/${pullNumber}`;

      const response = await fetch(apiUrl, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
        credentials: 'include',
      });

      if (response.status === 401) {
        setErrorStatus(401);
        throw new Error('Missing installation context. Please reconnect your GitHub App.');
      }

      if (response.status === 403) {
        setErrorStatus(403);
        throw new Error('Repository is not accessible to this installation.');
      }

      if (response.status === 404) {
        setErrorStatus(404);
        throw new Error('Pull request not found.');
      }

      if (!response.ok) {
        setErrorStatus(response.status);
        throw new Error('Unable to check pull request.');
      }

      const data = await response.json();
      setRepository(data.repository);
      setPullRequest(data.pull_request);
    } catch (err) {
      console.error('Error fetching pull request detail:', err);
      setError(err.message || 'Unable to check pull request.');
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzeConflicts = async () => {
    setAnalyzing(true);
    setAnalysisError(null);

    try {
      const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';
      const apiUrl = `${backendUrl}/api/github/repositories/${owner}/${repo}/pulls/${pullNumber}/conflicts`;

      const response = await fetch(apiUrl, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
        credentials: 'include',
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Unable to analyze conflicts.');
      }

      setConflictData(data);
    } catch (err) {
      console.error('Error analyzing conflicts:', err);
      setAnalysisError(err.message || 'Failed to analyze conflicts.');
    } finally {
      setAnalyzing(false);
    }
  };

  useEffect(() => {
    if (owner && repo && pullNumber) {
      fetchPullRequest();
    }
  }, [owner, repo, pullNumber]);

  return (
    <div className="min-h-screen bg-[#0B0F17] text-slate-100 flex flex-col font-sans selection:bg-sky-500/30 selection:text-sky-200">
      {/* Background ambient lighting */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <div className="absolute top-[-10%] left-[-10%] w-[45vw] h-[45vw] rounded-full bg-sky-500/5 blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40vw] h-[40vw] rounded-full bg-cyan-500/5 blur-[120px]" />
      </div>

      {/* Navigation Header */}
      <header className="sticky top-0 z-50 backdrop-blur-md bg-[#0B0F17]/80 border-b border-white/[0.06]">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Logo />
            <span className="hidden sm:inline-block w-px h-4 bg-white/10" />
            <div className="hidden sm:flex items-center gap-2 text-xs font-mono text-slate-400">
              <Link to="/repositories" className="hover:text-sky-300 transition-colors">
                repositories
              </Link>
              <span className="text-slate-600">/</span>
              <Link to={`/repositories/${owner}/${repo}`} className="hover:text-sky-300 transition-colors">
                {repo}
              </Link>
              <span className="text-slate-600">/</span>
              <span className="text-sky-400 font-bold">#{pullNumber}</span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={fetchPullRequest}
              disabled={loading}
              className="neu-button px-3.5 py-2 rounded-xl text-xs font-medium text-slate-300 hover:text-white flex items-center gap-1.5 transition-colors disabled:opacity-50"
              title="Refresh PR status"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-sky-400 ${loading ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">Refresh</span>
            </button>

            <Link
              to={`/repositories/${owner}/${repo}`}
              className="neu-button px-4 py-2 rounded-full text-xs font-medium text-slate-300 hover:text-white flex items-center gap-1.5 transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5 text-sky-400" />
              <span>Back to Pull Requests</span>
            </Link>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-6 py-10 sm:py-14 relative z-10">

        {/* State 1: Loading State */}
        {loading && (
          <div className="neu-panel rounded-2xl p-12 text-center border border-white/[0.07] my-12 shadow-[0_15px_40px_rgba(0,0,0,0.6)]">
            <div className="w-14 h-14 rounded-2xl neu-recessed flex items-center justify-center text-sky-400 mx-auto mb-5">
              <Loader2 className="w-7 h-7 animate-spin" />
            </div>
            <h3 className="text-lg font-bold text-white mb-2">
              Checking mergeability...
            </h3>
            <p className="text-xs sm:text-sm text-slate-400 max-w-sm mx-auto">
              Connecting to GitHub to inspect pull request #{pullNumber} and evaluate merge conflict status.
            </p>
          </div>
        )}

        {/* State 2: Error State */}
        {!loading && error && (
          <div className="neu-panel rounded-2xl p-10 text-center border border-rose-500/20 my-12 shadow-[0_15px_40px_rgba(0,0,0,0.6)]">
            <div className="w-14 h-14 rounded-2xl neu-recessed flex items-center justify-center text-rose-400 mx-auto mb-5 border border-rose-500/20">
              {errorStatus === 403 ? (
                <ShieldAlert className="w-7 h-7" />
              ) : (
                <AlertCircle className="w-7 h-7" />
              )}
            </div>
            <h3 className="text-lg font-bold text-white mb-2">
              {error}
            </h3>
            <p className="text-xs sm:text-sm text-slate-400 max-w-md mx-auto mb-6">
              {errorStatus === 404
                ? `Pull request #${pullNumber} does not exist in repository ${owner}/${repo}.`
                : errorStatus === 403
                ? `This repository is not permitted under the active GitHub App installation.`
                : errorStatus === 401
                ? `The secure session has expired. Please return to the connection page.`
                : `MergeMind was unable to retrieve mergeability details from GitHub.`}
            </p>
            <div className="flex items-center justify-center gap-4">
              <button
                onClick={fetchPullRequest}
                className="neu-button px-5 py-2.5 rounded-xl text-xs font-medium text-white hover:text-sky-300 transition-colors"
              >
                Try Again
              </button>
              <Link
                to={`/repositories/${owner}/${repo}`}
                className="neu-glow-btn px-5 py-2.5 rounded-xl text-xs font-semibold text-white"
              >
                Back to Repository
              </Link>
            </div>
          </div>
        )}

        {/* State 3: Success State (PR Details & Mergeability) */}
        {!loading && !error && pullRequest && (
          <div className="space-y-8">
            
            {/* PR Overview Card */}
            <div className="neu-panel rounded-2xl p-6 sm:p-8 border border-white/[0.07] shadow-[0_15px_40px_rgba(0,0,0,0.6)]">
              
              {/* Header Badges & Actions */}
              <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                <div className="flex items-center gap-2.5">
                  <span className="text-sm font-mono font-extrabold text-sky-400 px-2.5 py-1 rounded-lg neu-recessed border border-white/[0.04]">
                    #{pullRequest.number}
                  </span>

                  {pullRequest.draft ? (
                    <span className="text-xs font-mono px-2.5 py-1 rounded-lg bg-slate-800 text-slate-400 border border-slate-700">
                      Draft
                    </span>
                  ) : (
                    <span className="text-xs font-mono uppercase tracking-wider px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                      OPEN
                    </span>
                  )}
                </div>

                <a
                  href={pullRequest.html_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="neu-button px-3.5 py-1.5 rounded-xl text-xs font-medium text-slate-300 hover:text-white flex items-center gap-1.5 transition-colors group"
                >
                  <span>View on GitHub</span>
                  <ExternalLink className="w-3.5 h-3.5 text-sky-400 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
                </a>
              </div>

              {/* PR Title */}
              <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight leading-tight mb-4">
                {pullRequest.title}
              </h1>

              {/* Metadata Row: Author & Branches */}
              <div className="flex flex-wrap items-center gap-y-3 gap-x-6 text-xs text-slate-400 pt-2 pb-4">
                <div className="flex items-center gap-2">
                  <User className="w-3.5 h-3.5 text-slate-500" />
                  <span>Author:</span>
                  <span className="text-slate-200 font-mono font-medium">
                    {pullRequest.author || 'unknown'}
                  </span>
                </div>

                <div className="flex items-center gap-2 font-mono">
                  <GitBranch className="w-3.5 h-3.5 text-sky-400" />
                  <span className="px-2.5 py-1 rounded-md neu-recessed text-sky-300 font-semibold border border-white/[0.03]">
                    {pullRequest.head_branch}
                  </span>
                  <ArrowRight className="w-3 h-3 text-slate-500" />
                  <span className="px-2.5 py-1 rounded-md neu-recessed text-slate-300 border border-white/[0.03]">
                    {pullRequest.base_branch}
                  </span>
                </div>
              </div>

              {/* Divider */}
              <div className="h-px w-full bg-white/[0.05] my-2" />

              {/* Mergeability Section */}
              <div className="pt-4">
                
                {/* Case 1: Mergeable === true (Clean / No Conflicts) */}
                {pullRequest.mergeable === true && (
                  <div className="rounded-2xl p-6 neu-recessed border border-emerald-500/20 bg-emerald-950/10 relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-40 h-40 bg-emerald-500/5 rounded-full blur-2xl pointer-events-none" />
                    
                    <div className="flex items-start gap-4">
                      <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 flex-shrink-0">
                        <CheckCircle2 className="w-5 h-5" />
                      </div>
                      <div className="flex-1">
                        <div className="flex flex-wrap items-center justify-between gap-2 mb-1">
                          <h2 className="text-lg font-bold text-white flex items-center gap-2">
                            <span>No merge conflicts detected</span>
                          </h2>
                          {pullRequest.mergeable_state && (
                            <span className="text-[11px] font-mono px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                              state: {pullRequest.mergeable_state}
                            </span>
                          )}
                        </div>
                        <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
                          GitHub reports that this pull request can be cleanly and automatically merged into branch <code className="text-sky-300 font-mono px-1 py-0.5 rounded bg-slate-800/80">{pullRequest.base_branch}</code> without conflicts.
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Case 2: Mergeable === false (Conflict Detected) */}
                {pullRequest.mergeable === false && (
                  <div className="space-y-4">
                    {/* Conflict Notice Card */}
                    <div className="rounded-2xl p-6 sm:p-7 neu-recessed border border-amber-500/30 bg-amber-950/10 relative overflow-hidden">
                      <div className="absolute top-0 right-0 w-48 h-48 bg-amber-500/5 rounded-full blur-2xl pointer-events-none" />

                      <div className="flex items-start gap-4">
                        <div className="w-11 h-11 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 flex-shrink-0 mt-0.5">
                          <AlertTriangle className="w-6 h-6" />
                        </div>
                        <div className="flex-1">
                          <div className="flex flex-wrap items-center justify-between gap-2 mb-1.5">
                            <h2 className="text-lg sm:text-xl font-bold text-white flex items-center gap-2">
                              <span>Merge conflict detected</span>
                            </h2>
                            {pullRequest.mergeable_state && (
                              <span className="text-[11px] font-mono px-2 py-0.5 rounded-md bg-amber-500/10 text-amber-400 border border-amber-500/20">
                                state: {pullRequest.mergeable_state}
                              </span>
                            )}
                          </div>
                          <p className="text-xs sm:text-sm text-slate-300 leading-relaxed mb-6">
                            MergeMind can extract the conflicting files and inspect Base, Local, and Remote versions deterministically.
                          </p>

                          {/* Action Button for Conflict Analysis */}
                          <div className="flex flex-col sm:flex-row sm:items-center gap-4">
                            <button
                              type="button"
                              onClick={handleAnalyzeConflicts}
                              disabled={analyzing}
                              className="neu-glow-btn px-6 py-3 rounded-xl text-xs font-bold text-white flex items-center justify-center gap-2 shadow-[0_0_20px_rgba(56,189,248,0.25)] hover:shadow-[0_0_28px_rgba(56,189,248,0.4)] transition-all cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
                            >
                              {analyzing ? (
                                <>
                                  <Loader2 className="w-4 h-4 text-sky-300 animate-spin" />
                                  <span>Analyzing conflicts...</span>
                                </>
                              ) : (
                                <>
                                  <Sparkles className="w-4 h-4 text-sky-300" />
                                  <span>{conflictData ? 'Re-analyze Conflicts' : 'Analyze Conflicts →'}</span>
                                </>
                              )}
                            </button>
                            <span className="text-[11px] text-slate-400 italic">
                              Simulates Git 3-way merge in an isolated temporary sandbox
                            </span>
                          </div>

                          {/* Analysis Error State */}
                          {analysisError && (
                            <div className="mt-4 p-4 rounded-xl bg-rose-950/30 border border-rose-500/30 flex items-start gap-3">
                              <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
                              <div className="flex-1">
                                <p className="text-xs font-semibold text-rose-300 mb-1">
                                  Conflict extraction failed
                                </p>
                                <p className="text-xs text-rose-400/90 leading-relaxed">
                                  {analysisError}
                                </p>
                              </div>
                              <button
                                onClick={handleAnalyzeConflicts}
                                className="text-xs text-rose-300 hover:text-white underline"
                              >
                                Retry
                              </button>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Conflict Analysis Results Card */}
                    {conflictData && (
                      <div className="neu-panel rounded-2xl p-6 sm:p-7 border border-white/[0.08] shadow-[0_15px_40px_rgba(0,0,0,0.5)]">
                        <div className="flex flex-wrap items-center justify-between gap-3 mb-5 pb-4 border-b border-white/[0.06]">
                          <div className="flex items-center gap-3">
                            <h3 className="text-base sm:text-lg font-bold text-white">
                              Conflict Analysis
                            </h3>
                            <span className="text-xs font-mono px-2.5 py-1 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20 font-semibold flex items-center gap-1.5">
                              <AlertTriangle className="w-3.5 h-3.5" />
                              <span>
                                {conflictData.conflicts?.length || 0} conflicting {conflictData.conflicts?.length === 1 ? 'file' : 'files'}
                              </span>
                            </span>
                          </div>

                          {conflictData.changed_files && conflictData.changed_files.length > 0 && (
                            <span className="text-xs font-mono text-slate-400">
                              {conflictData.changed_files.length} total changed {conflictData.changed_files.length === 1 ? 'file' : 'files'} in PR
                            </span>
                          )}
                        </div>

                        {/* List of Conflicting Files */}
                        {conflictData.conflicts && conflictData.conflicts.length > 0 ? (
                          <div className="space-y-3 mb-6">
                            {conflictData.conflicts.map((c) => (
                              <div
                                key={c.path}
                                className="p-4 rounded-xl neu-recessed border border-white/[0.05] flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                              >
                                <div className="flex items-center gap-3 min-w-0">
                                  <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 flex-shrink-0">
                                    <FileCode className="w-4 h-4" />
                                  </div>
                                  <div className="truncate">
                                    <p className="font-mono text-sm font-semibold text-white truncate">
                                      {c.path}
                                    </p>
                                    <div className="flex items-center gap-2 text-[11px] text-slate-400 font-mono mt-0.5">
                                      {c.base_sha && <span>base: {c.base_sha.slice(0, 7)}</span>}
                                      {c.local_sha && <span>• local: {c.local_sha.slice(0, 7)}</span>}
                                      {c.remote_sha && <span>• remote: {c.remote_sha.slice(0, 7)}</span>}
                                    </div>
                                  </div>
                                </div>

                                <div className="flex items-center gap-2 flex-shrink-0">
                                  <span className="text-[11px] font-mono uppercase px-2.5 py-1 rounded-md bg-sky-500/10 text-sky-300 border border-sky-500/20">
                                    {c.language}
                                  </span>
                                  <span className="text-[11px] font-mono px-2.5 py-1 rounded-md bg-amber-500/10 text-amber-400 border border-amber-500/20">
                                    {c.conflict_type}
                                  </span>
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="p-4 rounded-xl neu-recessed border border-white/[0.04] text-center text-xs text-slate-400 mb-6">
                            No conflicting files detected in the simulation.
                          </div>
                        )}

                        {/* Success Footer */}
                        <div className="flex items-center justify-between pt-2">
                          <div className="flex items-center gap-2 text-xs font-medium text-emerald-400">
                            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                            <span>{conflictData.message || 'Conflict data extracted successfully.'}</span>
                          </div>

                          <button
                            onClick={handleAnalyzeConflicts}
                            disabled={analyzing}
                            className="neu-button px-3 py-1.5 rounded-lg text-xs font-medium text-slate-300 hover:text-white flex items-center gap-1.5 transition-colors disabled:opacity-50"
                          >
                            <RefreshCw className={`w-3.5 h-3.5 text-sky-400 ${analyzing ? 'animate-spin' : ''}`} />
                            <span>Refresh</span>
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Case 3: Mergeable === null (Calculating) */}
                {pullRequest.mergeable === null && (
                  <div className="rounded-2xl p-6 neu-recessed border border-sky-500/20 bg-sky-950/10 relative overflow-hidden">
                    <div className="flex items-start gap-4">
                      <div className="w-10 h-10 rounded-xl bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-sky-400 flex-shrink-0">
                        <RefreshCw className="w-5 h-5 animate-spin" />
                      </div>
                      <div className="flex-1">
                        <div className="flex flex-wrap items-center justify-between gap-2 mb-1">
                          <h2 className="text-lg font-bold text-white flex items-center gap-2">
                            <span>Checking mergeability...</span>
                          </h2>
                          <span className="text-[11px] font-mono px-2 py-0.5 rounded-md bg-sky-500/10 text-sky-400 border border-sky-500/20">
                            state: {pullRequest.mergeable_state || 'unknown'}
                          </span>
                        </div>
                        <p className="text-xs sm:text-sm text-slate-300 leading-relaxed mb-4">
                          GitHub is currently calculating the mergeability status for this pull request in the background. Please wait a moment and refresh.
                        </p>
                        <button
                          onClick={fetchPullRequest}
                          className="neu-button px-4 py-2 rounded-xl text-xs font-medium text-sky-300 hover:text-white flex items-center gap-1.5 transition-colors"
                        >
                          <RefreshCw className="w-3.5 h-3.5 text-sky-400" />
                          <span>Re-check Mergeability</span>
                        </button>
                      </div>
                    </div>
                  </div>
                )}

              </div>

              {/* Bottom GitHub Link */}
              <div className="mt-8 pt-4 border-t border-white/[0.04] flex items-center justify-between">
                <span className="text-xs font-mono text-slate-500">
                  {owner}/{repo} • PR #{pullRequest.number}
                </span>
                <a
                  href={pullRequest.html_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs font-mono text-sky-400 hover:text-sky-300 flex items-center gap-1.5 transition-colors"
                >
                  <span>View Pull Request on GitHub</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>

            </div>

          </div>
        )}

      </main>
    </div>
  );
}
