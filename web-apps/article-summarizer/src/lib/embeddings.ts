/**
 * OpenAI Embeddings Utilities
 *
 * Shared functions for generating text embeddings used by both search and chat features.
 */

export interface EmbeddingOptions {
  model?: string
  dimensions?: number
}

const DEFAULT_OPTIONS: EmbeddingOptions = {
  model: 'text-embedding-3-small',
  dimensions: 384
}

/**
 * Generates an embedding vector for the given text using OpenAI's API.
 *
 * @param text - The text to generate an embedding for
 * @param options - Optional configuration for the embedding model
 * @returns The embedding vector as an array of numbers
 * @throws Error if OpenAI API key is not configured or request fails
 */
export async function generateEmbedding(
  text: string,
  options: EmbeddingOptions = {}
): Promise<number[]> {
  const openaiApiKey = process.env.OPENAI_API_KEY

  if (!openaiApiKey) {
    throw new Error('OpenAI API key not configured')
  }

  const { model, dimensions } = { ...DEFAULT_OPTIONS, ...options }

  const response = await fetch('https://api.openai.com/v1/embeddings', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${openaiApiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      input: text,
      model,
      dimensions,
    }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(`Failed to generate embedding: ${response.statusText} - ${JSON.stringify(error)}`)
  }

  const data = await response.json()
  return data.data[0].embedding
}

/**
 * Batch generates embeddings for multiple texts.
 *
 * @param texts - Array of texts to generate embeddings for
 * @param options - Optional configuration for the embedding model
 * @returns Array of embedding vectors
 */
export async function generateEmbeddings(
  texts: string[],
  options: EmbeddingOptions = {}
): Promise<number[][]> {
  const openaiApiKey = process.env.OPENAI_API_KEY

  if (!openaiApiKey) {
    throw new Error('OpenAI API key not configured')
  }

  const { model, dimensions } = { ...DEFAULT_OPTIONS, ...options }

  const response = await fetch('https://api.openai.com/v1/embeddings', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${openaiApiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      input: texts,
      model,
      dimensions,
    }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(`Failed to generate embeddings: ${response.statusText} - ${JSON.stringify(error)}`)
  }

  const data = await response.json()
  return data.data.map((item: any) => item.embedding)
}
