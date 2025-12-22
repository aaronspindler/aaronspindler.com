import hashlib
import logging
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)


def is_local_ip(ip_address: str) -> bool:
    if not ip_address or ip_address == "unknown":
        return False

    if ip_address in ["127.0.0.1", "::1", "localhost"]:
        return True

    if ip_address.startswith(("10.", "192.168.", "172.")):
        if ip_address.startswith("172."):
            try:
                second_octet = int(ip_address.split(".")[1])
                return 16 <= second_octet <= 31
            except (ValueError, IndexError):
                return False
        return True

    return False


def is_reserved_ip(ip_address: str) -> bool:
    if not ip_address or ip_address == "unknown":
        return False

    try:
        import ipaddress as ipaddr

        ip = ipaddr.ip_address(ip_address)

        return (
            ip.is_private  # RFC 1918 private networks
            or ip.is_loopback  # 127.0.0.0/8
            or ip.is_link_local  # 169.254.0.0/16
            or ip.is_multicast  # 224.0.0.0/4 (multicast range)
            or ip.is_reserved  # Other reserved ranges
        )
    except ValueError:
        # Invalid IP address format - treat as reserved
        logger.warning(f"Invalid IP address format: {ip_address}")
        return True


def is_global_ip(ip_address: str) -> bool:
    if not ip_address or ip_address == "unknown":
        return False

    try:
        import ipaddress as ipaddr

        ip = ipaddr.ip_address(ip_address)
        return ip.is_global
    except ValueError:
        # Invalid IP address format
        logger.warning(f"Invalid IP address format: {ip_address}")
        return False


def is_trusted_proxy(ip_address: str) -> bool:
    if not ip_address or ip_address == "unknown":
        return False

    try:
        import ipaddress as ipaddr

        from django.conf import settings

        trusted_proxies = getattr(settings, "TRUSTED_PROXY_IPS", [])
        if not trusted_proxies:
            return False

        client_ip = ipaddr.ip_address(ip_address)

        for trusted in trusted_proxies:
            try:
                # Handle CIDR notation (e.g., "10.0.0.0/8")
                if "/" in trusted:
                    network = ipaddr.ip_network(trusted, strict=False)
                    if client_ip in network:
                        return True
                else:
                    # Handle single IP
                    trusted_ip = ipaddr.ip_address(trusted)
                    if client_ip == trusted_ip:
                        return True
            except (ValueError, ipaddr.AddressValueError):
                logger.warning(f"Invalid trusted proxy IP format: {trusted}")
                continue

        return False
    except Exception as e:
        logger.debug(f"Error checking trusted proxy: {e}")
        return False


def get_client_ip(request) -> str:
    try:
        remote_addr = request.META.get("REMOTE_ADDR", "").strip()
        is_from_trusted_proxy = is_trusted_proxy(remote_addr) if remote_addr else False

        if is_from_trusted_proxy:
            x_forwarded_for = request.headers.get("x-forwarded-for")
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(",")[0].strip()
                if ip_address:
                    if is_global_ip(ip_address):
                        return ip_address
                    else:
                        logger.debug(
                            f"X-Forwarded-For contains non-global IP {ip_address} from trusted proxy {remote_addr}, "
                            f"falling back to REMOTE_ADDR"
                        )

            x_real_ip = request.headers.get("x-real-ip")
            if x_real_ip:
                ip_address = x_real_ip.strip()
                if ip_address:
                    if is_global_ip(ip_address):
                        return ip_address
                    else:
                        logger.debug(
                            f"X-Real-IP contains non-global IP {ip_address} from trusted proxy {remote_addr}, "
                            f"falling back to REMOTE_ADDR"
                        )

        if remote_addr:
            if is_global_ip(remote_addr):
                return remote_addr
            else:
                logger.debug(
                    f"REMOTE_ADDR {remote_addr} is not a global IP. "
                    f"Request may be from untrusted proxy or misconfigured proxy chain."
                )

        return "unknown"

    except Exception as e:
        logger.debug(f"Error extracting IP address: {e}")
        return "unknown"


def get_request_headers(request) -> Dict[str, str]:
    headers = {}

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
    try:
        fingerprint_components = []

        if include_ip:
            ip_address = get_client_ip(request)
            fingerprint_components.append(f"ip:{ip_address}")

        headers = get_request_headers(request)
        for key in sorted(headers.keys()):  # Sort for consistency
            fingerprint_components.append(f"{key}:{headers[key]}")

        fingerprint_string = "|".join(fingerprint_components)

        fingerprint_hash = hashlib.sha256(fingerprint_string.encode("utf-8")).hexdigest()

        return fingerprint_hash

    except Exception as e:
        logger.error(f"Error generating request fingerprint: {e}", exc_info=True)
        import time

        return hashlib.sha256(f"fallback:{time.time()}".encode("utf-8")).hexdigest()


def get_request_fingerprint_data(request) -> Dict[str, Any]:
    try:
        ip_address = get_client_ip(request)
        headers = get_request_headers(request)

        query_params = dict(request.GET.lists()) if request.GET else {}
        # Convert single-item lists to single values for cleaner storage
        query_params = {k: v[0] if len(v) == 1 else v for k, v in query_params.items()}

        return {
            "ip_address": ip_address,
            "user_agent": request.headers.get("user-agent", "unknown"),
            "headers": headers,
            "fingerprint": generate_fingerprint(request, include_ip=True),
            "fingerprint_no_ip": generate_fingerprint(request, include_ip=False),
            "method": request.method,
            "path": request.path,
            "query_params": query_params,
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
            "query_params": {},
            "is_secure": False,
            "is_ajax": False,
        }


def parse_user_agent(user_agent: str) -> Dict[str, Optional[str]]:
    if not user_agent or user_agent == "unknown":
        return {
            "browser": None,
            "browser_version": None,
            "os": None,
            "device": None,
        }

    try:
        from user_agents import parse

        ua = parse(user_agent)

        browser = ua.browser.family if ua.browser.family else None
        browser_version = ua.browser.version_string if ua.browser.version_string else None

        os_name = ua.os.family if ua.os.family else None

        if ua.is_mobile:
            device = "Mobile"
        elif ua.is_tablet:
            device = "Tablet"
        elif ua.is_pc:
            device = "Desktop"
        elif ua.is_bot:
            device = "Bot"
        else:
            device = "Other"

        return {
            "browser": browser,
            "browser_version": browser_version,
            "os": os_name,
            "device": device,
        }

    except Exception as e:
        logger.warning(f"Error parsing user agent: {e}")
        return {
            "browser": None,
            "browser_version": None,
            "os": None,
            "device": None,
        }


def is_suspicious_request(request) -> Tuple[bool, Optional[str]]:
    from django.conf import settings

    allowed_bots = ["googlebot", "bingbot", "yandexbot", "duckduckbot", "baiduspider", "slurp"]

    try:
        user_agent = request.headers.get("user-agent", "")
        if not user_agent:
            return (True, "Missing User-Agent header")

        ua_lower = user_agent.lower()

        is_allowed_bot = any(bot in ua_lower for bot in allowed_bots)

        suspicious_ua_patterns = getattr(
            settings,
            "REQUEST_TRACKING_SUSPICIOUS_USER_AGENTS",
            ["curl", "wget", "python-requests", "scrapy", "bot", "crawler", "spider"],
        )

        if not is_allowed_bot:
            for pattern in suspicious_ua_patterns:
                if pattern.lower() in ua_lower:
                    return (True, f"Suspicious User-Agent pattern: {pattern}")

        suspicious_paths = getattr(
            settings,
            "REQUEST_TRACKING_SUSPICIOUS_PATHS",
            ["/wp-admin", "/wp-login", "/.env", "/.git", "/phpMyAdmin"],
        )

        path = request.path.lower()
        for suspicious_path in suspicious_paths:
            if path.startswith(suspicious_path.lower()):
                return (True, f"Suspicious path: {suspicious_path}")

        if not request.headers.get("accept"):
            return (True, "Missing Accept header")

        ip_address = get_client_ip(request)
        if ip_address == "unknown":
            return (True, "Unable to determine IP address")

        return (False, None)

    except Exception as e:
        logger.error(f"Error checking for suspicious request: {e}", exc_info=True)
        return (False, None)


def geolocate_ip(ip_address: str) -> Optional[Dict[str, Any]]:
    if not is_global_ip(ip_address):
        logger.debug(f"Skipping geolocation for non-global IP: {ip_address}")
        return None

    try:
        response = requests.get(f"http://ip-api.com/json/{ip_address}", timeout=5)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "success":
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


def geolocate_ips_batch(
    ip_addresses: List[str], batch_size: int = 100, max_batches: Optional[int] = None
) -> Dict[str, Optional[Dict[str, Any]]]:
    results = {}

    filtered_ips = [ip for ip in ip_addresses if is_global_ip(ip)]

    if not filtered_ips:
        logger.debug("No global IPs to geolocate after filtering")
        return results

    total_batches = (len(filtered_ips) + batch_size - 1) // batch_size
    batches_to_process = min(total_batches, max_batches) if max_batches else total_batches

    logger.info(
        f"Geolocating {len(filtered_ips)} IP addresses in batches of {batch_size} "
        f"(processing {batches_to_process}/{total_batches} batches)"
    )

    batches_processed = 0
    for i in range(0, len(filtered_ips), batch_size):
        if max_batches and batches_processed >= max_batches:
            logger.info(f"Reached max_batches limit ({max_batches}), stopping")
            break

        batch = filtered_ips[i : i + batch_size]
        batch_num = (i // batch_size) + 1

        try:
            response = requests.post(
                "http://ip-api.com/batch",
                json=batch,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

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

            logger.info(f"Batch {batch_num}/{total_batches} completed")

        except requests.RequestException as e:
            logger.error(f"Error geolocating batch {batch_num}: {e}")
            for ip in batch:
                results[ip] = None
        except Exception as e:
            logger.error(f"Unexpected error in batch {batch_num}: {e}", exc_info=True)
            for ip in batch:
                results[ip] = None

        batches_processed += 1

    logger.info(
        f"Geolocation complete: {sum(1 for v in results.values() if v is not None)}/{len(filtered_ips)} successful"
    )

    return results
