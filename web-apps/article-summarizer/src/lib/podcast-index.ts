/**
 * Client-side API wrapper for PodcastIndex search
 * Calls our Next.js API route which handles authentication
 */
export async function searchPodcastIndex(query: string, type: 'podcast' | 'episode' = 'podcast') {
  const url = `/api/podcast-search?q=${encodeURIComponent(query)}&type=${type}`;

  const response = await fetch(url, {
    method: 'GET',
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
    throw new Error(errorData.error || `API error: ${response.status} ${response.statusText}`);
  }

  const data = await response.json();
  return data;
}

/**
 * Get episodes for a specific podcast by feed ID
 */
export async function getPodcastEpisodes(feedId: number) {
  const url = `/api/podcast-episodes?feedId=${feedId}`;

  const response = await fetch(url, {
    method: 'GET',
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
    throw new Error(errorData.error || `API error: ${response.status} ${response.statusText}`);
  }

  const data = await response.json();
  return data;
}
