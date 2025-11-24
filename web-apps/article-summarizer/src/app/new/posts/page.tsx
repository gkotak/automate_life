'use client';

import { useState, useEffect, useRef } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { getDiscoveredPosts, checkNewPosts, getContentSources } from '@/lib/api-client';

interface Post {
  id: string;
  title: string;
  url: string;
  content_type: string;
  channel_title: string | null;
  published_date: string | null;
  found_at: string;
  is_new: boolean;
}

type SortField = 'title' | 'content_type' | 'published_date' | 'found_at';
type SortDirection = 'asc' | 'desc';

export default function PostsAdminPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true); // Start with true to show initial loading
  const [checking, setChecking] = useState(false);
  const [message, setMessage] = useState<{
    type: 'success' | 'error' | 'info';
    text: string;
  } | null>(null);
  const [newlyDiscoveredIds, setNewlyDiscoveredIds] = useState<Set<string>>(new Set());
  const [currentPage, setCurrentPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [hasNoSources, setHasNoSources] = useState(false);
  const itemsPerPage = 25;
  const [sortField, setSortField] = useState<SortField>('found_at');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const hasLoadedOnce = useRef(false);

  // Protect this page - redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
    }
  }, [user, authLoading, router]);

  // Load posts and check sources on mount (only show spinner on very first load)
  useEffect(() => {
    if (user) {
      const shouldShowSpinner = !hasLoadedOnce.current;
      loadPosts(false, shouldShowSpinner);
      checkSourcesCount();
      if (!hasLoadedOnce.current) {
        hasLoadedOnce.current = true;
      }
    }
  }, [user]);

  const checkSourcesCount = async () => {
    try {
      const data = await getContentSources(false);
      setHasNoSources(data.sources.length === 0);
    } catch (error) {
      console.error('Error checking sources:', error);
    }
  };

  const loadPosts = async (silent: boolean = false, showLoadingSpinner: boolean = true) => {
    if (showLoadingSpinner) {
      setLoading(true);
    }

    try {
      const data = await getDiscoveredPosts(200);
      console.log('API Response:', data);
      console.log('First post:', data.posts[0]);

      // Map posts to add is_new property and ensure proper types
      const postsWithIsNew: Post[] = data.posts.map(post => ({
        id: post.id,
        title: post.title,
        url: post.url,
        content_type: post.content_type,
        channel_title: post.channel_title ?? null,
        published_date: post.published_date ?? null,
        found_at: post.found_at,
        is_new: false
      }));

      setPosts(postsWithIsNew);
      setTotalCount(data.total);

      // Don't show message when just loading from database
    } catch (error) {
      console.error('Error loading posts:', error);
      if (!silent) {
        setMessage({
          type: 'error',
          text: error instanceof Error ? error.message : 'Failed to load posts'
        });
      }
    } finally {
      if (showLoadingSpinner) {
        setLoading(false);
      }
    }
  };

  const checkForNewPosts = async () => {
    setChecking(true);
    setMessage(null);

    try {
      const data = await checkNewPosts();

      // Track newly discovered IDs
      if (data.newly_discovered_ids && data.newly_discovered_ids.length > 0) {
        setNewlyDiscoveredIds(new Set(data.newly_discovered_ids));
      }

      setMessage({
        type: 'success',
        text: data.message
      });

      // Refresh the post list (silent = true, showLoadingSpinner = false)
      await loadPosts(true, false);
    } catch (error) {
      console.error('Error checking posts:', error);
      setMessage({
        type: 'error',
        text: error instanceof Error ? error.message : 'Failed to check posts'
      });
    } finally {
      setChecking(false);
    }
  };

  const handleProcess = (post: Post) => {
    // Redirect to article processing page with URL parameter
    router.push(`/new/article?url=${encodeURIComponent(post.url)}`);
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

  const sortPosts = (postsList: Post[]) => {
    return [...postsList].sort((a, b) => {
      let aValue: any;
      let bValue: any;

      switch (sortField) {
        case 'title':
          aValue = a.title.toLowerCase();
          bValue = b.title.toLowerCase();
          break;
        case 'content_type':
          aValue = a.content_type.toLowerCase();
          bValue = b.content_type.toLowerCase();
          break;
        case 'published_date':
          aValue = a.published_date ? new Date(a.published_date).getTime() : 0;
          bValue = b.published_date ? new Date(b.published_date).getTime() : 0;
          break;
        case 'found_at':
          aValue = a.found_at ? new Date(a.found_at).getTime() : 0;
          bValue = b.found_at ? new Date(b.found_at).getTime() : 0;
          break;
        default:
          return 0;
      }

      if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  };

  const formatContentType = (contentType: string) => {
    if (contentType === 'podcast_episode') return 'Podcast';
    if (contentType === 'article') return 'Article';
    return contentType;
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

  // Sort and paginate
  const sortedPosts = sortPosts(posts);
  const totalPages = Math.ceil(sortedPosts.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const paginatedPosts = sortedPosts.slice(startIndex, endIndex);

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
              Newsletter & Article Discovery
            </h1>
            <p className="text-gray-600">
              Check content sources for new posts and articles
            </p>
          </div>

          {/* Actions */}
          {!hasNoSources && (
            <div className="mb-6">
              <button
                onClick={checkForNewPosts}
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
                  'Check for New Posts'
                )}
              </button>
            </div>
          )}

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

          {/* Posts Table */}
          {loading ? (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-[#077331]"></div>
              <p className="mt-4 text-gray-600">Loading posts...</p>
            </div>
          ) : posts.length === 0 ? (
            <div className="text-center py-12">
              <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              {hasNoSources ? (
                <>
                  <p className="mt-4 text-gray-600">No content sources found</p>
                  <button
                    onClick={() => router.push('/sources?addSource=true')}
                    className="mt-4 px-4 py-2 bg-[#077331] text-white rounded-full hover:bg-[#055a24] transition-colors"
                  >
                    Add Your First Source
                  </button>
                </>
              ) : (
                <>
                  <p className="mt-4 text-gray-600">No discovered posts found</p>
                  <button
                    onClick={checkForNewPosts}
                    disabled={checking}
                    className={`mt-4 px-6 py-3 rounded-lg font-medium text-white transition-colors ${
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
                      'Check for New Posts'
                    )}
                  </button>
                </>
              )}
            </div>
          ) : (
            <>
              <div className="overflow-x-auto border border-gray-200 rounded-lg">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <SortableHeader field="title" label="Title" className="w-auto" />
                      <SortableHeader field="content_type" label="Type" className="w-24" />
                      <SortableHeader field="published_date" label="Published" className="w-28" />
                      <SortableHeader field="found_at" label="Found" className="w-28" />
                      <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider w-24">
                        Action
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {paginatedPosts.map((post) => {
                      const isNew = post.is_new || newlyDiscoveredIds.has(post.id);
                      const truncatedTitle = post.title.length > 200
                        ? post.title.substring(0, 200) + '...'
                        : post.title;
                      const channel = post.channel_title || 'Unknown Source';
                      const truncatedChannel = channel.length > 200
                        ? channel.substring(0, 200) + '...'
                        : channel;

                      return (
                        <tr key={post.id} className="hover:bg-gray-50 transition-colors">
                          <td className="px-6 py-4">
                            <div className="flex items-start gap-3">
                              <div className="min-w-0 flex-1">
                                <div className="text-sm font-medium text-gray-900 break-words" title={post.title}>
                                  {truncatedTitle}
                                </div>
                                <div className="text-xs text-gray-500 break-words mt-0.5" title={channel}>
                                  {truncatedChannel}
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
                            {formatContentType(post.content_type)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {formatDate(post.published_date)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {formatDate(post.found_at)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                            <button
                              onClick={() => handleProcess(post)}
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
                    Showing {startIndex + 1} to {Math.min(endIndex, sortedPosts.length)} of {sortedPosts.length} results
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
            <div className="flex gap-4">
              <a
                href="/sources"
                className="text-sm text-gray-600 hover:text-[#077331] transition-colors inline-flex items-center"
              >
                <svg className="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
                Manage Sources
              </a>
            </div>

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
