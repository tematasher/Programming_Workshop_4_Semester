import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import networkx as nx
from io import StringIO
import time

class WebsiteParser:
    def __init__(self, base_url, max_depth=3):
        self.base_url = base_url
        self.max_depth = max_depth
        self.graph = nx.DiGraph()
        self.visited = set()
        self.queue = []
        self.domain = urlparse(base_url).netloc
        
    def is_internal_link(self, url):
        parsed = urlparse(url)
        return parsed.netloc == self.domain or not parsed.netloc
        
    def normalize_url(self, url):
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        
    def parse(self):
        self.queue.append((self.base_url, 0))
        self.visited.add(self.base_url)
        self.graph.add_node(self.base_url)
        
        while self.queue:
            url, depth = self.queue.pop(0)
            
            if depth >= self.max_depth:
                continue
                
            try:
                response = requests.get(url, timeout=5)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    absolute_url = urljoin(url, href)
                    normalized_url = self.normalize_url(absolute_url)
                    
                    if self.is_internal_link(absolute_url) and normalized_url not in self.visited:
                        self.visited.add(normalized_url)
                        self.queue.append((normalized_url, depth + 1))
                        self.graph.add_node(normalized_url)
                    
                    if normalized_url in self.visited:
                        self.graph.add_edge(url, normalized_url)
                
                # Be polite
                time.sleep(0.5)
                    
            except Exception as e:
                print(f"Error parsing {url}: {e}")
        
        return self.graph
    
    def to_graphml(self):
        output = StringIO()
        nx.write_graphml(self.graph, output)
        return output.getvalue()