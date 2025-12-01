import { NextRequest } from 'next/server';

const YOUTUBE_API_KEY = process.env.YOUTUBE_API_KEY;
const YOUTUBE_API_BASE = 'https://www.googleapis.com/youtube/v3';

interface YouTubeSearchItem {
  id: {
    kind: string;
    channelId: string;
  };
  snippet: {
    title: string;
    description: string;
    thumbnails: {
      default: { url: string };
      medium: { url: string };
      high: { url: string };
    };
    channelTitle?: string;
    customUrl?: string;
  };
}

interface YouTubeChannelStatistics {
  subscriberCount: string;
  videoCount: string;
  viewCount: string;
}

/**
 * API route to search YouTube channels
 * GET /api/youtube-search?q=search+term
 */
export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const query = searchParams.get('q');

    if (!query) {
      return new Response(
        JSON.stringify({ error: 'Query parameter "q" is required' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    if (!YOUTUBE_API_KEY) {
      return new Response(
        JSON.stringify({ error: 'YouTube API key not configured' }),
        { status: 500, headers: { 'Content-Type': 'application/json' } }
      );
    }

    // Search for channels
    const searchUrl = new URL(`${YOUTUBE_API_BASE}/search`);
    searchUrl.searchParams.set('part', 'snippet');
    searchUrl.searchParams.set('type', 'channel');
    searchUrl.searchParams.set('q', query);
    searchUrl.searchParams.set('maxResults', '10');
    searchUrl.searchParams.set('key', YOUTUBE_API_KEY);

    const searchResponse = await fetch(searchUrl.toString());

    if (!searchResponse.ok) {
      const errorText = await searchResponse.text();
      console.error('YouTube API search error:', errorText);
      return new Response(
        JSON.stringify({ error: `YouTube API error: ${searchResponse.status}` }),
        { status: searchResponse.status, headers: { 'Content-Type': 'application/json' } }
      );
    }

    const searchData = await searchResponse.json();
    const items: YouTubeSearchItem[] = searchData.items || [];

    if (items.length === 0) {
      return new Response(
        JSON.stringify({ channels: [] }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      );
    }

    // Get channel IDs to fetch statistics
    const channelIds = items.map(item => item.id.channelId).join(',');

    // Fetch channel statistics (subscriber count, etc.)
    const channelsUrl = new URL(`${YOUTUBE_API_BASE}/channels`);
    channelsUrl.searchParams.set('part', 'statistics,snippet');
    channelsUrl.searchParams.set('id', channelIds);
    channelsUrl.searchParams.set('key', YOUTUBE_API_KEY);

    const channelsResponse = await fetch(channelsUrl.toString());

    if (!channelsResponse.ok) {
      console.error('YouTube API channels error');
      // Continue without statistics
    }

    const channelsData = channelsResponse.ok ? await channelsResponse.json() : null;
    const statisticsMap = new Map<string, YouTubeChannelStatistics>();

    if (channelsData?.items) {
      for (const channel of channelsData.items) {
        statisticsMap.set(channel.id, channel.statistics);
      }
    }

    // Format response
    const channels = items.map(item => {
      const statistics = statisticsMap.get(item.id.channelId);

      return {
        id: item.id.channelId,
        title: item.snippet.title,
        description: item.snippet.description,
        thumbnail: item.snippet.thumbnails.high?.url || item.snippet.thumbnails.medium?.url,
        customUrl: item.snippet.customUrl,
        subscriberCount: statistics?.subscriberCount,
        videoCount: statistics?.videoCount,
        viewCount: statistics?.viewCount,
      };
    });

    return new Response(
      JSON.stringify({ channels }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    );

  } catch (error) {
    console.error('YouTube search API error:', error);
    return new Response(
      JSON.stringify({ error: 'Internal server error' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}
