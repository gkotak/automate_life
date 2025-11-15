'use client';

import { useState, useEffect, useRef, Suspense, useMemo } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter, useSearchParams } from 'next/navigation';
import { createBrowserClient } from '@supabase/ssr';

// API configuration from environment variables
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ProcessingStep {
  id: string;
  label: string;
  status: 'pending' | 'processing' | 'complete' | 'skipped';
  detail?: string;
  link?: string;
  startTime?: number;
  duration?: number;
  substeps?: string[];
}

function AdminPageContent() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [isDemoVideo, setIsDemoVideo] = useState(false);
  const [steps, setSteps] = useState<ProcessingStep[]>([]);
  const [result, setResult] = useState<{
    status: 'success' | 'error' | 'info';
    message: string;
    articleId?: number;
  } | null>(null);
  const [duplicateWarning, setDuplicateWarning] = useState<{
    title: string;
    articleId: number;
    created_at: string;
    updated_at: string;
    url: string;
  } | null>(null);
  const audioDurationRef = useRef<number | null>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const hasAutoSubmittedRef = useRef(false);

  // Create Supabase client - same as AuthContext
  const supabase = useMemo(() => createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!
  ), []);

  // Protect this page - redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
    }
  }, [user, authLoading, router]);

  // Read URL parameter and auto-populate (no auto-submit)
  useEffect(() => {
    if (user) {
      const urlParam = searchParams.get('url');
      if (urlParam) {
        setUrl(urlParam);
      }
    }
  }, [user, searchParams]);

  // Real-time counter: Update duration every second for steps that are processing
  useEffect(() => {
    const interval = setInterval(() => {
      setSteps(prev => prev.map(step => {
        if (step.status === 'processing' && step.startTime) {
          const now = Date.now();
          const duration = Math.floor((now - step.startTime) / 1000);
          return { ...step, duration };
        }
        return step;
      }));
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const updateStep = (id: string, updates: Partial<ProcessingStep>) => {
    setSteps(prev => prev.map(step => {
      if (step.id === id) {
        const now = Date.now();

        if (updates.status === 'processing' && !step.startTime) {
          return { ...step, ...updates, startTime: now, duration: 0 };
        }

        if ((updates.status === 'complete' || updates.status === 'skipped') && step.startTime) {
          const duration = Math.max(1, Math.floor((now - step.startTime) / 1000));
          return { ...step, ...updates, duration };
        }

        return { ...step, ...updates };
      }
      return step;
    }));
  };

  const initializeSteps = () => {
    const initialSteps: ProcessingStep[] = [
      { id: 'fetch', label: 'Fetching article', status: 'pending' },
      { id: 'content', label: 'Extracting content', status: 'pending' },
      { id: 'transcript', label: 'Downloading media and processing transcript', status: 'pending', substeps: [] },
      { id: 'ai', label: 'Generating AI summary', status: 'pending' },
      { id: 'save', label: 'Saving to database', status: 'pending' },
    ];
    setSteps(initialSteps);
  };

  const handleSubmit = async (e: React.FormEvent, forceReprocess: boolean = false) => {
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
    setDuplicateWarning(null);
    audioDurationRef.current = null;
    initializeSteps();

    try {
      // Get auth token from Supabase
      const { data: { session } } = await supabase.auth.getSession();

      if (!session?.access_token) {
        throw new Error('Not authenticated. Please sign in again.');
      }

      const encodedUrl = encodeURIComponent(url.trim());
      // NOTE: EventSource doesn't support custom headers, so we pass the token as a query parameter
      // The backend will be updated to accept tokens from query params for SSE endpoints
      let streamUrl = `${API_URL}/api/process-direct?url=${encodedUrl}&token=${encodeURIComponent(session.access_token)}`;
      if (forceReprocess) {
        streamUrl += '&force_reprocess=true';
      }
      if (isDemoVideo) {
        streamUrl += '&demo_video=true';
      }

      const eventSource = new EventSource(streamUrl);

      eventSource.addEventListener('duplicate_detected', (e) => {
        const data = JSON.parse(e.data);
        eventSource.close();
        setLoading(false);
        setDuplicateWarning({
          title: data.title,
          articleId: data.article_id,
          created_at: data.created_at,
          updated_at: data.updated_at,
          url: data.url
        });
      });

      eventSource.addEventListener('fetch_start', () => {
        updateStep('fetch', { status: 'processing' });
      });

      eventSource.addEventListener('fetch_complete', () => {
        updateStep('fetch', { status: 'complete', detail: 'Article fetched successfully' });
      });

      eventSource.addEventListener('detecting_audio', (e) => {
        const data = JSON.parse(e.data);
        updateStep('content', {
          status: 'processing',
          detail: `Content type: Audio (${data.audio_count} file${data.audio_count > 1 ? 's' : ''})`
        });
      });

      eventSource.addEventListener('detecting_video', (e) => {
        const data = JSON.parse(e.data);
        updateStep('content', {
          status: 'processing',
          detail: `Content type: Video (${data.video_count} video${data.video_count > 1 ? 's' : ''})`
        });

        // Auto-complete after 1 second if still processing (for YouTube discovery path)
        setTimeout(() => {
          setSteps(prev => {
            const contentStep = prev.find(s => s.id === 'content');
            if (contentStep && contentStep.status === 'processing') {
              return prev.map(step => {
                if (step.id === 'content') {
                  return { ...step, status: 'complete', detail: 'Content ready', duration: 1 };
                }
                return step;
              });
            }
            return prev;
          });
        }, 1000);
      });

      eventSource.addEventListener('detecting_text_only', () => {
        updateStep('content', { status: 'complete', detail: 'Content type: Text-only' });
        updateStep('transcript', { status: 'processing' });
      });

      eventSource.addEventListener('processing_audio', (e) => {
        const data = JSON.parse(e.data);
        updateStep('content', { status: 'complete', detail: 'Media type: Audio' });
        updateStep('transcript', {
          status: 'processing',
          detail: `Processing audio ${data.audio_index} of ${data.total_audios}...`
        });
      });

      eventSource.addEventListener('downloading_audio', () => {
        // Auto-complete content extraction if it was skipped (e.g., direct YouTube URL)
        setSteps(prev => {
          const contentStep = prev.find(s => s.id === 'content');
          if (contentStep && (contentStep.status === 'pending' || contentStep.status === 'processing')) {
            // Content extraction was skipped or briefly processed, mark it as complete
            const duration = contentStep.startTime ? Math.max(1, Math.floor((Date.now() - contentStep.startTime) / 1000)) : 0;
            return prev.map(step => {
              if (step.id === 'content') {
                return { ...step, status: 'complete', detail: 'Content ready', duration };
              }
              return step;
            });
          }
          return prev;
        });

        updateStep('transcript', { status: 'processing', detail: 'Downloading audio file...' });
      });

      eventSource.addEventListener('transcribing_audio', (e) => {
        const data = JSON.parse(e.data);
        updateStep('transcript', {
          status: 'processing',
          detail: `Transcribing audio (${data.file_size_mb?.toFixed(1)}MB)...`
        });
      });

      eventSource.addEventListener('audio_chunking_required', (e) => {
        const data = JSON.parse(e.data);
        updateStep('transcript', {
          status: 'processing',
          detail: `Audio file is large (${data.file_size_mb?.toFixed(1)}MB), splitting into chunks...`
        });
      });

      eventSource.addEventListener('audio_split', (e) => {
        const data = JSON.parse(e.data);
        audioDurationRef.current = data.duration_minutes;
        updateStep('transcript', {
          status: 'processing',
          detail: `Split into ${data.total_chunks} chunks (${data.duration_minutes?.toFixed(1)} minutes)`,
          substeps: []
        });
      });

      eventSource.addEventListener('transcribing_chunk', (e) => {
        const data = JSON.parse(e.data);
        updateStep('transcript', {
          status: 'processing',
          detail: `Transcribing chunk ${data.current} of ${data.total}...`,
          substeps: [`Processing chunk ${data.current}/${data.total}`]
        });
      });

      eventSource.addEventListener('content_extracted', (e) => {
        const data = JSON.parse(e.data);
        const transcriptMethod = data.transcript_method;

        // Auto-complete content extraction if it was skipped (e.g., direct YouTube URL)
        setSteps(prev => {
          const contentStep = prev.find(s => s.id === 'content');
          if (contentStep && (contentStep.status === 'pending' || contentStep.status === 'processing')) {
            // Content extraction was skipped or briefly processed, mark it as complete
            const duration = contentStep.startTime ? Math.max(1, Math.floor((Date.now() - contentStep.startTime) / 1000)) : 0;
            return prev.map(step => {
              if (step.id === 'content') {
                return { ...step, status: 'complete', detail: 'Content ready', duration };
              }
              return step;
            });
          }
          return prev;
        });

        if (transcriptMethod === 'youtube') {
          const durationText = audioDurationRef.current ? ` (${audioDurationRef.current.toFixed(1)} min)` : '';
          updateStep('transcript', {
            status: 'complete',
            detail: `Extracted transcript from YouTube${durationText}`
          });
        } else if (transcriptMethod === 'chunked' || transcriptMethod === 'audio') {
          const durationText = audioDurationRef.current ? ` (${audioDurationRef.current.toFixed(1)} min)` : '';
          updateStep('transcript', {
            status: 'complete',
            detail: `Transcribed audio${durationText}`
          });
        } else {
          updateStep('transcript', {
            status: 'skipped',
            detail: 'No audio/video found'
          });
        }
      });

      eventSource.addEventListener('ai_start', () => {
        updateStep('ai', { status: 'processing' });
      });

      eventSource.addEventListener('ai_complete', () => {
        updateStep('ai', { status: 'complete', detail: 'Summary generated by Claude' });
      });

      eventSource.addEventListener('save_start', () => {
        updateStep('save', { status: 'processing' });
      });

      eventSource.addEventListener('save_complete', () => {
        updateStep('save', { status: 'complete', detail: 'Article saved to Supabase' });
      });

      eventSource.addEventListener('completed', (e) => {
        const data = JSON.parse(e.data);

        // Determine message based on whether article was already processed
        const message = data.already_processed
          ? data.message || 'Article added to your library!'
          : 'Article processed successfully!';

        setResult({
          status: 'success',
          message: message,
          articleId: data.article_id
        });
        setUrl('');
        setLoading(false);
        eventSource.close();
      });

      eventSource.addEventListener('error', (e: any) => {
        let message = 'Processing failed';
        try {
          if (e.data) {
            const data = JSON.parse(e.data);
            message = data.message || message;
          }
        } catch (parseError) {
          console.error('Error parsing error event data:', parseError);
        }
        setResult({
          status: 'error',
          message: message
        });
        setLoading(false);
        eventSource.close();
      });

      eventSource.onerror = () => {
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

  if (authLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-600">Loading...</div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

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

          <form ref={formRef} onSubmit={handleSubmit} className="space-y-6">
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

            <div className="flex items-center">
              <input
                type="checkbox"
                id="demoVideo"
                checked={isDemoVideo}
                onChange={(e) => setIsDemoVideo(e.target.checked)}
                disabled={loading}
                className="h-4 w-4 text-[#077331] focus:ring-[#077331] border-gray-300 rounded"
              />
              <label htmlFor="demoVideo" className="ml-2 block text-sm text-gray-700">
                Process as Demo Video (extract screen snapshots every 30 seconds)
              </label>
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

          {duplicateWarning && (
            <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
              <div className="flex items-start gap-3">
                <svg className="h-6 w-6 text-yellow-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                <div className="flex-1">
                  <h3 className="text-sm font-semibold text-yellow-800 mb-2">Article already exists!</h3>
                  <div className="text-sm text-yellow-700 space-y-1 mb-3">
                    <p><span className="font-medium">Title:</span> {duplicateWarning.title}</p>
                    <p><span className="font-medium">ID:</span> {duplicateWarning.articleId}</p>
                    <p><span className="font-medium">Created:</span> {new Date(duplicateWarning.created_at).toLocaleString()}</p>
                    <p className="mt-2 text-yellow-600">
                      <a
                        href={duplicateWarning.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="underline hover:text-yellow-800"
                      >
                        View existing article →
                      </a>
                    </p>
                  </div>
                  <p className="text-sm text-yellow-700 mb-4">
                    Reprocessing will cost API calls for transcription + AI summary.
                  </p>
                  <div className="flex gap-3">
                    <button
                      onClick={() => setDuplicateWarning(null)}
                      className="px-4 py-2 text-sm font-medium text-yellow-700 bg-white border border-yellow-300 rounded-md hover:bg-yellow-50 transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={(e) => {
                        setDuplicateWarning(null);
                        handleSubmit(e as any, true);
                      }}
                      className="px-4 py-2 text-sm font-medium text-white bg-yellow-600 rounded-md hover:bg-yellow-700 transition-colors"
                    >
                      Continue Anyway
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {steps.length > 0 && !duplicateWarning && (
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
                      {(step.status === 'processing' || step.status === 'complete' || step.status === 'skipped') && step.duration !== undefined && (
                        <span className="text-xs text-gray-400 ml-2">
                          ({step.duration}s)
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

export default function AdminPageClient() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-600">Loading...</div>
      </div>
    }>
      <AdminPageContent />
    </Suspense>
  );
}
