"""
Configuration utilities
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def _env_float_clamped(env_name: str, default: str, lo: float, hi: float) -> float:
    """Parse env as float; invalid values fall back to default; clamp to [lo, hi]."""
    try:
        v = float(os.getenv(env_name, default))
    except (TypeError, ValueError):
        v = float(default)
    return max(lo, min(hi, v))


class Config:
    """Application configuration"""
    
    # API Configuration
    ANTHROPIC_API_KEY: Optional[str] = os.getenv('ANTHROPIC_API_KEY')
    # Default: Haiku 4.5 non-dated alias (replaces retired claude-3-haiku-20240307, Apr 2026)
    CLAUDE_MODEL: str = os.getenv('CLAUDE_MODEL', 'claude-haiku-4-5')
    CLAUDE_API_TIMEOUT: int = int(os.getenv('CLAUDE_API_TIMEOUT', '120'))  # Default 120 seconds for complex queries
    # Bounded retries on HTTP 429 from Anthropic (respect Retry-When possible via Retry-After header).
    CLAUDE_RETRY_MAX_ATTEMPTS: int = int(os.getenv('CLAUDE_RETRY_MAX_ATTEMPTS', '3'))
    CLAUDE_RETRY_BASE_DELAY_SEC: float = float(os.getenv('CLAUDE_RETRY_BASE_DELAY_SEC', '2'))
    CLAUDE_RETRY_MAX_DELAY_SEC: float = float(os.getenv('CLAUDE_RETRY_MAX_DELAY_SEC', '60'))
    
    @classmethod
    def get_api_key_status(cls) -> dict:
        """Get status of API key for debugging"""
        key_present = cls.ANTHROPIC_API_KEY is not None
        key_length = len(cls.ANTHROPIC_API_KEY) if cls.ANTHROPIC_API_KEY else 0
        key_prefix = cls.ANTHROPIC_API_KEY[:12] + "..." if key_present and key_length > 12 else "N/A"
        return {
            'present': key_present,
            'length': key_length,
            'prefix': key_prefix
        }
    
    # Model aliases and fallbacks
    # Maps deprecated/unavailable models to working alternatives
    # Note: We don't alias Claude 4 models here - let them be tried first, fallback system handles failures
    MODEL_ALIASES = {
        # Retired Haiku 3 / 3.5 Haiku -> Haiku 4.5
        'claude-3-haiku-20240307': 'claude-haiku-4-5',
        'claude-3-5-haiku-20241022': 'claude-haiku-4-5',
        # Legacy Claude 3.5 Sonnet snapshots -> Sonnet 4 alias
        'claude-3-5-sonnet': 'claude-sonnet-4',
        'claude-3-5-sonnet-20241022': 'claude-sonnet-4',
        'claude-3-5-sonnet-20240620': 'claude-sonnet-4',
        # Legacy Claude 3 Sonnet/Opus -> current aliases
        'claude-3-opus-20240229': 'claude-opus-4',
        'claude-3-sonnet-20240229': 'claude-sonnet-4',
    }
    
    # List of verified working models (tested with current API key)
    # Ordered by preference for fallback - put verified working models first
    VERIFIED_MODELS = [
        'claude-haiku-4-5',
        'claude-haiku-4-5-20251001',
        'claude-sonnet-4',
        'claude-opus-4',
    ]
    
    FALLBACK_MODEL = 'claude-haiku-4-5'
    
    @classmethod
    def resolve_model(cls, requested_model: Optional[str] = None) -> str:
        """
        Resolve a model name, applying aliases and fallbacks.
        
        Args:
            requested_model: The requested model name (or None to use default)
            
        Returns:
            A working model name
        """
        model = requested_model or cls.CLAUDE_MODEL
        
        # Check if it's an alias
        if model in cls.MODEL_ALIASES:
            logger = __import__('logging').getLogger('config')
            logger.info(f"Model alias '{model}' mapped to '{cls.MODEL_ALIASES[model]}'")
            return cls.MODEL_ALIASES[model]
        
        return model
    
    # Gladly API Configuration
    GLADLY_API_KEY: Optional[str] = os.getenv('GLADLY_API_KEY')
    GLADLY_AGENT_EMAIL: Optional[str] = os.getenv('GLADLY_AGENT_EMAIL')
    
    # Zoom API Configuration
    ZOOM_ACCOUNT_ID: Optional[str] = os.getenv('ZOOM_ACCOUNT_ID')
    ZOOM_CLIENT_ID: Optional[str] = os.getenv('ZOOM_CLIENT_ID')
    ZOOM_CLIENT_SECRET: Optional[str] = os.getenv('ZOOM_CLIENT_SECRET')
    
    # Jira API Configuration (Bug Triage Copilot)
    JIRA_BASE_URL: str = os.getenv('JIRA_BASE_URL', 'https://halocollar.atlassian.net').rstrip('/')
    JIRA_EMAIL: Optional[str] = os.getenv('JIRA_EMAIL')
    JIRA_API_TOKEN: Optional[str] = os.getenv('JIRA_API_TOKEN')
    JIRA_CLIENT_ID: Optional[str] = os.getenv('JIRA_CLIENT_ID')
    JIRA_CLIENT_SECRET: Optional[str] = os.getenv('JIRA_CLIENT_SECRET')
    JIRA_OAUTH_TOKENS_FILE: str = os.getenv('JIRA_OAUTH_TOKENS_FILE', 'data/jira_oauth_tokens.json')
    # App base URL for OAuth callback (e.g. https://insight.halocollar.com). Required for Jira OAuth.
    APP_BASE_URL: Optional[str] = os.getenv('APP_BASE_URL')
    # Backlog overview: two Claude calls by default, optional third (description refine for priority table).
    # Pass 2 default 8192: scorecard JSON with many rows + reach notes often exceeds 4k output tokens.
    JIRA_BACKLOG_OVERVIEW_PASS1_MAX_TOKENS: int = int(os.getenv('JIRA_BACKLOG_OVERVIEW_PASS1_MAX_TOKENS', '4096'))
    JIRA_BACKLOG_OVERVIEW_PASS2_MAX_TOKENS: int = int(os.getenv('JIRA_BACKLOG_OVERVIEW_PASS2_MAX_TOKENS', '8192'))
    # Claude sampling for all backlog-overview passes (pass1/2/2b/title). Default 0 reduces run-to-run variance.
    JIRA_BACKLOG_OVERVIEW_TEMPERATURE: float = _env_float_clamped(
        'JIRA_BACKLOG_OVERVIEW_TEMPERATURE', '0', 0.0, 1.0
    )
    # Optional third call: refine ## Priority review using description excerpts for keys from pass-2 reprioritization table.
    JIRA_BACKLOG_OVERVIEW_DEEP_PASS_ENABLED: bool = os.getenv('JIRA_BACKLOG_OVERVIEW_DEEP_PASS', '1').lower() in (
        '1', 'true', 'yes',
    )
    JIRA_BACKLOG_OVERVIEW_DEEP_MAX_KEYS: int = int(os.getenv('JIRA_BACKLOG_OVERVIEW_DEEP_MAX_KEYS', '40'))
    JIRA_BACKLOG_OVERVIEW_PASS2B_MAX_TOKENS: int = int(os.getenv('JIRA_BACKLOG_OVERVIEW_PASS2B_MAX_TOKENS', '4096'))
    # Title scan + rewrite run on every backlog overview by default (unless disabled below).
    JIRA_BACKLOG_TITLE_REWRITE_ENABLED: bool = os.getenv('JIRA_BACKLOG_TITLE_REWRITE_ENABLED', '1').lower() in (
        '1', 'true', 'yes',
    )
    # Emergency kill switch: set to 1 to skip title scan/rewrite entirely.
    JIRA_BACKLOG_TITLE_REWRITE_DISABLED: bool = os.getenv('JIRA_BACKLOG_TITLE_REWRITE_DISABLED', '0').lower() in (
        '1', 'true', 'yes',
    )
    JIRA_BACKLOG_TITLE_REWRITE_MAX_ROWS: int = int(os.getenv('JIRA_BACKLOG_TITLE_REWRITE_MAX_ROWS', '5'))
    JIRA_BACKLOG_TITLE_REWRITE_MAX_KEYS: int = int(os.getenv('JIRA_BACKLOG_TITLE_REWRITE_MAX_KEYS', '10'))
    JIRA_BACKLOG_TITLE_REWRITE_MAX_TOKENS: int = int(os.getenv('JIRA_BACKLOG_TITLE_REWRITE_MAX_TOKENS', '700'))

    # Jira triage scorecard (optional): shortlist JSON → rubric JSON (v2, 14-point) → deterministic Raise/Lower.
    # Default off: same backlog-overview flow as before; enable per env. See docs/jira-bug-triage-scorecard.md
    JIRA_TRIAGE_SCORECARD_ENABLED: bool = os.getenv('JIRA_TRIAGE_SCORECARD_ENABLED', '0').lower() in (
        '1', 'true', 'yes',
    )
    JIRA_TRIAGE_SCORECARD_MAX_KEYS: int = int(os.getenv('JIRA_TRIAGE_SCORECARD_MAX_KEYS', '40'))
    JIRA_TRIAGE_SCORECARD_INCLUDE_GA_BLOCKERS: bool = os.getenv(
        'JIRA_TRIAGE_SCORECARD_INCLUDE_GA_BLOCKERS', '1'
    ).lower() in ('1', 'true', 'yes')
    # Legacy v1 scorecard only (ignored for schema v2).
    JIRA_TRIAGE_SCORECARD_MIN_CONFIDENCE: int = max(
        1, min(5, int(os.getenv('JIRA_TRIAGE_SCORECARD_MIN_CONFIDENCE', '2')))
    )
    # Raise/Lower only when implied vs current priority differs by at least this many ladder steps.
    # Defined in repo only — not overridden by deployment env (change here and redeploy).
    JIRA_TRIAGE_SCORECARD_MIN_DELTA_RANKS: int = 1
    # Legacy v1 scorecard only (ignored for schema v2).
    JIRA_TRIAGE_SCORECARD_WEIGHTS_JSON: Optional[str] = os.getenv('JIRA_TRIAGE_SCORECARD_WEIGHTS_JSON')
    JIRA_TRIAGE_SCORECARD_THRESHOLDS_JSON: Optional[str] = os.getenv('JIRA_TRIAGE_SCORECARD_THRESHOLDS_JSON')
    JIRA_TRIAGE_SCORECARD_SCHEMA_VERSION: str = os.getenv('JIRA_TRIAGE_SCORECARD_SCHEMA_VERSION', '2')
    JIRA_TRIAGE_SCORECARD_SHORTLIST_MAX_TOKENS: int = int(
        os.getenv('JIRA_TRIAGE_SCORECARD_SHORTLIST_MAX_TOKENS', '1536')
    )
    # When scorecard JSON parse fails, include a bounded excerpt of the assistant text in overview meta (debug).
    JIRA_TRIAGE_SCORECARD_EXPOSE_RAW_ON_FAILURE: bool = os.getenv(
        'JIRA_TRIAGE_SCORECARD_EXPOSE_RAW_ON_FAILURE', '1'
    ).lower() in ('1', 'true', 'yes')
    # Max chars stored in meta / sent to client (after optional PII redaction).
    JIRA_TRIAGE_SCORECARD_FAILURE_RAW_MAX_CHARS: int = max(
        0,
        int(os.getenv('JIRA_TRIAGE_SCORECARD_FAILURE_RAW_MAX_CHARS', '10000')),
    )
    # When enabled, clamp scorecard `reach` for issues with Jira label `ai-created` (case-insensitive).
    JIRA_TRIAGE_SCORECARD_AI_CREATED_ENABLED: bool = os.getenv(
        'JIRA_TRIAGE_SCORECARD_AI_CREATED_ENABLED', '1'
    ).lower() in ('1', 'true', 'yes')
    # Max reach (0–3) after clamp; default 2 caps high breadth scores for synthetic QA tickets.
    JIRA_TRIAGE_SCORECARD_AI_CREATED_MAX_REACH: int = max(
        0, min(3, int(os.getenv('JIRA_TRIAGE_SCORECARD_AI_CREATED_MAX_REACH', '2')))
    )

    # Storage Configuration
    STORAGE_TYPE: str = os.getenv('STORAGE_TYPE', 's3')
    S3_BUCKET_NAME: Optional[str] = os.getenv('S3_BUCKET_NAME')
    S3_FILE_KEY: str = os.getenv('S3_FILE_KEY', 'conversation_items.json')
    S3_REGION: str = os.getenv('S3_REGION', 'us-east-2')
    
    # Azure Storage Configuration
    AZURE_CONNECTION_STRING: Optional[str] = os.getenv('AZURE_CONNECTION_STRING')
    AZURE_CONTAINER_NAME: str = os.getenv('AZURE_CONTAINER_NAME', 'gladly-conversations')
    AZURE_BLOB_NAME: str = os.getenv('AZURE_BLOB_NAME', 'conversation_items.jsonl')
    
    # Flask Configuration
    FLASK_ENV: str = os.getenv('FLASK_ENV', 'production')
    FLASK_DEBUG: bool = os.getenv('FLASK_DEBUG', '0').lower() in ('true', '1', 'yes')
    FLASK_SECRET_KEY: Optional[str] = os.getenv('FLASK_SECRET_KEY')
    PORT: int = int(os.getenv('PORT', 5000))
    HOST: str = os.getenv('HOST', '0.0.0.0')

    # Slack bot webhook (internal; feature-flagged off by default)
    SLACK_SIGNING_SECRET: Optional[str] = os.getenv('SLACK_SIGNING_SECRET')
    SLACK_BOT_TOKEN: Optional[str] = os.getenv('SLACK_BOT_TOKEN')
    SLACK_BOT_ENABLED: bool = os.getenv('SLACK_BOT_ENABLED', '0').lower() in ('true', '1', 'yes')
    # Optional comma-separated Slack channel IDs; empty = all channels allowed
    SLACK_ALLOWED_CHANNEL_IDS: str = os.getenv('SLACK_ALLOWED_CHANNEL_IDS', '')
    # Optional model override for Slack bot answers (defaults to CLAUDE_MODEL)
    SLACK_BOT_MODEL: Optional[str] = os.getenv('SLACK_BOT_MODEL')

    # Notion (read-only) for Slack bot — scope primarily via Notion connection UI
    NOTION_TOKEN: Optional[str] = os.getenv('NOTION_TOKEN')
    # Optional comma-separated filters; empty = search whatever the integration can access
    NOTION_ALLOWED_PAGE_IDS: str = os.getenv('NOTION_ALLOWED_PAGE_IDS', '')
    NOTION_ALLOWED_DATABASE_IDS: str = os.getenv('NOTION_ALLOWED_DATABASE_IDS', '')

    @classmethod
    def parse_csv_ids(cls, raw: Optional[str]) -> frozenset:
        """Parse comma-separated IDs into a lowercase frozenset (empty if unset)."""
        if not raw:
            return frozenset()
        return frozenset(part.strip().lower() for part in raw.split(',') if part.strip())
    
    # Local file fallback
    LOCAL_FILE_PATH: str = os.getenv('LOCAL_FILE_PATH', 'conversation_items.jsonl')
    
    # Survicate Survey Configuration
    # Use cleaned CSV with proper headers (single header row with Answer/Comment labels)
    SURVICATE_CSV_PATH: str = os.getenv('SURVICATE_CSV_PATH', 'data/survicate_cancelled_subscriptions_cleaned.csv')
    
    # Survicate API Configuration
    SURVICATE_API_KEY: Optional[str] = os.getenv('SURVICATE_API_KEY')
    SURVICATE_WORKSPACE_KEY: Optional[str] = os.getenv('SURVICATE_WORKSPACE_KEY')
    SURVICATE_WORKSPACE_ID: Optional[str] = os.getenv('SURVICATE_WORKSPACE_ID')
    SURVICATE_SURVEY_ID: str = os.getenv('SURVICATE_SURVEY_ID', 'e08c3365f14085e2')
    SURVICATE_API_BASE_URL: str = os.getenv('SURVICATE_API_BASE_URL', 'https://data-api.survicate.com/v2')
    
    # Survicate S3 Cache Configuration
    SURVICATE_CACHE_MAX_AGE_HOURS: int = int(os.getenv('SURVICATE_CACHE_MAX_AGE_HOURS', '24'))
    SURVICATE_S3_CACHE_KEY: str = os.getenv('SURVICATE_S3_CACHE_KEY', 'survicate-cache/api_responses.csv')
    SURVICATE_S3_AUGMENTED_CACHE_KEY: str = os.getenv('SURVICATE_S3_AUGMENTED_CACHE_KEY', 'survicate-cache/api_responses_augmented.csv')
    SURVICATE_S3_AUGMENTED_PREFIX: str = os.getenv('SURVICATE_S3_AUGMENTED_PREFIX', 'survicate-cache/augmented/')
    SURVICATE_S3_METADATA_KEY: str = os.getenv('SURVICATE_S3_METADATA_KEY', 'survicate-cache/api_cache_meta.json')
    
    # Survicate Data Source Default
    # Default data source for Survicate/Churn analysis: 'api' (live API data) or 'file' (CSV file)
    # NOTE: This should match src/utils/constants.js: DEFAULT_SURVICATE_DATA_SOURCE
    # The frontend always sends data_source in API calls, so this is only used as a fallback
    # for direct API calls or edge cases. Keep both values in sync.
    SURVICATE_DEFAULT_DATA_SOURCE: str = os.getenv('SURVICATE_DEFAULT_DATA_SOURCE', 'api')
    SURVICATE_S3_AUGMENTED_METADATA_KEY: str = os.getenv('SURVICATE_S3_AUGMENTED_METADATA_KEY', 'survicate-cache/augmented_files_meta.json')
    
    # Survicate Chart Configuration
    SURVICATE_EXCLUDE_MONTHS: str = os.getenv('SURVICATE_EXCLUDE_MONTHS', '2024-11')  # Comma-separated list of year-month to exclude (e.g., '2024-11,2025-01')
    
    # Authentication Configuration
    # Password for password-based login (stored securely on backend)
    # Temporarily re-enabled as alternative to Google SSO (available until end of Feb 2026)
    AUTH_PASSWORD: str = os.getenv('AUTH_PASSWORD', 'gladly2024')
    # Admin password for admin tools (separate from regular auth)
    # Temporarily re-enabled as alternative to Google SSO (available until end of Feb 2026)
    ADMIN_PASSWORD: str = os.getenv('ADMIN_PASSWORD', '')
    # Admin email(s) for Google SSO admin access (comma-separated for multiple admins)
    ADMIN_EMAIL: Optional[str] = os.getenv('ADMIN_EMAIL', '')
    # Domains allowed for magic link and Google SSO (comma-separated, no @)
    # Example: halocollar.com,softeq.com
    ALLOWED_EMAIL_DOMAINS: str = os.getenv('ALLOWED_EMAIL_DOMAINS', 'halocollar.com')
    
    @classmethod
    def allowed_email_domains(cls) -> frozenset:
        """Parse ALLOWED_EMAIL_DOMAINS into a lowercase set. Empty/invalid env falls back to halocollar.com."""
        parts = {d.strip().lower() for d in cls.ALLOWED_EMAIL_DOMAINS.split(',') if d.strip()}
        return frozenset(parts) if parts else frozenset({'halocollar.com'})
    
    @classmethod
    def is_admin_email(cls, email: str) -> bool:
        """Check if email is an admin email"""
        if not cls.ADMIN_EMAIL:
            return False
        admin_emails = [e.strip().lower() for e in cls.ADMIN_EMAIL.split(',') if e.strip()]
        return email.lower() in admin_emails
    
    # Google OAuth Configuration
    GOOGLE_OAUTH_CLIENT_ID: Optional[str] = os.getenv('GOOGLE_OAUTH_CLIENT_ID')
    GOOGLE_OAUTH_CLIENT_SECRET: Optional[str] = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET')
    GOOGLE_OAUTH_REDIRECT_URI: Optional[str] = os.getenv('GOOGLE_OAUTH_REDIRECT_URI')
    
    # PII Protection Configuration
    # Enable PII protection before sending data to Claude API
    # Options: 'hash' (deterministic hash), 'redact' ([REDACTED] placeholder), 'remove' (delete), 'none' (disabled)
    PII_REDACT_MODE: str = os.getenv('PII_REDACT_MODE', 'hash')
    # Preserve customer/conversation IDs (don't pseudonymize) - set to 'true' to preserve
    PII_PRESERVE_IDS: bool = os.getenv('PII_PRESERVE_IDS', 'false').lower() in ('true', '1', 'yes')
    # Enable name detection (may have false positives) - set to 'true' to enable
    PII_ENABLE_NAME_DETECTION: bool = os.getenv('PII_ENABLE_NAME_DETECTION', 'false').lower() in ('true', '1', 'yes')
    
    # Cache Configuration
    # Enable caching (set to 'false' to disable)
    CACHE_ENABLED: bool = os.getenv('CACHE_ENABLED', 'true').lower() in ('true', '1', 'yes')
    # Default TTL for cache entries in seconds (default: 1 hour)
    CACHE_DEFAULT_TTL: int = int(os.getenv('CACHE_DEFAULT_TTL', '3600'))
    # Maximum number of cache entries (None = unlimited)
    CACHE_MAX_SIZE: Optional[int] = int(os.getenv('CACHE_MAX_SIZE')) if os.getenv('CACHE_MAX_SIZE') else None
    # TTL for Claude API responses in seconds (default: 24 hours - Claude responses are expensive)
    CACHE_CLAUDE_TTL: int = int(os.getenv('CACHE_CLAUDE_TTL', '86400'))
    # TTL for conversation summaries in seconds (default: 1 hour)
    CACHE_SUMMARY_TTL: int = int(os.getenv('CACHE_SUMMARY_TTL', '3600'))
    # TTL for conversation search results in seconds (default: 30 minutes)
    CACHE_SEARCH_TTL: int = int(os.getenv('CACHE_SEARCH_TTL', '1800'))
    # Redis configuration (for future distributed caching)
    REDIS_HOST: Optional[str] = os.getenv('REDIS_HOST')
    REDIS_PORT: int = int(os.getenv('REDIS_PORT', '6379'))
    
    @classmethod
    def get_pii_config(cls) -> dict:
        """Get PII protection configuration"""
        return {
            'redact_mode': cls.PII_REDACT_MODE if cls.PII_REDACT_MODE != 'none' else None,
            'preserve_ids': cls.PII_PRESERVE_IDS,
            'enable_name_detection': cls.PII_ENABLE_NAME_DETECTION
        }
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration"""
        if not cls.ANTHROPIC_API_KEY:
            print("Warning: ANTHROPIC_API_KEY not set")
            return False
        
        if cls.STORAGE_TYPE == 's3' and not cls.S3_BUCKET_NAME:
            print("Warning: S3_BUCKET_NAME not set for S3 storage")
            return False
        
        if cls.STORAGE_TYPE == 'azure' and not cls.AZURE_CONNECTION_STRING:
            print("Warning: AZURE_CONNECTION_STRING not set for Azure storage")
            return False
        
        return True
