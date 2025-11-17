import { NextRequest } from 'next/server';
import crypto from 'crypto';

const API_KEY = process.env.PODCAST_INDEX_KEY || 'BAZJFYRTJBXDTZZCFDAF';
const API_SECRET = process.env.PODCAST_INDEX_SECRET || '';
const BASE_URL = 'https://api.podcastindex.org/api/1.0';

interface PodcastIndexHeaders {
  'User-Agent': string;
  'X-Auth-Date': string;
  'X-Auth-Key': string;
  'Authorization': string;
}

function generateAuthHeaders(): PodcastIndexHeaders {
  const timestamp = Math.floor(Date.now() / 1000);
  const authString = API_KEY + API_SECRET + timestamp;
  const authHash = crypto.createHash('sha1').update(authString).digest('hex');

  return {
    'User-Agent': 'AutomateLife/1.0',
    'X-Auth-Date': timestamp.toString(),
    'X-Auth-Key': API_KEY,
    'Authorization': authHash,
  };
}

/**
 * API route to get episodes for a podcast feed
 * GET /api/podcast-episodes?feedId=123
 */
export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const feedId = searchParams.get('feedId');

    if (!feedId) {
      return new Response(
        JSON.stringify({ error: 'Feed ID is required' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    // Use /episodes/byfeedid endpoint
    const url = `${BASE_URL}/episodes/byfeedid?id=${feedId}`;

    const headers = generateAuthHeaders();

    const response = await fetch(url, {
      method: 'GET',
      headers,
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('PodcastIndex API error:', errorText);
      return new Response(
        JSON.stringify({ error: `PodcastIndex API error: ${response.status}` }),
        { status: response.status, headers: { 'Content-Type': 'application/json' } }
      );
    }

    const data = await response.json();

    return new Response(
      JSON.stringify(data),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    );

  } catch (error) {
    console.error('Podcast episodes API error:', error);
    return new Response(
      JSON.stringify({ error: 'Internal server error' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}
