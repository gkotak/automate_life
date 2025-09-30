# Authentication Setup for Video Summarizer

This guide explains how to configure the video summarizer to access paid subscription content.

## Quick Setup

1. **Install the new dependency:**
   ```bash
   cd programs/video_summarizer/scripts
   pip install -r requirements.txt
   ```

2. **Create credentials file:**
   ```bash
   cp .env.example .env
   ```

3. **Edit `.env` with your actual credentials**

## Authentication Methods

### Method 1: Environment Variables (Recommended)

Create a `.env` file in your project root with your subscription credentials:

```bash
# Substack subscriptions
SUBSTACK_EMAIL=your-email@example.com
SUBSTACK_PASSWORD=your-password

# Browser session cookies (for complex authentication)
NEWSLETTER_SESSION_COOKIES="session_id=abc123; auth_token=xyz789"

# Custom User-Agent (if needed)
USER_AGENT=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36
```

### Method 2: Browser Session Cookies

For sites with complex authentication, you can extract session cookies from your browser:

1. **Log into the subscription site in your browser**
2. **Open Developer Tools (F12)**
3. **Go to Application/Storage → Cookies**
4. **Copy relevant cookies to the NEWSLETTER_SESSION_COOKIES variable**

Example format:
```
NEWSLETTER_SESSION_COOKIES="sessionid=abc123; csrftoken=def456; auth=ghi789"
```

### Method 3: Platform-Specific APIs

Some platforms offer API access for subscribers:

```bash
# YouTube Premium API
YOUTUBE_API_KEY=your-api-key

# Other platform credentials
PLATFORM_USERNAME=username
PLATFORM_PASSWORD=password
```

## Supported Platforms

### Currently Implemented:
- **Substack**: Email/password authentication
- **Generic**: Session cookie support
- **YouTube**: API key support (for premium features)

### Easy to Add:
- **Medium**: Session cookies or API
- **Patreon**: API integration
- **Newsletter platforms**: Most support session cookies

## Security Best Practices

1. **Never commit `.env` to git:**
   ```bash
   echo ".env" >> .gitignore
   ```

2. **Use environment-specific files:**
   - `.env.local` (local development)
   - `.env.production` (production)

3. **Rotate credentials regularly**

4. **Use read-only API keys when available**

## Testing Authentication

Run the summarizer with a paid content URL to test:

```bash
python video_article_summarizer.py "https://example.substack.com/p/premium-post"
```

Check the logs for authentication status:
- ✓ Authentication successful
- ⚠️ Authentication failed

## Troubleshooting

### Common Issues:

1. **Login fails**: Check credentials in `.env`
2. **Session expires**: Update session cookies
3. **Rate limiting**: Add delays between requests
4. **CAPTCHA required**: May need manual browser session

### Getting Session Cookies:

1. Log into the site in Chrome/Firefox
2. Press F12 → Application → Cookies
3. Copy relevant cookies (usually `sessionid`, `auth_token`, etc.)
4. Add to `.env` file in the format: `name1=value1; name2=value2`

## Adding New Platforms

To add authentication for a new platform, edit the `_authenticate_for_domain` method in `video_article_summarizer.py`:

```python
elif 'newplatform.com' in domain:
    username = os.getenv('NEWPLATFORM_USERNAME')
    password = os.getenv('NEWPLATFORM_PASSWORD')
    if username and password:
        # Add authentication logic here
        pass
```

## Privacy Note

The summarizer only uses credentials to access content you've already paid for. No credentials are stored or transmitted outside your local environment.