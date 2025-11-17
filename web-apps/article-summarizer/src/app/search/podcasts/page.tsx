'use client';

import { useState } from 'react';
import { searchPodcastIndex, getPodcastEpisodes } from '@/lib/podcast-index';

interface SearchResult {
  id: number;
  title: string;
  author?: string;
  description?: string;
  feedUrl?: string;
  artwork?: string;
  itunesId?: number;
  episodeCount?: number;
  categories?: { [key: string]: string };
}

interface Episode {
  id: number;
  title: string;
  description?: string;
  datePublished: number;
  enclosureUrl?: string;
  link?: string;
  image?: string;
}

export default function PodcastSearchPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedPodcast, setSelectedPodcast] = useState<SearchResult | null>(null);
  const [episodes, setEpisodes] = useState<Episode[]>([]);
  const [episodesLoading, setEpisodesLoading] = useState(false);
  const [episodeSearchTerm, setEpisodeSearchTerm] = useState('');

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!searchTerm.trim()) {
      setError('Please enter a search term');
      return;
    }

    setLoading(true);
    setError(null);
    setResults([]);
    setSelectedPodcast(null);

    try {
      const data = await searchPodcastIndex(searchTerm, 'podcast');
      setResults(data.feeds || []);

      if ((data.feeds || []).length === 0) {
        setError('No results found. Try a different search term.');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to search podcasts');
      console.error('Search error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleViewEpisodes = async (podcast: SearchResult) => {
    setSelectedPodcast(podcast);
    setEpisodesLoading(true);
    setEpisodeSearchTerm('');

    try {
      const data = await getPodcastEpisodes(podcast.id);
      setEpisodes(data.items || []);
    } catch (err) {
      console.error('Error loading episodes:', err);
      setError('Failed to load episodes');
    } finally {
      setEpisodesLoading(false);
    }
  };

  // Basic stemming function to remove common suffixes
  const stem = (word: string): string => {
    word = word.toLowerCase();

    // Handle -ation/-tion words by removing 'ion' first, then handling potential 'at'/'t'
    if (word.endsWith('ation') && word.length > 7) {
      const base = word.slice(0, -5); // Remove 'ation', keep potential 'e'
      if (base.length >= 3) return base;
    }

    // Remove common suffixes (ordered by length to handle complex suffixes first)
    const suffixes = ['ibility', 'ability', 'ment', 'ness', 'tion', 'sion', 'ing', 'ed', 'er', 'or', 'ly', 'ate', 's'];
    for (const suffix of suffixes) {
      if (word.length > 4 && word.endsWith(suffix)) {
        let stemmed = word.slice(0, -suffix.length);

        // For 'ate' suffix, also try removing trailing 'e' to match 'ation' forms
        if (suffix === 'ate' && stemmed.endsWith('e')) {
          stemmed = stemmed.slice(0, -1);
        }

        // Only return if stem is at least 3 characters
        if (stemmed.length >= 3) {
          return stemmed;
        }
      }
    }
    return word;
  };

  // Tokenize and stem search terms
  const searchWords = episodeSearchTerm
    .toLowerCase()
    .split(/\s+/)
    .filter(w => w.length > 0)
    .map(w => ({ original: w, stemmed: stem(w) }));

  // Helper function to highlight matching words in text
  const highlightMatches = (text: string, searchTerms: { original: string; stemmed: string }[]): string => {
    if (!text || searchTerms.length === 0) return text;

    let result = text;
    const matchedRanges: { start: number; end: number }[] = [];

    // Find all matches
    const textLower = text.toLowerCase();
    const words = text.split(/(\W+)/); // Split but keep separators

    words.forEach((word, idx) => {
      const wordLower = word.toLowerCase();
      const wordStemmed = stem(wordLower);

      for (const { original, stemmed } of searchTerms) {
        const useSubstring = original.length >= 4;
        let shouldHighlight = false;

        // Check for stem match
        if (wordStemmed === stemmed && wordLower.length > 2) {
          shouldHighlight = true;
        }
        // Check for substring match (4+ chars)
        else if (useSubstring && wordLower.includes(original)) {
          shouldHighlight = true;
        }

        if (shouldHighlight) {
          // Mark this word for highlighting
          words[idx] = `<mark class="bg-yellow-200 px-0.5 rounded">${word}</mark>`;
          break; // Only highlight once per word
        }
      }
    });

    return words.join('');
  };

  // Score episodes based on fuzzy matching
  const scoredEpisodes = episodes.map(episode => {
    if (!episodeSearchTerm.trim()) {
      return { episode, score: 1, highlightedTitle: episode.title, highlightedDesc: episode.description };
    }

    const titleLower = (episode.title || '').toLowerCase();
    const descLower = (episode.description || '').toLowerCase();

    const titleWords = titleLower
      .split(/\W+/)
      .filter(w => w.length > 0);

    const descWords = descLower
      .split(/\W+/)
      .filter(w => w.length > 0);

    let score = 0;
    for (const { original, stemmed } of searchWords) {
      const searchTerm = original;
      const useSubstring = searchTerm.length >= 4;

      // Title matches
      for (const titleWord of titleWords) {
        // Exact stem match
        if (stem(titleWord) === stemmed) {
          score += 3;
        }
        // Substring match for longer queries (4+ chars)
        else if (useSubstring && titleWord.includes(searchTerm)) {
          score += 2;
        }
      }

      // Also check full title/description for substring matches (catches multi-word matches)
      if (useSubstring) {
        if (titleLower.includes(searchTerm)) {
          score += 1;
        }
      }

      // Description matches
      for (const descWord of descWords) {
        // Exact stem match
        if (stem(descWord) === stemmed) {
          score += 1;
        }
        // Substring match for longer queries
        else if (useSubstring && descWord.includes(searchTerm)) {
          score += 0.5;
        }
      }
    }

    // Generate highlighted versions
    const highlightedTitle = highlightMatches(episode.title, searchWords);
    const highlightedDesc = highlightMatches(episode.description || '', searchWords);

    return { episode, score, highlightedTitle, highlightedDesc };
  });

  // Filter and sort by score
  const filteredEpisodes = scoredEpisodes
    .filter(({ score }) => score > 0 || !episodeSearchTerm.trim())
    .sort((a, b) => b.score - a.score);

  const getPodcastIndexUrl = (result: SearchResult) => {
    return `https://podcastindex.org/podcast/${result.id}`;
  };

  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-6xl mx-auto">
        <div className="bg-white rounded-lg shadow-md p-8">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Podcast Search
            </h1>
            <p className="text-gray-600">
              Search for podcasts on PodcastIndex.org, then browse episodes
            </p>
          </div>

          {/* Search Form */}
          <form onSubmit={handleSearch} className="mb-8">
            <div className="space-y-4">
              {/* Search Input */}
              <div>
                <label htmlFor="search" className="block text-sm font-medium text-gray-700 mb-2">
                  Search for Podcasts
                </label>
                <div className="flex gap-2">
                  <input
                    id="search"
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Enter podcast name..."
                    className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#077331] focus:border-transparent"
                  />
                  <button
                    type="submit"
                    disabled={loading}
                    className={`px-6 py-2 rounded-lg font-medium text-white transition-colors ${
                      loading
                        ? 'bg-gray-400 cursor-not-allowed'
                        : 'bg-[#077331] hover:bg-[#055a24]'
                    }`}
                  >
                    {loading ? (
                      <span className="flex items-center">
                        <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Searching...
                      </span>
                    ) : (
                      'Search'
                    )}
                  </button>
                </div>
              </div>
            </div>
          </form>

          {/* Error Message */}
          {error && (
            <div className="mb-6 p-4 rounded-lg bg-red-50 text-red-800 border border-red-200">
              {error}
            </div>
          )}

          {/* Two Column Layout */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left Column - Podcast Results */}
            <div>
              {results.length > 0 && (
                <div>
                  <h2 className="text-xl font-semibold text-gray-900 mb-4">
                    Podcasts ({results.length})
                  </h2>
                  <div className="space-y-4">
                    {results.map((result) => (
                      <div
                        key={result.id}
                        className={`border rounded-lg p-4 transition-colors ${
                          selectedPodcast?.id === result.id
                            ? 'border-[#077331] bg-green-50'
                            : 'border-gray-200 hover:bg-gray-50'
                        }`}
                      >
                        <div className="flex gap-4">
                          {result.artwork && (
                            <img
                              src={result.artwork}
                              alt={result.title}
                              className="w-16 h-16 rounded-lg object-cover flex-shrink-0"
                            />
                          )}
                          <div className="flex-1 min-w-0">
                            <h3 className="text-base font-medium text-gray-900 mb-1 line-clamp-2">
                              {result.title}
                            </h3>
                            {result.author && (
                              <p className="text-xs text-gray-600 mb-2">
                                By {result.author}
                              </p>
                            )}
                            <div className="flex flex-wrap gap-2">
                              <button
                                onClick={() => handleViewEpisodes(result)}
                                className="inline-flex items-center px-3 py-1.5 bg-[#077331] text-white rounded-md hover:bg-[#055a24] transition-colors text-sm font-medium"
                              >
                                View Episodes
                              </button>
                              <a
                                href={getPodcastIndexUrl(result)}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center px-3 py-1.5 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition-colors text-sm"
                              >
                                <svg className="mr-1 h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                </svg>
                                Info
                              </a>
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {loading && (
                <div className="text-center py-12">
                  <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-[#077331]"></div>
                  <p className="mt-4 text-gray-600">Searching podcasts...</p>
                </div>
              )}

              {!loading && !error && results.length === 0 && searchTerm && (
                <div className="text-center py-12">
                  <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                  <p className="mt-4 text-gray-600">No podcasts found</p>
                </div>
              )}

              {!loading && results.length === 0 && !searchTerm && (
                <div className="text-center py-12">
                  <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                  <p className="mt-4 text-gray-600">Start searching for podcasts</p>
                </div>
              )}
            </div>

            {/* Right Column - Episodes */}
            <div>
              {selectedPodcast && (
                <div>
                  <div className="mb-4">
                    <h2 className="text-xl font-semibold text-gray-900 mb-2">
                      Episodes - {selectedPodcast.title}
                    </h2>
                    <input
                      type="text"
                      value={episodeSearchTerm}
                      onChange={(e) => setEpisodeSearchTerm(e.target.value)}
                      placeholder="Search episodes..."
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#077331] focus:border-transparent text-sm"
                    />
                  </div>

                  {episodesLoading ? (
                    <div className="text-center py-12">
                      <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-[#077331]"></div>
                      <p className="mt-4 text-sm text-gray-600">Loading episodes...</p>
                    </div>
                  ) : (
                    <div className="space-y-3 max-h-[600px] overflow-y-auto">
                      {filteredEpisodes.map(({ episode, highlightedTitle, highlightedDesc }) => (
                        <div
                          key={episode.id}
                          className="border border-gray-200 rounded-lg p-3 hover:bg-gray-50 transition-colors"
                        >
                          <h3
                            className="text-sm font-medium text-gray-900 mb-1 line-clamp-2"
                            dangerouslySetInnerHTML={{ __html: highlightedTitle || episode.title }}
                          />
                          <p className="text-xs text-gray-500 mb-2">
                            {formatDate(episode.datePublished)}
                          </p>
                          {highlightedDesc && (
                            <p
                              className="text-xs text-gray-700 line-clamp-2 mb-2"
                              dangerouslySetInnerHTML={{ __html: highlightedDesc }}
                            />
                          )}
                          {episode.link && (
                            <a
                              href={episode.link}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center text-xs text-[#077331] hover:text-[#055a24]"
                            >
                              View Episode
                              <svg className="ml-1 h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                              </svg>
                            </a>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Footer */}
          <div className="mt-8 pt-6 border-t border-gray-200">
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
