# Claude Model Compatibility Guide

## Overview

This document tracks which Claude models are available and working with our API configuration. Models may become deprecated or unavailable, so we maintain a fallback system.

## Working Models (Tested & Verified)

| Model Name | API Version | Status | Notes |
|-----------|-------------|--------|-------|
| `claude-3-opus-20240229` | `2023-06-01` | ✅ Active | Most capable, recommended default |
| `claude-3-sonnet-20240229` | `2023-06-01` | ✅ Active | Balanced performance |
| `claude-3-haiku-20240307` | `2023-06-01` | ✅ Active | Fastest, most cost-effective |

## Unavailable Models

| Model Name | Reason | Alternative |
|-----------|--------|-------------|
| `claude-3-5-sonnet` | Not available with current API key | Use `claude-3-opus-20240229` |
| `claude-3-5-sonnet-20241022` | Not available with current API key | Use `claude-3-opus-20240229` |
| `claude-3-5-sonnet-20240620` | Not available with current API key | Use `claude-3-opus-20240229` |
| `claude-3-5-haiku-20241022` | Not available with current API key | Use `claude-3-haiku-20240307` |

## API Version Compatibility

- **2023-06-01**: ✅ Works with all Claude 3 models
- **2024-10-01**: ❌ Invalid version (returns 400 error)

## Best Practices

1. **Avoid Dated Model Snapshots**: Dated models (e.g., `claude-3-5-sonnet-20240620`) can be deprecated. Prefer non-dated versions or verified dated snapshots.

2. **Use Model Aliases**: The codebase supports model aliases that automatically map to working models.

3. **Test New Models**: Before deploying, test new models with your API key to ensure availability.

4. **Monitor Deprecations**: Anthropic may deprecate models with notice. Check their [documentation](https://docs.anthropic.com/) regularly.

## Testing Model Availability

Run this on your server to test model availability:

```bash
docker exec gladly-prod python3 -c "
import requests, os
key = os.getenv('ANTHROPIC_API_KEY')
h = {'x-api-key': key, 'Content-Type': 'application/json', 'anthropic-version': '2023-06-01'}
for m in ['claude-3-opus-20240229', 'claude-3-sonnet-20240229', 'claude-3-haiku-20240307']:
    r = requests.post('https://api.anthropic.com/v1/messages', headers=h, json={'model': m, 'max_tokens': 10, 'messages': [{'role': 'user', 'content': 'hi'}]}, timeout=10)
    print(f'{m}: {\"✅\" if r.status_code == 200 else f\"❌ {r.status_code}\"}')
"
```

## Model Selection Guidelines

- **Best Performance**: `claude-3-opus-20240229`
- **Best Balance**: `claude-3-sonnet-20240229`
- **Best Speed/Cost**: `claude-3-haiku-20240307`

## Last Updated

- **Date**: October 31, 2025
- **Tested API Key**: sk-ant-api03-...
- **Verified Models**: claude-3-opus-20240229, claude-3-sonnet-20240229, claude-3-haiku-20240307

