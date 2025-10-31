# Claude Model Compatibility Guide

## Overview

This document tracks which Claude models are available and working with our API configuration. Models may become deprecated or unavailable, so we maintain a fallback system.

**Key Recommendation**: Use **non-dated model aliases** (e.g., `claude-sonnet-4`) for maximum robustness. These automatically route to the latest version and avoid deprecation issues.

## Recommended Models (2025)

### Primary Recommendation: Sonnet 4
- **Model**: `claude-sonnet-4` (non-dated alias) ✅ **RECOMMENDED**
- **Why**: Best balance of performance, cost, and robustness for RAG applications
- **Benefits**: Non-dated alias routes to latest version automatically, optimized for RAG, 200k context window

### Alternative Models

| Model Name | Type | Status | Notes |
|-----------|------|--------|-------|
| `claude-sonnet-4` | Non-dated alias | ✅ Recommended | Best for RAG - routes to latest Sonnet 4 |
| `claude-opus-4` | Non-dated alias | ✅ Available | Higher capability, more expensive |
| `claude-3-sonnet-20240229` | Dated snapshot | ✅ Active | Fallback option |
| `claude-3-haiku-20240307` | Dated snapshot | ✅ Active | Fastest, most cost-effective |

## Working Models (Tested & Verified)

| Model Name | API Version | Status | Notes |
|-----------|-------------|--------|-------|
| `claude-sonnet-4` | `2023-06-01` | ✅ Recommended | Non-dated alias, routes to latest Sonnet 4 |
| `claude-opus-4` | `2023-06-01` | ✅ Available | Non-dated alias, routes to latest Opus 4 |
| `claude-3-sonnet-20240229` | `2023-06-01` | ✅ Active | Fallback option, good for RAG |
| `claude-3-opus-20240229` | `2023-06-01` | ⚠️ Deprecated | Not recommended for RAG (deprecated) |
| `claude-3-haiku-20240307` | `2023-06-01` | ✅ Active | Fastest, most cost-effective |

## Unavailable Models

| Model Name | Reason | Alternative |
|-----------|--------|-------------|
| `claude-3-5-sonnet` | Not available with current API key | Use `claude-sonnet-4` or `claude-3-sonnet-20240229` |
| `claude-3-5-sonnet-20241022` | Not available with current API key | Use `claude-sonnet-4` or `claude-3-sonnet-20240229` |
| `claude-3-5-sonnet-20240620` | Not available with current API key | Use `claude-sonnet-4` or `claude-3-sonnet-20240229` |
| `claude-3-5-haiku-20241022` | Not available with current API key | Use `claude-3-haiku-20240307` |

## API Version Compatibility

- **2023-06-01**: ✅ Works with all Claude 3 and Claude 4 models

## Best Practices

1. **Use Non-Dated Aliases**: Prefer `claude-sonnet-4` over `claude-sonnet-4-20250514`. Non-dated aliases automatically route to the latest version and are more robust against deprecation.

2. **Model Aliases**: The codebase supports automatic model aliasing. Unavailable models automatically fall back to working alternatives.

3. **Test New Models**: Before deploying, test new models with your API key to ensure availability.

4. **Monitor Deprecations**: Anthropic may deprecate models with notice. Check their [documentation](https://docs.anthropic.com/) regularly.

## Testing Model Availability

Run this on your server to test model availability:

```bash
docker exec gladly-prod python3 -c "
import requests, os
key = os.getenv('ANTHROPIC_API_KEY')
h = {'x-api-key': key, 'Content-Type': 'application/json', 'anthropic-version': '2023-06-01'}
for m in ['claude-sonnet-4', 'claude-opus-4', 'claude-3-sonnet-20240229', 'claude-3-haiku-20240307']:
    r = requests.post('https://api.anthropic.com/v1/messages', headers=h, json={'model': m, 'max_tokens': 10, 'messages': [{'role': 'user', 'content': 'hi'}]}, timeout=10)
    print(f'{m}: {\"✅\" if r.status_code == 200 else f\"❌ {r.status_code}\"}')
"
```

## Model Selection Guidelines

- **Best for RAG**: `claude-sonnet-4` (non-dated alias) ⭐ **RECOMMENDED**
- **Best Performance**: `claude-opus-4` (if available and budget allows)
- **Best Balance**: `claude-3-sonnet-20240229` (fallback option)
- **Best Speed/Cost**: `claude-3-haiku-20240307`

## Why Non-Dated Aliases Are Better

1. **Automatic Updates**: Non-dated aliases (e.g., `claude-sonnet-4`) automatically route to the latest version
2. **Deprecation Resilience**: No need to update model names when Anthropic releases new versions
3. **Simplicity**: Easier to remember and use than dated snapshots
4. **Future-Proof**: Your code continues working even as new versions are released

## Migration Notes

- **Old Default**: `claude-3-opus-20240229` (deprecated)
- **New Default**: `claude-sonnet-4` (non-dated alias)
- **Automatic Fallback**: If Sonnet 4 is unavailable, system falls back to `claude-3-sonnet-20240229`

## Last Updated

- **Date**: January 2025
- **Default Model**: `claude-sonnet-4` (non-dated alias)
- **Recommended**: Use non-dated aliases for maximum robustness

