'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import {
  getContentSources,
  createContentSource,
  deleteContentSource,
  ContentSource,
  discoverSource,
  PreviewPost,
} from '@/lib/api-client';
import { searchPodcastIndex, getPodcastEpisodes } from '@/lib/podcast-index';
import { searchYouTubeChannels, getYouTubeChannelVideos, getChannelRSSFeedUrl, YouTubeChannel, YouTubeVideo } from '@/lib/youtube-api';
import { supabase } from '@/lib/supabase';
import { Trash2, X, Check, AlertCircle, Search } from 'lucide-react';

type NotificationType = 'success' | 'error' | 'info';

interface Notification {
  id: string;
  type: NotificationType;
  message: string;
}

interface PodcastSearchResult {
  id: number;
  title: string;
  author?: string;
  description?: string;
  feedUrl?: string;
  url?: string; // Alternative property name from API
  artwork?: string;
  image?: string; // Alternative property name from API
  itunesId?: number;
  episodeCount?: number;
  categories?: { [key: string]: string };
}

interface PodcastEpisode {
  id: number;
  title: string;
  datePublished: number;
  link?: string;
}

type AddMode = 'url' | 'podcast' | 'youtube';

interface DiscoveredSource {
  url: string;
  title: string;
  has_rss: boolean;
  source_type: string;
  preview_posts: PreviewPost[];
}

export default function ContentSourcesPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();

  const [sources, setSources] = useState<ContentSource[]>([]);
  const [loading, setLoading] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [addMode, setAddMode] = useState<AddMode>('url');

  // URL input mode state
  const [urlInput, setUrlInput] = useState('');
  const [discovering, setDiscovering] = useState(false);
  const [discoveredSource, setDiscoveredSource] = useState<DiscoveredSource | null>(null);

  // Podcast search mode state
  const [podcastSearchTerm, setPodcastSearchTerm] = useState('');
  const [podcastResults, setPodcastResults] = useState<PodcastSearchResult[]>([]);
  const [searchingPodcasts, setSearchingPodcasts] = useState(false);
  const [selectedPodcast, setSelectedPodcast] = useState<PodcastSearchResult | null>(null);
  const [podcastEpisodes, setPodcastEpisodes] = useState<Record<number, PodcastEpisode[]>>({});
  const [loadingEpisodes, setLoadingEpisodes] = useState<Record<number, boolean>>({});

  // YouTube channel search mode state
  const [youtubeSearchTerm, setYoutubeSearchTerm] = useState('');
  const [youtubeResults, setYoutubeResults] = useState<YouTubeChannel[]>([]);
  const [searchingYoutube, setSearchingYoutube] = useState(false);
  const [selectedYoutubeChannel, setSelectedYoutubeChannel] = useState<YouTubeChannel | null>(null);
  const [youtubeVideos, setYoutubeVideos] = useState<Record<string, YouTubeVideo[]>>({});
  const [loadingVideos, setLoadingVideos] = useState<Record<string, boolean>>({});

  // Protect this page - redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
    }
  }, [user, authLoading, router]);

  // Load sources on mount (only show spinner if no sources loaded yet)
  useEffect(() => {
    if (user) {
      loadSources(sources.length === 0);
    }
  }, [user]);

  const addNotification = (type: NotificationType, message: string) => {
    const id = Date.now().toString();
    const notification: Notification = { id, type, message };
    setNotifications((prev) => [...prev, notification]);

    // Auto-remove after 5 seconds
    setTimeout(() => {
      removeNotification(id);
    }, 5000);
  };

  const removeNotification = (id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  };

  const loadSources = async (showLoadingSpinner = true) => {
    try {
      if (showLoadingSpinner) {
        setLoading(true);
      }
      const data = await getContentSources(false);
      setSources(data.sources);
    } catch (error) {
      console.error('Error loading sources:', error);
      addNotification('error', error instanceof Error ? error.message : 'Failed to load sources');
    } finally {
      if (showLoadingSpinner) {
        setLoading(false);
      }
    }
  };

  /**
   * Add a channel to the public_channels table for privacy auto-detection
   * This ensures articles from this source are treated as public
   * Uses upsert logic - updates if URL already exists, inserts if new
   */
  const addToPublicChannels = async (params: {
    channelName: string;
    newsletterUrl?: string;
    rssFeedUrl?: string;
    podcastFeedUrl?: string;
    youtubeChannelUrl?: string;
  }) => {
    try {
      // Check if channel already exists by any of the provided URLs
      // This prevents duplicates when same channel is added with different name
      let existingId: number | null = null;

      if (params.youtubeChannelUrl) {
        const { data } = await supabase
          .from('public_channels')
          .select('id')
          .eq('youtube_channel_url', params.youtubeChannelUrl)
          .single();
        if (data) existingId = data.id;
      }

      if (!existingId && params.podcastFeedUrl) {
        const { data } = await supabase
          .from('public_channels')
          .select('id')
          .eq('podcast_feed_url', params.podcastFeedUrl)
          .single();
        if (data) existingId = data.id;
      }

      if (!existingId && params.newsletterUrl) {
        const { data } = await supabase
          .from('public_channels')
          .select('id')
          .eq('newsletter_url', params.newsletterUrl)
          .single();
        if (data) existingId = data.id;
      }

      if (!existingId && params.rssFeedUrl) {
        const { data } = await supabase
          .from('public_channels')
          .select('id')
          .eq('rss_feed_url', params.rssFeedUrl)
          .single();
        if (data) existingId = data.id;
      }

      // Note: We intentionally don't check by channel_name as a fallback
      // because different channels can have the same name

      const channelData = {
        channel_name: params.channelName,
        newsletter_url: params.newsletterUrl || null,
        rss_feed_url: params.rssFeedUrl || null,
        podcast_feed_url: params.podcastFeedUrl || null,
        youtube_channel_url: params.youtubeChannelUrl || null,
        is_active: true,
      };

      if (existingId) {
        // Update existing record
        const { error } = await supabase
          .from('public_channels')
          .update(channelData)
          .eq('id', existingId);

        if (error) {
          console.error('Error updating public_channels:', error);
        } else {
          console.log(`Updated public channel "${params.channelName}" (id: ${existingId})`);
        }
      } else {
        // Insert new record
        const { error } = await supabase
          .from('public_channels')
          .insert(channelData);

        if (error) {
          // Ignore duplicate key errors (race condition)
          if (!error.message.includes('duplicate') && !error.message.includes('unique')) {
            console.error('Error adding to public_channels:', error);
          }
        } else {
          console.log(`Added "${params.channelName}" to public_channels`);
        }
      }
    } catch (error) {
      // Non-critical error - don't block the main flow
      console.error('Error adding to public_channels:', error);
    }
  };

  const handleDiscoverURL = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!urlInput.trim()) {
      addNotification('error', 'Please enter a URL');
      return;
    }

    setDiscovering(true);
    setDiscoveredSource(null);

    try {
      const result = await discoverSource(urlInput, 'newsletter');
      setDiscoveredSource(result);
    } catch (error) {
      console.error('Error discovering source:', error);
      addNotification('error', error instanceof Error ? error.message : 'Failed to discover source');
    } finally {
      setDiscovering(false);
    }
  };

  const handleConfirmURLSource = async () => {
    if (!discoveredSource) return;

    try {
      await createContentSource({
        title: discoveredSource.title,
        url: discoveredSource.url,
        is_active: true,
        source_type: discoveredSource.source_type,
      });

      // Add to public_channels for privacy auto-detection
      // Newsletters/RSS feeds use domain-level matching
      await addToPublicChannels({
        channelName: discoveredSource.title,
        newsletterUrl: discoveredSource.source_type === 'newsletter' ? discoveredSource.url : undefined,
        rssFeedUrl: discoveredSource.has_rss ? discoveredSource.url : undefined,
      });

      addNotification('success', 'Source added successfully!');
      resetForm();
      loadSources();
    } catch (error) {
      console.error('Error creating source:', error);
      addNotification('error', error instanceof Error ? error.message : 'Failed to add source');
    }
  };

  const handleSearchPodcasts = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!podcastSearchTerm.trim()) {
      addNotification('error', 'Please enter a podcast name');
      return;
    }

    setSearchingPodcasts(true);
    setPodcastResults([]);
    setSelectedPodcast(null);
    setPodcastEpisodes({});

    try {
      const data = await searchPodcastIndex(podcastSearchTerm, 'podcast');
      const feeds = data.feeds || [];
      setPodcastResults(feeds);

      if (feeds.length === 0) {
        addNotification('info', 'No podcasts found. Try a different search term.');
      } else {
        // Fetch episodes for each podcast (first 2 only)
        feeds.forEach(async (podcast: PodcastSearchResult) => {
          try {
            setLoadingEpisodes(prev => ({ ...prev, [podcast.id]: true }));
            const episodesData = await getPodcastEpisodes(podcast.id);
            const episodes = (episodesData.items || []).slice(0, 2); // Get last 2 episodes
            setPodcastEpisodes(prev => ({ ...prev, [podcast.id]: episodes }));
          } catch (error) {
            console.error(`Error fetching episodes for podcast ${podcast.id}:`, error);
          } finally {
            setLoadingEpisodes(prev => ({ ...prev, [podcast.id]: false }));
          }
        });
      }
    } catch (error) {
      console.error('Error searching podcasts:', error);
      addNotification('error', error instanceof Error ? error.message : 'Failed to search podcasts');
    } finally {
      setSearchingPodcasts(false);
    }
  };

  const handleSelectPodcast = (podcast: PodcastSearchResult) => {
    setSelectedPodcast(podcast);
  };

  const handleConfirmPodcast = async () => {
    if (!selectedPodcast) {
      addNotification('error', 'No podcast selected');
      return;
    }

    // Try multiple possible property names for the feed URL
    const feedUrl = selectedPodcast.feedUrl || selectedPodcast.url;

    if (!feedUrl) {
      console.error('Podcast object:', selectedPodcast);
      addNotification('error', 'No podcast feed URL available');
      return;
    }

    try {
      await createContentSource({
        title: selectedPodcast.title,
        url: feedUrl,
        is_active: true,
        source_type: 'podcast',
      });

      // Add to public_channels for privacy auto-detection
      await addToPublicChannels({
        channelName: selectedPodcast.title,
        podcastFeedUrl: feedUrl,
      });

      addNotification('success', 'Podcast added successfully!');
      resetForm();
      loadSources();
    } catch (error) {
      console.error('Error creating source:', error);
      addNotification('error', error instanceof Error ? error.message : 'Failed to add podcast');
    }
  };

  const handleSearchYouTube = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!youtubeSearchTerm.trim()) {
      addNotification('error', 'Please enter a channel name');
      return;
    }

    setSearchingYoutube(true);
    setYoutubeResults([]);
    setSelectedYoutubeChannel(null);
    setYoutubeVideos({});

    try {
      const channels = await searchYouTubeChannels(youtubeSearchTerm);
      setYoutubeResults(channels);

      if (channels.length === 0) {
        addNotification('info', 'No channels found. Try a different search term.');
      } else {
        // Fetch recent videos for each channel (first 3)
        channels.forEach(async (channel: YouTubeChannel) => {
          try {
            setLoadingVideos(prev => ({ ...prev, [channel.id]: true }));
            const videos = await getYouTubeChannelVideos(channel.id, 3);
            setYoutubeVideos(prev => ({ ...prev, [channel.id]: videos }));
          } catch (error) {
            console.error(`Error fetching videos for channel ${channel.id}:`, error);
          } finally {
            setLoadingVideos(prev => ({ ...prev, [channel.id]: false }));
          }
        });
      }
    } catch (error) {
      console.error('Error searching YouTube:', error);
      addNotification('error', error instanceof Error ? error.message : 'Failed to search YouTube channels');
    } finally {
      setSearchingYoutube(false);
    }
  };

  const handleSelectYouTubeChannel = (channel: YouTubeChannel) => {
    setSelectedYoutubeChannel(channel);
  };

  const handleConfirmYouTubeChannel = async () => {
    if (!selectedYoutubeChannel) {
      addNotification('error', 'No channel selected');
      return;
    }

    // Use RSS feed URL as the normalized format across both tables
    // Format: https://www.youtube.com/feeds/videos.xml?channel_id=UCxxxx
    // This is easier to traverse when checking for new videos
    const rssFeedUrl = getChannelRSSFeedUrl(selectedYoutubeChannel.id);

    try {
      await createContentSource({
        title: selectedYoutubeChannel.title,
        url: rssFeedUrl,
        is_active: true,
        source_type: 'youtube_channel',
      });

      // Add to public_channels - use same RSS feed URL format for consistency
      await addToPublicChannels({
        channelName: selectedYoutubeChannel.title,
        youtubeChannelUrl: rssFeedUrl,
      });

      addNotification('success', 'YouTube channel added successfully!');
      resetForm();
      loadSources();
    } catch (error) {
      console.error('Error creating source:', error);
      addNotification('error', error instanceof Error ? error.message : 'Failed to add YouTube channel');
    }
  };

  const handleDelete = async (source: ContentSource) => {
    if (!confirm(`Are you sure you want to delete "${source.title}"?`)) {
      return;
    }

    try {
      await deleteContentSource(source.id);
      addNotification('success', 'Source deleted successfully!');
      loadSources();
    } catch (error) {
      console.error('Error deleting source:', error);
      addNotification('error', error instanceof Error ? error.message : 'Failed to delete source');
    }
  };

  const resetForm = () => {
    setUrlInput('');
    setPodcastSearchTerm('');
    setYoutubeSearchTerm('');
    setDiscoveredSource(null);
    setPodcastResults([]);
    setSelectedPodcast(null);
    setYoutubeResults([]);
    setSelectedYoutubeChannel(null);
    // Keep form open - just reset to URL mode
    setAddMode('url');
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

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
      <div className="max-w-6xl mx-auto">
        {/* Notifications */}
        {notifications.length > 0 && (
          <div className="fixed top-4 right-4 z-50 space-y-2">
            {notifications.map((notification) => (
              <div
                key={notification.id}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg max-w-md transition-all duration-300 ${
                  notification.type === 'success'
                    ? 'bg-green-50 border border-[#077331] text-[#077331]'
                    : notification.type === 'error'
                    ? 'bg-red-50 border border-red-200 text-red-800'
                    : 'bg-blue-50 border border-blue-200 text-blue-800'
                }`}
              >
                {notification.type === 'success' && <Check className="h-5 w-5 flex-shrink-0" />}
                {notification.type === 'error' && <AlertCircle className="h-5 w-5 flex-shrink-0" />}
                {notification.type === 'info' && <AlertCircle className="h-5 w-5 flex-shrink-0" />}
                <span className="flex-1 text-sm font-medium">{notification.message}</span>
                <button
                  onClick={() => removeNotification(notification.id)}
                  className="text-gray-400 hover:text-gray-600 transition-colors"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="bg-white rounded-lg shadow-md p-8">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Content Sources</h1>
            <p className="text-gray-600">Manage your RSS feeds and newsletter subscriptions</p>
          </div>

          {/* Add Form - Always Visible */}
          <div className="mb-8 p-6 border-2 border-[#077331] rounded-lg bg-green-50">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Add New Source</h2>

              {/* Mode Toggle */}
              <div className="flex gap-2 mb-6">
                <button
                  onClick={() => {
                    setAddMode('url');
                    setPodcastResults([]);
                    setSelectedPodcast(null);
                    setYoutubeResults([]);
                    setSelectedYoutubeChannel(null);
                    // Keep urlInput - don't clear it
                  }}
                  className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                    addMode === 'url'
                      ? 'bg-[#077331] text-white'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                >
                  Search Newsletter by URL
                </button>
                <button
                  onClick={() => {
                    setAddMode('podcast');
                    setDiscoveredSource(null);
                    setYoutubeResults([]);
                    setSelectedYoutubeChannel(null);
                    // Keep podcastSearchTerm - don't clear it
                  }}
                  className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                    addMode === 'podcast'
                      ? 'bg-[#077331] text-white'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                >
                  Search Podcast
                </button>
                <button
                  onClick={() => {
                    setAddMode('youtube');
                    setDiscoveredSource(null);
                    setPodcastResults([]);
                    setSelectedPodcast(null);
                    // Keep youtubeSearchTerm - don't clear it
                  }}
                  className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                    addMode === 'youtube'
                      ? 'bg-[#077331] text-white'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                >
                  Search YouTube Channel
                </button>
              </div>

              {/* URL Mode */}
              {addMode === 'url' && (
                <div>
                  <form onSubmit={handleDiscoverURL} className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Enter URL of newsletter or RSS feed
                    </label>
                    <div className="flex gap-2">
                      <input
                        type="url"
                        required
                        value={urlInput}
                        onChange={(e) => setUrlInput(e.target.value)}
                        placeholder="https://example.com/feed"
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-[#077331] focus:border-transparent"
                      />
                      <button
                        type="submit"
                        disabled={discovering}
                        className={`px-4 py-2 rounded-md font-medium text-white transition-colors ${
                          discovering
                            ? 'bg-gray-400 cursor-not-allowed'
                            : 'bg-[#077331] hover:bg-[#055a24]'
                        }`}
                      >
                        {discovering ? 'Discovering...' : 'Discover'}
                      </button>
                    </div>
                  </form>

                  {/* Discovery Preview */}
                  {discoveredSource && (
                    <div className="mt-4 p-4 bg-white rounded-lg border border-gray-200">
                      <h3 className="font-semibold text-lg mb-2">{discoveredSource.title}</h3>
                      <p className="text-sm text-gray-600 mb-2">{discoveredSource.url}</p>
                      <div className="flex items-center gap-2 mb-4">
                        <span
                          className={`text-xs px-2 py-1 rounded ${
                            discoveredSource.has_rss
                              ? 'bg-green-100 text-green-800'
                              : 'bg-yellow-100 text-yellow-800'
                          }`}
                        >
                          {discoveredSource.has_rss ? 'RSS Feed' : 'HTML Scraping'}
                        </span>
                      </div>

                      {discoveredSource.preview_posts.length > 0 && (
                        <div className="mb-4">
                          <h4 className="text-sm font-medium text-gray-700 mb-2">Recent Posts:</h4>
                          <div className="space-y-2">
                            {discoveredSource.preview_posts.map((post, idx) => (
                              <div key={idx} className="text-sm">
                                <a
                                  href={post.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-[#077331] hover:underline"
                                >
                                  {post.title}
                                </a>
                                {post.published_date && (
                                  <span className="text-gray-500 ml-2">
                                    {new Date(post.published_date).toLocaleDateString()}
                                  </span>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      <div className="flex gap-2">
                        <button
                          onClick={handleConfirmURLSource}
                          className="px-4 py-2 bg-[#077331] text-white rounded-lg hover:bg-[#055a24] transition-colors"
                        >
                          Add This Source
                        </button>
                        <button
                          onClick={() => setDiscoveredSource(null)}
                          className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Podcast Search Mode */}
              {addMode === 'podcast' && (
                <div>
                  <form onSubmit={handleSearchPodcasts} className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Search for a podcast by name
                    </label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        required
                        value={podcastSearchTerm}
                        onChange={(e) => setPodcastSearchTerm(e.target.value)}
                        placeholder="e.g., Dwarkesh Podcast"
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-[#077331] focus:border-transparent"
                      />
                      <button
                        type="submit"
                        disabled={searchingPodcasts}
                        className={`px-4 py-2 rounded-md font-medium text-white transition-colors inline-flex items-center ${
                          searchingPodcasts
                            ? 'bg-gray-400 cursor-not-allowed'
                            : 'bg-[#077331] hover:bg-[#055a24]'
                        }`}
                      >
                        <Search className="h-4 w-4 mr-2" />
                        {searchingPodcasts ? 'Searching...' : 'Search'}
                      </button>
                    </div>
                  </form>

                  {/* Podcast Results */}
                  {podcastResults.length > 0 && (
                    <div className="space-y-3 max-h-96 overflow-y-auto">
                      {podcastResults.map((podcast) => {
                        const episodes = podcastEpisodes[podcast.id] || [];
                        const isLoadingEpisodes = loadingEpisodes[podcast.id];
                        const artwork = podcast.artwork || podcast.image;

                        return (
                          <div
                            key={podcast.id}
                            onClick={() => handleSelectPodcast(podcast)}
                            className={`p-4 rounded-lg border-2 cursor-pointer transition-colors ${
                              selectedPodcast?.id === podcast.id
                                ? 'border-[#077331] bg-white'
                                : 'border-gray-200 bg-white hover:border-gray-300'
                            }`}
                          >
                            <div className="flex gap-3">
                              {artwork && (
                                <img
                                  src={artwork}
                                  alt={podcast.title}
                                  className="w-16 h-16 rounded object-cover flex-shrink-0"
                                />
                              )}
                              <div className="flex-1 min-w-0">
                                <h3 className="font-semibold">{podcast.title}</h3>
                                {podcast.author && (
                                  <p className="text-sm text-gray-600">{podcast.author}</p>
                                )}
                                {podcast.episodeCount && (
                                  <p className="text-xs text-gray-500 mt-1">
                                    {podcast.episodeCount} episodes
                                  </p>
                                )}

                                {/* Episode Previews */}
                                {isLoadingEpisodes && (
                                  <div className="mt-2 text-xs text-gray-500">
                                    Loading episodes...
                                  </div>
                                )}
                                {!isLoadingEpisodes && episodes.length > 0 && (
                                  <div className="mt-3 space-y-2">
                                    {episodes.map((episode) => (
                                      <div
                                        key={episode.id}
                                        className="text-xs text-gray-600 border-l-2 border-gray-300 pl-2"
                                      >
                                        <div className="font-medium line-clamp-1">
                                          {episode.title}
                                        </div>
                                        <div className="text-gray-500">
                                          {new Date(episode.datePublished * 1000).toLocaleDateString('en-US', {
                                            month: 'short',
                                            day: 'numeric',
                                            year: 'numeric'
                                          })}
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>
                              {selectedPodcast?.id === podcast.id && (
                                <Check className="h-5 w-5 text-[#077331] flex-shrink-0" />
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {/* Confirm Podcast Selection */}
                  {selectedPodcast && (
                    <div className="mt-4 flex gap-2">
                      <button
                        onClick={handleConfirmPodcast}
                        className="px-4 py-2 bg-[#077331] text-white rounded-lg hover:bg-[#055a24] transition-colors"
                      >
                        Add "{selectedPodcast.title}"
                      </button>
                      <button
                        onClick={() => setSelectedPodcast(null)}
                        className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                      >
                        Cancel
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* YouTube Channel Search Mode */}
              {addMode === 'youtube' && (
                <div>
                  <form onSubmit={handleSearchYouTube} className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Search for a YouTube channel by name
                    </label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        required
                        value={youtubeSearchTerm}
                        onChange={(e) => setYoutubeSearchTerm(e.target.value)}
                        placeholder="e.g., Lex Fridman"
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-[#077331] focus:border-transparent"
                      />
                      <button
                        type="submit"
                        disabled={searchingYoutube}
                        className={`px-4 py-2 rounded-md font-medium text-white transition-colors inline-flex items-center ${
                          searchingYoutube
                            ? 'bg-gray-400 cursor-not-allowed'
                            : 'bg-[#077331] hover:bg-[#055a24]'
                        }`}
                      >
                        <Search className="h-4 w-4 mr-2" />
                        {searchingYoutube ? 'Searching...' : 'Search'}
                      </button>
                    </div>
                  </form>

                  {/* YouTube Channel Results */}
                  {youtubeResults.length > 0 && (
                    <div className="space-y-3 max-h-96 overflow-y-auto">
                      {youtubeResults.map((channel) => {
                        const videos = youtubeVideos[channel.id] || [];
                        const isLoadingVideos = loadingVideos[channel.id];

                        return (
                          <div
                            key={channel.id}
                            onClick={() => handleSelectYouTubeChannel(channel)}
                            className={`p-4 rounded-lg border-2 cursor-pointer transition-colors ${
                              selectedYoutubeChannel?.id === channel.id
                                ? 'border-[#077331] bg-white'
                                : 'border-gray-200 bg-white hover:border-gray-300'
                            }`}
                          >
                            <div className="flex gap-3">
                              {channel.thumbnail && (
                                <img
                                  src={channel.thumbnail}
                                  alt={channel.title}
                                  className="w-16 h-16 rounded-full object-cover flex-shrink-0"
                                />
                              )}
                              <div className="flex-1 min-w-0">
                                <h3 className="font-semibold">{channel.title}</h3>
                                <div className="flex gap-3 text-xs text-gray-500 mt-1">
                                  {channel.subscriberCount && (
                                    <span>
                                      {parseInt(channel.subscriberCount).toLocaleString()} subscribers
                                    </span>
                                  )}
                                  {channel.videoCount && (
                                    <span>
                                      {parseInt(channel.videoCount).toLocaleString()} videos
                                    </span>
                                  )}
                                </div>

                                {/* Video Previews */}
                                {isLoadingVideos && (
                                  <div className="mt-2 text-xs text-gray-500">
                                    Loading recent videos...
                                  </div>
                                )}
                                {!isLoadingVideos && videos.length > 0 && (
                                  <div className="mt-3 space-y-2">
                                    {videos.map((video) => (
                                      <div
                                        key={video.id}
                                        className="text-xs text-gray-600 border-l-2 border-gray-300 pl-2"
                                      >
                                        <div className="font-medium line-clamp-1">
                                          {video.title}
                                        </div>
                                        <div className="text-gray-500">
                                          {new Date(video.publishedAt).toLocaleDateString('en-US', {
                                            month: 'short',
                                            day: 'numeric',
                                            year: 'numeric'
                                          })}
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>
                              {selectedYoutubeChannel?.id === channel.id && (
                                <Check className="h-5 w-5 text-[#077331] flex-shrink-0" />
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {/* Confirm YouTube Channel Selection */}
                  {selectedYoutubeChannel && (
                    <div className="mt-4 flex gap-2">
                      <button
                        onClick={handleConfirmYouTubeChannel}
                        className="px-4 py-2 bg-[#077331] text-white rounded-lg hover:bg-[#055a24] transition-colors"
                      >
                        Add "{selectedYoutubeChannel.title}"
                      </button>
                      <button
                        onClick={() => setSelectedYoutubeChannel(null)}
                        className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                      >
                        Cancel
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>

          {/* Sources List */}
          {loading ? (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-[#077331]"></div>
              <p className="mt-4 text-gray-600">Loading sources...</p>
            </div>
          ) : sources.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-600">No content sources found. Add your first source above!</p>
            </div>
          ) : (
            <div className="space-y-4">
              {sources.map((source) => (
                <div
                  key={source.id}
                  className="p-6 border rounded-lg border-gray-200 hover:border-[#077331] transition-colors"
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-gray-900 mb-2">{source.title}</h3>
                      <a
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-[#077331] hover:underline break-all"
                      >
                        {source.url}
                      </a>
                      <div className="mt-3 text-xs text-gray-500 space-y-1">
                        <div>Created: {formatDate(source.created_at)}</div>
                        {source.last_checked_at && (
                          <div>Last checked: {formatDate(source.last_checked_at)}</div>
                        )}
                      </div>
                    </div>

                    <div className="flex gap-2 ml-4">
                      <button
                        onClick={() => handleDelete(source)}
                        className="p-2 text-gray-500 hover:text-red-600 transition-colors"
                        title="Delete source"
                      >
                        <Trash2 className="h-5 w-5" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Footer */}
          <div className="mt-8 pt-6 border-t border-gray-200 flex justify-between items-center">
            <a
              href="/new/posts"
              className="text-sm text-gray-600 hover:text-[#077331] transition-colors"
            >
              ← Check for New Posts
            </a>
            <a
              href="/"
              className="text-sm text-gray-600 hover:text-[#077331] transition-colors"
            >
              Home
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
