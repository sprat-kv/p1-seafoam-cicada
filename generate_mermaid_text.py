#!/usr/bin/env python
"""Generate Mermaid text diagram for the graph."""

import os
from dotenv import load_dotenv

load_dotenv()

from app.graph.workflow import create_graph

def generate_mermaid():
    """Generate Mermaid text diagram."""
    builder = create_graph()
    graph = builder.compile()
    graph_structure = graph.get_graph()
    
    mermaid_text = graph_structure.draw_mermaid()
    output_path = os.path.join(os.path.dirname(__file__), "graph_visualization.mmd")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(mermaid_text)
    
    print(f"Mermaid diagram saved to: {output_path}")
    print("\nYou can view it at: https://mermaid.live/")
    print("\nFirst few lines:")
    print("-" * 70)
    print("\n".join(mermaid_text.split("\n")[:20]))
    
    return output_path

if __name__ == "__main__":
    generate_mermaid()
