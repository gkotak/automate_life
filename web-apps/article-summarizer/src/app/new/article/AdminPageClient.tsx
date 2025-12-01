'use client';

import { useState, useEffect, useRef, Suspense } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter, useSearchParams } from 'next/navigation';
import { supabase, supabaseUrl } from '@/lib/supabase';
import * as tus from 'tus-js-client';

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
  const [inputMode, setInputMode] = useState<'url' | 'file'>('url');
  const [url, setUrl] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [isDemoVideo, setIsDemoVideo] = useState(false);
  const [detectedPrivacy, setDetectedPrivacy] = useState<boolean | null>(null);
  const [steps, setSteps] = useState<ProcessingStep[]>([]);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [result, setResult] = useState<{
    status: 'success' | 'error' | 'info';
    message: string;
    articleId?: number;
    articleUrl?: string;
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

  const initializeSteps = (isFileUpload: boolean = false) => {
    const initialSteps: ProcessingStep[] = [
      {
        id: 'fetch',
        label: isFileUpload ? 'Uploading file' : 'Fetching article',
        status: 'pending'
      },
      { id: 'content', label: 'Extracting content', status: 'pending' },
      { id: 'transcript', label: 'Downloading media and processing transcript', status: 'pending', substeps: [] },
      { id: 'ai', label: 'Generating AI summary', status: 'pending' },
      { id: 'save', label: 'Saving to database', status: 'pending' },
    ];
    setSteps(initialSteps);
  };

  const handleSubmit = async (e: React.FormEvent, forceReprocess: boolean = false) => {
    e.preventDefault();

    // Validate input based on mode
    if (inputMode === 'url' && !url.trim()) {
      setResult({
        status: 'error',
        message: 'Please enter a URL'
      });
      return;
    }

    if (inputMode === 'file' && !selectedFile) {
      setResult({
        status: 'error',
        message: 'Please select a file'
      });
      return;
    }

    setLoading(true);
    setResult(null);
    setDuplicateWarning(null);
    setDetectedPrivacy(null);
    audioDurationRef.current = null;
    setUploadProgress(0);

    const isFileUpload = inputMode === 'file' && selectedFile;
    initializeSteps(isFileUpload);

    try {
      // Get auth token from Supabase
      const { data: { session } } = await supabase.auth.getSession();

      if (!session?.access_token) {
        throw new Error('Not authenticated. Please sign in again.');
      }

      let processUrl = url.trim();

      // If file upload mode, upload directly to Supabase using TUS protocol
      if (isFileUpload) {
        updateStep('fetch', { status: 'processing', detail: 'Uploading to cloud storage...' });

        // Generate storage path: user_{user_id}/{timestamp}_{filename}
        const timestamp = Math.floor(Date.now() / 1000);
        const fileExt = selectedFile.name.split('.').pop() || '';
        const safeName = selectedFile.name.replace(/\.[^/.]+$/, '').replace(/[^a-zA-Z0-9_-]/g, '_');
        const storagePath = `user_${user?.id}/${timestamp}_${safeName}.${fileExt}`;
        const bucketName = 'uploaded-media';

        // Upload using TUS protocol with progress tracking
        const uploadPromise = new Promise<string>((resolve, reject) => {
          const upload = new tus.Upload(selectedFile, {
            endpoint: `${supabaseUrl}/storage/v1/upload/resumable`,
            retryDelays: [0, 3000, 5000, 10000, 20000],
            headers: {
              authorization: `Bearer ${session.access_token}`,
              'x-upsert': 'true',
            },
            uploadDataDuringCreation: true,
            removeFingerprintOnSuccess: true,
            metadata: {
              bucketName: bucketName,
              objectName: storagePath,
              contentType: selectedFile.type || 'application/octet-stream',
              cacheControl: '3600',
            },
            chunkSize: 6 * 1024 * 1024, // 6MB chunks
            onError: (error) => {
              console.error('TUS upload error:', error);
              reject(new Error(`Upload failed: ${error.message}`));
            },
            onProgress: (bytesUploaded, bytesTotal) => {
              const percentage = Math.round((bytesUploaded / bytesTotal) * 100);
              setUploadProgress(percentage);
            },
            onSuccess: () => {
              // Construct the public URL
              const publicUrl = `${supabaseUrl}/storage/v1/object/public/${bucketName}/${storagePath}`;
              resolve(publicUrl);
            },
          });

          // Start the upload
          upload.start();
        });

        processUrl = await uploadPromise;
        setUploadProgress(100);
        updateStep('fetch', { status: 'complete', detail: `Uploaded ${selectedFile.name} to cloud storage` });

        // Hide progress bar after upload completes
        setTimeout(() => setUploadProgress(-1), 500);
      }

      const encodedUrl = encodeURIComponent(processUrl);
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

      // Listen for privacy detection event (auto-detected by backend)
      eventSource.addEventListener('privacy_detected', (e) => {
        const data = JSON.parse(e.data);
        setDetectedPrivacy(data.is_private);
      });

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
        // Auto-complete transcript step if it's still processing (defensive fallback)
        setSteps(prev => {
          const transcriptStep = prev.find(s => s.id === 'transcript');
          if (transcriptStep && transcriptStep.status === 'processing') {
            // Transcript processing didn't complete properly, mark it complete now
            const duration = transcriptStep.startTime ? Math.max(1, Math.floor((Date.now() - transcriptStep.startTime) / 1000)) : 0;
            const durationText = audioDurationRef.current ? ` (${audioDurationRef.current.toFixed(1)} min)` : '';
            return prev.map(step => {
              if (step.id === 'transcript') {
                return { ...step, status: 'complete', detail: `Transcribed media${durationText}`, duration };
              }
              return step;
            });
          }
          return prev;
        });

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
          articleId: data.article_id,
          articleUrl: data.url  // Use the URL from backend which is already correct
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
            {/* URL Input */}
            {inputMode === 'url' && (
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
                <div className="mt-2">
                  <button
                    type="button"
                    onClick={() => {
                      setInputMode('file');
                      setUrl('');
                    }}
                    disabled={loading}
                    className="text-sm text-[#077331] hover:text-[#055a24] underline disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Upload file instead
                  </button>
                </div>
              </div>
            )}

            {/* File Upload Input */}
            {inputMode === 'file' && (
              <div>
                <label htmlFor="file" className="block text-sm font-medium text-gray-700 mb-2">
                  Upload Video or Audio File
                </label>
                <div className="mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-gray-300 border-dashed rounded-lg hover:border-[#077331] transition-colors">
                  <div className="space-y-1 text-center w-full">
                    {!selectedFile ? (
                      <>
                        <svg
                          className="mx-auto h-12 w-12 text-gray-400"
                          stroke="currentColor"
                          fill="none"
                          viewBox="0 0 48 48"
                          aria-hidden="true"
                        >
                          <path
                            d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                            strokeWidth={2}
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </svg>
                        <div className="flex justify-center text-sm text-gray-600">
                          <label
                            htmlFor="file"
                            className="relative cursor-pointer bg-white rounded-md font-medium text-[#077331] hover:text-[#055a24] focus-within:outline-none focus-within:ring-2 focus-within:ring-offset-2 focus-within:ring-[#077331]"
                          >
                            <span>Upload a file</span>
                            <input
                              id="file"
                              name="file"
                              type="file"
                              className="sr-only"
                              accept="video/*,audio/*,.mp4,.mov,.avi,.mkv,.webm,.mp3,.wav,.m4a,.aac,.ogg,.flac,.pdf,application/pdf"
                              onChange={(e) => {
                                const file = e.target.files?.[0];
                                if (file) {
                                  const MAX_FILE_SIZE_MB = 100;
                                  const fileSizeMB = file.size / (1024 * 1024);
                                  if (fileSizeMB > MAX_FILE_SIZE_MB) {
                                    setResult({
                                      status: 'error',
                                      message: 'Files greater than 100 MB cannot be uploaded. Please host it elsewhere and paste the URL instead.'
                                    });
                                    e.target.value = '';
                                    return;
                                  }
                                  setSelectedFile(file);
                                }
                              }}
                              disabled={loading}
                            />
                          </label>
                          <p className="pl-1">or drag and drop</p>
                        </div>
                        <p className="text-xs text-gray-500 text-center">
                          Video: MP4, MOV, AVI, MKV, WebM
                          <br />
                          Audio: MP3, WAV, M4A, AAC, OGG, FLAC
                          <br />
                          Document: PDF
                        </p>
                      </>
                    ) : (
                      <div className="py-6">
                        <div className="flex items-center justify-between bg-gray-50 rounded-lg px-4 py-3 max-w-md mx-auto">
                          <div className="flex items-center gap-3 flex-1 min-w-0">
                            {/* File icon */}
                            <div className="flex-shrink-0">
                              <svg className="h-10 w-10 text-[#077331]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                              </svg>
                            </div>
                            {/* File info */}
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-semibold text-gray-900 truncate">
                                {selectedFile.name}
                              </p>
                              <p className="text-xs text-gray-500 mt-0.5">
                                {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                              </p>
                            </div>
                          </div>
                          {/* Remove button */}
                          <button
                            type="button"
                            onClick={() => {
                              setSelectedFile(null);
                              // Reset the file input
                              const fileInput = document.getElementById('file') as HTMLInputElement;
                              if (fileInput) fileInput.value = '';
                            }}
                            disabled={loading}
                            className="flex-shrink-0 ml-3 p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            title="Remove file"
                          >
                            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
                <div className="mt-2">
                  <button
                    type="button"
                    onClick={() => {
                      setInputMode('url');
                      setSelectedFile(null);
                    }}
                    disabled={loading}
                    className="text-sm text-[#077331] hover:text-[#055a24] underline disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Enter URL instead
                  </button>
                </div>
              </div>
            )}

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
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-medium text-gray-700">Processing Status</h3>
                {detectedPrivacy !== null && (
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    detectedPrivacy
                      ? 'bg-amber-100 text-amber-800'
                      : 'bg-blue-100 text-blue-800'
                  }`}>
                    {detectedPrivacy ? (
                      <>
                        <svg className="mr-1 h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
                        </svg>
                        Private
                      </>
                    ) : (
                      <>
                        <svg className="mr-1 h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM4.332 8.027a6.012 6.012 0 011.912-2.706C6.512 5.73 6.974 6 7.5 6A1.5 1.5 0 019 7.5V8a2 2 0 004 0 2 2 0 011.523-1.943A5.977 5.977 0 0116 10c0 .34-.028.675-.083 1H15a2 2 0 00-2 2v2.197A5.973 5.973 0 0110 16v-2a2 2 0 00-2-2 2 2 0 01-2-2 2 2 0 00-1.668-1.973z" clipRule="evenodd" />
                        </svg>
                        Public
                      </>
                    )}
                  </span>
                )}
              </div>
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
                    {/* Upload progress bar - show only during active file upload */}
                    {step.id === 'fetch' && step.status === 'processing' && inputMode === 'file' && uploadProgress > 0 && uploadProgress <= 100 && (
                      <div className="mt-2">
                        <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                          <span>Uploading to cloud storage...</span>
                          <span>{uploadProgress}%</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-[#077331] h-2 rounded-full transition-all duration-300"
                            style={{ width: `${uploadProgress}%` }}
                          ></div>
                        </div>
                      </div>
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
                      href={result.articleUrl || `/article/${result.articleId}`}
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
