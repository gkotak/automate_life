import { NextRequest } from 'next/server';

/**
 * API route to trigger post checking
 * Calls the content_checker_backend service
 */
export async function POST(request: NextRequest) {
  try {
    const contentCheckerUrl = process.env.CONTENT_CHECKER_API_URL || 'http://localhost:8001';
    const apiKey = process.env.CONTENT_CHECKER_API_KEY || '';

    // Call the content checker backend
    const response = await fetch(`${contentCheckerUrl}/api/posts/check`, {
      method: 'POST',
      headers: {
        'X-API-Key': apiKey,
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Post check failed:', errorText);
      return new Response(
        JSON.stringify({ error: 'Failed to check posts' }),
        { status: response.status, headers: { 'Content-Type': 'application/json' } }
      );
    }

    const data = await response.json();

    return new Response(
      JSON.stringify(data),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    );

  } catch (error) {
    console.error('Check posts API error:', error);
    return new Response(
      JSON.stringify({ error: 'Internal server error' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}
