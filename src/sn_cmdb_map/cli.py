#!/usr/bin/env python3
"""
ServiceNow CMDB Mapping Tool

Main entry point for the ServiceNow CMDB table relationship mapping tool.
"""

from .graph_builder import CMDBGraphBuilder
import sys
import argparse
import os
from pathlib import Path
from dotenv import load_dotenv


def main():
    """Main function for the CMDB mapping tool."""
    # Load environment variables from .env file if it exists
    load_dotenv()
    
    parser = argparse.ArgumentParser(
        description="Create paths between ServiceNow CMDB tables"
    )
    parser.add_argument(
        "source_table",
        type=str,
        help="Source table name (e.g., cmdb_ci_zone)"
    )
    parser.add_argument(
        "target_table",
        type=str,
        help="Target table name (e.g., cmdb_ci_server)"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        help="Directory containing JSON data files (default: current directory, or CMDB_DATA_DIR env var)"
    )
    parser.add_argument(
        "--layout",
        type=str,
        choices=["auto", "spring", "kamada_kawai", "planar", "circular", "random", "shell", "spectral", "spiral", "multipartite", "all"],
        default="auto",
        help="Graph layout algorithm to use (default: auto - tries layouts in optimal order)"
    )
    parser.add_argument(
        "--shortest-path",
        action="store_true",
        help="Show only the shortest path (default: show all paths)"
    )
    
    args = parser.parse_args()
    
    # Determine data directory from multiple sources (priority order):
    # 1. Command line argument
    # 2. Environment variable 
    # 3. Current directory
    data_dir = None
    if args.data_dir:
        data_dir = args.data_dir
    elif os.getenv('CMDB_DATA_DIR'):
        data_dir = os.getenv('CMDB_DATA_DIR')
    
    # Validate data directory if specified
    if data_dir:
        data_path = Path(data_dir)
        if not data_path.exists():
            print(f"Error: Data directory '{data_dir}' does not exist")
            sys.exit(1)
        if not data_path.is_dir():
            print(f"Error: '{data_dir}' is not a directory")
            sys.exit(1)
    
    # Initialize the graph builder
    builder = CMDBGraphBuilder(data_dir=data_dir)
    
    # Build the graph silently
    graph = builder.build_graph()
    
    if not graph:
        print("Error: Failed to build graph")
        sys.exit(1)
    
    # Generate path graph
    table_name = args.source_table
    target_table = args.target_table
    
    # Handle 'all' layout option
    if args.layout == "all":
        # Generate graphs for all available layouts
        layouts = ["spring", "kamada_kawai", "planar", "circular", "random", "shell", "spectral", "spiral", "multipartite"]
        success_count = 0
        total_layouts = len(layouts)
        
        for layout in layouts:
            print(f"Generating graph with {layout} layout...")
            success = builder.visualize_table_graph(
                table_name, 
                output_dir="path_graphs", 
                target_table=target_table, 
                shortest_path_only=args.shortest_path,
                layout=layout
            )
            if success:
                success_count += 1
        
        if success_count > 0:
            print(f"\nGraphs saved to: {builder.output_base_dir}/path_graphs/")
            print(f"Successfully generated {success_count}/{total_layouts} layouts")
            success = True
        else:
            print(f"Failed to generate graphs for any layout")
            success = False
    else:
        # Generate graph with single layout
        success = builder.visualize_table_graph(
            table_name, 
            output_dir="path_graphs", 
            target_table=target_table, 
            shortest_path_only=args.shortest_path,
            layout=args.layout
        )
    
    if success:
        if args.layout != "all":
            print(f"\nGraph saved to: {builder.output_base_dir}/path_graphs/")
    else:
        print(f"No paths found between '{table_name}' and '{target_table}'")
        sys.exit(1)


if __name__ == "__main__":
    main()