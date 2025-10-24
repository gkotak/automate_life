"""
Shared utilities for cookie analysis and categorization.

Used by both create_session.py and upload_session_to_supabase.py
to maintain consistent cookie classification logic.
"""

def categorize_cookie(name, domain, http_only, secure):
    """
    Categorize cookie by likely purpose based on common patterns.

    Args:
        name: Cookie name
        domain: Cookie domain
        http_only: Whether cookie has httpOnly flag
        secure: Whether cookie has secure flag

    Returns:
        tuple of (category, certainty) where certainty is 'high', 'medium', or 'low'
    """
    name_lower = name.lower()

    # High confidence security/protection cookies (CHECK FIRST - before 'token')
    # This order prevents csrf_token from being misclassified as auth
    if any(pattern in name_lower for pattern in [
        '__cf_bm', 'cf_clearance', '_cfuvid', 'csrf', 'xsrf'
    ]):
        return ('🛡️  Security/Protection', 'high')

    # High confidence authentication/session cookies
    if any(pattern in name_lower for pattern in [
        'session', 'auth', 'token', 'login', 'user', 'sid', 'connect.sid',
        'sess', '_session', 'sessionid', 'jsessionid'
    ]):
        return ('🔐 Authentication/Session', 'high')

    # High confidence tracking/analytics
    if any(pattern in name_lower for pattern in [
        '_ga', '_gid', '_gat', 'ajs_', 'amplitude', 'segment',
        'mixpanel', 'heap', 'analytics', 'tracking', '_fbp', '_fbc'
    ]):
        return ('📊 Analytics/Tracking', 'high')

    # A/B testing
    if any(pattern in name_lower for pattern in ['experiment', 'ab_test', 'variant']):
        return ('🧪 A/B Testing', 'high')

    # Load balancing
    if any(pattern in name_lower for pattern in ['awsalb', 'awselb', 'lb-']):
        return ('⚖️  Load Balancing', 'high')

    # Advertising
    if any(pattern in name_lower for pattern in ['_ad', 'doubleclick', 'adsense']):
        return ('📢 Advertising', 'high')

    # Medium confidence: httpOnly + secure often means auth
    if http_only and secure:
        return ('🔐 Authentication/Session', 'medium')

    # Low confidence fallback
    return ('❓ Unknown/Other', 'low')


# Standard category order for consistent display
COOKIE_CATEGORY_ORDER = [
    '🔐 Authentication/Session',
    '🛡️  Security/Protection',
    '⚖️  Load Balancing',
    '🧪 A/B Testing',
    '📊 Analytics/Tracking',
    '📢 Advertising',
    '❓ Unknown/Other'
]
