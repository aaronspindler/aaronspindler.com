#!/usr/bin/env python3
"""
Example script demonstrating how to use the knowledge graph system programmatically.
This script shows various ways to interact with the knowledge graph.
"""

import os
import sys
import django

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from pages.knowledge_graph import KnowledgeGraphBuilder, BlogPostParser
from pages.models import BlogPost, BlogPostLink


def demonstrate_parser():
    """Demonstrate the BlogPostParser functionality"""
    print("=== Blog Post Parser Demo ===")
    
    parser = BlogPostParser()
    
    # Get all blog posts
    posts = parser.get_all_blog_posts()
    print(f"Found {len(posts)} blog posts: {posts}")
    
    # Parse a specific post
    if posts:
        post_data = parser.parse_blog_post(posts[0])
        if post_data:
            print(f"\nParsed post: {post_data['title']}")
            print(f"Entry number: {post_data['entry_number']}")
            print(f"Internal links: {len(post_data['internal_links'])}")
            
            for link in post_data['internal_links']:
                print(f"  → {link['target_template']}: {link['link_text']}")


def demonstrate_builder():
    """Demonstrate the KnowledgeGraphBuilder functionality"""
    print("\n=== Knowledge Graph Builder Demo ===")
    
    builder = KnowledgeGraphBuilder()
    
    # Get current graph statistics
    graph_data = builder.get_graph_data()
    print(f"Current graph: {graph_data['total_posts']} posts, {graph_data['total_links']} links")
    
    # Show all posts
    print("\nBlog Posts:")
    for post in BlogPost.objects.all():
        incoming = post.incoming_links.count()
        outgoing = post.outgoing_links.count()
        print(f"  {post.entry_number}: {post.title} (in: {incoming}, out: {outgoing})")
    
    # Show all links
    print("\nLinks:")
    for link in BlogPostLink.objects.select_related('source_post', 'target_post'):
        print(f"  {link.source_post.title} → {link.target_post.title}: {link.link_text}")


def demonstrate_analysis():
    """Demonstrate some analysis of the knowledge graph"""
    print("\n=== Knowledge Graph Analysis ===")
    
    posts = BlogPost.objects.all()
    
    # Find most connected posts
    print("Most connected posts:")
    connected_posts = []
    for post in posts:
        total_connections = post.incoming_links.count() + post.outgoing_links.count()
        connected_posts.append((post, total_connections))
    
    connected_posts.sort(key=lambda x: x[1], reverse=True)
    for post, connections in connected_posts:
        print(f"  {post.title}: {connections} connections")
    
    # Find isolated posts (no connections)
    isolated_posts = [post for post, connections in connected_posts if connections == 0]
    if isolated_posts:
        print(f"\nIsolated posts ({len(isolated_posts)}):")
        for post in isolated_posts:
            print(f"  {post.title}")
    
    # Find hub posts (many outgoing connections)
    hub_posts = [post for post in posts if post.outgoing_links.count() > 2]
    if hub_posts:
        print(f"\nHub posts (many outgoing links):")
        for post in hub_posts:
            outgoing_count = post.outgoing_links.count()
            print(f"  {post.title}: {outgoing_count} outgoing links")


def demonstrate_rebuild():
    """Demonstrate rebuilding the knowledge graph"""
    print("\n=== Rebuilding Knowledge Graph ===")
    
    builder = KnowledgeGraphBuilder()
    
    print("Rebuilding graph...")
    builder.rebuild_graph()
    
    # Get updated statistics
    graph_data = builder.get_graph_data()
    print(f"Updated graph: {graph_data['total_posts']} posts, {graph_data['total_links']} links")


def main():
    """Main demonstration function"""
    print("Knowledge Graph System Demo")
    print("=" * 50)
    
    try:
        demonstrate_parser()
        demonstrate_builder()
        demonstrate_analysis()
        
        # Uncomment the next line to actually rebuild the graph
        # demonstrate_rebuild()
        
    except Exception as e:
        print(f"Error during demonstration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
