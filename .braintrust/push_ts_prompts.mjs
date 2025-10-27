import * as braintrust from "braintrust";
import { CHAT_ASSISTANT_METADATA, buildChatSystemPrompt } from "./web-apps/article-summarizer/src/lib/prompts.js";

async function main() {
  // Initialize project (API key from BRAINTRUST_API_KEY env var)
  const project = braintrust.projects.create("automate-life");

  // Create chat assistant prompt
  project.prompts.create({
    slug: CHAT_ASSISTANT_METADATA.slug,
    name: CHAT_ASSISTANT_METADATA.name,
    description: "RAG chat assistant for article Q&A",
    model: CHAT_ASSISTANT_METADATA.model,
    temperature: CHAT_ASSISTANT_METADATA.temperature,
    max_tokens: CHAT_ASSISTANT_METADATA.maxTokens,
    messages: [
      {
        role: "system",
        content: `You are a helpful AI assistant that answers questions based on article summaries and transcripts.

Context from relevant articles:
{{{context}}}

Guidelines:
- Answer questions based on the provided context from articles
- Cite articles by their title when referencing specific information
- If the context doesn't contain relevant information to answer the question, politely say so
- Be conversational, helpful, and concise
- Use markdown formatting for better readability
- If asked about sources, refer to the article titles provided in context`,
      },
    ],
  });

  // Publish prompts to Braintrust
  await project.publish();
  console.log("✅ TypeScript prompts published to Braintrust");
}

main().catch((error) => {
  console.error("❌ Error pushing TypeScript prompts:", error);
  process.exit(1);
});
