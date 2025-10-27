import * as braintrust from "braintrust";

async function main() {
  // Initialize project (API key from BRAINTRUST_API_KEY env var)
  const project = braintrust.projects.create({ name: "automate-life" });

  // Create chat assistant prompt
  // Values from src/lib/prompts.ts CHAT_ASSISTANT_METADATA
  project.prompts.create({
    slug: "chat-assistant",
    name: "Chat Assistant",
    description: "RAG chat assistant for article Q&A",
    model: "gpt-4-turbo-preview",
    params: {
      temperature: 0.7,
      max_tokens: 1500,
    },
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
    if_exists: "replace",
  });

  // Publish prompts to Braintrust
  await project.publish();
  console.log("✅ TypeScript prompts published to Braintrust");
}

main().catch((error) => {
  console.error("❌ Error pushing TypeScript prompts:", error);
  process.exit(1);
});
