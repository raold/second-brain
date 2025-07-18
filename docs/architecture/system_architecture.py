#!/usr/bin/env python3
"""
Generate system architecture diagram for Second Brain PostgreSQL Edition
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Circle, Rectangle
import numpy as np

def create_architecture_diagram():
    """Create the system architecture diagram."""
    fig, ax = plt.subplots(1, 1, figsize=(14, 10))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis('off')
    
    # Color scheme
    colors = {
        'postgres': '#336791',
        'fastapi': '#009485',
        'dashboard': '#FF6B6B',
        'client': '#4ECDC4',
        'vector': '#45B7D1',
        'background': '#F8F9FA',
        'text': '#2C3E50'
    }
    
    # Background
    bg = Rectangle((0, 0), 14, 10, facecolor=colors['background'], alpha=0.3)
    ax.add_patch(bg)
    
    # Title
    ax.text(7, 9.5, 'Second Brain - PostgreSQL + pgvector Architecture', 
            fontsize=20, fontweight='bold', ha='center', color=colors['text'])
    ax.text(7, 9.1, 'v2.4.2 - Architecture Cleanup', 
            fontsize=14, ha='center', color=colors['text'], alpha=0.7)
    
    # PostgreSQL Core (Center)
    postgres_box = FancyBboxPatch((5.5, 4), 3, 2.5, 
                                 boxstyle="round,pad=0.1", 
                                 facecolor=colors['postgres'], 
                                 edgecolor='white', linewidth=2)
    ax.add_patch(postgres_box)
    ax.text(7, 5.8, 'PostgreSQL', fontsize=14, fontweight='bold', 
            ha='center', va='center', color='white')
    ax.text(7, 5.4, '+ pgvector', fontsize=12, 
            ha='center', va='center', color='white')
    ax.text(7, 5.0, '+ JSONB', fontsize=12, 
            ha='center', va='center', color='white')
    ax.text(7, 4.6, '+ Full-text Search', fontsize=12, 
            ha='center', va='center', color='white')
    ax.text(7, 4.2, 'Core Data Storage', fontsize=10, 
            ha='center', va='center', color='white', style='italic')
    
    # FastAPI Server (Top)
    fastapi_box = FancyBboxPatch((5.5, 7), 3, 1.5, 
                                boxstyle="round,pad=0.1", 
                                facecolor=colors['fastapi'], 
                                edgecolor='white', linewidth=2)
    ax.add_patch(fastapi_box)
    ax.text(7, 8, 'FastAPI Server', fontsize=14, fontweight='bold', 
            ha='center', va='center', color='white')
    ax.text(7, 7.6, 'Async + Auth Tokens', fontsize=11, 
            ha='center', va='center', color='white')
    ax.text(7, 7.2, 'REST API', fontsize=11, 
            ha='center', va='center', color='white')
    
    # Dashboard WebUI (Left)
    dashboard_box = FancyBboxPatch((1, 4), 3, 2.5, 
                                  boxstyle="round,pad=0.1", 
                                  facecolor=colors['dashboard'], 
                                  edgecolor='white', linewidth=2)
    ax.add_patch(dashboard_box)
    ax.text(2.5, 5.8, 'Dashboard WebUI', fontsize=14, fontweight='bold', 
            ha='center', va='center', color='white')
    ax.text(2.5, 5.4, 'D3.js Visualization', fontsize=11, 
            ha='center', va='center', color='white')
    ax.text(2.5, 5.0, 'Memory Network', fontsize=11, 
            ha='center', va='center', color='white')
    ax.text(2.5, 4.6, 'Search Interface', fontsize=11, 
            ha='center', va='center', color='white')
    ax.text(2.5, 4.2, 'Analytics View', fontsize=11, 
            ha='center', va='center', color='white')
    
    # API Clients (Right)
    client_box = FancyBboxPatch((10, 4), 3, 2.5, 
                               boxstyle="round,pad=0.1", 
                               facecolor=colors['client'], 
                               edgecolor='white', linewidth=2)
    ax.add_patch(client_box)
    ax.text(11.5, 5.8, 'API Clients', fontsize=14, fontweight='bold', 
            ha='center', va='center', color='white')
    ax.text(11.5, 5.4, 'REST Clients', fontsize=11, 
            ha='center', va='center', color='white')
    ax.text(11.5, 5.0, 'Python SDK', fontsize=11, 
            ha='center', va='center', color='white')
    ax.text(11.5, 4.6, 'cURL/HTTPie', fontsize=11, 
            ha='center', va='center', color='white')
    ax.text(11.5, 4.2, 'Custom Apps', fontsize=11, 
            ha='center', va='center', color='white')
    
    # Vector Embeddings (Bottom)
    vector_box = FancyBboxPatch((5.5, 1.5), 3, 1.5, 
                               boxstyle="round,pad=0.1", 
                               facecolor=colors['vector'], 
                               edgecolor='white', linewidth=2)
    ax.add_patch(vector_box)
    ax.text(7, 2.5, 'OpenAI Embeddings', fontsize=14, fontweight='bold', 
            ha='center', va='center', color='white')
    ax.text(7, 2.1, 'text-embedding-3-small', fontsize=11, 
            ha='center', va='center', color='white')
    ax.text(7, 1.7, '1536 dimensions', fontsize=11, 
            ha='center', va='center', color='white')
    
    # Arrows and connections
    arrow_props = dict(arrowstyle='->', lw=2, color=colors['text'])
    
    # FastAPI to PostgreSQL
    ax.annotate('', xy=(7, 6.5), xytext=(7, 7), arrowprops=arrow_props)
    ax.text(7.5, 6.75, 'asyncpg', fontsize=9, color=colors['text'])
    
    # Dashboard to FastAPI
    ax.annotate('', xy=(5.5, 7.75), xytext=(4, 5.25), arrowprops=arrow_props)
    ax.text(4.5, 6.5, 'HTTP/REST', fontsize=9, color=colors['text'], rotation=45)
    
    # Clients to FastAPI
    ax.annotate('', xy=(8.5, 7.75), xytext=(10, 5.25), arrowprops=arrow_props)
    ax.text(9.5, 6.5, 'REST API', fontsize=9, color=colors['text'], rotation=-45)
    
    # PostgreSQL to Vector Embeddings
    ax.annotate('', xy=(7, 4), xytext=(7, 3), arrowprops=arrow_props)
    ax.text(7.5, 3.5, 'pgvector', fontsize=9, color=colors['text'])
    
    # Key Features boxes
    feature_boxes = [
        (0.5, 8.5, "✅ Simplified Architecture"),
        (0.5, 8.1, "⚡ High Performance"),
        (0.5, 7.7, "🔍 Vector + Text Search"),
        (0.5, 7.3, "🛡️ Token Authentication"),
        (0.5, 6.9, "📊 D3.js Visualizations"),
    ]
    
    for x, y, text in feature_boxes:
        ax.text(x, y, text, fontsize=10, color=colors['text'], 
                bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))
    
    # Tech Stack
    tech_stack = [
        (13.5, 8.5, "Tech Stack:"),
        (13.5, 8.1, "• PostgreSQL 16"),
        (13.5, 7.7, "• pgvector"),
        (13.5, 7.3, "• FastAPI"),
        (13.5, 6.9, "• D3.js"),
        (13.5, 6.5, "• OpenAI API"),
    ]
    
    for x, y, text in tech_stack:
        weight = 'bold' if 'Tech Stack' in text else 'normal'
        ax.text(x, y, text, fontsize=10, color=colors['text'], 
                ha='right', fontweight=weight)
    
    # Data Flow indicators
    ax.text(2.5, 3.2, '🔄 Real-time Updates', fontsize=10, 
            ha='center', color=colors['text'],
            bbox=dict(boxstyle="round,pad=0.3", facecolor='lightblue', alpha=0.7))
    
    ax.text(11.5, 3.2, '📡 API Responses', fontsize=10, 
            ha='center', color=colors['text'],
            bbox=dict(boxstyle="round,pad=0.3", facecolor='lightgreen', alpha=0.7))
    
    # Footer
    ax.text(7, 0.5, 'All components dockerized • Production ready • Horizontally scalable', 
            fontsize=12, ha='center', color=colors['text'], style='italic')
    
    plt.tight_layout()
    return fig

def main():
    """Generate and save the architecture diagram."""
    fig = create_architecture_diagram()
    
    # Save in multiple formats
    fig.savefig('docs/system_architecture.png', dpi=300, bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    fig.savefig('docs/system_architecture.pdf', bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    
    print("✅ System architecture diagram generated:")
    print("   📄 docs/system_architecture.png")
    print("   📄 docs/system_architecture.pdf")
    
    # Show the plot
    plt.show()

if __name__ == '__main__':
    main() 