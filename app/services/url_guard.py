"""Validate URLs, resolve all addresses, and pin the request to a vetted IP.

The same checks run for redirects and discovered pages. DNS is never resolved a
second time by HTTPX: the actual request URL contains the checked numeric IP.
"""

import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit, urlunsplit

from app.errors import AnalysisError


class UnsafeURL(ValueError):
    pass


def normalize_url(value: str) -> str:
    try:
        if len(value) > 2048 or any(ord(c) < 33 or ord(c) == 127 for c in value) or "\\" in value:
            raise UnsafeURL("URL contains invalid characters or exceeds 2048 characters")
        parts = urlsplit(value)
        if parts.scheme.lower() not in ("http", "https") or not parts.hostname:
            raise UnsafeURL("Use an absolute HTTP or HTTPS website URL")
        if parts.username is not None or parts.password is not None:
            raise UnsafeURL("URL credentials are not allowed")
        if parts.port not in (None, 80 if parts.scheme.lower() == "http" else 443):
            raise UnsafeURL("Only standard HTTP and HTTPS ports are allowed")
        host = parts.hostname.rstrip(".").encode("idna").decode("ascii").lower()
        if (
            not host
            or "%" in host
            or host == "localhost"
            or host.endswith((".localhost", ".local", ".internal", ".home", ".test", ".invalid"))
        ):
            raise UnsafeURL("Private and local destinations are not allowed")
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            # libc accepts abbreviated, octal and hex IPv4 forms that ipaddress
            # rejects. Avoid ambiguous hostnames before DNS or HTTP parsing.
            try:
                socket.inet_aton(host)
            except OSError:
                pass
            else:
                raise UnsafeURL("Use a canonical public IP address or hostname")
            if "." not in host or any(
                not label
                or len(label) > 63
                or not all(c.isalnum() or c == "-" for c in label)
                or label.startswith("-")
                or label.endswith("-")
                for label in host.split(".")
            ):
                raise UnsafeURL("A public website hostname is required") from None
        else:
            require_public(str(address))
        authority = f"[{host}]" if ":" in host else host
        return urlunsplit((parts.scheme.lower(), authority, parts.path or "/", parts.query, ""))
    except (ValueError, UnicodeError) as exc:
        if isinstance(exc, UnsafeURL):
            raise
        raise UnsafeURL("Invalid website URL") from None


def require_public(value: str) -> None:
    address = ipaddress.ip_address(value)
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        address = address.ipv4_mapped
    if not address.is_global or address.is_multicast or address.is_reserved:
        raise UnsafeURL("Private and non-public network addresses are not allowed")
    # Transition mechanisms can encode an internal IPv4 destination.
    if isinstance(address, ipaddress.IPv6Address) and (address.sixtofour or address.teredo):
        raise UnsafeURL("IPv6 transition addresses are not allowed")


async def resolve_public(url: str) -> list[str]:
    parts = urlsplit(normalize_url(url))
    try:
        records = await asyncio.wait_for(
            asyncio.get_running_loop().getaddrinfo(
                parts.hostname, 443 if parts.scheme == "https" else 80, type=socket.SOCK_STREAM
            ),
            timeout=5,
        )
    except (OSError, TimeoutError):
        raise AnalysisError("dns_failed", "Website hostname could not be resolved", 422) from None
    addresses = list(dict.fromkeys(row[4][0] for row in records))
    if not addresses:
        raise AnalysisError("dns_failed", "Website hostname could not be resolved", 422)
    try:
        for address in addresses:
            require_public(address)
    except ValueError:
        raise AnalysisError(
            "unsafe_url", "Website resolves to a private or non-public address", 422
        ) from None
    # Prefer IPv4 for hosts without outbound IPv6; both families have been checked.
    return sorted(addresses, key=lambda value: ":" in value)
