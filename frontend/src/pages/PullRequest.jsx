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
  Split,
  Eye,
  FileSearch,
} from 'lucide-react';
import VerificationCard from '../components/verification/VerificationCard';
import WorkflowPanel from '../components/workflow/WorkflowPanel';
import ConflictReviewPanel from '../components/review/ConflictReviewPanel';
import { subscribeToPipelineProgress } from '../services/websocket';

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
  const [activeContextTab, setActiveContextTab] = useState('tech'); // 'tech' | 'tree' | 'neighbors' | 'readme'
  const [filePreviewsOpen, setFilePreviewsOpen] = useState({});
  const [docPreviewsOpen, setDocPreviewsOpen] = useState({});

  // View state for conflict hunks
  const [showHunks, setShowHunks] = useState({});

  // LLM Merge Proposal state (Phase 4 Task 2)
  const [generatingProposal, setGeneratingProposal] = useState(false);
  const [proposalData, setProposalData] = useState(null);
  const [proposalError, setProposalError] = useState(null);
  const [copiedCode, setCopiedCode] = useState(false);

  // Phase 5: Deterministic Docker Verification Pipeline state
  const [verifyingProposal, setVerifyingProposal] = useState(false);
  const [verificationReport, setVerificationReport] = useState(null);
  const [verificationError, setVerificationError] = useState(null);

  // Phase 6: Autonomous LangGraph Workflow state
  const [runningWorkflow, setRunningWorkflow] = useState(false);
  const [workflowData, setWorkflowData] = useState(null);
  const [workflowError, setWorkflowError] = useState(null);
  const [maxRetries, setMaxRetries] = useState(2);

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

  const toggleHunks = (path) => {
    setShowHunks((prev) => ({
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
      setContextError(null);
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

      // If PR has conflicts already known, automatically kick off conflict analysis
      if (data.pull_request?.mergeable === false) {
        handleAnalyzeConflicts();
      }
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

  const handleVerifyProposal = async () => {
    if (!proposalData || !proposalData.merged_code) return;
    setVerifyingProposal(true);
    setVerificationError(null);

    try {
      const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';
      const apiUrl = `${backendUrl}/api/github/repositories/${owner}/${repo}/pulls/${pullNumber}/verify-proposal`;

      const targetFile =
        proposalData.file_path ||
        (conflictData?.conflicts?.[0]?.path) ||
        'modified_file';
      const language =
        proposalData.language ||
        (conflictData?.conflicts?.[0]?.language) ||
        'unknown';

      const token = localStorage.getItem('mergemind_token');
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}`, 'X-Session-Token': token } : {}),
        },
        credentials: 'include',
        body: JSON.stringify({
          target_file: targetFile,
          merged_code: proposalData.merged_code,
          language: language,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Verification pipeline failed.');
      }

      setVerificationReport(data);
    } catch (err) {
      console.error('Error during verification:', err);
      setVerificationError(err.message || 'Failed to verify proposal.');
    } finally {
      setVerifyingProposal(false);
    }
  };

  const handleRunWorkflow = async () => {
    setRunningWorkflow(true);
    setWorkflowError(null);

    try {
      const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';
      const apiUrl = `${backendUrl}/api/github/repositories/${owner}/${repo}/pulls/${pullNumber}/resolve-workflow?max_retries=${maxRetries}`;

      const token = localStorage.getItem('mergemind_token');
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
          ...(token ? { Authorization: `Bearer ${token}`, 'X-Session-Token': token } : {}),
        },
        credentials: 'include',
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Autonomous workflow execution failed.');
      }

      setWorkflowData(data);
      // Auto-populate proposal and verification displays with latest attempt
      if (data.current_proposal) {
        setProposalData(data.current_proposal);
      }
      if (data.current_verification) {
        setVerificationReport(data.current_verification);
      }
    } catch (err) {
      console.error('Error running autonomous workflow:', err);
      setWorkflowError(err.message || 'Failed to execute workflow.');
    } finally {
      setRunningWorkflow(false);
    }
  };

  useEffect(() => {
    if (owner && repo && pullNumber) {
      fetchPullRequest();
    }
  }, [owner, repo, pullNumber]);

  useEffect(() => {
    if (!owner || !repo || !pullNumber) return;
    const channelId = `${owner}_${repo}_${pullNumber}`;
    const unsubscribe = subscribeToPipelineProgress(
      channelId,
      (evt) => {
        console.log('[Live Pipeline Progress]', evt);
      },
      (err) => console.warn('[WS Connection Error]', err)
    );
    return () => unsubscribe();
  }, [owner, repo, pullNumber]);

  return (
    <div className="min-h-screen bg-[#0B0F17] text-slate-100 flex flex-col font-sans selection:bg-sky-500/30 selection:text-sky-200">
      {/* Background ambient lighting */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <div className="absolute top-[-10%] left-[-10%] w-[45vw] h-[45vw] rounded-full bg-sky-500/5 blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40vw] h-[40vw] rounded-full bg-cyan-500/5 blur-[120px]" />
      </div>

      {/* Navigation Header */}
      <header className="sticky top-0 z-50 backdrop-blur-md bg-[#0B0F17]/85 border-b border-white/[0.06]">
        <div className="max-w-[1600px] w-full mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
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

      {/* Main Container — Expanded for Grid Dashboard */}
      <main className="flex-1 max-w-[1600px] w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 relative z-10">

        {/* State 1: Loading State */}
        {loading && (
          <div className="neu-panel rounded-2xl p-12 text-center border border-white/[0.07] my-12 max-w-xl mx-auto shadow-[0_15px_40px_rgba(0,0,0,0.6)]">
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
          <div className="neu-panel rounded-2xl p-10 text-center border border-rose-500/20 my-12 max-w-xl mx-auto shadow-[0_15px_40px_rgba(0,0,0,0.6)]">
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

        {/* State 3: Success State */}
        {!loading && !error && pullRequest && (
          <div className="space-y-6">

            {/* Top PR Header Banner */}
            <div className="neu-panel rounded-2xl p-5 sm:p-6 border border-white/[0.07] shadow-[0_15px_40px_rgba(0,0,0,0.5)]">
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                <div className="space-y-2 min-w-0">
                  <div className="flex flex-wrap items-center gap-2.5">
                    <span className="text-sm font-mono font-extrabold text-sky-400 px-2.5 py-0.5 rounded-lg neu-recessed border border-white/[0.04]">
                      #{pullRequest.number}
                    </span>

                    {pullRequest.draft ? (
                      <span className="text-xs font-mono px-2.5 py-0.5 rounded-lg bg-slate-800 text-slate-400 border border-slate-700">
                        Draft
                      </span>
                    ) : (
                      <span className="text-xs font-mono uppercase tracking-wider px-2.5 py-0.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                        OPEN
                      </span>
                    )}

                    {pullRequest.mergeable_state && (
                      <span className={`text-[11px] font-mono px-2.5 py-0.5 rounded-lg border ${
                        pullRequest.mergeable === false
                          ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                          : pullRequest.mergeable === true
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                          : 'bg-sky-500/10 text-sky-400 border-sky-500/20'
                      }`}>
                        state: {pullRequest.mergeable_state}
                      </span>
                    )}

                    {conflictData?.conflicts && conflictData.conflicts.length > 0 && (
                      <span className="text-[11px] font-mono px-2.5 py-0.5 rounded-lg bg-amber-500/15 text-amber-300 border border-amber-500/30 flex items-center gap-1.5 font-semibold">
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                        <span>{conflictData.conflicts.length} conflicting {conflictData.conflicts.length === 1 ? 'file' : 'files'}</span>
                      </span>
                    )}
                  </div>

                  <h1 className="text-xl sm:text-2xl lg:text-3xl font-extrabold text-white tracking-tight leading-tight">
                    {pullRequest.title}
                  </h1>

                  <div className="flex flex-wrap items-center gap-y-2 gap-x-5 text-xs text-slate-400 font-mono">
                    <div className="flex items-center gap-1.5">
                      <User className="w-3.5 h-3.5 text-slate-500" />
                      <span>Author:</span>
                      <span className="text-slate-200 font-medium">{pullRequest.author || 'unknown'}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <GitBranch className="w-3.5 h-3.5 text-sky-400" />
                      <span className="px-2 py-0.5 rounded-md neu-recessed text-sky-300 font-semibold border border-white/[0.03]">
                        {pullRequest.head_branch}
                      </span>
                      <ArrowRight className="w-3 h-3 text-slate-500" />
                      <span className="px-2 py-0.5 rounded-md neu-recessed text-slate-300 border border-white/[0.03]">
                        {pullRequest.base_branch}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-3 flex-shrink-0 pt-2 lg:pt-0">
                  <button
                    type="button"
                    onClick={handleAnalyzeConflicts}
                    disabled={analyzing}
                    className="neu-glow-btn px-4 py-2 rounded-xl text-xs font-bold text-white flex items-center gap-2 transition-all cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed shadow-[0_0_20px_rgba(56,189,248,0.2)]"
                  >
                    {analyzing ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 text-sky-300 animate-spin" />
                        <span>Analyzing...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-3.5 h-3.5 text-sky-300" />
                        <span>{conflictData ? 'Re-analyze Conflicts' : 'Analyze Conflicts'}</span>
                      </>
                    )}
                  </button>

                  <a
                    href={pullRequest.html_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="neu-button px-3.5 py-2 rounded-xl text-xs font-medium text-slate-300 hover:text-white flex items-center gap-1.5 transition-colors group"
                  >
                    <span>View on GitHub</span>
                    <ExternalLink className="w-3.5 h-3.5 text-sky-400 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
                  </a>
                </div>
              </div>
            </div>

            {/* Case 1: Mergeable === true (Clean / No Conflicts) */}
            {pullRequest.mergeable === true && (
              <div className="rounded-2xl p-8 neu-recessed border border-emerald-500/20 bg-emerald-950/10 text-center max-w-2xl mx-auto my-6 space-y-4">
                <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mx-auto">
                  <CheckCircle2 className="w-6 h-6" />
                </div>
                <h2 className="text-xl font-bold text-white">No merge conflicts detected</h2>
                <p className="text-sm text-slate-300 leading-relaxed max-w-lg mx-auto">
                  GitHub reports that this pull request can be cleanly and automatically merged into branch <code className="text-sky-300 font-mono px-1.5 py-0.5 rounded bg-slate-800/80">{pullRequest.base_branch}</code> without conflicts.
                </p>
              </div>
            )}

            {/* Case 2: Mergeable === null (Calculating) */}
            {pullRequest.mergeable === null && (
              <div className="rounded-2xl p-8 neu-recessed border border-sky-500/20 bg-sky-950/10 text-center max-w-2xl mx-auto my-6 space-y-4">
                <div className="w-12 h-12 rounded-2xl bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-sky-400 mx-auto">
                  <RefreshCw className="w-6 h-6 animate-spin" />
                </div>
                <h2 className="text-xl font-bold text-white">Calculating mergeability...</h2>
                <p className="text-sm text-slate-300 leading-relaxed max-w-lg mx-auto">
                  GitHub is currently calculating the mergeability status in the background. Please wait a moment and refresh.
                </p>
                <button
                  onClick={fetchPullRequest}
                  className="neu-button px-5 py-2.5 rounded-xl text-xs font-semibold text-sky-300 hover:text-white inline-flex items-center gap-2"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Re-check Status</span>
                </button>
              </div>
            )}

            {/* Case 3: Mergeable === false (Conflicted — High-Productivity 2-Column Grid Dashboard) */}
            {pullRequest.mergeable === false && (
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">

                {/* ======================================================== */}
                {/* PRIMARY WORKSPACE: Left Column (7 cols on lg, 8 on xl)  */}
                {/* ======================================================== */}
                <div className="lg:col-span-7 xl:col-span-8 space-y-6">

                  {/* Conflict Extraction Error Banner */}
                  {analysisError && (
                    <div className="p-4 rounded-xl bg-rose-950/30 border border-rose-500/30 flex items-start gap-3">
                      <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
                      <div className="flex-1">
                        <p className="text-xs font-semibold text-rose-300">Conflict extraction failed</p>
                        <p className="text-xs text-rose-400/90 leading-relaxed mt-0.5">{analysisError}</p>
                      </div>
                      <button
                        onClick={handleAnalyzeConflicts}
                        className="neu-button px-3 py-1 rounded-lg text-xs text-rose-300 hover:text-white"
                      >
                        Retry
                      </button>
                    </div>
                  )}

                  {/* Conflict Analysis & Files Section */}
                  {conflictData && (
                    <div className="neu-panel rounded-2xl p-6 sm:p-7 border border-white/[0.08] shadow-[0_15px_40px_rgba(0,0,0,0.5)]">
                      <div className="flex flex-wrap items-center justify-between gap-3 mb-5 pb-4 border-b border-white/[0.06]">
                        <div className="flex items-center gap-3">
                          <h3 className="text-base sm:text-lg font-bold text-white flex items-center gap-2">
                            <span>Conflict Analysis</span>
                          </h3>
                          <span className="text-xs font-mono px-2.5 py-0.5 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20 font-semibold flex items-center gap-1.5">
                            <AlertTriangle className="w-3.5 h-3.5" />
                            <span>
                              {conflictData.conflicts?.length || 0} conflicting {conflictData.conflicts?.length === 1 ? 'file' : 'files'}
                            </span>
                          </span>
                        </div>

                        <div className="flex items-center gap-3 text-xs font-mono text-slate-400">
                          {conflictData.changed_files && conflictData.changed_files.length > 0 && (
                            <span>{conflictData.changed_files.length} total changed in PR</span>
                          )}
                          <button
                            onClick={handleAnalyzeConflicts}
                            disabled={analyzing}
                            className="neu-button px-2.5 py-1 rounded-lg text-slate-300 hover:text-white flex items-center gap-1 transition-colors"
                            title="Re-run Git simulation"
                          >
                            <RefreshCw className={`w-3 h-3 text-sky-400 ${analyzing ? 'animate-spin' : ''}`} />
                            <span>Refresh</span>
                          </button>
                        </div>
                      </div>

                      {/* Conflicting Files Cards Grid */}
                      {conflictData.conflicts && conflictData.conflicts.length > 0 ? (
                        <div className="grid grid-cols-1 gap-4">
                          {conflictData.conflicts.map((c) => (
                            <div
                              key={c.path}
                              className="p-5 rounded-xl neu-recessed border border-white/[0.05] space-y-4"
                            >
                              {/* File Header */}
                              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-white/[0.04]">
                                <div className="flex items-center gap-3 min-w-0">
                                  <div className="w-9 h-9 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 flex-shrink-0">
                                    <FileCode className="w-4 h-4" />
                                  </div>
                                  <div className="truncate">
                                    <p className="font-mono text-sm sm:text-base font-bold text-white truncate">
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
                                  <span className="text-[11px] font-mono uppercase px-2.5 py-1 rounded-md bg-sky-500/10 text-sky-300 border border-sky-500/20 font-semibold">
                                    {c.language}
                                  </span>
                                  <span className="text-[11px] font-mono px-2.5 py-1 rounded-md bg-amber-500/10 text-amber-400 border border-amber-500/20">
                                    {c.conflict_type}
                                  </span>
                                  <button
                                    type="button"
                                    onClick={() => handleGenerateProposal(c.path)}
                                    disabled={generatingProposal}
                                    className="neu-button px-3 py-1.5 rounded-lg text-xs font-mono text-violet-300 hover:text-white bg-violet-500/15 hover:bg-violet-500/25 border border-violet-500/35 flex items-center gap-1.5 transition-colors disabled:opacity-50"
                                    title={`Generate LLM proposal for ${c.path}`}
                                  >
                                    <Sparkles className="w-3.5 h-3.5 text-violet-400" />
                                    <span className="font-semibold">Propose Fix</span>
                                  </button>
                                </div>
                              </div>

                              {/* Semantic Structure AST Analysis */}
                              {c.ast_analysis && (
                                <div className="space-y-3">
                                  <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                                    <div className="flex items-center gap-2">
                                      <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold">
                                        Semantic Structure:
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
                                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono">
                                    <div className="p-3 rounded-lg bg-slate-950/60 border border-white/[0.04]">
                                      <span className="text-[10px] uppercase text-sky-400 font-bold block mb-1.5 flex items-center gap-1">
                                        <span>Local changes (target):</span>
                                      </span>
                                      {c.ast_analysis.changes?.local && c.ast_analysis.changes.local.length > 0 ? (
                                        <ul className="space-y-1 text-slate-300 text-[11px]">
                                          {c.ast_analysis.changes.local.map((ch, idx) => (
                                            <li key={idx} className="truncate">
                                              • {ch.node_name ? `${ch.node_name}()` : ch.details}
                                            </li>
                                          ))}
                                        </ul>
                                      ) : (
                                        <span className="text-slate-500 italic text-[11px]">No structural function delta</span>
                                      )}
                                    </div>

                                    <div className="p-3 rounded-lg bg-slate-950/60 border border-white/[0.04]">
                                      <span className="text-[10px] uppercase text-amber-400 font-bold block mb-1.5 flex items-center gap-1">
                                        <span>Remote changes (source):</span>
                                      </span>
                                      {c.ast_analysis.changes?.remote && c.ast_analysis.changes.remote.length > 0 ? (
                                        <ul className="space-y-1 text-slate-300 text-[11px]">
                                          {c.ast_analysis.changes.remote.map((ch, idx) => (
                                            <li key={idx} className="truncate">
                                              • {ch.node_name ? `${ch.node_name}()` : ch.details}
                                            </li>
                                          ))}
                                        </ul>
                                      ) : (
                                        <span className="text-slate-500 italic text-[11px]">No structural function delta</span>
                                      )}
                                    </div>
                                  </div>

                                  {/* Reason */}
                                  {c.ast_analysis.classification?.reason && (
                                    <p className="text-xs text-slate-300 bg-white/[0.02] p-2.5 rounded-lg border border-white/[0.03]">
                                      <span className="font-semibold text-sky-300">Reason: </span>
                                      {c.ast_analysis.classification.reason}
                                    </p>
                                  )}
                                </div>
                              )}

                              {/* Toggle Conflict Markers Hunk Preview */}
                              {c.conflict_markers && (c.conflict_markers.ours || c.conflict_markers.theirs) && (
                                <div className="pt-2 border-t border-white/[0.04]">
                                  <button
                                    type="button"
                                    onClick={() => toggleHunks(c.path)}
                                    className="text-xs font-mono text-slate-400 hover:text-sky-300 flex items-center gap-1.5 transition-colors"
                                  >
                                    <Split className="w-3.5 h-3.5 text-sky-400" />
                                    <span>{showHunks[c.path] ? 'Hide conflict markers hunk' : 'Inspect conflict markers hunk'}</span>
                                    {showHunks[c.path] ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                                  </button>

                                  {showHunks[c.path] && (
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3 text-xs font-mono">
                                      <div className="rounded-lg bg-sky-950/20 border border-sky-500/20 overflow-hidden">
                                        <div className="px-3 py-1.5 bg-sky-500/10 border-b border-sky-500/20 text-sky-300 text-[11px] font-bold">
                                          &lt;&lt;&lt;&lt;&lt;&lt;&lt; HEAD (Local / Ours)
                                        </div>
                                        <pre className="p-3 text-slate-300 max-h-48 overflow-auto whitespace-pre leading-relaxed text-[11px]">
                                          {c.conflict_markers.ours || '(empty)'}
                                        </pre>
                                      </div>

                                      <div className="rounded-lg bg-amber-950/20 border border-amber-500/20 overflow-hidden">
                                        <div className="px-3 py-1.5 bg-amber-500/10 border-b border-amber-500/20 text-amber-300 text-[11px] font-bold">
                                          &gt;&gt;&gt;&gt;&gt;&gt;&gt; {c.remote_sha ? c.remote_sha.slice(0, 7) : 'PR'} (Remote / Theirs)
                                        </div>
                                        <pre className="p-3 text-slate-300 max-h-48 overflow-auto whitespace-pre leading-relaxed text-[11px]">
                                          {c.conflict_markers.theirs || '(empty)'}
                                        </pre>
                                      </div>
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="p-6 rounded-xl neu-recessed border border-white/[0.04] text-center text-xs text-slate-400">
                          No conflicting files detected in the simulation.
                        </div>
                      )}
                    </div>
                  )}

                  {/* Phase 6: Autonomous LangGraph StateGraph Workflow */}
                  {(conflictData || workflowData || runningWorkflow) && (
                    <WorkflowPanel
                      workflowData={workflowData}
                      running={runningWorkflow}
                      onRunWorkflow={handleRunWorkflow}
                      maxRetries={maxRetries}
                      onChangeMaxRetries={setMaxRetries}
                      error={workflowError}
                    />
                  )}

                  {/* MergeMind Proposal Canvas (LLM Agent) */}
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

                          {/* Phase 8: Interactive 4-Way Review & Human Decision Panel */}
                          {proposalData.merged_code ? (
                            <ConflictReviewPanel
                              owner={owner}
                              repo={repo}
                              pullNumber={Number(pullNumber)}
                              filePath={conflictData?.conflicts?.[0]?.path || pullRequest?.head_branch || 'conflicted_file'}
                              baseCode={conflictData?.conflicts?.[0]?.base || ''}
                              localCode={conflictData?.conflicts?.[0]?.local || ''}
                              remoteCode={conflictData?.conflicts?.[0]?.remote || ''}
                              proposedCode={proposalData.merged_code}
                              reasoning={proposalData.reasoning}
                              confidence={proposalData.confidence}
                              verificationReport={verificationReport}
                              runId={workflowData?.merge_run_id}
                              onDecisionSubmitted={(decision, result) => {
                                console.log(`[Review Decision] ${decision}:`, result);
                              }}
                            />
                          ) : (
                            <div className="p-4 rounded-xl neu-recessed border border-white/[0.04] text-xs text-slate-400 text-center italic">
                              No resolved code produced. Status is unresolved.
                            </div>
                          )}

                          {/* Phase 5: Deterministic Docker Sandbox Verification */}
                          {proposalData.merged_code && (
                            <VerificationCard
                              report={verificationReport}
                              verifying={verifyingProposal}
                              onVerify={handleVerifyProposal}
                              error={verificationError}
                            />
                          )}

                        </div>
                      )}
                    </div>
                  )}

                </div>

                {/* ======================================================== */}
                {/* SIDEBAR PANEL: Right Column (5 cols on lg, 4 on xl)      */}
                {/* ======================================================== */}
                <div className="lg:col-span-5 xl:col-span-4 space-y-6 lg:sticky lg:top-20">

                  {/* Conflict Notice & Quick Action Card */}
                  <div className="neu-panel rounded-2xl p-5 border border-amber-500/30 bg-amber-950/10 shadow-[0_15px_40px_rgba(0,0,0,0.5)] space-y-4">
                    <div className="flex items-start gap-3">
                      <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 flex-shrink-0 mt-0.5">
                        <AlertTriangle className="w-5 h-5" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-2">
                          <h4 className="text-base font-bold text-white">Merge Conflict</h4>
                          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                            {pullRequest.mergeable_state || 'dirty'}
                          </span>
                        </div>
                        <p className="text-xs text-slate-300 mt-1 leading-relaxed">
                          MergeMind simulates Git 3-way merge in an isolated temporary sandbox to extract Base, Local, and Remote versions deterministically.
                        </p>
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={handleAnalyzeConflicts}
                      disabled={analyzing}
                      className="neu-glow-btn w-full py-2.5 rounded-xl text-xs font-bold text-white flex items-center justify-center gap-2 cursor-pointer disabled:opacity-60"
                    >
                      {analyzing ? (
                        <>
                          <Loader2 className="w-4 h-4 text-sky-300 animate-spin" />
                          <span>Simulating 3-way merge...</span>
                        </>
                      ) : (
                        <>
                          <Sparkles className="w-4 h-4 text-sky-300" />
                          <span>{conflictData ? 'Re-analyze Conflicts' : 'Analyze Conflicts'}</span>
                        </>
                      )}
                    </button>
                  </div>

                  {/* Repository Context Card with Clean Tab Navigation */}
                  <div className="neu-panel rounded-2xl p-5 border border-white/[0.08] shadow-[0_15px_40px_rgba(0,0,0,0.5)] space-y-4">
                    <div className="flex items-center justify-between gap-2 pb-3 border-b border-white/[0.06]">
                      <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-lg bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
                          <FolderTree className="w-4 h-4" />
                        </div>
                        <div>
                          <h4 className="text-sm font-bold text-white flex items-center gap-1.5">
                            <span>Repository Context</span>
                            <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-sky-500/10 text-sky-300 border border-sky-500/20">
                              deterministic
                            </span>
                          </h4>
                          <p className="text-[11px] text-slate-400">Metadata & structure</p>
                        </div>
                      </div>

                      <button
                        onClick={() => fetchRepositoryContext(conflictData?.conflicting_files || [])}
                        disabled={loadingContext}
                        className="neu-button p-1.5 rounded-lg text-slate-400 hover:text-white transition-colors disabled:opacity-50"
                        title="Re-extract repository context"
                      >
                        <RefreshCw className={`w-3.5 h-3.5 text-sky-400 ${loadingContext ? 'animate-spin' : ''}`} />
                      </button>
                    </div>

                    {/* Context Tab Navigation Pills */}
                    <div className="grid grid-cols-4 gap-1 p-1 rounded-xl neu-recessed border border-white/[0.03]">
                      <button
                        onClick={() => setActiveContextTab('tech')}
                        className={`py-1.5 px-2 rounded-lg text-[11px] font-mono font-medium transition-colors ${
                          activeContextTab === 'tech'
                            ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                            : 'text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        Tech
                      </button>
                      <button
                        onClick={() => setActiveContextTab('tree')}
                        className={`py-1.5 px-2 rounded-lg text-[11px] font-mono font-medium transition-colors ${
                          activeContextTab === 'tree'
                            ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                            : 'text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        Tree
                      </button>
                      <button
                        onClick={() => setActiveContextTab('neighbors')}
                        className={`py-1.5 px-2 rounded-lg text-[11px] font-mono font-medium transition-colors ${
                          activeContextTab === 'neighbors'
                            ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                            : 'text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        Neighbors
                      </button>
                      <button
                        onClick={() => setActiveContextTab('readme')}
                        className={`py-1.5 px-2 rounded-lg text-[11px] font-mono font-medium transition-colors ${
                          activeContextTab === 'readme'
                            ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                            : 'text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        README
                      </button>
                    </div>

                    {/* Loading State */}
                    {loadingContext && (
                      <div className="p-6 rounded-xl neu-recessed text-center space-y-2">
                        <Loader2 className="w-5 h-5 text-sky-400 animate-spin mx-auto" />
                        <p className="text-xs text-slate-400">Extracting context...</p>
                      </div>
                    )}

                    {/* Error State */}
                    {!loadingContext && contextError && (
                      <div className="p-3 rounded-xl bg-rose-950/30 border border-rose-500/20 text-xs text-rose-300 flex items-center justify-between gap-2">
                        <span className="truncate">{contextError}</span>
                        <button
                          type="button"
                          onClick={() => fetchRepositoryContext(conflictData?.conflicting_files || [])}
                          className="neu-button px-2.5 py-1 rounded-lg text-xs font-mono text-rose-200 hover:text-white border border-rose-500/30 hover:bg-rose-500/20 transition-colors flex-shrink-0"
                        >
                          Retry
                        </button>
                      </div>
                    )}

                    {/* Tab 1: Technologies & Frameworks */}
                    {!loadingContext && !contextError && repositoryContext && activeContextTab === 'tech' && (
                      <div className="space-y-3 max-h-[380px] overflow-y-auto pr-1">
                        {repositoryContext.project?.description && (
                          <div className="p-3 rounded-lg neu-recessed text-xs text-slate-300">
                            <span className="text-[10px] uppercase font-bold text-sky-400 block mb-1">Description</span>
                            {repositoryContext.project.description}
                          </div>
                        )}

                        <div className="flex flex-wrap gap-1.5">
                          {repositoryContext.project?.languages?.map((lang, idx) => (
                            <span
                              key={`lang-${idx}`}
                              className="px-2 py-1 rounded-md bg-sky-500/10 text-sky-300 border border-sky-500/20 text-[11px] font-mono capitalize"
                            >
                              {lang}
                            </span>
                          ))}

                          {repositoryContext.project?.package_managers?.map((pm, idx) => (
                            <span
                              key={`pm-${idx}`}
                              className="px-2 py-1 rounded-md bg-slate-500/10 text-slate-300 border border-slate-500/20 text-[11px] font-mono"
                            >
                              {pm}
                            </span>
                          ))}

                          {repositoryContext.detected_technologies?.map((tech, idx) => (
                            <span
                              key={`tech-${idx}`}
                              className="px-2 py-1 rounded-md bg-indigo-500/10 text-indigo-300 border border-indigo-500/25 text-[11px] font-mono"
                            >
                              {tech.name}
                            </span>
                          ))}
                        </div>

                        {repositoryContext.detected_configs && repositoryContext.detected_configs.length > 0 && (
                          <div className="pt-2 border-t border-white/[0.04]">
                            <span className="text-[10px] font-mono uppercase text-slate-400 block mb-1.5">Config files:</span>
                            <div className="flex flex-wrap gap-1">
                              {repositoryContext.detected_configs.map((cfg, idx) => (
                                <span key={idx} className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/[0.03] text-slate-300 border border-white/[0.04]">
                                  {cfg}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Tab 2: File Tree */}
                    {!loadingContext && !contextError && repositoryContext && activeContextTab === 'tree' && (
                      <div className="space-y-2">
                        <div className="p-3 rounded-xl bg-slate-950/80 border border-white/[0.04] max-h-[380px] overflow-y-auto">
                          <pre className="text-[11px] font-mono text-slate-300 leading-relaxed whitespace-pre">
                            {repositoryContext.tree || 'No tree entries found.'}
                          </pre>
                        </div>
                      </div>
                    )}

                    {/* Tab 3: Neighbor Files */}
                    {!loadingContext && !contextError && repositoryContext && activeContextTab === 'neighbors' && (
                      <div className="space-y-2 max-h-[380px] overflow-y-auto pr-1">
                        {repositoryContext.relevant_files && repositoryContext.relevant_files.length > 0 ? (
                          repositoryContext.relevant_files.map((file, idx) => (
                            <div key={idx} className="p-2.5 rounded-xl neu-recessed border border-white/[0.04]">
                              <button
                                type="button"
                                onClick={() => toggleFilePreview(file.path)}
                                className="w-full flex items-center justify-between text-left text-xs font-mono text-slate-300 hover:text-white"
                              >
                                <span className="truncate">{file.path}</span>
                                {filePreviewsOpen[file.path] ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                              </button>
                              {filePreviewsOpen[file.path] && (
                                <pre className="mt-2 p-2 rounded bg-slate-950/90 text-[10px] font-mono text-slate-300 max-h-40 overflow-auto whitespace-pre">
                                  {file.content || '(empty)'}
                                </pre>
                              )}
                            </div>
                          ))
                        ) : (
                          <p className="text-xs text-slate-500 italic p-2">No neighbor files discovered.</p>
                        )}
                      </div>
                    )}

                    {/* Tab 4: README */}
                    {!loadingContext && !contextError && repositoryContext && activeContextTab === 'readme' && (
                      <div className="p-3 rounded-xl bg-slate-950/80 border border-white/[0.04] max-h-[380px] overflow-y-auto">
                        <pre className="text-[11px] font-mono text-slate-300 leading-relaxed whitespace-pre-wrap">
                          {repositoryContext.documentation?.readme || 'No README file discovered in repository.'}
                        </pre>
                      </div>
                    )}

                  </div>

                </div>

              </div>
            )}

          </div>
        )}

      </main>
    </div>
  );
}
