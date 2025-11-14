# PII Protection Guide

This document describes the PII (Personally Identifiable Information) protection features implemented in the Gladly Conversation Analyzer to help prevent PII violations when sending data to external APIs like Claude.

## Overview

Even with a business account with Claude, it's important to protect customer data. This system automatically detects and redacts PII before sending conversation and survey data to the Claude API.

## What PII is Protected?

The system detects and protects the following types of PII:

### Automatically Detected
- **Email addresses**: `user@example.com` → `[EMAIL:abc123def456]`
- **Phone numbers**: `(555) 123-4567` → `[PHONE:xyz789]`
- **Credit card numbers**: `1234-5678-9012-3456` → `[CREDIT_CARD:...]`
- **Social Security Numbers**: `123-45-6789` → `[SSN:...]`
- **IP addresses**: `192.168.1.1` → `[IP_ADDRESS:...]`
- **Physical addresses**: Street addresses with common patterns

### Structured Data Fields
- **Customer IDs**: Pseudonymized (e.g., `CUS_abc123def456`)
- **Conversation IDs**: Pseudonymized (e.g., `CON_xyz789`)
- **User IDs**: Pseudonymized (e.g., `USR_def456`)
- **Email fields**: Redacted or hashed
- **First/Last names**: Redacted

### Optional Detection
- **Names in text**: Can be enabled but may have false positives

## Configuration

PII protection is configured via environment variables in your `.env` file:

### PII_REDACT_MODE

Controls how PII is handled:

- **`hash`** (default): Replace PII with deterministic hash
  - Same input always produces same hash
  - Useful for maintaining consistency across analyses
  - Example: `john@example.com` → `[EMAIL:abc123def456]`
  
- **`redact`**: Replace with generic placeholder
  - Example: `john@example.com` → `[REDACTED_EMAIL]`
  
- **`remove`**: Remove PII entirely
  - Example: `Contact john@example.com` → `Contact`
  
- **`none`**: Disable PII protection
  - ⚠️ **Not recommended for production use**

### PII_PRESERVE_IDS

- **`false`** (default): Customer/conversation IDs are pseudonymized
- **`true`**: Keep original IDs (may be needed for debugging)

### PII_ENABLE_NAME_DETECTION

- **`false`** (default): Don't attempt to detect names in text
- **`true`**: Attempt to detect and redact names (may have false positives)

## Example Configuration

```bash
# Recommended production configuration
PII_REDACT_MODE=hash
PII_PRESERVE_IDS=false
PII_ENABLE_NAME_DETECTION=false

# For debugging (preserve IDs but still redact other PII)
PII_REDACT_MODE=hash
PII_PRESERVE_IDS=true
PII_ENABLE_NAME_DETECTION=false

# Maximum protection (redact everything)
PII_REDACT_MODE=redact
PII_PRESERVE_IDS=false
PII_ENABLE_NAME_DETECTION=true
```

## How It Works

### Automatic Protection

PII protection is automatically applied when:

1. **Conversation data** is formatted for Claude API (RAG queries)
2. **Survey data** is formatted for Claude API (Survicate analysis)
3. **Topic extraction** processes conversation transcripts

### Protection Flow

```
Original Data → PII Detection → Redaction/Pseudonymization → Claude API
```

1. Data is scanned for PII patterns
2. Detected PII is replaced based on `PII_REDACT_MODE`
3. IDs are pseudonymized (unless `PII_PRESERVE_IDS=true`)
4. Sanitized data is sent to Claude API

## Examples

### Before Protection

```json
{
  "customerId": "CUST_12345",
  "conversationId": "CONV_67890",
  "content": {
    "type": "EMAIL",
    "subject": "Order Issue",
    "body": "Hi, my name is John Smith. My email is john.smith@example.com and my phone is 555-123-4567. I live at 123 Main St, Anytown, ST 12345."
  }
}
```

### After Protection (hash mode)

```json
{
  "customerId": "CUS_abc123def456",
  "conversationId": "CON_xyz789",
  "content": {
    "type": "EMAIL",
    "subject": "Order Issue",
    "body": "Hi, my name is [POTENTIAL_NAME:...]. My email is [EMAIL:def456] and my phone is [PHONE:abc123]. I live at [ADDRESS_STREET:...]."
  }
}
```

### After Protection (redact mode)

```json
{
  "customerId": "CUS_abc123def456",
  "conversationId": "CON_xyz789",
  "content": {
    "type": "EMAIL",
    "subject": "Order Issue",
    "body": "Hi, my name is [REDACTED_POTENTIAL_NAME]. My email is [REDACTED_EMAIL] and my phone is [REDACTED_PHONE]. I live at [REDACTED_ADDRESS_STREET]."
  }
}
```

## Survey Data Protection

Survey responses are also protected:

- **Email addresses**: Redacted or hashed
- **User IDs**: Pseudonymized
- **First/Last names**: Always redacted
- **Answer text**: Scanned for PII patterns

## Best Practices

### For Production Use

1. **Always enable PII protection**: Set `PII_REDACT_MODE=hash` or `redact`
2. **Pseudonymize IDs**: Keep `PII_PRESERVE_IDS=false` unless debugging
3. **Monitor for false positives**: Review redacted data periodically
4. **Document your configuration**: Note which mode you're using and why

### For Development/Testing

1. You may temporarily set `PII_PRESERVE_IDS=true` to preserve IDs for debugging
2. Use `PII_REDACT_MODE=redact` to see what's being redacted
3. Never commit `.env` files with `PII_REDACT_MODE=none` to version control

### Compliance Considerations

While this system helps protect PII, consider:

- **Data retention policies**: How long is data stored?
- **Access controls**: Who can access the data?
- **Audit logging**: Are PII redactions logged?
- **Legal requirements**: Does your jurisdiction require specific protections?

## Limitations

1. **Pattern-based detection**: Uses regex patterns, may miss some PII formats
2. **Context-dependent**: Some PII (like names) requires context to detect accurately
3. **False positives**: Name detection may flag non-names as PII
4. **Not encryption**: Redaction is not encryption - don't rely on it for highly sensitive data

## Troubleshooting

### PII Not Being Redacted

1. Check your `.env` file has `PII_REDACT_MODE` set (not `none`)
2. Verify the configuration is loaded: Check application logs
3. Ensure you're using the latest version with PII protection

### Too Many False Positives

1. Disable name detection: `PII_ENABLE_NAME_DETECTION=false`
2. Use `hash` mode instead of `redact` to see what's being hashed
3. Review the patterns in `backend/utils/pii_protection.py`

### Need to Debug IDs

1. Temporarily set `PII_PRESERVE_IDS=true`
2. Remember to set it back to `false` for production

## Technical Details

### Implementation

- **Module**: `backend/utils/pii_protection.py`
- **Integration points**:
  - `backend/utils/helpers.py` - `format_conversation_for_claude()`, `format_survey_for_claude()`
  - `backend/services/topic_extraction_service.py` - `_format_conversation_transcript()`

### Customization

To add custom PII patterns, edit `backend/utils/pii_protection.py` and add patterns to the `PATTERNS` dictionary.

## Support

For questions or issues with PII protection:

1. Review this documentation
2. Check application logs for PII protection messages
3. Review the code in `backend/utils/pii_protection.py`
4. Test with different `PII_REDACT_MODE` values to understand behavior

## Related Documentation

- [Deployment Guide](DEPLOYMENT.md)
- [Configuration Guide](../README.md#configuration)
- [Claude API Usage](README_claude_api.md)

