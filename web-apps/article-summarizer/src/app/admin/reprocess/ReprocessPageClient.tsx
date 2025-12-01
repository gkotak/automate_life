'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Article {
  id: number;
  title: string;
  url: string;
  content_source: string;
  created_at: string;
  updated_at: string;
}

interface ArticleReprocessInfo {
  article_id: number;
  title: string;
  url: string;
  is_private: boolean;
  has_transcript: boolean;
  has_video_frames: boolean;
  has_embedding: boolean;
  has_themed_insights: boolean;
  content_source: string;
  available_operations: string[];
  unavailable_operations: Record<string, string>;
  // Phase 2: Media storage info
  has_stored_media?: boolean;
  media_storage_bucket?: string;
  media_size_mb?: number;
  media_days_remaining?: number;
  media_is_permanent?: boolean;
}

interface ReprocessStep {
  id: string;
  label: string;
  checked: boolean;
  disabled: boolean;
  reason?: string;
}

interface ProcessingEvent {
  type: string;
  message?: string;
  step?: string;
  success?: boolean;
  error?: string;
}

export default function ReprocessPageClient() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();

  // State
  const [isPrivate, setIsPrivate] = useState(false);
  const [articles, setArticles] = useState<Article[]>([]);
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);
  const [articleInfo, setArticleInfo] = useState<ArticleReprocessInfo | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingArticles, setLoadingArticles] = useState(false);
  const [loadingInfo, setLoadingInfo] = useState(false);
  const [steps, setSteps] = useState<ReprocessStep[]>([]);
  const [processingEvents, setProcessingEvents] = useState<ProcessingEvent[]>([]);
  const [result, setResult] = useState<{
    status: 'success' | 'error' | 'partial';
    message: string;
    articleUrl?: string;
  } | null>(null);

  // Auth check
  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
    }
  }, [user, authLoading, router]);

  // Fetch articles when isPrivate or searchQuery changes
  useEffect(() => {
    if (user) {
      fetchArticles();
    }
  }, [user, isPrivate, searchQuery]);

  // Fetch article info when selection changes
  useEffect(() => {
    if (selectedArticle) {
      fetchArticleInfo(selectedArticle.id);
    } else {
      setArticleInfo(null);
      setSteps([]);
    }
  }, [selectedArticle, isPrivate]);

  const fetchArticles = async () => {
    if (!user) return;

    setLoadingArticles(true);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) return;

      const params = new URLSearchParams({
        is_private: isPrivate.toString(),
        limit: '50',
        token: session.access_token
      });

      if (searchQuery) {
        params.append('search', searchQuery);
      }

      const response = await fetch(`${API_URL}/api/reprocess/list?${params}`);
      if (!response.ok) throw new Error('Failed to fetch articles');

      const data = await response.json();
      setArticles(data.articles || []);
    } catch (error) {
      console.error('Error fetching articles:', error);
      setArticles([]);
    } finally {
      setLoadingArticles(false);
    }
  };

  const fetchArticleInfo = async (articleId: number) => {
    if (!user) return;

    setLoadingInfo(true);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) return;

      const params = new URLSearchParams({
        article_id: articleId.toString(),
        is_private: isPrivate.toString(),
        token: session.access_token
      });

      const response = await fetch(`${API_URL}/api/reprocess/info?${params}`);
      if (!response.ok) throw new Error('Failed to fetch article info');

      const info: ArticleReprocessInfo = await response.json();
      setArticleInfo(info);

      // Initialize steps based on available operations
      const newSteps: ReprocessStep[] = [
        // Phase 1 operations
        {
          id: 'ai_summary',
          label: 'Regenerate AI Summary',
          checked: info.available_operations.includes('ai_summary'),
          disabled: !info.available_operations.includes('ai_summary'),
          reason: info.unavailable_operations['ai_summary']
        },
        {
          id: 'themed_insights',
          label: 'Regenerate Themed Insights',
          checked: false,
          disabled: !info.available_operations.includes('themed_insights'),
          reason: info.unavailable_operations['themed_insights']
        },
        {
          id: 'embedding',
          label: 'Regenerate Embedding',
          checked: false,
          disabled: !info.available_operations.includes('embedding'),
          reason: info.unavailable_operations['embedding']
        },
        // Phase 2 operations (require stored media)
        {
          id: 'video_frames',
          label: 'Re-extract Video Frames',
          checked: false,
          disabled: !info.available_operations.includes('video_frames'),
          reason: info.unavailable_operations['video_frames']
        },
        {
          id: 'transcript',
          label: 'Regenerate Transcript (Deepgram)',
          checked: false,
          disabled: !info.available_operations.includes('transcript'),
          reason: info.unavailable_operations['transcript']
        }
      ];
      setSteps(newSteps);
    } catch (error) {
      console.error('Error fetching article info:', error);
      setArticleInfo(null);
      setSteps([]);
    } finally {
      setLoadingInfo(false);
    }
  };

  const toggleStep = (stepId: string) => {
    setSteps(prev => prev.map(step =>
      step.id === stepId && !step.disabled
        ? { ...step, checked: !step.checked }
        : step
    ));
  };

  const handleReprocess = async () => {
    if (!selectedArticle || !user) return;

    const selectedSteps = steps.filter(s => s.checked).map(s => s.id);
    if (selectedSteps.length === 0) {
      setResult({
        status: 'error',
        message: 'Please select at least one operation'
      });
      return;
    }

    setLoading(true);
    setResult(null);
    setProcessingEvents([]);

    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) {
        throw new Error('Not authenticated');
      }

      // Build request body
      const requestBody = {
        article_id: selectedArticle.id,
        is_private: isPrivate,
        steps: selectedSteps
      };

      // Use fetch with SSE for streaming
      const response = await fetch(
        `${API_URL}/api/reprocess/run?token=${encodeURIComponent(session.access_token)}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(requestBody)
        }
      );

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      // Read the SSE stream
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (reader) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data:')) {
            try {
              const data = JSON.parse(line.slice(5).trim());
              handleSSEEvent(data);
            } catch (e) {
              // Ignore parse errors
            }
          }
        }
      }
    } catch (error) {
      console.error('Reprocess error:', error);
      setResult({
        status: 'error',
        message: error instanceof Error ? error.message : 'Failed to reprocess article'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSSEEvent = (data: any) => {
    // Handle different event types based on the data content
    if (data.error) {
      setProcessingEvents(prev => [...prev, {
        type: 'error',
        error: data.error
      }]);
      setResult({
        status: 'error',
        message: data.error
      });
      return;
    }

    if (data.step) {
      // Step-related event
      if (data.success !== undefined) {
        // Step complete
        setProcessingEvents(prev => [...prev, {
          type: 'step_complete',
          step: data.step,
          success: data.success,
          message: data.message
        }]);
      } else if (data.reason) {
        // Step skipped
        setProcessingEvents(prev => [...prev, {
          type: 'step_skipped',
          step: data.step,
          message: data.reason
        }]);
      } else {
        // Step started
        setProcessingEvents(prev => [...prev, {
          type: 'step_start',
          step: data.step,
          message: data.message
        }]);
      }
    }

    if (data.article_id && data.all_success !== undefined) {
      // Completion event
      const articleUrl = data.url;
      if (data.all_success) {
        setResult({
          status: 'success',
          message: 'All operations completed successfully!',
          articleUrl
        });
      } else if (data.any_success) {
        setResult({
          status: 'partial',
          message: 'Some operations completed with errors',
          articleUrl
        });
      } else {
        setResult({
          status: 'error',
          message: 'All operations failed'
        });
      }
    }
  };

  if (authLoading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-gray-400">Loading...</div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100">
      <div className="max-w-4xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold mb-6">Reprocess Articles</h1>

        {/* Article Type Toggle */}
        <div className="mb-6">
          <div className="flex items-center space-x-4">
            <label className="flex items-center cursor-pointer">
              <input
                type="radio"
                name="articleType"
                checked={!isPrivate}
                onChange={() => {
                  setIsPrivate(false);
                  setSelectedArticle(null);
                }}
                className="mr-2"
              />
              <span>Public Articles</span>
            </label>
            <label className="flex items-center cursor-pointer">
              <input
                type="radio"
                name="articleType"
                checked={isPrivate}
                onChange={() => {
                  setIsPrivate(true);
                  setSelectedArticle(null);
                }}
                className="mr-2"
              />
              <span>Private Articles</span>
            </label>
          </div>
        </div>

        {/* Search */}
        <div className="mb-6">
          <input
            type="text"
            placeholder="Search articles by title..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Article List */}
          <div className="bg-gray-800 rounded-lg p-4">
            <h2 className="text-lg font-semibold mb-4">Select Article</h2>
            {loadingArticles ? (
              <div className="text-gray-400 text-center py-8">Loading articles...</div>
            ) : articles.length === 0 ? (
              <div className="text-gray-400 text-center py-8">No articles found</div>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {articles.map((article) => (
                  <div
                    key={article.id}
                    onClick={() => setSelectedArticle(article)}
                    className={`p-3 rounded-lg cursor-pointer transition-colors ${
                      selectedArticle?.id === article.id
                        ? 'bg-blue-600'
                        : 'bg-gray-700 hover:bg-gray-600'
                    }`}
                  >
                    <div className="font-medium truncate">{article.title}</div>
                    <div className="text-sm text-gray-400 flex items-center gap-2 mt-1">
                      <span className="px-2 py-0.5 bg-gray-600 rounded text-xs">
                        {article.content_source}
                      </span>
                      <span className="truncate">{new URL(article.url).hostname}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Reprocess Options */}
          <div className="bg-gray-800 rounded-lg p-4">
            <h2 className="text-lg font-semibold mb-4">Reprocess Options</h2>

            {!selectedArticle ? (
              <div className="text-gray-400 text-center py-8">
                Select an article to see options
              </div>
            ) : loadingInfo ? (
              <div className="text-gray-400 text-center py-8">Loading article info...</div>
            ) : articleInfo ? (
              <div className="space-y-4">
                {/* Article Info */}
                <div className="bg-gray-700 rounded-lg p-3">
                  <div className="font-medium">{articleInfo.title}</div>
                  <div className="text-sm text-gray-400 mt-1">
                    <div>Content: {articleInfo.content_source}</div>
                    <div>Has transcript: {articleInfo.has_transcript ? 'Yes' : 'No'}</div>
                    <div>Has embedding: {articleInfo.has_embedding ? 'Yes' : 'No'}</div>
                    {isPrivate && (
                      <div>Has themed insights: {articleInfo.has_themed_insights ? 'Yes' : 'No'}</div>
                    )}
                  </div>
                </div>

                {/* Media Storage Status (Phase 2) */}
                {articleInfo.content_source !== 'article' && (
                  <div className={`rounded-lg p-3 ${
                    articleInfo.has_stored_media
                      ? 'bg-green-900/30 border border-green-700/50'
                      : 'bg-yellow-900/30 border border-yellow-700/50'
                  }`}>
                    <div className="flex items-center gap-2">
                      {articleInfo.has_stored_media ? (
                        <>
                          <span className="text-green-400 text-sm font-medium">Media Stored</span>
                          {articleInfo.media_size_mb && (
                            <span className="text-gray-400 text-sm">({articleInfo.media_size_mb} MB)</span>
                          )}
                        </>
                      ) : (
                        <span className="text-yellow-400 text-sm font-medium">No Stored Media</span>
                      )}
                    </div>
                    {articleInfo.has_stored_media && (
                      <div className="text-xs text-gray-400 mt-1">
                        {articleInfo.media_is_permanent ? (
                          <span className="text-blue-400">Permanent (direct upload)</span>
                        ) : articleInfo.media_days_remaining !== undefined ? (
                          <span>Expires in {articleInfo.media_days_remaining} days</span>
                        ) : (
                          <span>TTL media</span>
                        )}
                      </div>
                    )}
                    {!articleInfo.has_stored_media && (
                      <div className="text-xs text-gray-400 mt-1">
                        Re-process article to enable video frame extraction and transcript regeneration
                      </div>
                    )}
                  </div>
                )}

                {/* Step Checkboxes */}
                <div className="space-y-3">
                  {steps.map((step) => (
                    <label
                      key={step.id}
                      className={`flex items-start gap-3 p-3 rounded-lg ${
                        step.disabled
                          ? 'bg-gray-700/50 cursor-not-allowed'
                          : 'bg-gray-700 cursor-pointer hover:bg-gray-600'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={step.checked}
                        onChange={() => toggleStep(step.id)}
                        disabled={step.disabled}
                        className="mt-1"
                      />
                      <div className="flex-1">
                        <div className={step.disabled ? 'text-gray-500' : ''}>
                          {step.label}
                        </div>
                        {step.reason && (
                          <div className="text-sm text-yellow-500 mt-1">
                            {step.reason}
                          </div>
                        )}
                      </div>
                    </label>
                  ))}
                </div>

                {/* Reprocess Button */}
                <button
                  onClick={handleReprocess}
                  disabled={loading || steps.filter(s => s.checked).length === 0}
                  className={`w-full py-3 rounded-lg font-medium transition-colors ${
                    loading || steps.filter(s => s.checked).length === 0
                      ? 'bg-gray-600 cursor-not-allowed'
                      : 'bg-blue-600 hover:bg-blue-700'
                  }`}
                >
                  {loading ? 'Processing...' : 'Reprocess Article'}
                </button>
              </div>
            ) : (
              <div className="text-gray-400 text-center py-8">
                Failed to load article info
              </div>
            )}
          </div>
        </div>

        {/* Processing Events */}
        {processingEvents.length > 0 && (
          <div className="mt-6 bg-gray-800 rounded-lg p-4">
            <h3 className="text-lg font-semibold mb-3">Processing Log</h3>
            <div className="space-y-2 font-mono text-sm">
              {processingEvents.map((event, i) => (
                <div
                  key={i}
                  className={`${
                    event.type === 'error' || (event.type === 'step_complete' && !event.success)
                      ? 'text-red-400'
                      : event.type === 'step_complete' && event.success
                      ? 'text-green-400'
                      : event.type === 'step_skipped'
                      ? 'text-yellow-400'
                      : 'text-gray-300'
                  }`}
                >
                  {event.step && <span className="text-blue-400">[{event.step}]</span>}{' '}
                  {event.message || event.error}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Result */}
        {result && (
          <div
            className={`mt-6 p-4 rounded-lg ${
              result.status === 'success'
                ? 'bg-green-900/50 border border-green-700'
                : result.status === 'partial'
                ? 'bg-yellow-900/50 border border-yellow-700'
                : 'bg-red-900/50 border border-red-700'
            }`}
          >
            <div className="font-medium">{result.message}</div>
            {result.articleUrl && (
              <a
                href={result.articleUrl}
                className="text-blue-400 hover:underline mt-2 inline-block"
              >
                View Article &rarr;
              </a>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
