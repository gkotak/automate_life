/**
 * OpenAI Embeddings Utilities (with Braintrust logging)
 *
 * Shared functions for generating text embeddings used by both search and chat features.
 */

import { wrapOpenAI, initLogger } from 'braintrust';
import OpenAI from 'openai';

export interface EmbeddingOptions {
  model?: string
  dimensions?: number
}

const DEFAULT_OPTIONS: EmbeddingOptions = {
  model: 'text-embedding-3-small',
  dimensions: 384
}

// Initialize Braintrust logger
let braintrustLogger: ReturnType<typeof initLogger> | null = null;

function getBraintrustLogger() {
  if (!braintrustLogger && process.env.BRAINTRUST_API_KEY) {
    try {
      braintrustLogger = initLogger({
        apiKey: process.env.BRAINTRUST_API_KEY,
        projectName: 'automate-life',
      });
      console.log('✅ [BRAINTRUST] Logger initialized for embeddings');
    } catch (error) {
      console.warn('⚠️ [BRAINTRUST] Failed to initialize logger:', error);
    }
  }
  return braintrustLogger;
}

// Create wrapped OpenAI client for Braintrust logging
let cachedClient: OpenAI | null = null;

function getClient(): OpenAI {
  if (!cachedClient) {
    // Initialize logger first
    getBraintrustLogger();

    const openaiApiKey = process.env.OPENAI_API_KEY;
    if (!openaiApiKey) {
      throw new Error('OpenAI API key not configured');
    }
    cachedClient = wrapOpenAI(new OpenAI({
      apiKey: openaiApiKey,
    }));
  }
  return cachedClient;
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
  const { model, dimensions } = { ...DEFAULT_OPTIONS, ...options }

  const client = getClient();

  const response = await client.embeddings.create({
    input: text,
    model: model!,
    dimensions,
  });

  return response.data[0].embedding;
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
  const { model, dimensions } = { ...DEFAULT_OPTIONS, ...options }

  const client = getClient();

  const response = await client.embeddings.create({
    input: texts,
    model: model!,
    dimensions,
  });

  return response.data.map((item) => item.embedding);
}
