import os
import sys
import pytest
import networkx as nx
from app.services.parser import WebsiteParser


@pytest.fixture
def mock_requests(monkeypatch):
    class MockResponse:
        def __init__(self, text, links=[]):
            self.text = text
            self.links = links
        
        def find_all(self, *args, **kwargs):
            return [MockLink(link) for link in self.links]
    
    class MockLink:
        def __init__(self, href):
            self.attrs = {"href": href}
    
    def mock_get(url, *args, **kwargs):
        pages = {
            "https://example.com": MockResponse(
                "Main page",
                links=["/about", "/contact"]
            ),
            "https://example.com/about": MockResponse(
                "About page",
                links=["/", "/contact"]
            ),
            "https://example.com/contact": MockResponse(
                "Contact page",
                links=["/"]
            ),
        }
        return pages.get(url, MockResponse("Not found", links=[]))
    
    monkeypatch.setattr("requests.get", mock_get)

def test_parser_single_page():
    parser = WebsiteParser("https://example.com", max_depth=0)
    graph = parser.parse()
    assert len(graph.nodes) == 1
    assert "https://example.com" in graph.nodes
    assert len(graph.edges) == 0

def test_parser_with_links(mock_requests):
    parser = WebsiteParser("https://example.com", max_depth=2)
    graph = parser.parse()
    
    assert len(graph.nodes) == 3
    assert "https://example.com" in graph.nodes
    assert "https://example.com/about" in graph.nodes
    assert "https://example.com/contact" in graph.nodes
    
    assert ("https://example.com", "https://example.com/about") in graph.edges
    assert ("https://example.com/about", "https://example.com/contact") in graph.edges
    assert ("https://example.com/contact", "https://example.com") in graph.edges

def test_parser_cyclic_links(mock_requests):
    parser = WebsiteParser("https://example.com", max_depth=3)
    graph = parser.parse()
    
    assert len(graph.nodes) == 3
    assert len(graph.edges) == 4

def test_parser_external_links(mock_requests):
    parser = WebsiteParser("https://example.com", max_depth=1)
    graph = parser.parse()
    
    for node in graph.nodes:
        assert node.startswith("https://example.com")