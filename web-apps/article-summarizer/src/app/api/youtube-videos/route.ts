import { NextRequest } from 'next/server';

const YOUTUBE_API_KEY = process.env.YOUTUBE_API_KEY;
const YOUTUBE_API_BASE = 'https://www.googleapis.com/youtube/v3';

interface YouTubeVideoItem {
  id: {
    kind: string;
    videoId: string;
  };
  snippet: {
    title: string;
    description: string;
    publishedAt: string;
    thumbnails: {
      default: { url: string };
      medium: { url: string };
      high: { url: string };
    };
    channelId: string;
    channelTitle: string;
  };
}

/**
 * API route to get recent videos from a YouTube channel
 * GET /api/youtube-videos?channelId=UCxxxxx&maxResults=3
 */
export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const channelId = searchParams.get('channelId');
    const maxResults = searchParams.get('maxResults') || '3';

    if (!channelId) {
      return new Response(
        JSON.stringify({ error: 'Channel ID is required' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    if (!YOUTUBE_API_KEY) {
      return new Response(
        JSON.stringify({ error: 'YouTube API key not configured' }),
        { status: 500, headers: { 'Content-Type': 'application/json' } }
      );
    }

    // Search for recent videos from this channel
    const searchUrl = new URL(`${YOUTUBE_API_BASE}/search`);
    searchUrl.searchParams.set('part', 'snippet');
    searchUrl.searchParams.set('channelId', channelId);
    searchUrl.searchParams.set('type', 'video');
    searchUrl.searchParams.set('order', 'date'); // Most recent first
    searchUrl.searchParams.set('maxResults', maxResults);
    searchUrl.searchParams.set('key', YOUTUBE_API_KEY);

    const response = await fetch(searchUrl.toString());

    if (!response.ok) {
      const errorText = await response.text();
      console.error('YouTube API videos error:', errorText);
      return new Response(
        JSON.stringify({ error: `YouTube API error: ${response.status}` }),
        { status: response.status, headers: { 'Content-Type': 'application/json' } }
      );
    }

    const data = await response.json();
    const items: YouTubeVideoItem[] = data.items || [];

    // Format response
    const videos = items.map(item => ({
      id: item.id.videoId,
      title: item.snippet.title,
      description: item.snippet.description,
      publishedAt: item.snippet.publishedAt,
      thumbnail: item.snippet.thumbnails.medium?.url || item.snippet.thumbnails.default?.url,
      channelId: item.snippet.channelId,
      channelTitle: item.snippet.channelTitle,
    }));

    return new Response(
      JSON.stringify({ videos }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    );

  } catch (error) {
    console.error('YouTube videos API error:', error);
    return new Response(
      JSON.stringify({ error: 'Internal server error' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}
