import json

response = {
  "status": "completed",
  "result": "<?xml version='1.0' encoding='utf-8'?>\n<graphml xmlns=\"http://graphml.graphdrawing.org/xmlns\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xsi:schemaLocation=\"http://graphml.graphdrawing.org/xmlns http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd\"><graph edgedefault=\"directed\"><node id=\"http://example.com\"/>\n</graph></graphml>"
}

with open('website_graph.graphml', 'w', encoding='utf-8') as f:
    f.write(response['result'])