"""
Request fingerprinting and IP tracking utilities for security and analytics.
"""

import hashlib
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


def get_client_ip(request) -> str:
    """
    Extract the client's IP address from the request.
    Handles proxy headers (X-Forwarded-For, X-Real-IP) and falls back to REMOTE_ADDR.
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        Client IP address as string, or 'unknown' if extraction fails
    """
    try:
        # Check X-Forwarded-For first (most common proxy header)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # X-Forwarded-For can contain multiple IPs (client, proxy1, proxy2, ...)
            # The first IP is typically the original client
            ip_address = x_forwarded_for.split(',')[0].strip()
            if ip_address:
                return ip_address
        
        # Check X-Real-IP header (used by some proxies like nginx)
        x_real_ip = request.META.get('HTTP_X_REAL_IP')
        if x_real_ip:
            ip_address = x_real_ip.strip()
            if ip_address:
                return ip_address
        
        # Fall back to REMOTE_ADDR (direct connection)
        remote_addr = request.META.get('REMOTE_ADDR', '').strip()
        if remote_addr:
            return remote_addr
        
        return 'unknown'
        
    except Exception as e:
        logger.debug(f"Error extracting IP address: {e}")
        return 'unknown'


def get_request_headers(request) -> Dict[str, str]:
    """
    Extract relevant HTTP headers from the request for fingerprinting.
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        Dictionary of relevant headers
    """
    headers = {}
    
    # Headers that are useful for fingerprinting
    relevant_headers = [
        'HTTP_USER_AGENT',
        'HTTP_ACCEPT',
        'HTTP_ACCEPT_LANGUAGE',
        'HTTP_ACCEPT_ENCODING',
        'HTTP_DNT',  # Do Not Track
        'HTTP_CONNECTION',
        'HTTP_UPGRADE_INSECURE_REQUESTS',
        'HTTP_SEC_FETCH_SITE',
        'HTTP_SEC_FETCH_MODE',
        'HTTP_SEC_FETCH_USER',
        'HTTP_SEC_FETCH_DEST',
        'HTTP_SEC_CH_UA',
        'HTTP_SEC_CH_UA_MOBILE',
        'HTTP_SEC_CH_UA_PLATFORM',
    ]
    
    for header in relevant_headers:
        value = request.META.get(header)
        if value:
            headers[header] = value
    
    return headers


def generate_fingerprint(request, include_ip: bool = True) -> str:
    """
    Generate a unique fingerprint hash for the request.
    
    The fingerprint is based on:
    - IP address (optional)
    - User agent
    - Accept headers (content types, language, encoding)
    - Browser security headers
    
    Args:
        request: Django HttpRequest object
        include_ip: Whether to include IP address in fingerprint (default: True)
        
    Returns:
        SHA256 hash representing the request fingerprint
    """
    try:
        fingerprint_components = []
        
        # Add IP address if requested
        if include_ip:
            ip_address = get_client_ip(request)
            fingerprint_components.append(f"ip:{ip_address}")
        
        # Add headers
        headers = get_request_headers(request)
        for key in sorted(headers.keys()):  # Sort for consistency
            fingerprint_components.append(f"{key}:{headers[key]}")
        
        # Combine all components
        fingerprint_string = '|'.join(fingerprint_components)
        
        # Generate hash
        fingerprint_hash = hashlib.sha256(fingerprint_string.encode('utf-8')).hexdigest()
        
        return fingerprint_hash
        
    except Exception as e:
        logger.error(f"Error generating request fingerprint: {e}", exc_info=True)
        # Return a fallback fingerprint based on timestamp
        import time
        return hashlib.sha256(f"fallback:{time.time()}".encode('utf-8')).hexdigest()


def get_request_fingerprint_data(request) -> Dict[str, any]:
    """
    Get comprehensive fingerprint data for a request.
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        Dictionary containing:
        - ip_address: Client IP address
        - user_agent: User agent string
        - headers: Dictionary of relevant headers
        - fingerprint: Unique fingerprint hash (with IP)
        - fingerprint_no_ip: Fingerprint hash without IP (for tracking across IPs)
        - method: HTTP method
        - path: Request path
    """
    try:
        ip_address = get_client_ip(request)
        headers = get_request_headers(request)
        
        return {
            'ip_address': ip_address,
            'user_agent': request.META.get('HTTP_USER_AGENT', 'unknown'),
            'headers': headers,
            'fingerprint': generate_fingerprint(request, include_ip=True),
            'fingerprint_no_ip': generate_fingerprint(request, include_ip=False),
            'method': request.method,
            'path': request.path,
            'is_secure': request.is_secure(),
            'is_ajax': request.headers.get('X-Requested-With') == 'XMLHttpRequest',
        }
        
    except Exception as e:
        logger.error(f"Error getting request fingerprint data: {e}", exc_info=True)
        return {
            'ip_address': 'unknown',
            'user_agent': 'unknown',
            'headers': {},
            'fingerprint': 'error',
            'fingerprint_no_ip': 'error',
            'method': 'unknown',
            'path': 'unknown',
            'is_secure': False,
            'is_ajax': False,
        }


def parse_user_agent(user_agent: str) -> Dict[str, Optional[str]]:
    """
    Parse a user agent string to extract browser and OS information.
    This is a simplified parser - for production use, consider using a library like user-agents.
    
    Args:
        user_agent: User agent string
        
    Returns:
        Dictionary with browser, version, os, and device information
    """
    if not user_agent or user_agent == 'unknown':
        return {
            'browser': None,
            'browser_version': None,
            'os': None,
            'device': None,
        }
    
    ua_lower = user_agent.lower()
    
    # Detect browser
    browser = None
    browser_version = None
    
    if 'edg/' in ua_lower:
        browser = 'Edge'
    elif 'chrome/' in ua_lower and 'edg/' not in ua_lower:
        browser = 'Chrome'
    elif 'firefox/' in ua_lower:
        browser = 'Firefox'
    elif 'safari/' in ua_lower and 'chrome/' not in ua_lower:
        browser = 'Safari'
    elif 'opera/' in ua_lower or 'opr/' in ua_lower:
        browser = 'Opera'
    
    # Detect OS
    os = None
    if 'windows' in ua_lower:
        os = 'Windows'
    elif 'mac os' in ua_lower or 'macos' in ua_lower:
        os = 'macOS'
    elif 'linux' in ua_lower:
        os = 'Linux'
    elif 'android' in ua_lower:
        os = 'Android'
    elif 'ios' in ua_lower or 'iphone' in ua_lower or 'ipad' in ua_lower:
        os = 'iOS'
    
    # Detect device type
    device = 'Desktop'
    if 'mobile' in ua_lower or 'android' in ua_lower or 'iphone' in ua_lower:
        device = 'Mobile'
    elif 'tablet' in ua_lower or 'ipad' in ua_lower:
        device = 'Tablet'
    
    return {
        'browser': browser,
        'browser_version': browser_version,
        'os': os,
        'device': device,
        'raw': user_agent,
    }


def is_suspicious_request(request) -> Tuple[bool, Optional[str]]:
    """
    Perform basic checks to identify potentially suspicious requests.
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        Tuple of (is_suspicious: bool, reason: Optional[str])
    """
    try:
        # Check for missing User-Agent (common for bots)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        if not user_agent:
            return (True, 'Missing User-Agent header')
        
        # Check for suspicious user agents
        suspicious_patterns = [
            'curl',
            'wget',
            'python-requests',
            'scrapy',
            'bot',
            'crawler',
            'spider',
        ]
        
        ua_lower = user_agent.lower()
        for pattern in suspicious_patterns:
            if pattern in ua_lower and 'googlebot' not in ua_lower and 'bingbot' not in ua_lower:
                return (True, f'Suspicious User-Agent pattern: {pattern}')
        
        # Check for missing common headers
        if not request.META.get('HTTP_ACCEPT'):
            return (True, 'Missing Accept header')
        
        # Check for IP address issues
        ip_address = get_client_ip(request)
        if ip_address == 'unknown':
            return (True, 'Unable to determine IP address')
        
        return (False, None)
        
    except Exception as e:
        logger.error(f"Error checking for suspicious request: {e}", exc_info=True)
        return (False, None)

