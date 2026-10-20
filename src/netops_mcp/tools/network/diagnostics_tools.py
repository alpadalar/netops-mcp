"""Additional diagnostics for NetOps MCP (v1.2): TLS, WHOIS, reverse DNS, email DNS."""

import socket
import ssl
import time
from typing import Any, Dict, List, Optional

from mcp.types import TextContent as Content

from ...validators.input_validator import (
    ValidationError,
    validate_domain,
    validate_hostname,
    validate_ip_address,
    validate_port,
)
from ..base import NetOpsTool

_MAX_WHOIS_CHARS = 20000


class DiagnosticsTools(NetOpsTool):
    """TLS certificate inspection, WHOIS, reverse DNS and SPF/DKIM/DMARC checks."""

    def tls_certificate_check(self, host: str, port: int = 443, timeout: int = 10) -> List[Content]:
        """Inspect the TLS certificate a host presents (verified against system CAs).

        Args:
            host: Target hostname or IP
            port: TLS port
            timeout: Connect/handshake timeout in seconds

        Returns:
            JSON content with subject, issuer, validity window, SANs, protocol, cipher
        """
        try:
            if not self._validate_host(host):
                raise ValueError("Invalid host provided")
            validate_port(int(port))
            timeout = max(1, min(int(timeout), 60))
            # Pin the connection to the SSRF-classified IP (no second DNS lookup, so
            # a DNS-rebind between check and connect cannot reach a blocked address).
            # Fail-closed: an unresolvable host is rejected here.
            ips = self._enforce_ssrf(host, int(port))
            if not ips:
                raise ValidationError(f"could not resolve {host}")
            connect_ip = str(ips[0])

            result: Dict[str, Any] = {"host": host, "port": int(port), "verified": True}
            ctx = ssl.create_default_context()
            try:
                with socket.create_connection((connect_ip, int(port)), timeout=timeout) as raw:
                    with ctx.wrap_socket(raw, server_hostname=host) as tls:
                        cert = tls.getpeercert() or {}
                        cipher = tls.cipher()
                        result["protocol"] = tls.version()
                        result["cipher"] = cipher[0] if cipher else None
                        result.update(self._summarize_cert(cert))
            except ssl.SSLCertVerificationError as e:
                result["verified"] = False
                result["verify_error"] = e.verify_message or str(e)
            except (socket.timeout, TimeoutError):
                raise ValueError(f"Connection to {host}:{port} timed out") from None
            except (ssl.SSLError, OSError) as e:
                raise ValueError(f"TLS handshake failed: {e}") from None
            return self._format_response(result, "tls_certificate_check")
        except Exception as e:
            return self._handle_error("check TLS certificate", e)

    @staticmethod
    def _summarize_cert(cert: Dict[str, Any]) -> Dict[str, Any]:
        def flat(name: Any) -> Dict[str, str]:
            return {k: v for rdn in name for (k, v) in rdn} if name else {}

        out: Dict[str, Any] = {
            "subject": flat(cert.get("subject")),
            "issuer": flat(cert.get("issuer")),
            "serial_number": cert.get("serialNumber"),
            "not_before": cert.get("notBefore"),
            "not_after": cert.get("notAfter"),
            "san": [v for (_, v) in cert.get("subjectAltName", [])],
        }
        if cert.get("notAfter"):
            remaining = ssl.cert_time_to_seconds(cert["notAfter"]) - time.time()
            out["days_remaining"] = int(remaining // 86400)
            out["expired"] = remaining < 0
        return out

    def whois_lookup(self, query: str, timeout: int = 30) -> List[Content]:
        """Run a WHOIS lookup for a domain or IP address.

        Args:
            query: Domain name or IP address
            timeout: Command timeout in seconds

        Returns:
            JSON content with the (truncated) WHOIS record
        """
        try:
            try:
                validate_ip_address(query)
            except ValidationError:
                validate_domain(query)
            timeout = max(1, min(int(timeout), 120))
            res = self._execute_command(["whois", query], timeout)
            if not res.get("success"):
                raise RuntimeError(res.get("stderr") or "whois failed")
            text = res.get("stdout", "")
            return self._format_response(
                {
                    "query": query,
                    "truncated": len(text) > _MAX_WHOIS_CHARS,
                    "record": text[:_MAX_WHOIS_CHARS],
                },
                "whois_lookup",
            )
        except Exception as e:
            return self._handle_error("whois lookup", e)

    def reverse_dns_lookup(self, ip: str, timeout: int = 5) -> List[Content]:
        """Resolve the PTR record(s) of an IP address (forward-confirmed).

        Args:
            ip: IPv4 or IPv6 address
            timeout: Resolver lifetime in seconds

        Returns:
            JSON content with PTR names and whether each forward-resolves back to ip
        """
        try:
            ip = validate_ip_address(ip)
            import dns.exception
            import dns.resolver
            import dns.reversename

            resolver = dns.resolver.Resolver()
            resolver.lifetime = max(1, min(int(timeout), 30))
            names: List[str] = []
            try:
                answer = resolver.resolve(dns.reversename.from_address(ip), "PTR")
                names = [str(r).rstrip(".") for r in answer]
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                pass
            except dns.exception.Timeout:
                raise ValueError("Reverse DNS query timed out") from None
            records = []
            for name in names:
                confirmed = False
                try:
                    for rtype in ("A", "AAAA"):
                        try:
                            fwd = resolver.resolve(name, rtype)
                        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
                            continue
                        if ip in {r.to_text() for r in fwd}:
                            confirmed = True
                except dns.exception.DNSException:
                    pass
                records.append({"name": name, "forward_confirmed": confirmed})
            return self._format_response({"ip": ip, "ptr": records}, "reverse_dns_lookup")
        except Exception as e:
            return self._handle_error("reverse DNS lookup", e)

    def email_dns_check(self, domain: str, dkim_selector: Optional[str] = None) -> List[Content]:
        """Check a domain's mail DNS posture: MX, SPF, DMARC and optional DKIM.

        Args:
            domain: Domain to check
            dkim_selector: Optional DKIM selector to look up

        Returns:
            JSON content with the raw records and simple findings
        """
        try:
            validate_domain(domain)
            if dkim_selector is not None:
                validate_hostname(f"{dkim_selector}.x.example")
            import dns.exception
            import dns.resolver

            resolver = dns.resolver.Resolver()
            resolver.lifetime = 5

            def query(name: str, rtype: str) -> List[str]:
                try:
                    return [r.to_text() for r in resolver.resolve(name, rtype)]
                except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                    return []
                except dns.exception.Timeout:
                    raise ValueError(f"DNS query for {name} timed out") from None

            def txt(name: str) -> List[str]:
                return [t.replace('" "', "").strip('"') for t in query(name, "TXT")]

            mx = query(domain, "MX")
            spf = [t for t in txt(domain) if t.lower().startswith("v=spf1")]
            dmarc = [t for t in txt(f"_dmarc.{domain}") if t.lower().startswith("v=dmarc1")]
            findings: List[str] = []
            if not mx:
                findings.append("No MX records")
            if not spf:
                findings.append("No SPF record")
            elif len(spf) > 1:
                findings.append("Multiple SPF records (invalid)")
            elif spf[0].rstrip().endswith("+all"):
                findings.append("SPF ends with +all (permits any sender)")
            if not dmarc:
                findings.append("No DMARC record")
            elif "p=none" in dmarc[0].replace(" ", "").lower():
                findings.append("DMARC policy is p=none (monitoring only)")
            data: Dict[str, Any] = {"domain": domain, "mx": mx, "spf": spf, "dmarc": dmarc}
            if dkim_selector:
                data["dkim"] = txt(f"{dkim_selector}._domainkey.{domain}")
                if not data["dkim"]:
                    findings.append(f"No DKIM record for selector {dkim_selector}")
            data["findings"] = findings
            return self._format_response(data, "email_dns_check")
        except Exception as e:
            return self._handle_error("email DNS check", e)
