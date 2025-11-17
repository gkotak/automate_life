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
  // Hash is computed as: SHA1(apiKey + apiSecret + unixTimestamp)
  const authString = API_KEY + API_SECRET + timestamp;
  const authHash = crypto.createHash('sha1').update(authString).digest('hex');

  // Debug logging (without sensitive data)
  console.log('Auth Debug:', {
    apiKeyLength: API_KEY.length,
    apiSecretLength: API_SECRET.length,
    timestamp: timestamp,
    authHashLength: authHash.length,
  });

  return {
    'User-Agent': 'AutomateLife/1.0',
    'X-Auth-Date': timestamp.toString(),
    'X-Auth-Key': API_KEY,
    'Authorization': authHash,
  };
}

/**
 * API route to search PodcastIndex.org
 * GET /api/podcast-search?q=search+term&type=podcast|episode
 */
export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const query = searchParams.get('q');
    const type = searchParams.get('type') || 'podcast';

    if (!query) {
      return new Response(
        JSON.stringify({ error: 'Query parameter "q" is required' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    if (type !== 'podcast' && type !== 'episode') {
      return new Response(
        JSON.stringify({ error: 'Type must be "podcast" or "episode"' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    // Use /search/byterm for podcasts and /search/byperson for episodes
    // Note: Episode search searches for episodes where the person/term is mentioned
    const endpoint = type === 'podcast' ? '/search/byterm' : '/search/byperson';
    const url = `${BASE_URL}${endpoint}?q=${encodeURIComponent(query)}`;

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
    console.error('Podcast search API error:', error);
    return new Response(
      JSON.stringify({ error: 'Internal server error' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}
