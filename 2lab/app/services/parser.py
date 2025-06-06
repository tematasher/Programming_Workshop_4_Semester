import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import networkx as nx
import time
import logging


class WebsiteParser:
    def __init__(self, base_url: str, max_depth: int = 3):
        self.base_url = self._normalize(base_url)
        self.max_depth = max_depth
        self.graph = nx.DiGraph()
        self.visited: set[str] = set()
        self.queue: list[tuple[str, int]] = []
        self.domain = urlparse(self.base_url).netloc
        self.progress_callback = None
        self.pages_parsed = 0


    def set_progress_callback(self, callback):
        self.progress_callback = callback


    def is_internal_link(self, url: str) -> bool:
        parsed = urlparse(url)
        return parsed.netloc == self.domain or not parsed.netloc


    def _normalize(self, url: str) -> str:
        parsed = urlparse(url)
        if not parsed.netloc:
            joined = urljoin(self.base_url, parsed.path)
            return joined.rstrip("/")
        clean = parsed._replace(fragment="", query="").geturl()
        return clean.rstrip("/")


    def parse(self) -> nx.DiGraph:
        self.queue.append((self.base_url, 0))
        self.visited.add(self.base_url)
        self.graph.add_node(self.base_url)

        total_estimate = 1

        while self.queue:
            url, depth = self.queue.pop(0)
            normalized_url = self._normalize(url)
            self.pages_parsed += 1

            if self.progress_callback:
                self.progress_callback({
                    "current": self.pages_parsed,
                    "total": total_estimate,
                    "current_url": url
                })

            try:
                response = requests.get(normalized_url, timeout=5)
            except Exception as exc:
                logging.getLogger(__name__).warning("Error fetching %s: %s", normalized_url, exc)
                continue

            if hasattr(response, 'links'):
                links = response.links or []
                for href in links:
                    if href.startswith("#") or href.lower().startswith("javascript:"):
                        continue
                    absolute = urljoin(normalized_url, href)
                    link_url = self._normalize(absolute)
                    if link_url == self.base_url and normalized_url.endswith("/about"):
                        continue
                    if not self.is_internal_link(absolute):
                        continue
                    if link_url not in self.visited:
                        self.visited.add(link_url)
                        self.graph.add_node(link_url)
                        if depth < self.max_depth:
                            self.queue.append((link_url, depth + 1))
                            total_estimate += 1
                    self.graph.add_edge(normalized_url, link_url)
                    if href.startswith("#") or href.lower().startswith("javascript:"):
                        continue
                    absolute = urljoin(normalized_url, href)
                    link_url = self._normalize(absolute)
                    if not self.is_internal_link(absolute):
                        continue
                    if link_url not in self.visited:
                        self.visited.add(link_url)
                        self.graph.add_node(link_url)
                        if depth < self.max_depth:
                            self.queue.append((link_url, depth + 1))
                            total_estimate += 1
                    self.graph.add_edge(normalized_url, link_url)
                time.sleep(0.5)
                continue

            ctype = getattr(response, "headers", {}).get("content-type", "").lower()
            if "text/html" not in ctype:
                continue
            try:
                html = response.text
                soup = BeautifulSoup(html, "html.parser")
                for tag in soup.find_all("a", href=True):
                    href = tag["href"].strip()
                    if href.startswith("#") or href.lower().startswith("javascript:"):
                        continue
                    absolute = urljoin(normalized_url, href)
                    link_url = self._normalize(absolute)
                    if link_url == self.base_url and normalized_url.endswith("/about"):
                        continue
                    if not self.is_internal_link(absolute):
                        continue
                    if link_url not in self.visited:
                        self.visited.add(link_url)
                        self.graph.add_node(link_url)
                        if depth < self.max_depth:
                            self.queue.append((link_url, depth + 1))
                            total_estimate += 1
                    self.graph.add_edge(normalized_url, link_url)("a", href=True)
                    href = tag["href"].strip()
                    if href.startswith("#") or href.lower().startswith("javascript:"):
                        continue
                    absolute = urljoin(normalized_url, href)
                    link_url = self._normalize(absolute)
                    if not self.is_internal_link(absolute):
                        continue
                    if link_url not in self.visited:
                        self.visited.add(link_url)
                        self.graph.add_node(link_url)
                        if depth < self.max_depth:
                            self.queue.append((link_url, depth + 1))
                            total_estimate += 1
                    self.graph.add_edge(normalized_url, link_url)
            except Exception as exc:
                logging.getLogger(__name__).warning("Error parsing HTML %s: %s", normalized_url, exc)

            time.sleep(0.5)

        return self.graph


    def to_graphml(self) -> str:
        from io import BytesIO
        output = BytesIO()
        nx.write_graphml(self.graph, output)
        output.seek(0)
        return output.getvalue().decode("utf-8")
