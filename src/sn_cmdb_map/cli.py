#!/usr/bin/env python3
"""
ServiceNow CMDB Mapping Tool

Main entry point for the ServiceNow CMDB table relationship mapping tool.
"""

from .graph_builder import CMDBGraphBuilder
import sys
import argparse


def main():
    """Main function for the CMDB mapping tool."""
    parser = argparse.ArgumentParser(
        description="Create paths between ServiceNow CMDB tables"
    )
    parser.add_argument(
        "--generate-single-table-graph",
        type=str,
        required=True,
        help="Source table name (e.g., cmdb_ci_zone)"
    )
    parser.add_argument(
        "--target-table",
        type=str,
        required=True,
        help="Target table name (e.g., cmdb_ci_server)"
    )
    parser.add_argument(
        "--shortest-path",
        action="store_true",
        help="Show only the shortest path (default: show all paths)"
    )
    
    args = parser.parse_args()
    
    # Initialize the graph builder
    builder = CMDBGraphBuilder()
    
    # Build the graph silently
    graph = builder.build_graph()
    
    if not graph:
        print("Error: Failed to build graph")
        sys.exit(1)
    
    # Generate path graph
    table_name = args.generate_single_table_graph
    target_table = args.target_table
    
    success = builder.visualize_table_graph(
        table_name, 
        output_dir="path_graphs", 
        target_table=target_table, 
        shortest_path_only=args.shortest_path
    )
    
    if success:
        print(f"\nGraph saved to: {builder.output_base_dir}/path_graphs/")
    else:
        print(f"No paths found between '{table_name}' and '{target_table}'")
        sys.exit(1)


if __name__ == "__main__":
    main()