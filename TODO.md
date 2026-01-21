# TODO

## High Priority
- [done] Add logging and error handling (template load, JSON parse failures, SMTP/API errors) with clear exit codes for cron.
- [done] Modularize code (logs.py, report.py, email_sender.py, config.py) to improve testability and reuse.
- [done] Validate environment variables strictly (required: GEMINI_API_KEY, SMTP_HOST, MAIL_TO; numeric SMTP_PORT; non-zero exit on failure).
- [done] Add timeout/retry for Gemini and SMTP calls; surface failures in logs.

## Medium Priority
- Cache prompt template in memory to avoid repeated disk I/O.
- Improve long-log handling: smarter truncation with warnings, token-aware limits.
- Add type hints across functions for IDE/lint support.
- Add unit/integration tests with fixture logs (parse, summarize, JSON parse, email construction).

## Low Priority
- Update package metadata: description and version bump (e.g., 0.6.0 for JSON output).
- Review .gitignore to ensure .env and build artifacts are ignored.
- Extend README: JSON schema description, prompt customization, troubleshooting.
- Optional archive feature: --archive-dir to save sent reports (JSON + Markdown).

## Notes
- JSON structured output with response_mime_type/schema is implemented; falls back to text on parse failure.
- Prompt template: editable at src/upsum/prompt_template.txt; placeholders formatted_date, log_content, reboot_text, dietpi_release_notes.
