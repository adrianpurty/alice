# NexTTS API Reference

> **Version**: 1.0.0  
> **Base URL**: `https://api.nexxtts.io`

---

## Authentication

### API Keys

All API requests require authentication using an API key. Include your API key in the `Authorization` header:

```bash
curl -H "Authorization: Bearer nxtts_your_api_key" https://api.nexxtts.io/v1/tts/generate
```

#### Create API Key

```http
POST /v1/auth/keys
```

**Request:**
```json
{
  "name": "production-key"
}
```

**Response:**
```json
{
  "key": "nxtts_abc123...",
  "name": "production-key",
  "created_at": "2026-04-25T10:00:00Z"
}
```

> **Important:** Save the API key immediately. It will not be shown again.

#### List API Keys

```http
GET /v1/auth/keys
```

**Response:**
```json
{
  "keys": [
    {
      "id": "uuid",
      "name": "production-key",
      "is_active": true,
      "created_at": "2026-04-25T10:00:00Z",
      "last_used_at": "2026-04-25T12:00:00Z"
    }
  ]
}
```

#### Revoke API Key

```http
DELETE /v1/auth/keys/{key_id}
```

**Response:**
```json
{
  "success": true
}
```

---

## Text-to-Speech (TTS)

### Generate Audio

```http
POST /v1/tts/generate
```

Generate full audio from text.

**Request:**
```json
{
  "text": "Hello, welcome to NexTTS!",
  "voice": "en-Carter",
  "format": "mp3",
  "speed": 1.0
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | string | Yes | Text to synthesize (max 5000 chars) |
| `voice` | string | No | Voice ID (default: en-Carter) |
| `format` | string | No | Audio format: `mp3`, `wav`, `ogg` |
| `speed` | float | No | Speech speed (0.5 - 2.0) |

**Response:**
```json
{
  "audio_url": "https://cdn.nexxtts.io/audio/abc123.mp3",
  "duration_sec": 2.5,
  "tokens_used": 150
}
```

### Stream Audio

```http
WebSocket /v1/tts/stream
```

Stream audio chunks in real-time.

**Connect:**
```javascript
const ws = new WebSocket('wss://api.nexxtts.io/v1/tts/stream', {
  headers: { 'Authorization': 'Bearer nxtts_your_key' }
});

ws.on('open', () => {
  ws.send(JSON.stringify({
    text: "Hello world",
    voice: "en-Carter"
  }));
});

ws.on('message', (audioChunk) => {
  // Handle audio chunks
});
```

**Response (streamed):**
```
<audio-chunk-1><audio-chunk-2><audio-chunk-3>...
```

---

## Automatic Speech Recognition (ASR)

### Transcribe Audio

```http
POST /v1/asr/transcribe
```

Transcribe audio to text.

**Request:**
```json
{
  "audio_url": "https://example.com/audio.mp3",
  "language": "en",
  "model": "base"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `audio_url` | string | Yes | URL to audio file |
| `language` | string | No | Language code (default: auto-detect) |
| `model` | string | No | Model size: `base`, `large` |

**Response:**
```json
{
  "text": "Hello, this is a transcription.",
  "language": "en",
  "confidence": 0.95,
  "duration_sec": 5.2
}
```

---

## Usage

### Get Current Usage

```http
GET /v1/usage
```

**Response:**
```json
{
  "user_id": "uuid",
  "plan": "pro",
  "requests_this_month": 1250,
  "tokens_used": 45000,
  "remaining": -1
}
```

### Get Usage History

```http
GET /v1/usage/history
```

**Response:**
```json
{
  "history": [
    {
      "date": "2026-04",
      "requests": 1250,
      "tokens": 45000
    },
    {
      "date": "2026-03",
      "requests": 980,
      "tokens": 35000
    }
  ]
}
```

---

## Billing

### Create Subscription

```http
POST /v1/billing/subscribe
```

**Request:**
```json
{
  "plan": "pro"
}
```

**Response:**
```json
{
  "subscription_id": "sub_xxx",
  "status": "active",
  "current_period_end": "2026-05-25T10:00:00Z"
}
```

### List Invoices

```http
GET /v1/billing/invoices
```

**Response:**
```json
{
  "invoices": [
    {
      "id": "in_xxx",
      "amount": 4900,
      "status": "paid",
      "created": "2026-04-01T00:00:00Z"
    }
  ]
}
```

### Customer Portal

```http
POST /v1/billing/portal
```

**Response:**
```json
{
  "url": "https://billing.stripe.com/p/session/xxx"
}
```

---

## Monitoring

### Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "checks": {
    "database": { "healthy": true, "message": "OK" },
    "stripe": { "healthy": true, "message": "OK" },
    "system": { "healthy": true, "cpu_percent": 45, "memory_percent": 62 }
  },
  "timestamp": 1714041600
}
```

### Metrics

```http
GET /metrics
```

Returns Prometheus-formatted metrics.

---

## Error Codes

| Code | Description |
|------|-------------|
| `400` | Bad Request - Invalid parameters |
| `401` | Unauthorized - Invalid API key |
| `403` | Forbidden - Rate limit exceeded |
| `429` | Too Many Requests - Upgrade plan |
| `500` | Internal Server Error |

---

## Rate Limits

| Plan | Requests/Month | Voices | Audio Minutes |
|------|---------------|--------|--------------|
| Free | 100 | 1 | 10 |
| Pay-as-you-go | Unlimited | 5 | Unlimited |
| Pro | Unlimited | 10 | Unlimited |
| Enterprise | Unlimited | Unlimited | Unlimited |