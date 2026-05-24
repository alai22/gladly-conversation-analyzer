# Text interview examples

Example fixtures for the AI 1:1 Text Interview feature.

| File | Description |
|------|-------------|
| `config.example.json` | Researcher setup payload for `POST /api/interviews/sessions` |
| `transcript.example.json` | Sample participant/assistant turns |
| `insights.example.json` | Structured output schema after session end |

## API quick reference

```bash
# Create session (authenticated)
curl -X POST http://localhost:5000/api/interviews/sessions \
  -H "Content-Type: application/json" \
  -H "X-Auth-Token: $TOKEN" \
  -d @config.example.json

# Participant message (public token)
curl -X POST http://localhost:5000/api/interviews/join/$TOKEN/message \
  -H "Content-Type: application/json" \
  -d '{"message": "Yes, that is fine"}'
```

Set `INTERVIEW_MOCK_LLM=true` to run without Anthropic API calls.
