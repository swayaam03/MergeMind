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
  FolderTree,
  BookOpen,
  Cpu,
  FileText,
  ChevronDown,
  ChevronUp,
  Layers,
  Boxes,
  Copy,
  Check,
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

  // Repository Context state
  const [repositoryContext, setRepositoryContext] = useState(null);
  const [loadingContext, setLoadingContext] = useState(false);
  const [contextError, setContextError] = useState(null);
  const [contextOpen, setContextOpen] = useState(true);
  const [readmeOpen, setReadmeOpen] = useState(false);
  const [treeOpen, setTreeOpen] = useState(false);
  const [filePreviewsOpen, setFilePreviewsOpen] = useState({});
  const [docPreviewsOpen, setDocPreviewsOpen] = useState({});

  // LLM Merge Proposal state (Phase 4 Task 2)
  const [generatingProposal, setGeneratingProposal] = useState(false);
  const [proposalData, setProposalData] = useState(null);
  const [proposalError, setProposalError] = useState(null);
  const [copiedCode, setCopiedCode] = useState(false);

  const toggleDocPreview = (path) => {
    setDocPreviewsOpen((prev) => ({
      ...prev,
      [path]: !prev[path],
    }));
  };

  const toggleFilePreview = (path) => {
    setFilePreviewsOpen((prev) => ({
      ...prev,
      [path]: !prev[path],
    }));
  };

  const fetchRepositoryContext = async (conflictingFiles = []) => {
    setLoadingContext(true);
    setContextError(null);

    try {
      const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';
      let apiUrl = `${backendUrl}/api/github/repositories/${owner}/${repo}/pulls/${pullNumber}/context`;
      if (conflictingFiles && conflictingFiles.length > 0) {
        const query = conflictingFiles
          .map((f) => `conflicting_files=${encodeURIComponent(f)}`)
          .join('&');
        apiUrl += `?${query}`;
      }

      const response = await fetch(apiUrl, {
        method: 'GET',
        headers: {
          Accept: 'application/json',
        },
        credentials: 'include',
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Unable to retrieve repository context.');
      }

      setRepositoryContext(data);
    } catch (err) {
      console.error('Error fetching repository context:', err);
      setContextError(err.message || 'Failed to extract repository context.');
    } finally {
      setLoadingContext(false);
    }
  };

  const fetchPullRequest = async () => {
    setLoading(true);
    setError(null);
    setErrorStatus(null);
    setConflictData(null);
    setAnalysisError(null);
    setRepositoryContext(null);
    setContextError(null);

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
      // Automatically trigger repository context extraction with discovered conflicting files
      fetchRepositoryContext(data.conflicting_files || []);
    } catch (err) {
      console.error('Error analyzing conflicts:', err);
      setAnalysisError(err.message || 'Failed to analyze conflicts.');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleGenerateProposal = async (targetFilePath = null) => {
    setGeneratingProposal(true);
    setProposalError(null);

    try {
      const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';
      let apiUrl = `${backendUrl}/api/github/repositories/${owner}/${repo}/pulls/${pullNumber}/merge-proposal`;
      if (targetFilePath) {
        apiUrl += `?file_path=${encodeURIComponent(targetFilePath)}`;
      }

      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(targetFilePath ? { file_path: targetFilePath } : {}),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Unable to generate merge proposal.');
      }

      setProposalData(data);
    } catch (err) {
      console.error('Error generating merge proposal:', err);
      setProposalError(err.message || 'Failed to generate merge proposal.');
    } finally {
      setGeneratingProposal(false);
    }
  };

  const handleCopyCode = (code) => {
    if (!code) return;
    navigator.clipboard.writeText(code);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
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
            <div className="flex flex-wrap items-center justify-center gap-3">
              <button
                onClick={fetchPullRequest}
                className="neu-button px-5 py-2.5 rounded-xl text-xs font-medium text-white hover:text-sky-300 transition-colors"
              >
                Try Again
              </button>
              {errorStatus === 401 ? (
                <Link
                  to="/connect"
                  className="neu-glow-btn px-5 py-2.5 rounded-xl text-xs font-semibold text-white"
                >
                  Connect GitHub
                </Link>
              ) : (
                <Link
                  to={`/repositories/${owner}/${repo}`}
                  className="neu-glow-btn px-5 py-2.5 rounded-xl text-xs font-semibold text-white"
                >
                  Back to Pull Requests
                </Link>
              )}
              <Link
                to="/repositories"
                className="neu-button px-5 py-2.5 rounded-xl text-xs font-medium text-slate-300 hover:text-white"
              >
                All Repositories
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
                                className="p-4 rounded-xl neu-recessed border border-white/[0.05] space-y-3"
                              >
                                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
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
                                    <button
                                      type="button"
                                      onClick={() => handleGenerateProposal(c.path)}
                                      disabled={generatingProposal}
                                      className="neu-button px-2.5 py-1 rounded-md text-[11px] font-mono text-violet-300 hover:text-white bg-violet-500/10 hover:bg-violet-500/20 border border-violet-500/30 flex items-center gap-1 transition-colors disabled:opacity-50"
                                      title={`Generate LLM proposal for ${c.path}`}
                                    >
                                      <Sparkles className="w-3 h-3 text-violet-400" />
                                      <span>Propose Fix</span>
                                    </button>
                                  </div>
                                </div>

                                {/* Semantic Structure AST Analysis Card */}
                                {c.ast_analysis && (
                                  <div className="pt-3 border-t border-white/[0.06] space-y-2.5">
                                    <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                                      <div className="flex items-center gap-2">
                                        <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold">
                                          Semantic Structure
                                        </span>
                                        <span className="text-[11px] font-mono font-bold px-2 py-0.5 rounded bg-indigo-500/15 text-indigo-300 border border-indigo-500/30">
                                          {c.ast_analysis.classification?.category || 'UNKNOWN'}
                                        </span>
                                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/[0.04] text-slate-400">
                                          deterministic
                                        </span>
                                      </div>
                                      <span className="text-[10px] text-slate-500 font-mono">
                                        Tree-sitter AST
                                      </span>
                                    </div>

                                    {/* Local vs Remote structural changes summary */}
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs font-mono">
                                      <div className="p-2.5 rounded-lg bg-slate-950/60 border border-white/[0.04]">
                                        <span className="text-[10px] uppercase text-sky-400 font-bold block mb-1">
                                          Local changes (target):
                                        </span>
                                        {c.ast_analysis.changes?.local && c.ast_analysis.changes.local.length > 0 ? (
                                          <ul className="space-y-1 text-slate-300">
                                            {c.ast_analysis.changes.local.map((ch, idx) => (
                                              <li key={idx} className="truncate">
                                                • {ch.node_name ? `${ch.node_name}()` : ch.details}
                                              </li>
                                            ))}
                                          </ul>
                                        ) : (
                                          <span className="text-slate-500 italic">No structural delta</span>
                                        )}
                                      </div>

                                      <div className="p-2.5 rounded-lg bg-slate-950/60 border border-white/[0.04]">
                                        <span className="text-[10px] uppercase text-amber-400 font-bold block mb-1">
                                          Remote changes (source):
                                        </span>
                                        {c.ast_analysis.changes?.remote && c.ast_analysis.changes.remote.length > 0 ? (
                                          <ul className="space-y-1 text-slate-300">
                                            {c.ast_analysis.changes.remote.map((ch, idx) => (
                                              <li key={idx} className="truncate">
                                                • {ch.node_name ? `${ch.node_name}()` : ch.details}
                                              </li>
                                            ))}
                                          </ul>
                                        ) : (
                                          <span className="text-slate-500 italic">No structural delta</span>
                                        )}
                                      </div>
                                    </div>

                                    {/* Deterministic Explanation Reason */}
                                    {c.ast_analysis.classification?.reason && (
                                      <p className="text-xs text-slate-300 bg-white/[0.02] p-2.5 rounded-lg border border-white/[0.03]">
                                        <span className="font-semibold text-sky-300">Reason: </span>
                                        {c.ast_analysis.classification.reason}
                                      </p>
                                    )}
                                  </div>
                                )}
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

                    {/* Repository Context Card (Phase 4 Task 1) */}
                    {(conflictData || repositoryContext || loadingContext) && (
                      <div className="neu-panel rounded-2xl p-6 sm:p-7 border border-white/[0.08] shadow-[0_15px_40px_rgba(0,0,0,0.5)] space-y-6">
                        {/* Header with expand toggle */}
                        <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-white/[0.06]">
                          <div className="flex items-center gap-3">
                            <div className="w-9 h-9 rounded-xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
                              <FolderTree className="w-5 h-5" />
                            </div>
                            <div>
                              <div className="flex items-center gap-2">
                                <h3 className="text-base sm:text-lg font-bold text-white">
                                  Repository Context
                                </h3>
                                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-sky-500/10 text-sky-300 border border-sky-500/20">
                                  deterministic
                                </span>
                              </div>
                              <p className="text-xs text-slate-400 mt-0.5">
                                Project-level metadata, dependencies, tree structure & neighbor files for LLM Merge Agent
                              </p>
                            </div>
                          </div>

                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => fetchRepositoryContext(conflictData?.conflicting_files || [])}
                              disabled={loadingContext}
                              className="neu-button px-3 py-1.5 rounded-lg text-xs font-medium text-slate-300 hover:text-white flex items-center gap-1.5 transition-colors disabled:opacity-50"
                              title="Re-extract repository context"
                            >
                              <RefreshCw className={`w-3.5 h-3.5 text-sky-400 ${loadingContext ? 'animate-spin' : ''}`} />
                              <span className="hidden sm:inline">Refresh Context</span>
                            </button>

                            <button
                              onClick={() => setContextOpen(!contextOpen)}
                              className="neu-button px-2.5 py-1.5 rounded-lg text-xs text-slate-400 hover:text-white transition-colors"
                              title={contextOpen ? 'Collapse context' : 'Expand context'}
                            >
                              {contextOpen ? (
                                <ChevronUp className="w-4 h-4" />
                              ) : (
                                <ChevronDown className="w-4 h-4" />
                              )}
                            </button>
                          </div>
                        </div>

                        {/* Loading State */}
                        {loadingContext && (
                          <div className="p-8 rounded-xl neu-recessed border border-white/[0.04] text-center space-y-3">
                            <Loader2 className="w-6 h-6 text-sky-400 animate-spin mx-auto" />
                            <p className="text-xs text-slate-300 font-medium">
                              Extracting repository structure, README, technologies, and neighbor files...
                            </p>
                          </div>
                        )}

                        {/* Error State */}
                        {!loadingContext && contextError && (
                          <div className="p-4 rounded-xl bg-rose-950/30 border border-rose-500/30 flex items-start gap-3">
                            <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
                            <div className="flex-1">
                              <p className="text-xs font-semibold text-rose-300">
                                Repository context extraction failed
                              </p>
                              <p className="text-xs text-rose-400/90 leading-relaxed mt-0.5">
                                {contextError}
                              </p>
                            </div>
                            <button
                              onClick={() => fetchRepositoryContext(conflictData?.conflicting_files || [])}
                              className="text-xs text-rose-300 hover:text-white underline"
                            >
                              Retry
                            </button>
                          </div>
                        )}

                        {/* Context Content (Expanded) */}
                        {!loadingContext && !contextError && repositoryContext && contextOpen && (
                          <div className="space-y-6">

                            {/* Section 0: Project Description (Deterministic) */}
                            {repositoryContext.project?.description && (
                              <div className="p-3.5 rounded-xl neu-recessed border border-sky-500/20 bg-sky-950/20 flex items-start gap-2.5">
                                <Info className="w-4 h-4 text-sky-400 flex-shrink-0 mt-0.5" />
                                <div className="min-w-0">
                                  <h4 className="text-[11px] font-bold uppercase tracking-wider text-sky-300 font-mono">
                                    Project Description
                                  </h4>
                                  <p className="text-xs text-slate-300 mt-1 leading-relaxed">
                                    {repositoryContext.project.description}
                                  </p>
                                </div>
                              </div>
                            )}

                            {/* Section 1: Detected Technologies & Frameworks */}
                            <div>
                              <div className="flex items-center gap-2 mb-3">
                                <Cpu className="w-4 h-4 text-indigo-400" />
                                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono">
                                  Detected Technologies & Frameworks
                                </h4>
                                <span className="text-[11px] font-mono text-slate-500">
                                  ({(repositoryContext.detected_technologies?.length || 0) + (repositoryContext.project?.frameworks?.length || 0)})
                                </span>
                              </div>

                              <div className="flex flex-wrap gap-2">
                                {repositoryContext.project?.languages?.map((lang, idx) => (
                                  <div
                                    key={`lang-${idx}`}
                                    className="p-2 rounded-xl neu-recessed border border-sky-500/20 flex items-center gap-2 text-xs"
                                  >
                                    <span className="w-2 h-2 rounded-full bg-sky-400" />
                                    <span className="font-bold text-white font-mono capitalize">{lang}</span>
                                    <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-sky-500/10 text-sky-300 border border-sky-500/20">
                                      language
                                    </span>
                                  </div>
                                ))}

                                {repositoryContext.project?.package_managers?.map((pm, idx) => (
                                  <div
                                    key={`pm-${idx}`}
                                    className="p-2 rounded-xl neu-recessed border border-white/[0.04] flex items-center gap-2 text-xs"
                                  >
                                    <span className="font-bold text-white font-mono">{pm}</span>
                                    <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-slate-500/10 text-slate-300 border border-slate-500/20">
                                      pkg manager
                                    </span>
                                  </div>
                                ))}

                                {repositoryContext.detected_technologies && repositoryContext.detected_technologies.map((tech, idx) => {
                                  const catColors = {
                                    framework: 'bg-indigo-500/10 text-indigo-300 border-indigo-500/25',
                                    language: 'bg-sky-500/10 text-sky-300 border-sky-500/25',
                                    testing: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/25',
                                    runtime: 'bg-purple-500/10 text-purple-300 border-purple-500/25',
                                    package_manager: 'bg-slate-500/10 text-slate-300 border-slate-500/25',
                                    build: 'bg-amber-500/10 text-amber-300 border-amber-500/25',
                                  };
                                  const badgeClass = catColors[tech.category] || 'bg-sky-500/10 text-sky-300 border-sky-500/25';

                                  return (
                                    <div
                                      key={`tech-${idx}`}
                                      className="p-2 rounded-xl neu-recessed border border-white/[0.04] flex items-center gap-2 text-xs"
                                    >
                                      <span className="font-bold text-white font-mono">{tech.name}</span>
                                      {tech.version && (
                                        <span className="font-mono text-[10px] text-slate-400 px-1.5 py-0.5 rounded bg-black/40">
                                          {tech.version}
                                        </span>
                                      )}
                                      <span className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded border ${badgeClass}`}>
                                        {tech.category}
                                      </span>
                                      <span className="text-[10px] text-slate-500 font-mono hidden sm:inline">
                                        via {tech.detected_from}
                                      </span>
                                    </div>
                                  );
                                })}

                                {(!repositoryContext.detected_technologies?.length && !repositoryContext.project?.languages?.length) && (
                                  <p className="text-xs text-slate-500 italic">No standard frameworks or manifests identified.</p>
                                )}
                              </div>
                            </div>

                            {/* Section 2: GitHub Languages breakdown */}
                            {repositoryContext.languages && Object.keys(repositoryContext.languages).length > 0 && (
                              <div>
                                <div className="flex items-center gap-2 mb-2">
                                  <Layers className="w-4 h-4 text-sky-400" />
                                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono">
                                    Repository Languages
                                  </h4>
                                </div>
                                <div className="flex flex-wrap gap-2">
                                  {Object.entries(repositoryContext.languages).map(([lang, bytes]) => (
                                    <div
                                      key={lang}
                                      className="px-2.5 py-1 rounded-lg bg-white/[0.03] border border-white/[0.04] text-xs font-mono flex items-center gap-2 text-slate-300"
                                    >
                                      <span className="w-2 h-2 rounded-full bg-sky-400" />
                                      <span className="font-medium text-white">{lang}</span>
                                      <span className="text-[11px] text-slate-500">
                                        {(bytes / 1024).toFixed(1)} KB
                                      </span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Section 3: Documentation Sources */}
                            {((repositoryContext.documentation?.files && repositoryContext.documentation.files.length > 0) || repositoryContext.readme_preview) && (
                              <div className="space-y-2">
                                <div className="flex items-center gap-2">
                                  <BookOpen className="w-4 h-4 text-sky-400" />
                                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono">
                                    Documentation Sources
                                  </h4>
                                  <span className="text-[11px] font-mono text-slate-500">
                                    ({repositoryContext.documentation?.files?.length || 1} files
                                    {repositoryContext.documentation?.truncated ? ' • truncated' : ''})
                                  </span>
                                </div>

                                {repositoryContext.documentation?.files?.length > 0 ? (
                                  repositoryContext.documentation.files.map((docFile) => {
                                    const isDocOpen = Boolean(docPreviewsOpen[docFile.path]);
                                    return (
                                      <div
                                        key={docFile.path}
                                        className="rounded-xl neu-recessed border border-white/[0.04] overflow-hidden"
                                      >
                                        <button
                                          type="button"
                                          onClick={() => toggleDocPreview(docFile.path)}
                                          className="w-full p-3 flex items-center justify-between text-left hover:bg-white/[0.02] transition-colors"
                                        >
                                          <div className="flex items-center gap-2.5 text-xs font-mono">
                                            <FileText className="w-3.5 h-3.5 text-sky-400" />
                                            <span className="font-semibold text-white">{docFile.path}</span>
                                            <span className="text-[10px] text-slate-500">
                                              ({docFile.content?.length || 0} chars{docFile.truncated ? ', capped' : ''})
                                            </span>
                                          </div>
                                          <span className="text-xs text-slate-400 flex items-center gap-1 font-mono">
                                            {isDocOpen ? 'Hide' : 'View'}
                                            {isDocOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                                          </span>
                                        </button>

                                        {isDocOpen && (
                                          <div className="p-4 border-t border-white/[0.04] bg-slate-950/70 max-h-64 overflow-y-auto font-mono text-xs text-slate-300 whitespace-pre-wrap leading-relaxed">
                                            {docFile.content}
                                          </div>
                                        )}
                                      </div>
                                    );
                                  })
                                ) : (
                                  repositoryContext.readme_preview && (
                                    <div className="rounded-xl neu-recessed border border-white/[0.04] overflow-hidden">
                                      <button
                                        type="button"
                                        onClick={() => setReadmeOpen(!readmeOpen)}
                                        className="w-full p-3 flex items-center justify-between text-left hover:bg-white/[0.02] transition-colors"
                                      >
                                        <div className="flex items-center gap-2.5 text-xs font-mono">
                                          <FileText className="w-3.5 h-3.5 text-sky-400" />
                                          <span className="font-semibold text-white">README.md</span>
                                          <span className="text-[10px] text-slate-500">
                                            ({repositoryContext.readme_preview.length} chars)
                                          </span>
                                        </div>
                                        <span className="text-xs text-slate-400 flex items-center gap-1 font-mono">
                                          {readmeOpen ? 'Hide' : 'View'}
                                          {readmeOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                                        </span>
                                      </button>

                                      {readmeOpen && (
                                        <div className="p-4 border-t border-white/[0.04] bg-slate-950/70 max-h-64 overflow-y-auto font-mono text-xs text-slate-300 whitespace-pre-wrap leading-relaxed">
                                          {repositoryContext.readme_preview}
                                        </div>
                                      )}
                                    </div>
                                  )
                                )}
                              </div>
                            )}

                            {/* Section 4: Repository Structure (Collapsible) */}
                            {(repositoryContext.structure?.tree || repositoryContext.directory_structure) && (
                              <div className="rounded-xl neu-recessed border border-white/[0.04] overflow-hidden">
                                <button
                                  type="button"
                                  onClick={() => setTreeOpen(!treeOpen)}
                                  className="w-full p-3.5 flex items-center justify-between text-left hover:bg-white/[0.02] transition-colors"
                                >
                                  <div className="flex items-center gap-2.5 text-xs font-mono">
                                    <FolderTree className="w-4 h-4 text-sky-400" />
                                    <span className="font-semibold text-white">Repository Structure</span>
                                    <span className="text-[10px] text-slate-500">
                                      ({(repositoryContext.directory_structure?.length || 0)} indexed entries
                                      {(repositoryContext.structure?.truncated || repositoryContext.tree_truncated) ? ' • truncated' : ''})
                                    </span>
                                  </div>
                                  <span className="text-xs text-slate-400 flex items-center gap-1 font-mono">
                                    {treeOpen ? 'Hide' : 'View'}
                                    {treeOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                                  </span>
                                </button>

                                {treeOpen && (
                                  <div className="p-4 border-t border-white/[0.04] bg-slate-950/70 max-h-64 overflow-y-auto font-mono text-xs text-slate-300">
                                    {repositoryContext.structure?.tree ? (
                                      <pre className="whitespace-pre font-mono text-[11px] leading-relaxed text-slate-300">
                                        {repositoryContext.structure.tree}
                                      </pre>
                                    ) : (
                                      <div className="space-y-1">
                                        {repositoryContext.directory_structure.map((fpath, idx) => (
                                          <div key={idx} className="flex items-center gap-2 py-0.5 hover:text-sky-300 transition-colors">
                                            <span className="text-slate-600 select-none">#</span>
                                            <span>{fpath}</span>
                                          </div>
                                        ))}
                                      </div>
                                    )}
                                  </div>
                                )}
                              </div>
                            )}

                            {/* Section 5: Relevant Neighbor Files */}
                            <div>
                              <div className="flex items-center gap-2 mb-3">
                                <FileCode className="w-4 h-4 text-emerald-400" />
                                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono">
                                  Relevant Neighbor & Test Files
                                </h4>
                                <span className="text-[11px] font-mono text-slate-500">
                                  ({repositoryContext.relevant_files?.length || 0})
                                </span>
                              </div>

                              {repositoryContext.relevant_files && repositoryContext.relevant_files.length > 0 ? (
                                <div className="space-y-3">
                                  {repositoryContext.relevant_files.map((file) => {
                                    const isPreviewOpen = Boolean(filePreviewsOpen[file.path]);
                                    return (
                                      <div
                                        key={file.path}
                                        className="rounded-xl neu-recessed border border-white/[0.04] overflow-hidden"
                                      >
                                        <div className="p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                                          <div className="flex items-center gap-2.5 min-w-0">
                                            <FileText className="w-4 h-4 text-sky-400 flex-shrink-0" />
                                            <span className="font-mono text-xs font-semibold text-white truncate">
                                              {file.path}
                                            </span>
                                            {file.reason && (
                                              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 flex-shrink-0">
                                                {file.reason}
                                              </span>
                                            )}
                                          </div>

                                          <div className="flex items-center gap-3 self-end sm:self-center">
                                            <span className="text-[10px] font-mono text-slate-500">
                                              {file.size} bytes {file.truncated ? '(capped)' : ''}
                                            </span>
                                            <button
                                              type="button"
                                              onClick={() => toggleFilePreview(file.path)}
                                              className="text-xs font-mono text-sky-400 hover:text-sky-300 flex items-center gap-1 cursor-pointer"
                                            >
                                              {isPreviewOpen ? 'Hide code' : 'Preview code'}
                                              {isPreviewOpen ? (
                                                <ChevronUp className="w-3.5 h-3.5" />
                                              ) : (
                                                <ChevronDown className="w-3.5 h-3.5" />
                                              )}
                                            </button>
                                          </div>
                                        </div>

                                        {isPreviewOpen && (
                                          <div className="border-t border-white/[0.04] bg-slate-950/70 p-4 max-h-60 overflow-y-auto">
                                            <pre className="font-mono text-xs text-slate-300 whitespace-pre-wrap leading-relaxed">
                                              {file.content}
                                            </pre>
                                          </div>
                                        )}
                                      </div>
                                    );
                                  })}
                                </div>
                              ) : (
                                <p className="text-xs text-slate-500 italic">
                                  No additional neighbor or unit test files required.
                                </p>
                              )}
                            </div>

                          </div>
                        )}
                      </div>
                    )}

                    {/* MergeMind AI Merge Proposal Card (Phase 4 Task 2) */}
                    {(conflictData || proposalData || generatingProposal) && (
                      <div className="neu-panel rounded-2xl p-6 sm:p-7 border border-violet-500/20 bg-gradient-to-b from-violet-950/10 to-transparent shadow-[0_15px_40px_rgba(0,0,0,0.5)] space-y-6">
                        {/* Header */}
                        <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-white/[0.06]">
                          <div className="flex items-center gap-3">
                            <div className="w-9 h-9 rounded-xl bg-violet-500/15 border border-violet-500/30 flex items-center justify-center text-violet-300">
                              <Sparkles className="w-5 h-5" />
                            </div>
                            <div>
                              <div className="flex items-center gap-2">
                                <h3 className="text-base sm:text-lg font-bold text-white">
                                  MergeMind Proposal
                                </h3>
                                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-violet-500/20 text-violet-300 border border-violet-500/30 font-semibold">
                                  LLM Agent
                                </span>
                              </div>
                              <p className="text-xs text-slate-400 mt-0.5">
                                Semantic conflict resolution synthesized from AST analysis and repository context
                              </p>
                            </div>
                          </div>

                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => handleGenerateProposal()}
                              disabled={generatingProposal}
                              className="neu-button px-4 py-2 rounded-xl text-xs font-semibold text-white bg-violet-600/30 hover:bg-violet-600/50 border border-violet-500/40 flex items-center gap-2 transition-all disabled:opacity-50 shadow-lg shadow-violet-950/40"
                              title="Generate semantic merge proposal"
                            >
                              {generatingProposal ? (
                                <>
                                  <Loader2 className="w-4 h-4 text-violet-300 animate-spin" />
                                  <span>Reasoning...</span>
                                </>
                              ) : (
                                <>
                                  <Sparkles className="w-4 h-4 text-violet-300" />
                                  <span>{proposalData ? 'Regenerate Proposal' : 'Generate Merge Proposal'}</span>
                                </>
                              )}
                            </button>
                          </div>
                        </div>

                        {/* Prominent Verification Notice */}
                        <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-start gap-2.5">
                          <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                          <div>
                            <p className="text-xs font-bold text-amber-300">
                              AI-generated proposal — not yet verified
                            </p>
                            <p className="text-[11px] text-amber-400/80 mt-0.5 leading-relaxed">
                              This resolution was generated by the LLM merge agent. Verification inside a Docker sandbox and Semgrep security scanning are executed in subsequent pipeline stages before any merge decision.
                            </p>
                          </div>
                        </div>

                        {/* Loading State */}
                        {generatingProposal && (
                          <div className="p-8 rounded-xl neu-recessed border border-white/[0.04] text-center space-y-3">
                            <Loader2 className="w-6 h-6 text-violet-400 animate-spin mx-auto" />
                            <p className="text-xs text-slate-300 font-medium">
                              Analyzing Base, Local, and Remote changes with LLM Merge Agent...
                            </p>
                            <p className="text-[11px] text-slate-500 font-mono">
                              Using LiteLLM to synthesize intent and preserve changes
                            </p>
                          </div>
                        )}

                        {/* Error State */}
                        {!generatingProposal && proposalError && (
                          <div className="p-4 rounded-xl bg-rose-950/30 border border-rose-500/30 flex items-start gap-3">
                            <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
                            <div className="flex-1">
                              <p className="text-xs font-semibold text-rose-300">
                                Merge proposal generation failed
                              </p>
                              <p className="text-xs text-rose-400/90 leading-relaxed mt-0.5">
                                {proposalError}
                              </p>
                            </div>
                            <button
                              onClick={() => handleGenerateProposal()}
                              className="text-xs text-rose-300 hover:text-white underline font-medium"
                            >
                              Retry
                            </button>
                          </div>
                        )}

                        {/* Proposal Results */}
                        {!generatingProposal && proposalData && (
                          <div className="space-y-5">
                            {/* Status & Metadata Header */}
                            <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 rounded-xl neu-recessed border border-white/[0.05]">
                              <div className="flex items-center gap-2.5">
                                <span className="text-xs text-slate-400 font-mono">Status:</span>
                                <span
                                  className={`text-xs font-mono font-bold px-2.5 py-1 rounded-md border ${
                                    proposalData.status === 'resolved'
                                      ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                                      : 'bg-rose-500/15 text-rose-300 border-rose-500/30'
                                  }`}
                                >
                                  {proposalData.status.toUpperCase()}
                                </span>
                                {proposalData.file_path && (
                                  <span className="text-xs font-mono text-white font-semibold">
                                    {proposalData.file_path}
                                  </span>
                                )}
                              </div>

                              {proposalData.model && (
                                <div className="flex items-center gap-1.5 text-[11px] font-mono text-slate-400">
                                  <span>Model:</span>
                                  <span className="text-sky-300 bg-white/[0.04] px-2 py-0.5 rounded border border-white/[0.06]">
                                    {proposalData.model}
                                  </span>
                                </div>
                              )}
                            </div>

                            {/* Explanation Section */}
                            {proposalData.explanation && (
                              <div className="p-4 rounded-xl neu-recessed border border-white/[0.04] space-y-1.5">
                                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono">
                                  Agent Explanation
                                </h4>
                                <p className="text-xs text-slate-300 leading-relaxed">
                                  {proposalData.explanation}
                                </p>
                              </div>
                            )}

                            {/* Preserved Changes */}
                            {proposalData.preserved_changes && proposalData.preserved_changes.length > 0 && (
                              <div className="p-4 rounded-xl neu-recessed border border-emerald-500/10 bg-emerald-950/10 space-y-2">
                                <div className="flex items-center gap-2">
                                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                                  <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-300 font-mono">
                                    Preserved Intent & Changes
                                  </h4>
                                </div>
                                <ul className="space-y-1 text-xs text-slate-300">
                                  {proposalData.preserved_changes.map((item, idx) => (
                                    <li key={idx} className="flex items-start gap-2">
                                      <span className="text-emerald-400 select-none">•</span>
                                      <span>{item}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}

                            {/* Risks & Edge Cases */}
                            {proposalData.risks && proposalData.risks.length > 0 && (
                              <div className="p-4 rounded-xl neu-recessed border border-amber-500/10 bg-amber-950/10 space-y-2">
                                <div className="flex items-center gap-2">
                                  <AlertTriangle className="w-4 h-4 text-amber-400" />
                                  <h4 className="text-xs font-bold uppercase tracking-wider text-amber-300 font-mono">
                                    Identified Risks & Caveats
                                  </h4>
                                </div>
                                <ul className="space-y-1 text-xs text-slate-300">
                                  {proposalData.risks.map((risk, idx) => (
                                    <li key={idx} className="flex items-start gap-2">
                                      <span className="text-amber-400 select-none">•</span>
                                      <span>{risk}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}

                            {/* Proposed Merged Code View */}
                            {proposalData.merged_code ? (
                              <div className="rounded-xl neu-recessed border border-white/[0.06] overflow-hidden">
                                <div className="p-3.5 flex items-center justify-between border-b border-white/[0.04] bg-white/[0.02]">
                                  <div className="flex items-center gap-2">
                                    <FileCode className="w-4 h-4 text-violet-400" />
                                    <span className="text-xs font-mono font-semibold text-white">
                                      Proposed Merged Code
                                    </span>
                                  </div>

                                  <button
                                    type="button"
                                    onClick={() => handleCopyCode(proposalData.merged_code)}
                                    className="neu-button px-2.5 py-1 rounded-lg text-xs font-mono text-slate-300 hover:text-white flex items-center gap-1.5 transition-colors"
                                  >
                                    {copiedCode ? (
                                      <>
                                        <Check className="w-3.5 h-3.5 text-emerald-400" />
                                        <span className="text-emerald-400">Copied</span>
                                      </>
                                    ) : (
                                      <>
                                        <Copy className="w-3.5 h-3.5 text-slate-400" />
                                        <span>Copy code</span>
                                      </>
                                    )}
                                  </button>
                                </div>

                                <div className="p-4 bg-slate-950/80 max-h-96 overflow-y-auto overflow-x-auto">
                                  <pre className="font-mono text-xs text-slate-200 whitespace-pre leading-relaxed">
                                    {proposalData.merged_code}
                                  </pre>
                                </div>
                              </div>
                            ) : (
                              <div className="p-4 rounded-xl neu-recessed border border-white/[0.04] text-xs text-slate-400 text-center italic">
                                No resolved code produced. Status is unresolved.
                              </div>
                            )}

                          </div>
                        )}
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
