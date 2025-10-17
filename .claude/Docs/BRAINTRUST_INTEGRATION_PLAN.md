# Braintrust Integration Plan

## Overview

Plan for integrating Braintrust logging across all Claude API and OpenAI API calls in the project. This provides unified observability, cost tracking, and performance monitoring for all LLM interactions.

## Integration Approaches

### 1. For Anthropic Claude API
- **Method**: Use Braintrust AI Proxy with OpenAI client libraries
- **Base URL**: `https://api.braintrust.dev/v1/proxy`
- **Approach**: Switch from `anthropic.Anthropic()` to `OpenAI()` with proxy
- **Benefit**: OpenAI-compatible interface automatically translates to Anthropic API

### 2. For OpenAI APIs
- **Method**: Use `braintrust.wrap_openai()` wrapper
- **Approach**: Wrap existing OpenAI clients with Braintrust instrumentation
- **Benefit**: Minimal code changes, automatic logging

## Installation & Setup

### Python Backend

```bash
pip install braintrust
```

### Next.js Frontend

```bash
cd web-apps/article-summarizer
npm install braintrust
```

### Environment Configuration

```bash
# .env or environment
BRAINTRUST_API_KEY=your-api-key-here
```

## Implementation Details

### 1. Claude API - `programs/article_summarizer/common/claude_client.py`

**Current Implementation** (lines 72-79):
```python
import anthropic

client = anthropic.Anthropic(api_key=api_key)

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=8000,
    messages=[{"role": "user", "content": prompt}]
)
```

**New Implementation**:
```python
import braintrust
from openai import OpenAI

# Initialize Braintrust (call once at startup)
braintrust.login()  # Uses BRAINTRUST_API_KEY env var

# Use OpenAI client with Braintrust proxy for Anthropic models
client = braintrust.wrap_openai(
    OpenAI(
        base_url="https://api.braintrust.dev/v1/proxy",
        api_key=api_key  # Your ANTHROPIC_API_KEY
    )
)

# Convert Anthropic message format to OpenAI format
response = client.chat.completions.create(
    model="claude-sonnet-4-20250514",
    max_tokens=8000,
    messages=[{"role": "user", "content": prompt}]
)

# Extract text from response
response_text = response.choices[0].message.content
```

**Why this approach**:
- Braintrust AI Proxy translates OpenAI API calls to Anthropic API calls
- All calls automatically logged to Braintrust
- Uses `wrap_openai()` for additional instrumentation
- Minimal changes to message format

---

### 2. OpenAI Whisper API - `programs/article_summarizer/processors/file_transcriber.py`

**Current Implementation** (lines 40-98):
```python
from openai import OpenAI

self.client = OpenAI(api_key=api_key)

transcript = self.client.audio.transcriptions.create(
    file=audio_file,
    model=Config.WHISPER_MODEL,
    response_format="verbose_json",
    timestamp_granularities=["word", "segment"]
)
```

**New Implementation**:
```python
import braintrust
from openai import OpenAI

# Initialize Braintrust (call once at startup)
braintrust.login()

# Wrap OpenAI client
self.client = braintrust.wrap_openai(OpenAI(api_key=api_key))

# Rest of the code stays the same
transcript = self.client.audio.transcriptions.create(
    file=audio_file,
    model=Config.WHISPER_MODEL,
    response_format="verbose_json",
    timestamp_granularities=["word", "segment"]
)
```

**Changes needed**:
- Add `import braintrust`
- Call `braintrust.login()` once at initialization
- Wrap client with `braintrust.wrap_openai()`
- All subsequent API calls automatically logged

---

### 3. OpenAI Chat API - `web-apps/article-summarizer/src/app/api/chat/route.ts`

**Current Implementation** (estimated):
```typescript
import { OpenAI } from 'openai';

const client = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

const stream = await client.chat.completions.create({
  model: 'gpt-4-turbo-preview',
  messages: messages,
  stream: true,
});
```

**New Implementation**:
```typescript
import { wrapOpenAI } from "braintrust";
import { OpenAI } from 'openai';

const client = wrapOpenAI(
  new OpenAI({
    apiKey: process.env.OPENAI_API_KEY,
  })
);

// Rest stays the same
const stream = await client.chat.completions.create({
  model: 'gpt-4-turbo-preview',
  messages: messages,
  stream: true,
});
```

**Environment variable** (add to `.env.local`):
```bash
BRAINTRUST_API_KEY=your-api-key-here
```

---

### 4. OpenAI Embeddings - `web-apps/article-summarizer/src/lib/embeddings.ts`

**Same pattern**:
```typescript
import { wrapOpenAI } from "braintrust";
import { OpenAI } from 'openai';

const client = wrapOpenAI(
  new OpenAI({
    apiKey: process.env.OPENAI_API_KEY,
  })
);

// Use client as normal
const response = await client.embeddings.create({
  model: 'text-embedding-3-small',
  input: text,
});
```

---

## Files to Modify

```
programs/article_summarizer/
├── common/
│   ├── claude_client.py          # Switch to OpenAI + Proxy
│   └── requirements.txt           # Add braintrust
└── processors/
    └── file_transcriber.py        # Wrap OpenAI client

web-apps/article-summarizer/
├── src/
│   ├── app/api/chat/route.ts     # Wrap OpenAI client
│   └── lib/embeddings.ts          # Wrap OpenAI client
└── package.json                   # Add braintrust
```

## Benefits

### Unified Logging
- All Claude API calls logged (via proxy)
- All OpenAI API calls logged (Whisper, Chat, Embeddings)
- Single dashboard in Braintrust to view all traces

### Performance Monitoring
- Track latency for each API call
- Monitor token usage across providers
- Compare performance between models

### Cost Tracking
- Automatic cost calculation for OpenAI
- Transparent pricing visibility

### Debugging
- See full request/response payloads
- Trace errors and failures
- Replay problematic requests

## Implementation Steps

1. **Install Dependencies**:
   ```bash
   # Python
   pip install braintrust

   # Next.js
   cd web-apps/article-summarizer && npm install braintrust
   ```

2. **Configure Environment**:
   ```bash
   export BRAINTRUST_API_KEY="your-key"
   ```

3. **Update Python Files**:
   - Modify `claude_client.py` to use OpenAI + Proxy
   - Modify `file_transcriber.py` to wrap client

4. **Update TypeScript Files**:
   - Wrap OpenAI client in `chat/route.ts`
   - Wrap OpenAI client in `embeddings.ts`

5. **Test Integration**:
   - Run article_summarizer and verify traces in Braintrust
   - Test chat interface and verify streaming works
   - Check embeddings API still functions correctly

## Considerations

### Anthropic API Compatibility
- The proxy approach means using OpenAI-style message format
- Anthropic-specific features (like `system` parameter separate from messages) need to be adapted to OpenAI format
- Most features are compatible, but edge cases may need testing

### Streaming Support
- Both approaches support streaming responses
- No changes needed to existing streaming logic

### Error Handling
- Braintrust wrapper is transparent - errors from underlying APIs pass through
- Add try/catch around `braintrust.login()` in case of network issues

### Performance
- Minimal overhead (< 1ms) for logging
- Proxy adds ~50-100ms latency for routing through Braintrust edge
- Cached requests return in < 100ms

## Resources

- [Braintrust AI Proxy Docs](https://www.braintrust.dev/docs/guides/proxy)
- [Braintrust Python SDK](https://www.braintrust.dev/docs/reference/libs/python)
- [Braintrust Cookbook Examples](https://github.com/braintrustdata/braintrust-cookbook)
- [OpenAI-compatible interface for Anthropic](https://www.braintrust.dev/blog/ai-proxy)

## Status

- [x] Research completed
- [x] Architecture designed
- [x] Documentation created
- [ ] Python backend implementation
- [ ] TypeScript frontend implementation
- [ ] Testing and validation
