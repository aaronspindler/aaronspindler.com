import logging
import re

from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed
from django.http import HttpResponseForbidden
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class RequestFingerprintMiddleware(MiddlewareMixin):
    def __init__(self, get_response):
        super().__init__(get_response)
        try:
            logger.debug("RequestFingerprintMiddleware initialized")
        except Exception as e:
            logger.error(f"Failed to initialize RequestFingerprintMiddleware: {e}")
            raise MiddlewareNotUsed(f"RequestFingerprintMiddleware disabled: {e}") from e

    def _should_skip_path(self, path):
        exclude_paths = getattr(settings, "REQUEST_TRACKING_EXCLUDE_PATHS", [])
        for excluded in exclude_paths:
            if path.startswith(excluded):
                return True
        return False

    def _check_ip_ban(self, ip_address):
        from django.db import models

        from utils.models import Ban, IPAddress

        try:
            ip_obj = IPAddress.objects.filter(ip_address=ip_address).first()
            if not ip_obj:
                return None

            now = timezone.now()
            ban = (
                Ban.objects.filter(
                    ip_address=ip_obj,
                    is_active=True,
                )
                .filter(models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now))
                .first()
            )

            return ban
        except Exception as e:
            logger.error(f"Error checking IP ban: {e}")
            return None

    def _check_fingerprint_ban(self, fingerprint_hash):
        from django.db import models

        from utils.models import Ban, Fingerprint

        try:
            fp_obj = Fingerprint.objects.filter(hash=fingerprint_hash).first()
            if not fp_obj:
                return None

            now = timezone.now()
            ban = (
                Ban.objects.filter(
                    fingerprint=fp_obj,
                    is_active=True,
                )
                .filter(models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now))
                .first()
            )

            return ban
        except Exception as e:
            logger.error(f"Error checking fingerprint ban: {e}")
            return None

    def _check_user_agent_ban(self, user_agent):
        from django.db import models

        from utils.models import Ban

        if not user_agent:
            return None

        try:
            now = timezone.now()
            ua_bans = (
                Ban.objects.filter(
                    is_active=True,
                )
                .exclude(user_agent_pattern="")
                .filter(models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now))
            )

            for ban in ua_bans:
                try:
                    if re.search(ban.user_agent_pattern, user_agent, re.IGNORECASE):
                        return ban
                except re.error:
                    logger.warning(f"Invalid regex pattern in ban {ban.id}: {ban.user_agent_pattern}")
                    continue

            return None
        except Exception as e:
            logger.error(f"Error checking user agent ban: {e}")
            return None

    def process_request(self, request):
        from utils.security import generate_fingerprint, get_client_ip, is_global_ip

        path = request.path

        if self._should_skip_path(path):
            return None

        ip_address = get_client_ip(request)
        if not is_global_ip(ip_address):
            return None

        user_agent = request.headers.get("user-agent", "")

        ip_ban = self._check_ip_ban(ip_address)
        if ip_ban:
            logger.warning(f"Blocked banned IP: {ip_address} (Ban ID: {ip_ban.id}, Reason: {ip_ban.reason})")
            return HttpResponseForbidden("Access denied.")

        fingerprint_hash = generate_fingerprint(request, include_ip=False)
        fp_ban = self._check_fingerprint_ban(fingerprint_hash)
        if fp_ban:
            logger.warning(
                f"Blocked banned fingerprint: {fingerprint_hash[:16]}... from IP {ip_address} "
                f"(Ban ID: {fp_ban.id}, Reason: {fp_ban.reason})"
            )
            return HttpResponseForbidden("Access denied.")

        ua_ban = self._check_user_agent_ban(user_agent)
        if ua_ban:
            logger.warning(
                f"Blocked banned user agent pattern from IP {ip_address} "
                f"(Ban ID: {ua_ban.id}, Pattern: {ua_ban.user_agent_pattern})"
            )
            return HttpResponseForbidden("Access denied.")

        try:
            from utils.models import TrackedRequest

            tracked_request = TrackedRequest.create_from_request(request)
            request.tracked_request = tracked_request

            if tracked_request.is_suspicious:
                logger.warning(
                    f"Suspicious request detected: {request.method} {path} | "
                    f"IP: {ip_address} | Reason: {tracked_request.suspicious_reason}"
                )

        except Exception as e:
            logger.error(f"Error creating request fingerprint: {e}", exc_info=True)

        return None
