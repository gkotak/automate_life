/**
 * YouTube Data API v3 client
 *
 * Provides functions to search for channels and fetch recent videos
 * API Documentation: https://developers.google.com/youtube/v3/docs
 */

const YOUTUBE_API_BASE = 'https://www.googleapis.com/youtube/v3';

export interface YouTubeChannel {
  id: string;
  title: string;
  description: string;
  thumbnail: string;
  customUrl?: string;
  subscriberCount?: string;
  videoCount?: string;
  viewCount?: string;
}

export interface YouTubeVideo {
  id: string;
  title: string;
  description: string;
  publishedAt: string;
  thumbnail: string;
  channelId: string;
  channelTitle: string;
}

/**
 * Search for YouTube channels by name
 */
export async function searchYouTubeChannels(query: string): Promise<YouTubeChannel[]> {
  const response = await fetch(`/api/youtube-search?q=${encodeURIComponent(query)}`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to search YouTube channels');
  }

  const data = await response.json();
  return data.channels || [];
}

/**
 * Get recent videos from a YouTube channel
 */
export async function getYouTubeChannelVideos(
  channelId: string,
  maxResults: number = 3
): Promise<YouTubeVideo[]> {
  const response = await fetch(
    `/api/youtube-videos?channelId=${encodeURIComponent(channelId)}&maxResults=${maxResults}`
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to fetch channel videos');
  }

  const data = await response.json();
  return data.videos || [];
}

/**
 * Convert channel ID to YouTube RSS feed URL
 */
export function getChannelRSSFeedUrl(channelId: string): string {
  return `https://www.youtube.com/feeds/videos.xml?channel_id=${channelId}`;
}

/**
 * Convert channel ID to YouTube channel URL
 */
export function getChannelUrl(channelId: string, customUrl?: string): string {
  if (customUrl) {
    return `https://www.youtube.com/${customUrl}`;
  }
  return `https://www.youtube.com/channel/${channelId}`;
}
