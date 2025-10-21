'use client';

import { useState } from 'react';

interface ProcessingStep {
  id: string;
  label: string;
  status: 'pending' | 'processing' | 'complete' | 'skipped';
  detail?: string;
  link?: string;
  elapsed?: number; // seconds elapsed for this step
  substeps?: string[]; // for showing chunked audio processing
}

export default function AdminPage() {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [steps, setSteps] = useState<ProcessingStep[]>([]);
  const [result, setResult] = useState<{
    status: 'success' | 'error';
    message: string;
    articleId?: number;
  } | null>(null);

  const updateStep = (id: string, updates: Partial<ProcessingStep>) => {
    setSteps(prev => prev.map(step =>
      step.id === id ? { ...step, ...updates } : step
    ));
  };

  const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

  const initializeSteps = () => {
    // Initialize steps
    const initialSteps: ProcessingStep[] = [
      { id: 'fetch', label: 'Fetching article', status: 'pending', elapsed: 0 },
      { id: 'media', label: 'Detecting media content', status: 'pending', elapsed: 0 },
      { id: 'content', label: 'Extracting content', status: 'pending', elapsed: 0 },
      { id: 'transcript', label: 'Download audio and processing transcript', status: 'pending', elapsed: 0, substeps: [] },
      { id: 'ai', label: 'Generating AI summary', status: 'pending', elapsed: 0 },
      { id: 'save', label: 'Saving to database', status: 'pending', elapsed: 0 },
    ];
    setSteps(initialSteps);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!url.trim()) {
      setResult({
        status: 'error',
        message: 'Please enter a URL'
      });
      return;
    }

    setLoading(true);
    setResult(null);
    initializeSteps();

    try {
      // Start article processing and get job_id
      const response = await fetch('https://automatelife-production.up.railway.app/api/process-article-stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer article-summarizer-production-key-2025'
        },
        body: JSON.stringify({ url: url.trim() })
      });

      if (!response.ok) {
        const data = await response.json();
        setResult({
          status: 'error',
          message: data.detail || 'Failed to start processing'
        });
        setLoading(false);
        return;
      }

      const { job_id } = await response.json();
      console.log('Job started with ID:', job_id);

      // Connect to SSE stream immediately
      const eventSource = new EventSource(
        `https://automatelife-production.up.railway.app/api/status/${job_id}?api_key=article-summarizer-production-key-2025`
      );

      console.log('EventSource connection opened for job:', job_id);

      eventSource.addEventListener('started', (e) => {
        const data = JSON.parse(e.data);
        console.log('Processing started:', data);
      });

      eventSource.addEventListener('fetch_start', (e) => {
        const data = JSON.parse(e.data);
        console.log('Event: fetch_start', data);
        updateStep('fetch', { status: 'processing', elapsed: data.elapsed });
      });

      eventSource.addEventListener('fetch_complete', (e) => {
        const data = JSON.parse(e.data);
        console.log('Event: fetch_complete', data);
        updateStep('fetch', {
          status: 'complete',
          detail: `Article fetched successfully`,
          elapsed: data.elapsed
        });
      });

      eventSource.addEventListener('media_detect_start', (e) => {
        const data = JSON.parse(e.data);
        updateStep('media', { status: 'processing', elapsed: data.elapsed });
      });

      eventSource.addEventListener('media_detected', (e) => {
        const data = JSON.parse(e.data);
        const mediaType = data.media_type || 'text-only';
        const displayType = mediaType.charAt(0).toUpperCase() + mediaType.slice(1);
        updateStep('media', {
          status: 'complete',
          detail: `Content type: ${displayType}`,
          elapsed: data.elapsed
        });
      });

      eventSource.addEventListener('content_extract_start', (e) => {
        const data = JSON.parse(e.data);
        updateStep('content', { status: 'processing', elapsed: data.elapsed });
      });

      eventSource.addEventListener('content_extracted', (e) => {
        const data = JSON.parse(e.data);
        const transcriptMethod = data.transcript_method;

        updateStep('content', {
          status: 'complete',
          detail: 'Content extracted',
          elapsed: data.elapsed
        });

        // Handle transcript step based on method
        if (transcriptMethod === 'youtube') {
          updateStep('transcript', {
            status: 'complete',
            detail: 'Transcript found via YouTube',
            elapsed: data.elapsed
          });
        } else if (transcriptMethod === 'chunked') {
          updateStep('transcript', {
            status: 'processing',
            detail: 'Processing audio chunks...',
            elapsed: data.elapsed
          });
        } else if (transcriptMethod === 'audio') {
          updateStep('transcript', {
            status: 'processing',
            detail: 'Processing audio transcript...',
            elapsed: data.elapsed
          });
        } else {
          updateStep('transcript', {
            status: 'skipped',
            detail: 'No audio found',
            elapsed: data.elapsed
          });
        }
      });

      eventSource.addEventListener('ai_start', (e) => {
        const data = JSON.parse(e.data);
        updateStep('ai', { status: 'processing', elapsed: data.elapsed });
      });

      eventSource.addEventListener('ai_complete', (e) => {
        const data = JSON.parse(e.data);
        updateStep('ai', {
          status: 'complete',
          detail: 'Summary generated by Claude',
          elapsed: data.elapsed
        });
      });

      eventSource.addEventListener('save_start', (e) => {
        const data = JSON.parse(e.data);
        updateStep('save', { status: 'processing', elapsed: data.elapsed });
      });

      eventSource.addEventListener('save_complete', (e) => {
        const data = JSON.parse(e.data);
        updateStep('save', {
          status: 'complete',
          detail: 'Article saved to Supabase',
          elapsed: data.elapsed
        });
      });

      eventSource.addEventListener('completed', (e) => {
        const data = JSON.parse(e.data);
        setResult({
          status: 'success',
          message: 'Article processed successfully!',
          articleId: data.article_id
        });
        setUrl('');
        setLoading(false);
        eventSource.close();
      });

      eventSource.addEventListener('error', (e) => {
        const data = JSON.parse(e.data);
        setResult({
          status: 'error',
          message: data.message || 'Processing failed'
        });
        setLoading(false);
        eventSource.close();
      });

      eventSource.onerror = () => {
        console.error('SSE connection error');
        setResult({
          status: 'error',
          message: 'Connection to server lost'
        });
        setLoading(false);
        eventSource.close();
      };

    } catch (error) {
      setResult({
        status: 'error',
        message: error instanceof Error ? error.message : 'Network error occurred'
      });
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto">
        <div className="bg-white rounded-lg shadow-md p-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Article Processor Admin
          </h1>
          <p className="text-gray-600 mb-8">
            Submit article URLs to process and summarize
          </p>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="url" className="block text-sm font-medium text-gray-700 mb-2">
                Article URL
              </label>
              <input
                type="url"
                id="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://example.com/article"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#077331] focus:border-transparent"
                disabled={loading}
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className={`w-full py-3 px-4 rounded-lg font-medium text-white transition-colors ${
                loading
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-[#077331] hover:bg-[#055a24]'
              }`}
            >
              {loading ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Processing...
                </span>
              ) : (
                'Process Article'
              )}
            </button>
          </form>

          {/* Processing Steps */}
          {steps.length > 0 && (
            <div className="mt-8 space-y-3">
              <h3 className="text-sm font-medium text-gray-700 mb-4">Processing Status</h3>
              {steps.map((step) => (
                <div key={step.id} className="flex items-start gap-3">
                  <div className="flex-shrink-0 mt-0.5">
                    {step.status === 'complete' && (
                      <svg className="h-5 w-5 text-[#077331]" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                    )}
                    {step.status === 'processing' && (
                      <svg className="animate-spin h-5 w-5 text-[#077331]" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                    )}
                    {step.status === 'pending' && (
                      <div className="h-5 w-5 rounded-full border-2 border-gray-300"></div>
                    )}
                    {step.status === 'skipped' && (
                      <svg className="h-5 w-5 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                      </svg>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-baseline justify-between">
                      <p className={`text-sm font-medium ${
                        step.status === 'complete' ? 'text-gray-900' :
                        step.status === 'processing' ? 'text-[#077331]' :
                        step.status === 'skipped' ? 'text-gray-400' :
                        'text-gray-500'
                      }`}>
                        {step.label}
                      </p>
                      {(step.status === 'processing' || step.status === 'complete') && step.elapsed !== undefined && (
                        <span className="text-xs text-gray-400 ml-2">
                          ({step.elapsed}s)
                        </span>
                      )}
                    </div>
                    {step.detail && (
                      <p className="text-xs text-gray-500 mt-0.5">{step.detail}</p>
                    )}
                    {step.substeps && step.substeps.length > 0 && (
                      <div className="mt-1 pl-3 border-l-2 border-[#077331]">
                        {step.substeps.map((substep, idx) => (
                          <p key={idx} className="text-xs text-[#077331] mt-0.5">
                            • {substep}
                          </p>
                        ))}
                      </div>
                    )}
                    {step.link && (
                      <a href={step.link} className="text-xs text-[#077331] hover:underline mt-1 inline-block">
                        View →
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {result && (
            <div
              className={`mt-6 p-4 rounded-lg border-2 ${
                result.status === 'success'
                  ? 'bg-green-50 border-[#077331]'
                  : 'bg-red-50 border-red-300'
              }`}
            >
              <div className="flex">
                <div className="flex-shrink-0">
                  {result.status === 'success' ? (
                    <svg className="h-6 w-6 text-[#077331]" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                  ) : (
                    <svg className="h-6 w-6 text-red-500" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                  )}
                </div>
                <div className="ml-3 flex-1">
                  <p className={`text-sm font-medium ${
                    result.status === 'success' ? 'text-[#077331]' : 'text-red-800'
                  }`}>
                    {result.message}
                  </p>
                  {result.articleId && (
                    <a
                      href={`/article/${result.articleId}`}
                      className="mt-3 inline-flex items-center px-4 py-2 bg-[#077331] text-white text-sm font-medium rounded-lg hover:bg-[#055a24] transition-colors"
                    >
                      View Article
                      <svg className="ml-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </a>
                  )}
                </div>
              </div>
            </div>
          )}

          <div className="mt-8 pt-6 border-t border-gray-200">
            <a
              href="/"
              className="text-sm text-gray-600 hover:text-[#077331] transition-colors inline-flex items-center"
            >
              <svg className="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              Back to Articles
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
