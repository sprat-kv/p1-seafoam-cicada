#!/usr/bin/env python
"""
Visualize the LangGraph workflow using draw_mermaid_png().
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app.graph.workflow import create_graph

def visualize_graph():
    """Generate PNG visualization of the graph."""
    print("Creating graph builder...")
    builder = create_graph()
    
    print("Compiling graph...")
    graph = builder.compile()
    
    print("Getting graph structure...")
    graph_structure = graph.get_graph()
    
    output_dir = os.path.dirname(__file__)
    
    # Method 1: Try PNG generation (returns bytes)
    print("\nMethod 1: Generating Mermaid PNG...")
    try:
        png_bytes = graph_structure.draw_mermaid_png()
        output_path = os.path.join(output_dir, "graph_visualization.png")
        with open(output_path, "wb") as f:
            f.write(png_bytes)
        print(f"SUCCESS: Graph visualization saved to: {output_path}")
        return output_path
    except Exception as e:
        print(f"PNG generation failed: {e}")
    
    # Method 2: Try Mermaid text
    print("\nMethod 2: Generating Mermaid text...")
    try:
        mermaid_text = graph_structure.draw_mermaid()
        mermaid_path = os.path.join(output_dir, "graph_visualization.mmd")
        with open(mermaid_path, "w", encoding="utf-8") as f:
            f.write(mermaid_text)
        print(f"SUCCESS: Mermaid diagram saved to: {mermaid_path}")
        print("\nYou can view it at: https://mermaid.live/")
        print("Or copy the content and paste it into any Mermaid viewer.")
        return mermaid_path
    except Exception as e:
        print(f"Mermaid text generation failed: {e}")
    
    # Method 3: Try ASCII (requires grandalf)
    print("\nMethod 3: Generating ASCII diagram...")
    try:
        ascii_diagram = graph_structure.draw_ascii()
        ascii_path = os.path.join(output_dir, "graph_visualization.txt")
        with open(ascii_path, "w", encoding="utf-8") as f:
            f.write(ascii_diagram)
        print(f"SUCCESS: ASCII diagram saved to: {ascii_path}")
        print("\n" + "=" * 70)
        print("ASCII Graph Visualization:")
        print("=" * 70)
        print(ascii_diagram)
        return ascii_path
    except Exception as e:
        print(f"ASCII generation failed: {e}")
        print("\nTo enable ASCII visualization, install: pip install grandalf")
    
    print("\nAll visualization methods failed. Please check the errors above.")
    return None

if __name__ == "__main__":
    result = visualize_graph()
    if result:
        print(f"\nVisualization saved successfully: {result}")
        sys.exit(0)
    else:
        print("\nFailed to generate visualization.")
        sys.exit(1)
