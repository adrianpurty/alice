# NexTTS Quickstart

Get up and running with NexTTS in 5 minutes.

---

## Installation

### Python SDK

```bash
pip install nexxtts
```

### Node.js SDK (coming soon)

```bash
npm install nexxtts
```

---

## Quick Start

### 1. Get Your API Key

Sign up at [nexxtts.io](https://nexxtts.io) and get your API key from the dashboard.

### 2. Generate Speech

```python
from nexxtts import NexTTS

client = NexTTS(api_key="nxtts_your_key")

audio = client.tts.generate(
    text="Hello, world!",
    voice="en-Carter"
)

audio.save("hello.mp3")
```

### 3. Stream Audio

```python
from nexxtts import NexTTS

client = NexTTS(api_key="nxtts_your_key")

for chunk in client.tts.stream(text="Hello, streaming world!"):
    audio_file.write(chunk)
```

### 4. Transcribe Audio

```python
from nexxtts import NexTTS

client = NexTTS(api_key="nxtts_your_key")

result = client.asr.transcribe(
    audio_url="https://example.com/audio.mp3",
    language="en"
)

print(result.text)
```

---

## Available Voices

```python
from nexxtts import NexTTS

client = NexTTS(api_key="nxtts_your_key")

# List available voices
voices = client.voices.list()
print(voices)

# Use a specific voice
audio = client.tts.generate(
    text="Custom voice example",
    voice="en-Emma"
)
```

---

## Cloud API Usage

### REST API

```bash
curl -X POST https://api.nexxtts.io/v1/tts/generate \
  -H "Authorization: Bearer nxtts_your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello from the REST API",
    "voice": "en-Carter"
  }'
```

### WebSocket Streaming

```javascript
const { NexTTS } = require('nexxtts');

const client = new NexTTS({ api_key: 'nxtts_your_key' });

const stream = client.tts.stream({
  text: 'Hello, websocket streaming!',
  voice: 'en-Carter'
});

stream.on('data', (chunk) => {
  // Handle audio chunk
  audioBuffer.push(chunk);
});

stream.on('end', () => {
  console.log('Stream complete');
});
```

---

## Error Handling

```python
from nexxtts import NexTTS, RateLimitError, AuthenticationError

client = NexTTS(api_key="nxtts_your_key")

try:
    audio = client.tts.generate(text="Hello!")
except RateLimitError as e:
    print(f"Rate limit exceeded: {e.message}")
    print(f"Your plan: {e.plan}")
    print(f"Upgrade at: https://nexxtts.io/dashboard")
except AuthenticationError as e:
    print(f"Invalid API key: {e.message}")
except Exception as e:
    print(f"Error: {e.message}")
```

---

## Common Issues

### Rate Limit Exceeded

```python
from nexxtts import NexTTS

client = NexTTS(api_key="nxtts_your_key")

# Check remaining requests
usage = client.usage.get()
print(f"Remaining: {usage.remaining}")
```

### Invalid API Key

Make sure your API key starts with `nxtts_` and is active in your dashboard.

### Audio Quality

For best quality, use:
- Short text chunks (<1000 chars)
- Standard voices (en-Carter, en-Emma)
- MP3 format at 192kbps

---

## Next Steps

- [API Reference](api-reference.md) - Full API documentation
- [Voice Library](https://nexxtts.io/voices) - Browse available voices
- [Pricing](https://nexxtts.io/pricing) - Upgrade your plan
- [Support](https://nexxtts.io/support) - Get help