import datetime
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from jinja2 import Template
from markdown_it import MarkdownIt

from .config import SmtpConfig


SMTP_TIMEOUT_SECONDS = 15
SMTP_MAX_RETRIES = 3
SMTP_BACKOFF_SECONDS = 2

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; background-color: #f6f8fa; color: #24292e; padding: 20px; margin: 0; }
    .container { max-width: 800px; background: #ffffff; border: 1px solid #e1e4e8; border-radius: 8px; overflow: hidden; margin: 0 auto; box-shadow: 0 4px 15px rgba(0,0,0,0.06); }
    .header { background: linear-gradient(135deg, #1f2328 0%, #2f363d 100%); color: #ffffff; padding: 30px; text-align: center; }
    .header h1 { margin: 0; font-size: 24px; font-weight: 600; letter-spacing: -0.5px; }
    .content { padding: 35px 30px; line-height: 1.6; font-size: 15px; }
    
    /* Markdown rendering styles */
    .content h2 { border-bottom: 2px solid #eaecef; padding-bottom: 8px; margin-top: 30px; margin-bottom: 16px; font-size: 18px; color: #0969da; }
    .content h3 { font-size: 16px; margin-top: 20px; color: #24292e; border-bottom: 1px dashed #eaecef; padding-bottom: 4px; }
    .content p, .content ul, .content ol { margin-top: 0; margin-bottom: 16px; }
    .content ul, .content ol { padding-left: 20px; }
    .content li { margin-bottom: 6px; }
    .content strong { color: #111; }
    .content blockquote { padding: 0 1em; color: #57606a; border-left: .25em solid #d0d7de; margin: 0 0 16px 0; }
    .content hr { height: .25em; padding: 0; margin: 24px 0; background-color: #fdfeff; border: 0; border-bottom: 1px solid #d0d7de; }
    .content code { padding: .2em .4em; margin: 0; font-size: 85%; white-space: break-spaces; background-color: rgba(175,184,193,0.2); border-radius: 6px; font-family: ui-monospace,SFMono-Regular,SF Mono,Menlo,Consolas,Liberation Mono,monospace; }
    
    .footer { background-color: #f6f8fa; color: #57606a; text-align: center; padding: 20px; font-size: 12px; border-top: 1px solid #eaecef; line-height: 1.5; }
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>{{ subject }}</h1>
    </div>
    <div class="content">
        {{ html_content | safe }}
    </div>
    <div class="footer">
        본 리포트는 upsum 시스템 업데이트 요약 도구에 의해 자동으로 작성되었습니다.<br>
        생성일시: {{ now_str }}
    </div>
</div>
</body>
</html>
"""


def send_email(subject: str, body: str, smtp_config: SmtpConfig, logger) -> None:
    """Send the summary email as both plain text and HTML using Jinja2 templates via sysutils."""
    md = MarkdownIt()
    raw_html = md.render(body)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    template = Template(HTML_TEMPLATE)
    html_body = template.render(
        subject=subject,
        html_content=raw_html,
        now_str=now_str
    )

    import sysutils.email
    sysutils.email.send_email(
        subject=subject,
        body=body,
        html_body=html_body,
        smtp_config=smtp_config,
        logger_instance=logger,
    )

