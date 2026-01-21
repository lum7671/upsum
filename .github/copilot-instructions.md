# Copilot Instructions for upsum Project

## Project Overview

**upsum (Update Summarizer)** is a Python CLI tool that:
- Analyzes system update logs (optimized for DietPi on Raspberry Pi 4B)
- Generates structured Korean-language summaries using Google Gemini AI
- Sends email reports via SMTP
- Designed for cron automation for daily update monitoring

**Version**: 0.9.0  
**Target Users**: Linux system administrators (Korean-speaking)  
**Primary Use Case**: Automated daily system update reports for DietPi/Debian-based systems

## Architecture & Module Structure

### Core Modules

```
src/upsum/
├── __init__.py          # Package initialization, version management
├── __main__.py          # Entry point, orchestrates main workflow
├── config.py            # Configuration management, env var handling, logging setup
├── logs.py              # Log file discovery and parsing
├── report.py            # Gemini API integration, JSON→Markdown conversion
├── email_sender.py      # SMTP email delivery with retry logic
└── prompt_template.txt  # Gemini prompt template (Korean, customizable)
```

### Data Flow

```
CLI Args → Config Loading (.env) 
  → Log File Discovery (~/logs or --log-dir)
  → Log Parsing (reboot detection, content extraction)
  → Prompt Generation (template + log data)
  → Gemini API Call (JSON schema mode)
  → JSON Parsing (with fallback to raw text)
  → Markdown Conversion
  → Email Sending (SMTP with HTML + Plain Text)
  → Logging (syslog or stderr)
```

## Technology Stack

- **Language**: Python 3.8+
- **Package Manager**: Rye (managed project)
- **AI Model**: Google Gemini 2.5 Flash (via `google-genai` SDK)
- **Email**: SMTP with TLS (port 587), multipart MIME (HTML + Plain Text)
- **Markdown**: `markdown-it-py` for HTML conversion
- **Environment**: `python-dotenv` for configuration
- **Logging**: syslog integration (`/dev/log`) with stderr fallback

## Key Design Patterns

### 1. Configuration Management
- **Pattern**: Dataclass-based config (`AppConfig`, `SmtpConfig`)
- **Validation**: Required env vars checked at startup, numeric validation for ports
- **Error Handling**: Custom `ConfigError` exception for config failures

### 2. Retry Logic with Exponential Backoff
- **Gemini API**: 3 retries, 30s timeout, backoff: 1s → 2s → 4s
- **SMTP**: 3 retries, 15s timeout, backoff: 1s → 2s → 4s
- **Authentication Errors**: No retry (fail fast)

### 3. Dependency Injection
- Logger instances passed to functions (not global)
- Config objects injected into functions
- Enables better testability

### 4. Graceful Degradation
- JSON parsing failures → fallback to raw text
- Syslog unavailable → stderr logging
- Template file missing → explicit error (no silent failure)

## Environment Variables

### Required
- `GEMINI_API_KEY`: Google AI Studio API key
- `SMTP_HOST`: SMTP server address
- `MAIL_TO`: Recipient email address

### Optional
- `SMTP_PORT`: Default 587
- `SMTP_USER`: SMTP authentication username
- `SMTP_PASSWORD`: SMTP password (Gmail app password recommended)
- `MAIL_FROM`: Sender email (default: upsum@example.com)

## Code Conventions

### Error Handling
- Use `ConfigError` for configuration-related failures
- Log warnings for retryable errors
- Log errors for final failures
- Exit codes: 0 (success), 1 (failure)
- Always include context in error messages (Korean for user-facing errors)

### Logging
- **INFO**: Normal operation milestones
- **WARNING**: Retryable errors, non-critical issues
- **ERROR**: Fatal errors, final retry failures
- Format: `"upsum: %(levelname)s %(message)s"`

### Naming Conventions
- Functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE` (e.g., `GEMINI_TIMEOUT_SECONDS`)
- Private functions: prefix with `_` (e.g., `_get_env`, `_call_gemini`)

### Type Hints
- Use type hints for function parameters and return values
- Use `Optional[T]` for nullable types
- Import from `typing` module: `Optional`, `Any`, etc.

## Critical Implementation Details

### Gemini API Integration (report.py)

**Current Known Issue (2026-01-21):**
```
ERROR: Models.generate_content() got an unexpected keyword argument 'generation_config'
```
- **Cause**: `google-genai` library API changed
- **Current Code**: Uses `generation_config` parameter
- **Fix Needed**: Update to match latest `google-genai` SDK API

**JSON Schema (required fields):**
```python
{
    "title": str,              # Report title with date
    "reboot_required": str,    # Reboot necessity status
    "summary": str,            # Factual summary of updates
    "analysis": str,           # Analysis of log data
    "near_future": str,        # Monitoring items, predictions
    "actions": list[str]       # Prioritized admin action items
}
```

**Model Configuration:**
- Model: `gemini-2.5-flash`
- Response format: `application/json`
- Response schema: See `json_schema` in `generate_summary_with_gemini()`
- Timeout handling: Catches `TypeError` for compatibility

### Email Sending (email_sender.py)

**MIME Structure:**
```
MIMEMultipart("alternative")
├── MIMEText(body, "plain", "utf-8")    # Plain text version
└── MIMEText(html_body, "html", "utf-8") # HTML version (Markdown→HTML)
```

**SMTP Flow:**
1. Connect to SMTP server with timeout
2. STARTTLS if port 587
3. Login if credentials provided
4. Send multipart message
5. Close connection

**Authentication Errors:**
- `SMTPAuthenticationError`: No retry, immediate failure
- Other exceptions: Retry with exponential backoff

### Log Parsing (logs.py)

**Reboot Detection:**
- Keywords: `"reboot is required"`, `"rebooting"` (case-insensitive)
- Returns boolean flag

**Log Size Management:**
- Checks for special markers: `"상세 업데이트 내역:"`, `"업데이트 내역:"`
- If present: return full content
- If > 3000 chars: truncate with `"[로그가 길어서 일부만 표시됨]"`

## Testing & Development

### Dry Run Mode
```bash
rye run upsum --dry-run
```
- Skips email sending
- Prints summary to console
- Use for testing prompt changes, API integration

### Local Testing
```bash
# Test with specific log file
rye run upsum --log-file /path/to/test.log --dry-run

# Test with different log directory
rye run upsum --log-dir /var/log/apt --dry-run
```

### Debugging Gemini Responses
- Check `parse_json_response()` for JSON cleaning logic
- Removes code fences: ` ```json`, ` ``` `
- Logs warnings on parse failures

## Prompt Template Customization

**File**: `src/upsum/prompt_template.txt`

**Placeholders:**
- `{formatted_date}`: YYYY년 MM월 DD일 format
- `{log_content}`: Parsed log content
- `{reboot_text}`: Reboot requirement message
- `{dietpi_release_notes}`: Auto-detected DietPi version notes

**Persona**: 20-year Linux sysadmin, DietPi specialist, Korean output

**Output Requirements**: 
- Fact-based reporting
- Korean language
- JSON structure adherence
- Actionable recommendations

## Common Pitfalls to Avoid

### 1. ❌ Don't hardcode configuration
```python
# BAD
api_key = "sk-abc123..."  

# GOOD
api_key = config.gemini_api_key
```

### 2. ❌ Don't use global logger
```python
# BAD
logger = logging.getLogger("upsum")
def some_function():
    logger.info("...")

# GOOD
def some_function(logger):
    logger.info("...")
```

### 3. ❌ Don't ignore retry failures
```python
# BAD
try:
    api_call()
except:
    pass  # Silent failure

# GOOD
for attempt in range(MAX_RETRIES):
    try:
        api_call()
        break
    except Exception as e:
        if attempt == MAX_RETRIES - 1:
            logger.error(f"Failed after {MAX_RETRIES} attempts: {e}")
            raise
```

### 4. ❌ Don't mix Korean and English in user-facing messages
```python
# BAD
logger.error(f"SMTP authentication failed for {user}")

# GOOD (user-facing)
logger.error(f"SMTP 인증 실패. 사용자 이름과 비밀번호를 확인해주세요.")

# GOOD (technical/debug)
logger.warning(f"Gemini API call failed (attempt {attempt}/{max}); retrying in {wait}s: {e}")
```

### 5. ❌ Don't assume file paths
```python
# BAD
template_path = "prompt_template.txt"

# GOOD
template_path = Path(__file__).parent / "prompt_template.txt"
```

## File Modification Guidelines

### When Editing config.py
- Validate all input (env vars, port numbers, paths)
- Use `_get_env()` helper for consistency
- Add new fields to appropriate dataclass
- Update README.md environment variables table

### When Editing report.py
- Test JSON schema changes with `--dry-run`
- Update `convert_json_to_markdown()` for new fields
- Consider Gemini API rate limits
- Keep retry logic consistent

### When Editing email_sender.py
- Test with `--dry-run` first
- Verify both HTML and plain text rendering
- Don't change retry logic without updating constants
- Log all SMTP errors clearly

### When Editing logs.py
- Consider log file size impacts
- Test reboot detection with various log formats
- Don't break existing keyword detection

## Security Considerations

### API Key Management
- Never log API keys (even partially)
- Never commit `.env` file
- Recommend `chmod 600 .env` in docs
- Use environment variables, never hardcode

### Email Security
- Recommend Gmail app passwords (not account passwords)
- Support STARTTLS (port 587)
- Don't log SMTP passwords
- Validate SMTP_PORT range (1-65535)

### Log File Handling
- Don't execute log file contents
- Sanitize paths before file operations
- Check file existence before reading
- Handle malformed log files gracefully

## Known Issues & TODOs

### Active Issues (2026-01-21)
1. **Gemini API `generation_config` error**: Library version incompatibility
   - Error: `Models.generate_content() got an unexpected keyword argument 'generation_config'`
   - See: logs in `all_2026-1-21-10_36_28.csv`
   - Fix: Update `google-genai` SDK usage in `report.py`

### TODO (from TODO.md)
- [ ] Cache prompt template in memory (avoid repeated disk I/O)
- [ ] Add type hints across all functions
- [ ] Add unit/integration tests with fixture logs
- [ ] Implement token-aware log truncation (smarter than 3000 chars)
- [ ] Optional archive feature: save sent reports to `--archive-dir`

### Future Enhancements
- [ ] Support multiple log file formats (apt, yum, pacman)
- [ ] Add email attachment option (original log file)
- [ ] Implement log diff reporting (compare with previous day)
- [ ] Add web dashboard for report history
- [ ] Support multiple recipients
- [ ] Add Slack/Discord notification options

## Dependencies

```toml
dependencies = [
    "google-genai",           # Gemini API client (version not pinned - TODO)
    "python-dotenv",          # Environment variable management
    "markdown-it-py>=4.0.0",  # Markdown to HTML conversion
]
```

**Note**: Consider pinning `google-genai` version to avoid API breaking changes.

## Deployment Notes

### Cron Usage
- Use absolute paths for `rye` executable
- Specify project path with `-p` flag
- Redirect output to log file: `> /path/to/upsum_cron.log 2>&1`
- Ensure `.env` file is readable by cron user

### System Requirements
- Python 3.8+
- Linux or macOS (tested on DietPi/Raspberry Pi 4B)
- Internet connectivity (Gemini API, SMTP)
- Syslog support (optional, falls back to stderr)

## Contributing Guidelines

When adding new features:
1. Update `__version__` in `__init__.py`
2. Add corresponding tests (when test framework added)
3. Update README.md with usage examples
4. Update this Copilot instructions file
5. Add TODO items to TODO.md if incomplete
6. Maintain Korean language for user-facing output
7. Follow existing error handling patterns
8. Add logging for significant operations

## Contact & Maintenance

**Author**: Nate Doohyun Jang  
**Repository**: https://github.com/lum7671/upsum  
**Target Audience**: Korean-speaking Linux sysadmins  
**Support**: DietPi on Raspberry Pi 4B (primary), general Debian-based systems (secondary)

---

**Last Updated**: 2026-01-21  
**Copilot Version**: This file is for GitHub Copilot context enhancement
