import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import networkx as nx
from io import BytesIO
import time


class WebsiteParser:
    def __init__(self, base_url, max_depth=3):
        self.base_url = base_url
        self.max_depth = max_depth
        self.graph = nx.DiGraph()
        self.visited = set()
        self.queue = []
        self.domain = urlparse(base_url).netloc
        self.total_links = 0
        self.current_url = ""
        self.progress_callback = None
        

    def set_progress_callback(self, callback):
        self.progress_callback = callback
        

    def is_internal_link(self, url):
        parsed = urlparse(url)
        return parsed.netloc == self.domain or not parsed.netloc
        

    def normalize_url(self, url):
        parsed = urlparse(url)

        if not parsed.netloc:
            return urljoin(self.base_url, parsed.path)
        
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        

    def parse(self):
        self.queue.append((self.base_url, 0))
        self.visited.add(self.base_url)
        self.graph.add_node(self.base_url)
        processed = 0
        
        while self.queue:
            url, depth = self.queue.pop(0)
            self.current_url = url
            processed += 1

            if self.progress_callback:
                self.progress_callback(processed, len(self.queue) + processed)
                
            try:
                response = requests.get(url, timeout=5)

                content_type = response.headers.get('Content-Type', '')
                is_xml = 'xml' in content_type or 'xhtml' in content_type
                
                if is_xml:
                    soup = BeautifulSoup(response.content, 'xml')
                else:
                    soup = BeautifulSoup(response.content, 'html.parser')
                
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    # Пропустим якорные ссылки
                    if href.startswith('#') or href.startswith('javascript:'):
                        continue
                        
                    absolute_url = urljoin(url, href)
                    normalized_url = self.normalize_url(absolute_url)
                    
                    if self.is_internal_link(absolute_url):
                        # Всегда добавляем ребро
                        if normalized_url not in self.graph:
                            self.graph.add_node(normalized_url)
                            if depth < self.max_depth - 1:
                                self.queue.append((normalized_url, depth + 1))
                        
                        self.graph.add_edge(url, normalized_url)
                
                # Be polite
                time.sleep(0.5)
                    
            except Exception as e:
                print(f"Error parsing {url}: {e}")
        
        return self.graph
    
    
    def to_graphml(self):
        from io import BytesIO
        output = BytesIO()
        nx.write_graphml(self.graph, output)
        output.seek(0)
        return output.getvalue().decode('utf-8')
    