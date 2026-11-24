"""Opt-in public-page intake. No invention text is sent; redirects and destinations are checked."""
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import http.client
import ipaddress
import socket
import ssl
from urllib.parse import urljoin, urlsplit

# Single public abstractions only; no generated combinations or free-text query upload.
TOPICS = ('UV air treatment', 'respiratory protective devices', 'optical shielding', 'water leak detection',
          'automatic shutoff valves', 'recommendation systems', 'distributed data systems', 'industrial sensors',
          'machine learning systems', 'medical imaging', 'battery management', 'robotic control')


def destination(url):
    if not isinstance(url, str) or any(c.isspace() or ord(c) < 32 for c in url):
        raise ValueError('Enter a public HTTPS page URL')
    parts = urlsplit(url)
    if parts.scheme != 'https' or not parts.hostname or parts.username or parts.password or parts.port not in (None, 443) or parts.query:
        raise ValueError('Use a public HTTPS page without credentials, a query string, or a nonstandard port. Do not use private or signed document links.')
    addresses = list(dict.fromkeys(x[4][0] for x in socket.getaddrinfo(parts.hostname, 443, type=socket.SOCK_STREAM)))
    if not addresses or any(not ipaddress.ip_address(ip).is_global or ipaddress.ip_address(ip).is_multicast or ipaddress.ip_address(ip).is_reserved for ip in addresses):
        raise ValueError('Private, loopback, and reserved network destinations are not allowed')
    return parts, addresses[0]


class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, hostname, ip):
        super().__init__(hostname, timeout=15)
        self.ip = ip

    def connect(self):
        # Connect to the validated address, while preserving TLS hostname verification.
        sock = socket.create_connection((self.ip, 443), self.timeout)
        try:
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except Exception:
            sock.close()
            raise


class TextPage(HTMLParser):
    def __init__(self):
        super().__init__(); self.skip = 0; self.parts = []; self.title = []; self.in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'nav', 'footer', 'form', 'noscript', 'svg'):
            self.skip += 1
        if tag == 'title': self.in_title = True
        if tag in ('p', 'h1', 'h2', 'h3', 'li', 'div'): self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'nav', 'footer', 'form', 'noscript', 'svg'):
            self.skip = max(0, self.skip - 1)
        if tag == 'title': self.in_title = False

    def handle_data(self, text):
        if self.in_title: self.title.append(text)
        if not self.skip: self.parts.append(text + ' ')


def fetch_public(url):
    for _ in range(4):
        parts, ip = destination(url)
        connection = PinnedHTTPS(parts.hostname, ip)
        try:
            connection.request('GET', parts.path or '/', headers={'User-Agent': 'InventionDisclosureLocal/0.1', 'Accept': 'text/html,text/plain', 'Accept-Encoding': 'identity'})
            response = connection.getresponse()
            if response.status in (301, 302, 303, 307, 308):
                url = urljoin(url, response.getheader('Location', ''))
                continue
            if response.status != 200:
                raise ValueError('Public page could not be retrieved; no source was marked inspected')
            content_type = response.getheader('Content-Type', '').lower()
            if not any(x in content_type for x in ('text/html', 'text/plain')):
                raise ValueError('This prototype supports readable public HTML or text pages, not PDFs or other files')
            raw = response.read(1_000_001)
            if len(raw) > 1_000_000:
                raise ValueError('Public page exceeds the 1 MB intake limit')
            parser = TextPage(); parser.feed(raw.decode('utf-8', errors='replace'))
            paragraphs = [' '.join(x.split()) for x in ''.join(parser.parts).splitlines() if x.strip()]
            text = '\n'.join(f'P{i+1}: {line}' for i, line in enumerate(paragraphs))
            if len(text) < 200:
                raise ValueError('Not enough readable source text; no evidence was recorded')
            return {'url': url.split('#')[0], 'title': ' '.join(parser.title).strip()[:250] or parts.hostname,
                    'text': text[:20000], 'digest': hashlib.sha256(raw).hexdigest(),
                    'accessed': datetime.now(timezone.utc).date().isoformat()}
        finally:
            connection.close()
    raise ValueError('Too many redirects; no source was imported')
