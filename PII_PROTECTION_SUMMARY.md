# PII Protection Implementation Summary

## What Was Implemented

A comprehensive PII (Personally Identifiable Information) protection system has been added to your Gladly Conversation Analyzer. This system automatically detects and redacts PII before sending data to the Claude API, helping prevent PII violations even with a business account.

## Key Features

### 1. Automatic PII Detection
- Email addresses
- Phone numbers
- Credit card numbers
- Social Security Numbers
- IP addresses
- Physical addresses
- Customer/Conversation/User IDs (pseudonymized)

### 2. Flexible Redaction Modes
- **Hash mode** (default): Deterministic hashing - same input = same hash
- **Redact mode**: Generic placeholders like `[REDACTED_EMAIL]`
- **Remove mode**: Complete removal of PII
- **None mode**: Disabled (not recommended)

### 3. Integrated Protection
- Automatically applied to conversation data sent to Claude
- Automatically applied to survey data sent to Claude
- Automatically applied during topic extraction

## Files Created/Modified

### New Files
- `backend/utils/pii_protection.py` - Core PII protection utilities
- `docs/PII_PROTECTION.md` - Comprehensive documentation

### Modified Files
- `backend/utils/config.py` - Added PII configuration options
- `backend/utils/helpers.py` - Integrated PII protection into data formatting
- `backend/services/topic_extraction_service.py` - Added PII protection to transcripts
- `env.example` - Added PII configuration examples

## Recommended Actions

### 1. Review and Configure (Required)

Add these settings to your `.env` file on your EC2 instance:

```bash
# Recommended production settings
PII_REDACT_MODE=hash
PII_PRESERVE_IDS=false
PII_ENABLE_NAME_DETECTION=false
```

**Default behavior**: If you don't set these, the system defaults to `hash` mode with IDs pseudonymized, which is a safe default.

### 2. Test the Implementation

1. **Test locally first**:
   ```bash
   # Set in your local .env
   PII_REDACT_MODE=hash
   PII_PRESERVE_IDS=false
   ```

2. **Run a test query** through the web interface or API
3. **Check the logs** to verify PII is being redacted
4. **Review Claude responses** - you should see hashed IDs instead of original IDs

### 3. Deploy to Production

1. **Update your EC2 `.env` file**:
   ```bash
   # SSH into your EC2 instance
   cd /path/to/your/app
   nano .env
   
   # Add the PII protection settings
   PII_REDACT_MODE=hash
   PII_PRESERVE_IDS=false
   PII_ENABLE_NAME_DETECTION=false
   ```

2. **Restart your application**:
   ```bash
   # If using systemd
   sudo systemctl restart your-app-service
   
   # Or if running manually
   # Stop and restart your Flask app
   ```

3. **Verify it's working**:
   - Check application logs for PII protection messages
   - Test a query and verify IDs are pseudonymized

### 4. Monitor and Adjust

- **Review redacted data**: Periodically check what's being redacted
- **Adjust if needed**: If you see too many false positives, disable name detection
- **For debugging**: Temporarily set `PII_PRESERVE_IDS=true` if you need to see original IDs

## Configuration Options Explained

### PII_REDACT_MODE

| Mode | Description | Use Case |
|------|-------------|----------|
| `hash` | Deterministic hash (default) | **Recommended** - Maintains consistency across analyses |
| `redact` | Generic placeholder | Good for seeing what's redacted |
| `remove` | Complete removal | Maximum privacy, may affect analysis quality |
| `none` | Disabled | **Not recommended** - Only for testing |

### PII_PRESERVE_IDS

- `false` (default): IDs are pseudonymized (e.g., `CUS_abc123def456`)
- `true`: Keep original IDs (useful for debugging)

### PII_ENABLE_NAME_DETECTION

- `false` (default): Don't attempt to detect names in text
- `true`: Attempt to detect names (may have false positives)

## What Gets Protected

### Conversation Data
- Customer IDs → Pseudonymized
- Conversation IDs → Pseudonymized
- Email addresses in content → Hashed/Redacted
- Phone numbers in content → Hashed/Redacted
- Addresses in content → Hashed/Redacted
- Other PII patterns → Detected and redacted

### Survey Data
- Email addresses → Hashed/Redacted
- User IDs → Pseudonymized
- First/Last names → Always redacted
- Answer text → Scanned for PII patterns

## Example Transformation

**Before:**
```
Customer: CUST_12345
Conversation: CONV_67890
Content: "Hi, my email is john@example.com and my phone is 555-123-4567"
```

**After (hash mode):**
```
Customer: CUS_abc123def456
Conversation: CON_xyz789
Content: "Hi, my email is [EMAIL:def456] and my phone is [PHONE:abc123]"
```

## Important Notes

1. **Default is safe**: If you don't configure anything, the system defaults to `hash` mode with IDs pseudonymized
2. **No breaking changes**: Existing functionality continues to work
3. **Backward compatible**: Old data formats are still supported
4. **Performance impact**: Minimal - PII detection is fast regex-based

## Next Steps

1. ✅ **Review** the documentation in `docs/PII_PROTECTION.md`
2. ✅ **Configure** your `.env` file with PII protection settings
3. ✅ **Test** locally to verify it's working
4. ✅ **Deploy** to production
5. ✅ **Monitor** and adjust as needed

## Questions?

- See `docs/PII_PROTECTION.md` for detailed documentation
- Check `backend/utils/pii_protection.py` for implementation details
- Review application logs for PII protection activity

## Compliance Note

While this system helps protect PII, ensure you also:
- Follow your organization's data handling policies
- Comply with applicable privacy regulations (CCPA, etc.)
- Implement proper access controls
- Maintain audit logs
- Review data retention policies

