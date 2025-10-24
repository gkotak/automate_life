'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';

// API configuration from environment variables
const CONTENT_CHECKER_API_URL = process.env.NEXT_PUBLIC_CONTENT_CHECKER_API_URL || 'http://localhost:8001';
const CONTENT_CHECKER_API_KEY = process.env.NEXT_PUBLIC_CONTENT_CHECKER_API_KEY || '';

interface PodcastEpisode {
  id: string;
  episode_title: string;
  podcast_title: string;
  episode_url: string;
  podcast_video_url: string | null;
  progress_percent: number | null;
  published_date: string | null;
  found_at: string | null;
  status: string;
  is_new: boolean;
  duration_seconds: number | null;
}

type SortField = 'title' | 'published_date' | 'found_at' | 'duration_seconds' | 'status';
type SortDirection = 'asc' | 'desc';

export default function PodcastsAdminPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [podcasts, setPodcasts] = useState<PodcastEpisode[]>([]);
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(false);
  const [message, setMessage] = useState<{
    type: 'success' | 'error' | 'info';
    text: string;
  } | null>(null);
  const [newlyDiscoveredIds, setNewlyDiscoveredIds] = useState<Set<string>>(new Set());
  const [currentPage, setCurrentPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const itemsPerPage = 25;
  const [sortField, setSortField] = useState<SortField>('found_at');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  // Protect this page - redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
    }
  }, [user, authLoading, router]);

  // Load podcasts on mount
  useEffect(() => {
    if (user) {
      loadPodcasts();
    }
  }, [user]);

  const loadPodcasts = async (silent: boolean = false) => {
    if (!silent) {
      setLoading(true);
    }

    try {
      const headers: HeadersInit = {};
      if (CONTENT_CHECKER_API_KEY) {
        headers['X-API-Key'] = CONTENT_CHECKER_API_KEY;
      }

      const response = await fetch(
        `${CONTENT_CHECKER_API_URL}/api/podcasts/discovered?limit=200`,
        { headers }
      );

      if (!response.ok) {
        throw new Error('Failed to load podcasts');
      }

      const data = await response.json();
      setPodcasts(data.podcasts);
      setTotalCount(data.total);

      // Don't show message when just loading from database
    } catch (error) {
      console.error('Error loading podcasts:', error);
      if (!silent) {
        setMessage({
          type: 'error',
          text: error instanceof Error ? error.message : 'Failed to load podcasts'
        });
      }
    } finally {
      if (!silent) {
        setLoading(false);
      }
    }
  };

  const checkNewPodcasts = async () => {
    setChecking(true);
    setMessage(null);

    try {
      const headers: HeadersInit = {
        'Content-Type': 'application/json'
      };
      if (CONTENT_CHECKER_API_KEY) {
        headers['X-API-Key'] = CONTENT_CHECKER_API_KEY;
      }

      const response = await fetch(
        `${CONTENT_CHECKER_API_URL}/api/podcasts/check`,
        {
          method: 'POST',
          headers
        }
      );

      if (!response.ok) {
        throw new Error('Failed to check podcasts');
      }

      const data = await response.json();

      // Track newly discovered IDs
      if (data.newly_discovered_ids && data.newly_discovered_ids.length > 0) {
        setNewlyDiscoveredIds(new Set(data.newly_discovered_ids));
      }

      setMessage({
        type: 'success',
        text: data.message
      });

      // Refresh the podcast list
      await loadPodcasts(true);
    } catch (error) {
      console.error('Error checking podcasts:', error);
      setMessage({
        type: 'error',
        text: error instanceof Error ? error.message : 'Failed to check podcasts'
      });
    } finally {
      setChecking(false);
    }
  };

  const handleProcess = (podcast: PodcastEpisode) => {
    // Redirect to existing admin page with URL parameter
    const url = podcast.podcast_video_url || podcast.episode_url;
    router.push(`/admin?url=${encodeURIComponent(url)}`);
  };

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      // Toggle direction if clicking the same column
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      // Set new field with default descending for dates, ascending for others
      setSortField(field);
      setSortDirection(field === 'published_date' || field === 'found_at' ? 'desc' : 'asc');
    }
  };

  const sortPodcasts = (podcastsList: PodcastEpisode[]) => {
    return [...podcastsList].sort((a, b) => {
      let aValue: any;
      let bValue: any;

      switch (sortField) {
        case 'title':
          aValue = a.episode_title.toLowerCase();
          bValue = b.episode_title.toLowerCase();
          break;
        case 'published_date':
          aValue = a.published_date ? new Date(a.published_date).getTime() : 0;
          bValue = b.published_date ? new Date(b.published_date).getTime() : 0;
          break;
        case 'found_at':
          aValue = a.found_at ? new Date(a.found_at).getTime() : 0;
          bValue = b.found_at ? new Date(b.found_at).getTime() : 0;
          break;
        case 'duration_seconds':
          aValue = a.duration_seconds || 0;
          bValue = b.duration_seconds || 0;
          break;
        case 'status':
          aValue = a.status.toLowerCase();
          bValue = b.status.toLowerCase();
          break;
        default:
          return 0;
      }

      if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'N/A';
    try {
      return new Date(dateStr).toLocaleDateString('en-US', {
        month: '2-digit',
        day: '2-digit',
        year: 'numeric'
      });
    } catch {
      return 'Invalid date';
    }
  };

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return 'N/A';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes} min`;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'discovered':
        return 'bg-blue-100 text-blue-800';
      case 'processing':
        return 'bg-yellow-100 text-yellow-800';
      case 'processed':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  // Sort and paginate
  const sortedPodcasts = sortPodcasts(podcasts);
  const totalPages = Math.ceil(sortedPodcasts.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const paginatedPodcasts = sortedPodcasts.slice(startIndex, endIndex);

  const goToPage = (page: number) => {
    setCurrentPage(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Sortable column header component
  const SortableHeader = ({ field, label, className = "" }: { field: SortField; label: string; className?: string }) => (
    <th
      scope="col"
      className={`px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors ${className}`}
      onClick={() => handleSort(field)}
    >
      <div className="flex items-center gap-1">
        {label}
        {sortField === field && (
          <span className="text-[#077331]">
            {sortDirection === 'asc' ? '↑' : '↓'}
          </span>
        )}
      </div>
    </th>
  );

  // Show loading while checking auth
  if (authLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-600">Loading...</div>
      </div>
    );
  }

  // Don't render if not authenticated (will redirect)
  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        <div className="bg-white rounded-lg shadow-md p-8">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Podcast Discovery
            </h1>
            <p className="text-gray-600">
              Check PocketCasts for new podcast episodes and process them
            </p>
          </div>

          {/* Actions */}
          <div className="mb-6">
            <button
              onClick={checkNewPodcasts}
              disabled={checking}
              className={`px-6 py-3 rounded-lg font-medium text-white transition-colors ${
                checking
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-[#077331] hover:bg-[#055a24]'
              }`}
            >
              {checking ? (
                <span className="flex items-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Checking...
                </span>
              ) : (
                'Check for New Podcasts'
              )}
            </button>
          </div>

          {/* Message */}
          {message && (
            <div
              className={`mb-6 p-4 rounded-lg ${
                message.type === 'success'
                  ? 'bg-green-50 text-green-800 border border-green-200'
                  : message.type === 'error'
                  ? 'bg-red-50 text-red-800 border border-red-200'
                  : 'bg-blue-50 text-blue-800 border border-blue-200'
              }`}
            >
              {message.text}
            </div>
          )}

          {/* Podcasts Table */}
          {loading ? (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-[#077331]"></div>
              <p className="mt-4 text-gray-600">Loading podcasts...</p>
            </div>
          ) : podcasts.length === 0 ? (
            <div className="text-center py-12">
              <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
              </svg>
              <p className="mt-4 text-gray-600">No discovered podcasts found</p>
              <button
                onClick={checkNewPodcasts}
                className="mt-4 px-4 py-2 bg-[#077331] text-white rounded-lg hover:bg-[#055a24] transition-colors"
              >
                Check for Podcasts
              </button>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto border border-gray-200 rounded-lg">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <SortableHeader field="title" label="Title" className="w-[45%]" />
                      <SortableHeader field="published_date" label="Release Date" />
                      <SortableHeader field="found_at" label="Listened Date" />
                      <SortableHeader field="duration_seconds" label="Duration" />
                      <SortableHeader field="status" label="Status" />
                      <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Action
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {paginatedPodcasts.map((podcast) => {
                      const isNew = podcast.is_new || newlyDiscoveredIds.has(podcast.id);
                      const truncatedTitle = podcast.episode_title.length > 200
                        ? podcast.episode_title.substring(0, 200) + '...'
                        : podcast.episode_title;
                      const truncatedPodcast = podcast.podcast_title.length > 200
                        ? podcast.podcast_title.substring(0, 200) + '...'
                        : podcast.podcast_title;

                      return (
                        <tr key={podcast.id} className="hover:bg-gray-50 transition-colors">
                          <td className="px-6 py-4">
                            <div className="flex items-start gap-3">
                              <div className="min-w-0 flex-1">
                                <div className="text-sm font-medium text-gray-900 break-words" title={podcast.episode_title}>
                                  {truncatedTitle}
                                </div>
                                <div className="text-xs text-gray-500 break-words mt-0.5" title={podcast.podcast_title}>
                                  {truncatedPodcast}
                                </div>
                              </div>
                              {isNew && (
                                <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium bg-[#077331] text-white flex-shrink-0">
                                  NEW
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {formatDate(podcast.published_date)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {formatDate(podcast.found_at)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {formatDuration(podcast.duration_seconds)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium ${getStatusColor(podcast.status)}`}>
                              {podcast.status}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                            <button
                              onClick={() => handleProcess(podcast)}
                              className="inline-flex items-center px-3 py-1.5 border border-[#077331] text-[#077331] rounded-md hover:bg-[#077331] hover:text-white transition-colors font-medium"
                            >
                              Process
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-6 px-4">
                  <div className="text-sm text-gray-700">
                    Showing {startIndex + 1} to {Math.min(endIndex, sortedPodcasts.length)} of {sortedPodcasts.length} results
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => goToPage(currentPage - 1)}
                      disabled={currentPage === 1}
                      className={`px-3 py-1 rounded-md text-sm font-medium ${
                        currentPage === 1
                          ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                          : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
                      }`}
                    >
                      Previous
                    </button>

                    {/* Page numbers */}
                    {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                      let pageNum;
                      if (totalPages <= 5) {
                        pageNum = i + 1;
                      } else if (currentPage <= 3) {
                        pageNum = i + 1;
                      } else if (currentPage >= totalPages - 2) {
                        pageNum = totalPages - 4 + i;
                      } else {
                        pageNum = currentPage - 2 + i;
                      }

                      return (
                        <button
                          key={pageNum}
                          onClick={() => goToPage(pageNum)}
                          className={`px-3 py-1 rounded-md text-sm font-medium ${
                            currentPage === pageNum
                              ? 'bg-[#077331] text-white'
                              : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
                          }`}
                        >
                          {pageNum}
                        </button>
                      );
                    })}

                    <button
                      onClick={() => goToPage(currentPage + 1)}
                      disabled={currentPage === totalPages}
                      className={`px-3 py-1 rounded-md text-sm font-medium ${
                        currentPage === totalPages
                          ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                          : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
                      }`}
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </>
          )}

          {/* Footer */}
          <div className="mt-8 pt-6 border-t border-gray-200 flex justify-between items-center">
            <a
              href="/admin"
              className="text-sm text-gray-600 hover:text-[#077331] transition-colors inline-flex items-center"
            >
              <svg className="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              Back to Article Admin
            </a>

            <a
              href="/"
              className="text-sm text-gray-600 hover:text-[#077331] transition-colors inline-flex items-center"
            >
              <svg className="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
              </svg>
              Home
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
