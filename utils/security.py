"""
Request fingerprinting and IP tracking utilities for security and analytics.
"""

import hashlib
import logging
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)


def is_local_ip(ip_address: str) -> bool:
    """
    Check if an IP address is local/private.

    Args:
        ip_address: IP address string

    Returns:
        True if the IP is local/private, False otherwise
    """
    if not ip_address or ip_address == "unknown":
        return False

    # Check for localhost
    if ip_address in ["127.0.0.1", "::1", "localhost"]:
        return True

    # Check for private IP ranges (RFC 1918)
    if ip_address.startswith(("10.", "192.168.", "172.")):
        # For 172.x.x.x, need to check if it's in the 172.16.0.0 - 172.31.255.255 range
        if ip_address.startswith("172."):
            try:
                second_octet = int(ip_address.split(".")[1])
                return 16 <= second_octet <= 31
            except (ValueError, IndexError):
                return False
        return True

    return False


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
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            # X-Forwarded-For can contain multiple IPs (client, proxy1, proxy2, ...)
            # The first IP is typically the original client
            ip_address = x_forwarded_for.split(",")[0].strip()
            if ip_address:
                return ip_address

        # Check X-Real-IP header (used by some proxies like nginx)
        x_real_ip = request.headers.get("x-real-ip")
        if x_real_ip:
            ip_address = x_real_ip.strip()
            if ip_address:
                return ip_address

        # Fall back to REMOTE_ADDR (direct connection)
        remote_addr = request.META.get("REMOTE_ADDR", "").strip()
        if remote_addr:
            return remote_addr

        return "unknown"

    except Exception as e:
        logger.debug(f"Error extracting IP address: {e}")
        return "unknown"


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
        "HTTP_USER_AGENT",
        "HTTP_ACCEPT",
        "HTTP_ACCEPT_LANGUAGE",
        "HTTP_ACCEPT_ENCODING",
        "HTTP_DNT",  # Do Not Track
        "HTTP_CONNECTION",
        "HTTP_UPGRADE_INSECURE_REQUESTS",
        "HTTP_SEC_FETCH_SITE",
        "HTTP_SEC_FETCH_MODE",
        "HTTP_SEC_FETCH_USER",
        "HTTP_SEC_FETCH_DEST",
        "HTTP_SEC_CH_UA",
        "HTTP_SEC_CH_UA_MOBILE",
        "HTTP_SEC_CH_UA_PLATFORM",
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
        fingerprint_string = "|".join(fingerprint_components)

        # Generate hash
        fingerprint_hash = hashlib.sha256(fingerprint_string.encode("utf-8")).hexdigest()

        return fingerprint_hash

    except Exception as e:
        logger.error(f"Error generating request fingerprint: {e}", exc_info=True)
        # Return a fallback fingerprint based on timestamp
        import time

        return hashlib.sha256(f"fallback:{time.time()}".encode("utf-8")).hexdigest()


def get_request_fingerprint_data(request) -> Dict[str, Any]:
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
            "ip_address": ip_address,
            "user_agent": request.headers.get("user-agent", "unknown"),
            "headers": headers,
            "fingerprint": generate_fingerprint(request, include_ip=True),
            "fingerprint_no_ip": generate_fingerprint(request, include_ip=False),
            "method": request.method,
            "path": request.path,
            "is_secure": request.is_secure(),
            "is_ajax": request.headers.get("X-Requested-With") == "XMLHttpRequest",
        }

    except Exception as e:
        logger.error(f"Error getting request fingerprint data: {e}", exc_info=True)
        return {
            "ip_address": "unknown",
            "user_agent": "unknown",
            "headers": {},
            "fingerprint": "error",
            "fingerprint_no_ip": "error",
            "method": "unknown",
            "path": "unknown",
            "is_secure": False,
            "is_ajax": False,
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
    if not user_agent or user_agent == "unknown":
        return {
            "browser": None,
            "browser_version": None,
            "os": None,
            "device": None,
        }

    ua_lower = user_agent.lower()

    # Detect browser
    browser = None
    browser_version = None

    if "edg/" in ua_lower:
        browser = "Edge"
    elif "chrome/" in ua_lower and "edg/" not in ua_lower:
        browser = "Chrome"
    elif "firefox/" in ua_lower:
        browser = "Firefox"
    elif "safari/" in ua_lower and "chrome/" not in ua_lower:
        browser = "Safari"
    elif "opera/" in ua_lower or "opr/" in ua_lower:
        browser = "Opera"

    # Detect OS
    os = None
    if "windows" in ua_lower:
        os = "Windows"
    elif "mac os" in ua_lower or "macos" in ua_lower:
        os = "macOS"
    elif "linux" in ua_lower:
        os = "Linux"
    elif "android" in ua_lower:
        os = "Android"
    elif "ios" in ua_lower or "iphone" in ua_lower or "ipad" in ua_lower:
        os = "iOS"

    # Detect device type
    device = "Desktop"
    if "mobile" in ua_lower or "android" in ua_lower or "iphone" in ua_lower:
        device = "Mobile"
    elif "tablet" in ua_lower or "ipad" in ua_lower:
        device = "Tablet"

    return {
        "browser": browser,
        "browser_version": browser_version,
        "os": os,
        "device": device,
        "raw": user_agent,
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
        user_agent = request.headers.get("user-agent", "")
        if not user_agent:
            return (True, "Missing User-Agent header")

        # Check for suspicious user agents
        suspicious_patterns = [
            "curl",
            "wget",
            "python-requests",
            "scrapy",
            "bot",
            "crawler",
            "spider",
        ]

        ua_lower = user_agent.lower()
        for pattern in suspicious_patterns:
            if pattern in ua_lower and "googlebot" not in ua_lower and "bingbot" not in ua_lower:
                return (True, f"Suspicious User-Agent pattern: {pattern}")

        # Check for missing common headers
        if not request.headers.get("accept"):
            return (True, "Missing Accept header")

        # Check for IP address issues
        ip_address = get_client_ip(request)
        if ip_address == "unknown":
            return (True, "Unable to determine IP address")

        return (False, None)

    except Exception as e:
        logger.error(f"Error checking for suspicious request: {e}", exc_info=True)
        return (False, None)


def geolocate_ip(ip_address: str) -> Optional[Dict[str, Any]]:
    """
    Geolocate a single IP address using ip-api.com.

    Args:
        ip_address: IP address to geolocate

    Returns:
        Dictionary with geolocation data or None if failed
        Response includes: country, countryCode, region, regionName, city,
                          zip, lat, lon, timezone, isp, org, as, query

    Note:
        Free tier limit: 45 requests per minute
        For batch requests, use geolocate_ips_batch()
    """
    # Skip local/private IPs
    if is_local_ip(ip_address):
        logger.debug(f"Skipping geolocation for local/private IP: {ip_address}")
        return None

    try:
        response = requests.get(f"http://ip-api.com/json/{ip_address}", timeout=5)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "success":
            # Remove status and query fields (query is the IP we already have)
            data.pop("status", None)
            data.pop("query", None)
            logger.debug(f"Successfully geolocated IP {ip_address}: {data.get('city')}, {data.get('country')}")
            return data
        else:
            logger.warning(f"Geolocation failed for IP {ip_address}: {data.get('message', 'Unknown error')}")
            return None

    except requests.RequestException as e:
        logger.error(f"Error geolocating IP {ip_address}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error geolocating IP {ip_address}: {e}", exc_info=True)
        return None


def geolocate_ips_batch(ip_addresses: List[str], batch_size: int = 100) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Geolocate multiple IP addresses in batches using ip-api.com batch endpoint.

    Args:
        ip_addresses: List of IP addresses to geolocate
        batch_size: Number of IPs per batch (max 100 for free tier)

    Returns:
        Dictionary mapping IP addresses to their geolocation data

    Note:
        Free tier limit: 15 requests per minute for batch endpoint
        Each batch can contain up to 100 IP addresses
    """
    results = {}

    # Filter out local/private IPs
    filtered_ips = [ip for ip in ip_addresses if not is_local_ip(ip)]

    if not filtered_ips:
        logger.debug("No valid IPs to geolocate after filtering")
        return results

    logger.info(f"Geolocating {len(filtered_ips)} IP addresses in batches of {batch_size}")

    # Process in batches
    for i in range(0, len(filtered_ips), batch_size):
        batch = filtered_ips[i : i + batch_size]
        batch_num = (i // batch_size) + 1

        try:
            # ip-api.com batch endpoint expects JSON array of IP addresses
            response = requests.post(
                "http://ip-api.com/batch",
                json=batch,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            # Process batch results
            for result in data:
                if result.get("status") == "success":
                    ip = result.pop("query")
                    result.pop("status")
                    results[ip] = result
                    logger.debug(f"Batch {batch_num}: Geolocated {ip} -> {result.get('city')}, {result.get('country')}")
                else:
                    ip = result.get("query", "unknown")
                    logger.warning(f"Batch {batch_num}: Failed to geolocate {ip}: {result.get('message')}")
                    results[ip] = None

            logger.info(f"Batch {batch_num}/{(len(filtered_ips) + batch_size - 1) // batch_size} completed")

        except requests.RequestException as e:
            logger.error(f"Error geolocating batch {batch_num}: {e}")
            for ip in batch:
                results[ip] = None
        except Exception as e:
            logger.error(f"Unexpected error in batch {batch_num}: {e}", exc_info=True)
            for ip in batch:
                results[ip] = None

    logger.info(
        f"Geolocation complete: {sum(1 for v in results.values() if v is not None)}/{len(filtered_ips)} successful"
    )

    return results
