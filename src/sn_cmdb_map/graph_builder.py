#!/usr/bin/env python3
"""
ServiceNow CMDB Table Relationship Graph

This script creates a directed graph of ServiceNow CMDB tables using NetworkX.
Nodes represent CMDB tables and edges represent relationships between them.
"""

import json
import networkx as nx
from pathlib import Path
from typing import Dict, List, Set, Tuple
import sys
from collections import defaultdict
import math
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os
import random
from datetime import datetime
try:
    from networkx_viewer import Viewer
    NETWORKX_VIEWER_AVAILABLE = True
    NETWORKX_VIEWER_ERROR = None
except ImportError as e:
    NETWORKX_VIEWER_AVAILABLE = False
    NETWORKX_VIEWER_ERROR = str(e)

class CMDBGraphBuilder:
    def __init__(self, base_path: str = "."):
        """Initialize the CMDB graph builder."""
        self.base_path = Path(base_path)
        self.graph = nx.DiGraph()
        self.tables = {}  # Store table information
        self.relationship_types = {}  # Store relationship type information
        self.packages = {}  # Store package information
        self.sys_id_to_table = {}  # Mapping from sys_id to table name
        
        # Create timestamped output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_base_dir = self.base_path / f"cmdb_analysis_{timestamp}"
        self.output_base_dir.mkdir(exist_ok=True)
        
    def load_tables(self) -> None:
        """Load table information from sys_db_object.json."""
        tables_file = self.base_path / "sys_db_object.json"
        if not tables_file.exists():
            print(f"Warning: {tables_file} not found. Continuing without table metadata.")
            return
            
        try:
            with open(tables_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # First pass: create sys_id to table name mapping
            self.sys_id_to_table = {}
            if 'records' in data:
                for record in data['records']:
                    table_name = record.get('name', '')
                    sys_id = record.get('sys_id', '')
                    if table_name and sys_id:
                        self.sys_id_to_table[sys_id] = table_name
                
                # Second pass: build table info with resolved super_class names
                for record in data['records']:
                    table_name = record.get('name', '')
                    if table_name:
                        super_class_id = record.get('super_class', '')
                        super_class_name = self.sys_id_to_table.get(super_class_id, '') if super_class_id else ''
                        
                        self.tables[table_name] = {
                            'label': record.get('label', table_name),
                            'super_class': super_class_name,
                            'super_class_id': super_class_id,
                            'scope': record.get('sys_scope', 'global'),
                            'package': record.get('sys_package', ''),
                            'is_extendable': record.get('is_extendable', 'false') == 'true'
                        }
                        
            
        except Exception as e:
            print(f"Error loading tables: {e}")
    
    def load_relationship_types(self) -> None:
        """Load relationship type definitions from cmdb_rel_type.json."""
        rel_types_file = self.base_path / "cmdb_rel_type.json"
        if not rel_types_file.exists():
            print(f"Warning: {rel_types_file} not found. Continuing without relationship type metadata.")
            return
            
        try:
            with open(rel_types_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            if 'records' in data:
                for record in data['records']:
                    rel_id = record.get('sys_id', '')
                    if rel_id:
                        self.relationship_types[rel_id] = {
                            'name': record.get('name', ''),
                            'parent_descriptor': record.get('parent_descriptor', ''),
                            'child_descriptor': record.get('child_descriptor', ''),
                            'sys_name': record.get('sys_name', ''),
                            'scope': record.get('sys_scope', 'global')
                        }
                        
            
        except Exception as e:
            print(f"Error loading relationship types: {e}")
    
    def load_packages(self) -> None:
        """Load package information from sys_package.json."""
        packages_file = self.base_path / "sys_package.json"
        if not packages_file.exists():
            print(f"Warning: {packages_file} not found. Continuing without package metadata.")
            return
            
        try:
            with open(packages_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            if 'records' in data:
                for record in data['records']:
                    source = record.get('source', '')
                    sys_id = record.get('sys_id', '')
                    package_info = {
                        'name': record.get('name', source),
                        'version': record.get('version', ''),
                        'license_category': record.get('license_category', 'none'),
                        'sys_class_name': record.get('sys_class_name', ''),
                        'active': record.get('active', 'true') == 'true',
                        'source': source
                    }
                    
                    # Index by both source and sys_id for flexibility
                    if source:
                        self.packages[source] = package_info
                    if sys_id:
                        self.packages[sys_id] = package_info
                        
            
        except Exception as e:
            print(f"Error loading packages: {e}")
    
    def add_suggested_relationships(self, file_name: str) -> int:
        """Add relationships from a suggested relationships file."""
        rel_file = self.base_path / file_name
        if not rel_file.exists():
            print(f"Warning: {rel_file} not found.")
            return 0
            
        relationships_added = 0
        
        try:
            with open(rel_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            if 'records' in data:
                for record in data['records']:
                    base_class = record.get('base_class', '')
                    dependent_class = record.get('dependent_class', '')
                    rel_type_id = record.get('cmdb_rel_type', '')
                    is_parent = record.get('parent', 'false').lower() == 'true'
                    
                    if base_class and dependent_class and rel_type_id:
                        # Get relationship type info
                        rel_info = self.relationship_types.get(rel_type_id, {})
                        rel_name = rel_info.get('name', f'rel_{rel_type_id[:8]}')
                        
                        # Determine direction based on parent/child designation
                        if is_parent:
                            # base_class is parent, dependent_class is child
                            source = base_class
                            target = dependent_class
                            edge_label = rel_info.get('parent_descriptor', rel_name.split('::')[0] if '::' in rel_name else rel_name)
                        else:
                            # base_class is child, dependent_class is parent
                            source = dependent_class
                            target = base_class
                            edge_label = rel_info.get('child_descriptor', rel_name.split('::')[1] if '::' in rel_name else rel_name)
                        
                        # Add nodes if they don't exist
                        if source not in self.graph:
                            self.graph.add_node(source, **self._get_node_attributes(source))
                        if target not in self.graph:
                            self.graph.add_node(target, **self._get_node_attributes(target))
                        
                        # Add edge with relationship information
                        edge_attrs = {
                            'relationship_type': rel_name,
                            'relationship_id': rel_type_id,
                            'label': edge_label,
                            'source_file': file_name,
                            'scope': rel_info.get('scope', 'global')
                        }
                        
                        self.graph.add_edge(source, target, **edge_attrs)
                        relationships_added += 1
                        
            return relationships_added
            
        except Exception as e:
            print(f"Error loading relationships from {file_name}: {e}")
            return 0
    
    def _get_node_attributes(self, table_name: str) -> Dict:
        """Get node attributes for a table."""
        table_info = self.tables.get(table_name, {})
        return {
            'label': table_info.get('label', table_name),
            'super_class': table_info.get('super_class', ''),
            'scope': table_info.get('scope', 'unknown'),
            'package': table_info.get('package', ''),
            'is_extendable': table_info.get('is_extendable', False),
            'type': 'cmdb_table'
        }
    
    def get_table_display_label(self, table_name: str, max_length: int = 25) -> str:
        """Get the human-readable display label for a table."""
        table_info = self.tables.get(table_name, {})
        label = table_info.get('label', table_name)
        
        # If no label is available, use the table name
        if not label or label == table_name:
            # Make table name more readable by replacing underscores
            display_name = table_name.replace('_', ' ').title()
        else:
            display_name = label
        
        # Truncate if too long
        if len(display_name) > max_length:
            display_name = display_name[:max_length-3] + "..."
        
        return display_name
    
    def get_table_inheritance_chain(self, table_name: str) -> List[str]:
        """Get the inheritance chain for a table following super_class hierarchy."""
        chain = [table_name]
        current_table = table_name
        visited = set()  # Prevent infinite loops
        
        while current_table and current_table not in visited:
            visited.add(current_table)
            table_info = self.tables.get(current_table, {})
            super_class = table_info.get('super_class', '')
            
            if super_class and super_class != current_table:
                chain.append(super_class)
                current_table = super_class
            else:
                break
        
        return chain
    
    def find_inherited_relationships(self, target_table: str) -> Set[str]:
        """Find all tables that have relationships applicable to target_table via inheritance."""
        inheritance_chain = self.get_table_inheritance_chain(target_table)
        applicable_tables = set()
        
        # For each table in the inheritance chain, find tables that have relationships to them
        for ancestor_table in inheritance_chain:
            if ancestor_table in self.graph:
                applicable_tables.add(ancestor_table)
        
        return applicable_tables

    def get_package_display_name(self, package_source: str, max_length: int = 30) -> str:
        """Get the human-readable display name for a package."""
        if not package_source:
            return "Unknown Package"
            
        package_info = self.packages.get(package_source, {})
        if not package_info:
            return "Unknown Package"
        name = package_info.get('name', package_source)
        
        # Clean up common prefixes and make more readable
        if name.startswith('@servicenow/'):
            name = name.replace('@servicenow/', 'SN: ')
        elif name.startswith('@devsnc/'):
            name = name.replace('@devsnc/', 'DevSNC: ')
        elif name.startswith('com.'):
            # Convert com.glide.service-portal -> Service Portal
            parts = name.split('.')
            if len(parts) > 2:
                name = ' '.join(word.title() for word in parts[2:])
                name = name.replace('-', ' ').replace('_', ' ')
        elif package_source.startswith('sn_'):
            # Use the friendly name if available, otherwise clean up the source
            if not name or name == package_source:
                name = package_source.replace('sn_', 'SN ').replace('_', ' ').title()
        
        # Truncate if too long
        if len(name) > max_length:
            name = name[:max_length-3] + "..."
        
        return name
    
    def add_class_hierarchy_edges(self) -> int:
        """Add class hierarchy edges based on super_class relationships."""
        hierarchy_edges_added = 0
        
        for table_name, table_info in self.tables.items():
            super_class = table_info.get('super_class', '')
            
            if super_class and super_class != table_name:
                # Add nodes if they don't exist
                if table_name not in self.graph:
                    self.graph.add_node(table_name, **self._get_node_attributes(table_name))
                if super_class not in self.graph:
                    self.graph.add_node(super_class, **self._get_node_attributes(super_class))
                
                # Add hierarchy edge with special attributes
                edge_attrs = {
                    'relationship_type': 'class_hierarchy',
                    'label': 'parent of',
                    'source_file': 'sys_db_object.json',
                    'scope': 'hierarchy',
                    'edge_type': 'hierarchy',  # Mark as hierarchy edge
                    'style': 'dotted'  # Visual hint for dotted lines
                }
                
                # Parent -> Child relationship (superclass is parent of subclass)
                self.graph.add_edge(super_class, table_name, **edge_attrs)
                hierarchy_edges_added += 1
        
        return hierarchy_edges_added

    def build_graph(self) -> nx.DiGraph:
        """Build the complete CMDB relationship graph."""
        # Load metadata silently
        self.load_tables()
        self.load_relationship_types()
        self.load_packages()
        
        # Add relationships from both suggested relationship files
        self.add_suggested_relationships("cmdb_rel_type_suggest.json")
        self.add_suggested_relationships("em_suggested_relation_type.json")
        
        # Add class hierarchy edges
        self.add_class_hierarchy_edges()
        
        return self.graph
    
    def get_graph_statistics(self) -> Dict:
        """Get detailed statistics about the graph."""
        if not self.graph:
            return {}
            
        stats = {
            'nodes': self.graph.number_of_nodes(),
            'edges': self.graph.number_of_edges(),
            'is_directed': self.graph.is_directed(),
            'is_connected': nx.is_weakly_connected(self.graph) if self.graph.is_directed() else nx.is_connected(self.graph),
            'number_of_components': nx.number_weakly_connected_components(self.graph) if self.graph.is_directed() else nx.number_connected_components(self.graph),
            'density': nx.density(self.graph),
            'average_degree': sum(dict(self.graph.degree()).values()) / self.graph.number_of_nodes() if self.graph.number_of_nodes() > 0 else 0
        }
        
        # Top nodes by degree
        if self.graph.number_of_nodes() > 0:
            degree_centrality = nx.degree_centrality(self.graph)
            stats['top_central_nodes'] = sorted(degree_centrality.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return stats
    
    def export_graph(self, format_type: str = "gexf", output_file: str = None) -> str:
        """Export the graph to various formats."""
        if not output_file:
            output_file = f"cmdb_graph.{format_type}"
        
        output_path = self.base_path / output_file
        
        try:
            if format_type.lower() == "gexf":
                nx.write_gexf(self.graph, output_path)
            elif format_type.lower() == "gml":
                nx.write_gml(self.graph, output_path)
            elif format_type.lower() == "graphml":
                nx.write_graphml(self.graph, output_path)
            elif format_type.lower() == "json":
                # Export as JSON using node-link format
                graph_data = nx.node_link_data(self.graph)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(graph_data, f, indent=2, ensure_ascii=False)
            elif format_type.lower() == "png":
                # Export as PNG using matplotlib visualization
                success = self._export_png_graph(output_path)
                if not success:
                    raise ValueError("Failed to generate PNG visualization")
            else:
                raise ValueError(f"Unsupported format: {format_type}")
                
            print(f"Graph exported to {output_path}")
            return str(output_path)
            
        except Exception as e:
            print(f"Error exporting graph: {e}")
            return ""
    
    def _export_png_graph(self, output_path: str, max_nodes: int = 100) -> bool:
        """Export the graph as a PNG visualization."""
        import matplotlib
        matplotlib.use('Agg')  # Use non-interactive backend
        
        if not self.graph:
            print("Error: No graph available for PNG export.")
            return False
        
        # Use a subset if the graph is too large
        if self.graph.number_of_nodes() > max_nodes:
            print(f"Graph has {self.graph.number_of_nodes()} nodes. Using largest connected component for PNG export (max {max_nodes} nodes).")
            
            # Get the largest connected component
            if self.graph.is_directed():
                components = list(nx.weakly_connected_components(self.graph))
            else:
                components = list(nx.connected_components(self.graph))
            
            # Sort by size and take the largest component
            components.sort(key=len, reverse=True)
            largest_component = components[0]
            
            if len(largest_component) > max_nodes:
                # Take a subset of the largest component
                component_nodes = list(largest_component)[:max_nodes]
                subgraph = self.graph.subgraph(component_nodes)
                print(f"Using subset of {len(component_nodes)} nodes from largest component")
            else:
                subgraph = self.graph.subgraph(largest_component)
                print(f"Using largest component with {len(largest_component)} nodes")
        else:
            subgraph = self.graph
            print(f"Exporting complete graph with {self.graph.number_of_nodes()} nodes")
        
        try:
            print("Creating PNG graph visualization...")
            
            # Create figure
            plt.figure(figsize=(16, 12))
            plt.clf()
            
            # Create layout - try planar first, then other good options for this type of graph
            try:
                print("Attempting planar layout...")
                pos = nx.planar_layout(subgraph)
                layout_used = "planar"
                print("Using planar layout")
            except nx.NetworkXException:
                print("Planar layout failed (expected for CMDB graphs), trying Kamada-Kawai layout...")
                try:
                    pos = nx.kamada_kawai_layout(subgraph, scale=2)
                    layout_used = "kamada_kawai"
                    print("Using Kamada-Kawai layout")
                except:
                    print("Kamada-Kawai layout failed, trying spring layout...")
                    try:
                        pos = nx.spring_layout(subgraph, k=2, iterations=50, seed=42)
                        layout_used = "spring"
                        print("Using spring layout")
                    except:
                        print("Spring layout failed, using circular layout...")
                        pos = nx.circular_layout(subgraph)
                        layout_used = "circular"
                        print("Using circular layout")
            
            # Draw nodes with colors and sizes
            node_sizes = []
            node_colors = []
            package_groups = {}  # Track which packages are present for legend
            
            for node in subgraph.nodes():
                degree = subgraph.degree(node)
                node_sizes.append(max(150, min(800, degree * 80)))
                
                # Get table package information
                table_info = self.tables.get(node, {})
                package_source = table_info.get('package', '')
                scope = table_info.get('scope', 'unknown')
                
                # Determine color based on package/scope
                if scope == 'global':
                    node_colors.append('#4CAF50')  # Green for global
                    package_groups['Global Scope'] = '#4CAF50'
                elif package_source and package_source != 'global':
                    # Use different colors for different package types
                    if package_source.startswith('sn_'):
                        node_colors.append('#9C27B0')  # Purple for ServiceNow packages
                        package_groups['ServiceNow Packages'] = '#9C27B0'
                    elif package_source.startswith('com.'):
                        node_colors.append('#FF9800')  # Orange for com. packages
                        package_groups['Plugins/Extensions'] = '#FF9800'
                    else:
                        node_colors.append('#607D8B')  # Blue-grey for other packages
                        package_groups['Other Packages'] = '#607D8B'
                else:
                    node_colors.append('#2196F3')  # Blue for unknown/other
                    package_groups['Other/Unknown'] = '#2196F3'
            
            # Draw the graph
            nx.draw_networkx_nodes(subgraph, pos, 
                                  node_color=node_colors, 
                                  node_size=node_sizes,
                                  alpha=0.8)
            
            # Separate edges by type for different styling
            ci_edges = []
            hierarchy_edges = []
            
            for source, target, data in subgraph.edges(data=True):
                edge_type = data.get('edge_type', 'ci')
                if edge_type == 'hierarchy':
                    hierarchy_edges.append((source, target))
                else:
                    ci_edges.append((source, target))
            
            if subgraph.is_directed():
                # Draw CI relationship edges (solid lines)
                if ci_edges:
                    nx.draw_networkx_edges(subgraph, pos, 
                                          edgelist=ci_edges,
                                          edge_color='gray', 
                                          arrows=True, 
                                          arrowsize=20,
                                          alpha=0.6,
                                          width=1.5,
                                          style='solid')
                
                # Draw hierarchy edges (dotted lines)
                if hierarchy_edges:
                    nx.draw_networkx_edges(subgraph, pos, 
                                          edgelist=hierarchy_edges,
                                          edge_color='blue', 
                                          arrows=True, 
                                          arrowsize=15,
                                          alpha=0.5,
                                          width=1,
                                          style='dotted')
            else:
                # For undirected graphs (shouldn't happen, but handle gracefully)
                nx.draw_networkx_edges(subgraph, pos, 
                                      edge_color='gray', 
                                      alpha=0.6,
                                      width=1.5)
            
            # Add labels for important nodes using display labels
            degrees = dict(subgraph.degree())
            important_nodes = {}
            sorted_nodes = sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:20]
            for node, degree in sorted_nodes:
                display_label = self.get_table_display_label(node, max_length=15)
                important_nodes[node] = display_label
                
            nx.draw_networkx_labels(subgraph, pos, 
                                   labels=important_nodes,
                                   font_size=8,
                                   font_weight='bold')
            
            plt.title(f'ServiceNow CMDB Table Relationships\n({subgraph.number_of_nodes()} nodes, {subgraph.number_of_edges()} edges, {layout_used} layout)', 
                     fontsize=16, fontweight='bold', pad=20)
            plt.axis('off')
            
            # Add legend with dynamic package information
            legend_elements = []
            for package_label, color in sorted(package_groups.items()):
                legend_elements.append(patches.Patch(color=color, label=package_label))
            plt.legend(handles=legend_elements, loc='upper right', fontsize=10)
            
            plt.tight_layout()
            
            # Save the PNG
            plt.savefig(output_path, format='png', dpi=200, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            plt.close()
            
            print(f"PNG graph visualization saved to: {output_path}")
            
            return True
            
        except Exception as e:
            print(f"Error creating PNG visualization: {e}")
            plt.close()
            return False
    
    
    def print_sample_relationships(self, limit: int = 10) -> None:
        """Print a sample of relationships for inspection."""
        print(f"\nSample relationships (first {limit}):")
        print("-" * 80)
        
        count = 0
        for source, target, data in self.graph.edges(data=True):
            if count >= limit:
                break
                
            rel_type = data.get('relationship_type', 'unknown')
            label = data.get('label', 'no label')
            source_file = data.get('source_file', 'unknown')
            
            print(f"{source} --[{label}]--> {target}")
            print(f"  Relationship: {rel_type} (from {source_file})")
            print()
            
            count += 1
    
    def find_table_relationships(self, table_name: str) -> Dict:
        """Find all relationships for a specific table."""
        if table_name not in self.graph:
            return {'error': f"Table '{table_name}' not found in graph"}
        
        incoming = []
        outgoing = []
        
        # Incoming relationships (other tables pointing to this one)
        for source, target, data in self.graph.in_edges(table_name, data=True):
            incoming.append({
                'source': source,
                'relationship': data.get('label', 'unknown'),
                'type': data.get('relationship_type', 'unknown')
            })
        
        # Outgoing relationships (this table pointing to others)
        for source, target, data in self.graph.out_edges(table_name, data=True):
            outgoing.append({
                'target': target,
                'relationship': data.get('label', 'unknown'),
                'type': data.get('relationship_type', 'unknown')
            })
        
        return {
            'table': table_name,
            'incoming_relationships': incoming,
            'outgoing_relationships': outgoing,
            'total_incoming': len(incoming),
            'total_outgoing': len(outgoing)
        }
    
    def create_table_centered_graph(self, table_name: str, max_depth: int = 2) -> nx.DiGraph:
        """Create a graph centered on a specific table showing its relationships."""
        if table_name not in self.graph:
            return None
        
        # Create new graph centered on the table
        centered_graph = nx.DiGraph()
        
        # Add the central table
        centered_graph.add_node(table_name, **self.graph.nodes[table_name])
        
        # Get inheritance chain for the target table to find inherited relationships
        applicable_tables = self.find_inherited_relationships(table_name)
        
        # Add direct relationships (depth 1) including inherited ones
        for source, target, data in self.graph.edges(data=True):
            # Check if this edge involves the target table or any of its ancestors
            source_matches = source == table_name or source in applicable_tables
            target_matches = target == table_name or target in applicable_tables
            
            if source_matches or target_matches:
                # Add nodes if they don't exist
                if source not in centered_graph:
                    # If this is an inherited relationship, note the original target table
                    source_attrs = dict(self.graph.nodes[source])
                    if source in applicable_tables and source != table_name:
                        source_attrs['inherited_from'] = source
                        source_attrs['target_table'] = table_name
                    centered_graph.add_node(source, **source_attrs)
                    
                if target not in centered_graph:
                    # If this is an inherited relationship, note the original target table
                    target_attrs = dict(self.graph.nodes[target])
                    if target in applicable_tables and target != table_name:
                        target_attrs['inherited_from'] = target
                        target_attrs['target_table'] = table_name
                    centered_graph.add_node(target, **target_attrs)
                
                # Add edge with inheritance information
                edge_attrs = dict(data)
                if source in applicable_tables and source != table_name:
                    edge_attrs['inherited_from_source'] = source
                    edge_attrs['target_table'] = table_name
                if target in applicable_tables and target != table_name:
                    edge_attrs['inherited_from_target'] = target
                    edge_attrs['target_table'] = table_name
                    
                centered_graph.add_edge(source, target, **edge_attrs)
        
        # Add indirect relationships (depth 2) if requested
        if max_depth > 1:
            direct_neighbors = set(centered_graph.nodes()) - {table_name}
            for neighbor in list(direct_neighbors):
                for source, target, data in self.graph.edges(data=True):
                    # Only add edges that connect to our existing graph
                    # Either: neighbor -> new_node or new_node -> neighbor
                    if source == neighbor and target not in centered_graph:
                        # neighbor points to a new node
                        if centered_graph.number_of_nodes() < 20:
                            centered_graph.add_node(target, **self.graph.nodes[target])
                            centered_graph.add_edge(source, target, **data)
                    elif target == neighbor and source not in centered_graph:
                        # new node points to neighbor
                        if centered_graph.number_of_nodes() < 20:
                            centered_graph.add_node(source, **self.graph.nodes[source])
                            centered_graph.add_edge(source, target, **data)
        
        return centered_graph
    
    def find_all_paths_between_tables(self, source_table: str, target_table: str, max_paths: int = 10, max_path_length: int = 5) -> List[List[str]]:
        """Find all paths between two tables in the graph, including inheritance-based paths."""
        if source_table not in self.graph:
            return []
        
        all_paths = []
        
        try:
            # First, find direct paths to the target table
            if target_table in self.graph:
                try:
                    direct_paths = list(nx.all_simple_paths(self.graph, source_table, target_table, cutoff=max_path_length))
                    for path in direct_paths:
                        all_paths.append((path, None))  # (path, no_ancestor)
                except nx.NetworkXNoPath:
                    pass
            
            # Then find paths through inheritance hierarchy
            target_inheritance_chain = self.get_table_inheritance_chain(target_table)
            
            # For each ancestor in the inheritance chain, find paths to it
            for ancestor_table in target_inheritance_chain[1:]:  # Skip the target table itself (first in chain)
                if ancestor_table in self.graph:
                    try:
                        # Find paths to this ancestor
                        paths_to_ancestor = list(nx.all_simple_paths(self.graph, source_table, ancestor_table, cutoff=max_path_length))
                        
                        for path in paths_to_ancestor:
                            # Create inheritance path: source -> ... -> ancestor -> target
                            # We'll represent this as a path to target with inheritance metadata
                            inheritance_path = path + [target_table]
                            all_paths.append((inheritance_path, ancestor_table))
                                
                    except nx.NetworkXNoPath:
                        continue
            
            # Remove duplicates while preserving order and preferring shorter paths
            unique_paths = []
            seen_paths = set()
            
            for path_info in all_paths:
                path, ancestor = path_info
                path_tuple = tuple(path)
                
                # Skip if we've seen this exact path before
                if path_tuple in seen_paths:
                    continue
                    
                # For inheritance paths, check if we already have a better direct path
                if ancestor:
                    # Check if there's a direct path with the same or fewer nodes
                    direct_equivalent = tuple(path[:-1])  # Remove the inherited target
                    has_better_direct = any(
                        other_path_info[1] is None and 
                        tuple(other_path_info[0]) == direct_equivalent and
                        len(other_path_info[0]) <= len(path)
                        for other_path_info in all_paths
                    )
                    if has_better_direct:
                        continue
                
                seen_paths.add(path_tuple)
                unique_paths.append(path_info)
            
            # Sort by path length (preferring shorter paths) and limit number of paths
            unique_paths.sort(key=lambda x: (len(x[0]), x[1] is not None))  # Direct paths first, then by length
            if len(unique_paths) > max_paths:
                unique_paths = unique_paths[:max_paths]
            
            return unique_paths
            
        except Exception as e:
            print(f"Error finding paths: {e}")
            return []
    
    def create_path_graph_between_tables(self, source_table: str, target_table: str, max_paths: int = 10) -> nx.DiGraph:
        """Create a graph showing all paths between two tables."""
        if source_table not in self.graph:
            return None
        
        # Find all paths between the tables (including inheritance-based paths)
        path_infos = self.find_all_paths_between_tables(source_table, target_table, max_paths)
        
        if not path_infos:
            print(f"No paths found between '{source_table}' and '{target_table}'")
            return None
        
        # Create a new graph with all nodes and edges from the paths
        path_graph = nx.DiGraph()
        
        # Track which nodes are inheritance targets
        inheritance_targets = {}  # node -> ancestor_table
        
        # Add all nodes from all paths
        for path_info in path_infos:
            path, ancestor_table = path_info
            
            for node in path:
                if node not in path_graph:
                    if node == target_table and ancestor_table:
                        # This target node is reached through inheritance
                        node_attrs = dict(self.graph.nodes[node])
                        node_attrs['inherited_target'] = True
                        node_attrs['inherited_from'] = ancestor_table
                        path_graph.add_node(node, **node_attrs)
                        inheritance_targets[node] = ancestor_table
                    else:
                        # Regular node from the graph
                        path_graph.add_node(node, **self.graph.nodes[node])
        
        # Add all edges from all paths
        for path_info in path_infos:
            path, ancestor_table = path_info
            
            for i in range(len(path) - 1):
                source_node = path[i]
                target_node = path[i + 1]
                
                if self.graph.has_edge(source_node, target_node):
                    # Direct edge exists in the graph
                    edge_data = self.graph.edges[source_node, target_node]
                    path_graph.add_edge(source_node, target_node, **edge_data)
                else:
                    # This might be an inheritance-based edge
                    # Check if target_node is the final target and we have ancestor info
                    if target_node == target_table and ancestor_table:
                        if self.graph.has_edge(source_node, ancestor_table):
                            edge_data = dict(self.graph.edges[source_node, ancestor_table])
                            edge_data['inherited_edge'] = True
                            edge_data['inherited_from'] = ancestor_table
                            path_graph.add_edge(source_node, target_node, **edge_data)
        
        for i, path_info in enumerate(path_infos, 1):
            path, ancestor_table = path_info
            path_labels = [self.get_table_display_label(node, max_length=20) for node in path]
            print(f"Path {i}: {' → '.join(path_labels)}")
        
        return path_graph
    
    def visualize_table_graph(self, table_name: str, output_dir: str = "path_graphs", 
                             max_depth: int = 2, save_format: str = "png", target_table: str = None, shortest_path_only: bool = False) -> bool:
        """Create and save a visualization for a specific table's relationships."""
        
        # If target_table is specified, create a path graph between the two tables
        if target_table:
            max_paths = 1 if shortest_path_only else 10
            centered_graph = self.create_path_graph_between_tables(table_name, target_table, max_paths)
            graph_type = "shortest_path" if shortest_path_only else "path"
        else:
            # Create the table-centered graph
            centered_graph = self.create_table_centered_graph(table_name, max_depth)
            graph_type = "centered"
        
        if centered_graph is None or centered_graph.number_of_nodes() == 0:
            return False
        
        # Create output directory within timestamped directory
        output_path = self.output_base_dir / output_dir
        output_path.mkdir(exist_ok=True)
        
        # Set matplotlib backend
        import matplotlib
        matplotlib.use('Agg')
        
        try:
            
            # Create figure with size based on number of nodes
            fig_width = max(12, min(20, 10 + centered_graph.number_of_nodes() * 0.3))
            fig_height = max(8, min(16, 6 + centered_graph.number_of_nodes() * 0.2))
            plt.figure(figsize=(fig_width, fig_height))
            plt.clf()
            
            # Try planar layout first (more likely to work with smaller graphs)
            try:
                pos = nx.planar_layout(centered_graph, scale=2)
                layout_used = "planar"
            except nx.NetworkXException:
                try:
                    # Use larger scale for better spacing
                    scale_factor = max(2, centered_graph.number_of_nodes() * 0.2)
                    pos = nx.kamada_kawai_layout(centered_graph, scale=scale_factor)
                    layout_used = "kamada_kawai"
                except:
                    try:
                        # Increase k value for better node separation
                        k_value = max(2, centered_graph.number_of_nodes() * 0.15)
                        pos = nx.spring_layout(centered_graph, k=k_value, iterations=100, seed=42)
                        layout_used = "spring"
                    except:
                        pos = nx.circular_layout(centered_graph, scale=2)
                        layout_used = "circular"
            
            # Draw nodes with different colors for source/target tables vs others
            node_colors = []
            node_sizes = []
            package_groups = {}  # Track which packages are present for legend
            
            for node in centered_graph.nodes():
                if node == table_name:
                    node_colors.append('#FF5722')  # Red-orange for source table
                    node_sizes.append(800)
                elif target_table and node == target_table:
                    node_colors.append('#E91E63')  # Pink for target table
                    node_sizes.append(800)
                else:
                    # Get table package information
                    table_info = self.tables.get(node, {})
                    package_source = table_info.get('package', '')
                    scope = table_info.get('scope', 'unknown')
                    
                    # Determine color based on package/scope
                    if scope == 'global':
                        node_colors.append('#4CAF50')  # Green for global
                        package_groups['Global Scope'] = '#4CAF50'
                    elif package_source and package_source != 'global':
                        # Use different colors for different package types
                        if package_source.startswith('sn_'):
                            node_colors.append('#9C27B0')  # Purple for ServiceNow packages
                            package_name = self.get_package_display_name(package_source, max_length=20)
                            package_groups[f'SN Package ({package_name})'] = '#9C27B0'
                        elif package_source.startswith('com.'):
                            node_colors.append('#FF9800')  # Orange for com. packages
                            package_name = self.get_package_display_name(package_source, max_length=20)
                            package_groups[f'Plugin ({package_name})'] = '#FF9800'
                        else:
                            node_colors.append('#607D8B')  # Blue-grey for other packages
                            package_name = self.get_package_display_name(package_source, max_length=20)
                            package_groups[f'Package ({package_name})'] = '#607D8B'
                    else:
                        node_colors.append('#2196F3')  # Blue for unknown/other
                        package_groups['Other/Unknown'] = '#2196F3'
                    
                    degree = centered_graph.degree(node)
                    node_sizes.append(max(300, min(600, degree * 100)))
            
            # Draw nodes
            nx.draw_networkx_nodes(centered_graph, pos, 
                                  node_color=node_colors, 
                                  node_size=node_sizes,
                                  alpha=0.8)
            
            # Separate edges by type for different styling
            ci_edges = []
            hierarchy_edges = []
            
            for source, target, data in centered_graph.edges(data=True):
                edge_type = data.get('edge_type', 'ci')
                if edge_type == 'hierarchy':
                    hierarchy_edges.append((source, target))
                else:
                    ci_edges.append((source, target))
            
            # Draw CI relationship edges (solid lines)
            if ci_edges:
                nx.draw_networkx_edges(centered_graph, pos, 
                                      edgelist=ci_edges,
                                      edge_color='gray', 
                                      arrows=True, 
                                      arrowsize=20,
                                      alpha=0.7,
                                      width=2,
                                      style='solid')
            
            # Draw hierarchy edges (dotted lines)
            if hierarchy_edges:
                nx.draw_networkx_edges(centered_graph, pos, 
                                      edgelist=hierarchy_edges,
                                      edge_color='blue', 
                                      arrows=True, 
                                      arrowsize=15,
                                      alpha=0.6,
                                      width=1.5,
                                      style='dotted')
            
            # Calculate optimal spacing for labels based on graph density
            num_nodes = centered_graph.number_of_nodes()
            num_edges = centered_graph.number_of_edges()
            density = num_edges / (num_nodes * (num_nodes - 1)) if num_nodes > 1 else 0
            
            # Adjust font sizes based on graph density and node count
            node_font_size = max(6, min(12, 14 - num_nodes // 3))
            edge_font_size = max(5, min(8, 9 - num_nodes // 5))
            
            # Draw node labels using human-readable labels with better positioning
            node_labels = {}
            for node in centered_graph.nodes():
                node_attrs = centered_graph.nodes[node]
                
                # Check if this is an inherited relationship or inherited target
                if target_table is None and 'target_table' in node_attrs and 'inherited_from' in node_attrs:
                    # Show target table name with actual table in parentheses (for single table graphs)
                    target_table_name = node_attrs['target_table']
                    inherited_from = node_attrs['inherited_from']
                    target_display = self.get_table_display_label(target_table_name, max_length=15)
                    inherited_display = self.get_table_display_label(inherited_from, max_length=15)
                    display_label = f"{target_display} ({inherited_display})"
                elif 'inherited_target' in node_attrs and 'inherited_from' in node_attrs:
                    # Show target table name with inherited ancestor in parentheses (for path graphs)
                    inherited_from = node_attrs['inherited_from']
                    target_display = self.get_table_display_label(node, max_length=15)
                    inherited_display = self.get_table_display_label(inherited_from, max_length=15)
                    display_label = f"{target_display} ({inherited_display})"
                else:
                    # Use human-readable label from sys_db_object.json
                    display_label = self.get_table_display_label(node, max_length=20)
                    
                node_labels[node] = display_label
            
            # Draw node labels with background boxes for better readability
            nx.draw_networkx_labels(centered_graph, pos, 
                                   labels=node_labels,
                                   font_size=node_font_size,
                                   font_weight='bold',
                                   bbox=dict(boxstyle='round,pad=0.2', 
                                           facecolor='white', 
                                           edgecolor='gray',
                                           alpha=0.9))
            
            # Draw edge labels more selectively to reduce clutter
            edge_labels = {}
            
            # Only show edge labels for the most important edges or when graph is small
            show_edge_labels = num_nodes <= 15 or density < 0.3
            
            if show_edge_labels:
                for source, target, data in centered_graph.edges(data=True):
                    label = data.get('label', data.get('relationship_type', 'unknown'))
                    # Truncate long labels more aggressively
                    if len(label) > 12:
                        label = label[:10] + ".."
                    edge_labels[(source, target)] = label
                
                # Draw edge labels with background and reduced clutter
                if edge_labels:
                    nx.draw_networkx_edge_labels(centered_graph, pos, 
                                                edge_labels=edge_labels,
                                                font_size=edge_font_size,
                                                alpha=0.8,
                                                bbox=dict(boxstyle='round,pad=0.1', 
                                                        facecolor='lightyellow', 
                                                        edgecolor='none',
                                                        alpha=0.7))
            
            # Title and formatting using human-readable label
            table_display_label = self.get_table_display_label(table_name, max_length=50)
            if target_table:
                target_display_label = self.get_table_display_label(target_table, max_length=50)
                path_type = "Shortest Path" if shortest_path_only else "Paths"
                plt.title(f'CMDB {path_type}: {table_display_label} → {target_display_label}\n'
                         f'({centered_graph.number_of_nodes()} tables, {centered_graph.number_of_edges()} relationships, {layout_used} layout)', 
                         fontsize=14, fontweight='bold', pad=20)
            else:
                plt.title(f'CMDB Relationships for: {table_display_label}\n'
                         f'({centered_graph.number_of_nodes()} tables, {centered_graph.number_of_edges()} relationships, {layout_used} layout)', 
                         fontsize=14, fontweight='bold', pad=20)
            
            # Add legend using display label and dynamic package information
            central_table_label = self.get_table_display_label(table_name, max_length=30)
            if target_table:
                target_table_label = self.get_table_display_label(target_table, max_length=30)
                legend_elements = [
                    patches.Patch(color='#FF5722', label=f'Source ({central_table_label})'),
                    patches.Patch(color='#E91E63', label=f'Target ({target_table_label})')
                ]
            else:
                legend_elements = [
                    patches.Patch(color='#FF5722', label=f'Central Table ({central_table_label})')
                ]
            
            # Add edge type legend if we have both types
            if ci_edges and hierarchy_edges:
                from matplotlib.lines import Line2D
                legend_elements.extend([
                    Line2D([0], [0], color='gray', linewidth=2, label='CI Relationships'),
                    Line2D([0], [0], color='blue', linewidth=1.5, linestyle='dotted', label='Class Hierarchy')
                ])
            elif hierarchy_edges:
                from matplotlib.lines import Line2D
                legend_elements.append(
                    Line2D([0], [0], color='blue', linewidth=1.5, linestyle='dotted', label='Class Hierarchy')
                )
            elif ci_edges:
                from matplotlib.lines import Line2D
                legend_elements.append(
                    Line2D([0], [0], color='gray', linewidth=2, label='CI Relationships')
                )
            
            # Add package groups found in this graph
            for package_label, color in sorted(package_groups.items()):
                legend_elements.append(patches.Patch(color=color, label=package_label))
            
            # Position legend outside the plot area to avoid overlapping
            plt.legend(handles=legend_elements, loc='center left', bbox_to_anchor=(1.02, 0.5), fontsize=9)
            
            plt.axis('off')
            plt.tight_layout()
            
            # Save the image
            if target_table:
                if shortest_path_only:
                    output_file = output_path / f"{table_name}_to_{target_table}_shortest_path.{save_format}"
                else:
                    output_file = output_path / f"{table_name}_to_{target_table}_paths.{save_format}"
            else:
                output_file = output_path / f"{table_name}.{save_format}"
            plt.savefig(output_file, format=save_format, dpi=200, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            plt.close()
            
            return True
            
        except Exception as e:
            import traceback
            print(f"Error creating graph for {table_name}: {e}")
            print(f"Error details: {traceback.format_exc()}")
            plt.close()
            return False
    
    def generate_all_table_graphs(self, output_dir: str = "table_graphs", 
                                 max_tables: int = None, min_relationships: int = 1) -> int:
        """Generate individual graphs for all tables (or top N tables)."""
        if not self.graph:
            print("Error: No graph available. Please build the graph first.")
            return 0
        
        # Get tables with their relationship counts
        table_relationships = {}
        for node in self.graph.nodes():
            total_rels = self.graph.in_degree(node) + self.graph.out_degree(node)
            if total_rels >= min_relationships:
                table_relationships[node] = total_rels
        
        # Sort by relationship count
        sorted_tables = sorted(table_relationships.items(), key=lambda x: x[1], reverse=True)
        
        # Limit number of tables if specified
        if max_tables:
            sorted_tables = sorted_tables[:max_tables]
        
        print(f"Generating individual graphs for {len(sorted_tables)} tables...")
        print(f"Output directory: {self.base_path / output_dir}")
        
        successful = 0
        for i, (table_name, rel_count) in enumerate(sorted_tables, 1):
            display_label = self.get_table_display_label(table_name, max_length=40)
            print(f"\n{i:3d}/{len(sorted_tables)}: {display_label} ({rel_count} relationships)")
            if self.visualize_table_graph(table_name, output_dir):
                successful += 1
        
        print(f"\nCompleted: {successful}/{len(sorted_tables)} graphs generated successfully")
        return successful
    
    def view_graph_interactive(self, max_nodes: int = 100) -> bool:
        """Launch an interactive viewer for the graph using networkx-viewer."""
        if not NETWORKX_VIEWER_AVAILABLE:
            print("Error: networkx-viewer is not available.")
            if NETWORKX_VIEWER_ERROR:
                print(f"Import error: {NETWORKX_VIEWER_ERROR}")
            if "_tkinter" in str(NETWORKX_VIEWER_ERROR):
                print("\nThis appears to be a tkinter issue (interactive viewing not available).")
                print("Alternatives:")
                print("  1. Export to GEXF and use Gephi: python main.py --export-format gexf")
                print("  2. Export to PDF with graph visualization: python main.py --export-format pdf")
                print("  3. Create matplotlib image: Accept matplotlib fallback below")
            else:
                print("Please install networkx-viewer with: uv add networkx-viewer")
            
            # Offer matplotlib fallback
            print("\nAlternative: Would you like to view with matplotlib? (y/n)", end=" ")
            try:
                import sys
                response = input().lower().strip()
                if response in ['y', 'yes']:
                    return self.view_graph_matplotlib(max_nodes)
            except (EOFError, KeyboardInterrupt):
                pass
            return False
        
        if not self.graph:
            print("Error: No graph available. Please build the graph first.")
            return False
        
        # Use a subset if the graph is too large
        if self.graph.number_of_nodes() > max_nodes:
            print(f"Graph has {self.graph.number_of_nodes()} nodes. Using largest connected component for viewing (max {max_nodes} nodes).")
            
            # Get the largest connected component
            if self.graph.is_directed():
                components = list(nx.weakly_connected_components(self.graph))
            else:
                components = list(nx.connected_components(self.graph))
            
            # Sort by size and take the largest component
            components.sort(key=len, reverse=True)
            largest_component = components[0]
            
            if len(largest_component) > max_nodes:
                # Take a subset of the largest component
                component_nodes = list(largest_component)[:max_nodes]
                subgraph = self.graph.subgraph(component_nodes)
                print(f"Viewing subset of {len(component_nodes)} nodes from largest component")
            else:
                subgraph = self.graph.subgraph(largest_component)
                print(f"Viewing largest component with {len(largest_component)} nodes")
        else:
            subgraph = self.graph
            print(f"Viewing complete graph with {self.graph.number_of_nodes()} nodes")
        
        try:
            print("Launching interactive graph viewer...")
            print("Controls:")
            print("  - Mouse: Pan and zoom")
            print("  - Click nodes: Select and highlight")
            print("  - Right-click: Context menu")
            print("  - Close window to return to command line")
            
            # Create viewer and show
            viewer = Viewer(subgraph)
            viewer.show()
            
            return True
            
        except Exception as e:
            print(f"Error launching viewer: {e}")
            return False
    
    def view_graph_matplotlib(self, max_nodes: int = 100) -> bool:
        """Create a matplotlib visualization and save as image for viewing."""
        # Don't try to use interactive backend if tkinter isn't available
        import matplotlib
        matplotlib.use('Agg')  # Use non-interactive backend
        
        if not self.graph:
            print("Error: No graph available. Please build the graph first.")
            return False
        
        # Use a subset if the graph is too large
        if self.graph.number_of_nodes() > max_nodes:
            print(f"Graph has {self.graph.number_of_nodes()} nodes. Using largest connected component for viewing (max {max_nodes} nodes).")
            
            # Get the largest connected component
            if self.graph.is_directed():
                components = list(nx.weakly_connected_components(self.graph))
            else:
                components = list(nx.connected_components(self.graph))
            
            # Sort by size and take the largest component
            components.sort(key=len, reverse=True)
            largest_component = components[0]
            
            if len(largest_component) > max_nodes:
                # Take a subset of the largest component
                component_nodes = list(largest_component)[:max_nodes]
                subgraph = self.graph.subgraph(component_nodes)
                print(f"Viewing subset of {len(component_nodes)} nodes from largest component")
            else:
                subgraph = self.graph.subgraph(largest_component)
                print(f"Viewing largest component with {len(largest_component)} nodes")
        else:
            subgraph = self.graph
            print(f"Viewing complete graph with {self.graph.number_of_nodes()} nodes")
        
        try:
            print("Creating matplotlib graph visualization...")
            print("Note: Saving as image since interactive viewing requires tkinter")
            
            # Create interactive plot
            plt.figure(figsize=(14, 10))
            plt.clf()
            
            # Create layout - try planar first, then other good options for this type of graph
            try:
                print("Attempting planar layout...")
                pos = nx.planar_layout(subgraph)
                print("Using planar layout")
            except nx.NetworkXException:
                print("Planar layout failed (expected for CMDB graphs), trying Kamada-Kawai layout...")
                try:
                    pos = nx.kamada_kawai_layout(subgraph, scale=2)
                    print("Using Kamada-Kawai layout")
                except:
                    print("Kamada-Kawai layout failed, trying spring layout...")
                    try:
                        pos = nx.spring_layout(subgraph, k=2, iterations=50, seed=42)
                        print("Using spring layout")
                    except:
                        print("Spring layout failed, using circular layout...")
                        pos = nx.circular_layout(subgraph)
                        print("Using circular layout")
            
            # Draw nodes with colors and sizes
            node_sizes = []
            node_colors = []
            package_groups = {}  # Track which packages are present for legend
            
            for node in subgraph.nodes():
                degree = subgraph.degree(node)
                node_sizes.append(max(100, min(1000, degree * 50)))
                
                # Get table package information
                table_info = self.tables.get(node, {})
                package_source = table_info.get('package', '')
                scope = table_info.get('scope', 'unknown')
                
                # Determine color based on package/scope
                if scope == 'global':
                    node_colors.append('#4CAF50')  # Green for global
                    package_groups['Global Scope'] = '#4CAF50'
                elif package_source and package_source != 'global':
                    # Use different colors for different package types
                    if package_source.startswith('sn_'):
                        node_colors.append('#9C27B0')  # Purple for ServiceNow packages
                        package_groups['ServiceNow Packages'] = '#9C27B0'
                    elif package_source.startswith('com.'):
                        node_colors.append('#FF9800')  # Orange for com. packages
                        package_groups['Plugins/Extensions'] = '#FF9800'
                    else:
                        node_colors.append('#607D8B')  # Blue-grey for other packages
                        package_groups['Other Packages'] = '#607D8B'
                else:
                    node_colors.append('#2196F3')  # Blue for unknown/other
                    package_groups['Other/Unknown'] = '#2196F3'
            
            # Draw the graph
            nx.draw_networkx_nodes(subgraph, pos, 
                                  node_color=node_colors, 
                                  node_size=node_sizes,
                                  alpha=0.8)
            
            if subgraph.is_directed():
                nx.draw_networkx_edges(subgraph, pos, 
                                      edge_color='gray', 
                                      arrows=True, 
                                      arrowsize=15,
                                      alpha=0.6,
                                      width=1)
            else:
                nx.draw_networkx_edges(subgraph, pos, 
                                      edge_color='gray', 
                                      alpha=0.6,
                                      width=1)
            
            # Add labels for important nodes using display labels
            degrees = dict(subgraph.degree())
            important_nodes = {}
            sorted_nodes = sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:15]
            for node, degree in sorted_nodes:
                display_label = self.get_table_display_label(node, max_length=20)
                important_nodes[node] = display_label
                
            nx.draw_networkx_labels(subgraph, pos, 
                                   labels=important_nodes,
                                   font_size=8,
                                   font_weight='bold')
            
            plt.title(f'ServiceNow CMDB Table Relationships\n({subgraph.number_of_nodes()} nodes, {subgraph.number_of_edges()} edges)', 
                     fontsize=14, fontweight='bold')
            plt.axis('off')
            
            # Add legend with dynamic package information
            legend_elements = []
            for package_label, color in sorted(package_groups.items()):
                legend_elements.append(patches.Patch(color=color, label=package_label))
            plt.legend(handles=legend_elements, loc='upper right')
            
            plt.tight_layout()
            
            # Save the image instead of showing interactively
            output_file = self.base_path / "cmdb_graph_view.png"
            plt.savefig(output_file, dpi=150, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            plt.close()
            
            print(f"Graph visualization saved to: {output_file}")
            print("You can open this image file to view the graph.")
            
            return True
            
        except Exception as e:
            print(f"Error launching matplotlib viewer: {e}")
            return False


def main():
    """Main function to demonstrate usage."""
    # Initialize the graph builder
    builder = CMDBGraphBuilder()
    
    # Build the graph
    graph = builder.build_graph()
    
    # Print statistics
    stats = builder.get_graph_statistics()
    print(f"\nDetailed Statistics:")
    for key, value in stats.items():
        if key == 'top_central_nodes':
            print(f"  Top 5 most connected tables:")
            for i, (node, centrality) in enumerate(value[:5]):
                print(f"    {i+1}. {node} (centrality: {centrality:.4f})")
        else:
            print(f"  {key}: {value}")
    
    # Show sample relationships
    builder.print_sample_relationships()
    
    # Export graph in multiple formats
    print("\nExporting graph...")
    builder.export_graph("gexf")
    builder.export_graph("json")
    
    # Example: Find relationships for a specific table
    print("\nExample: Relationships for 'cmdb_ci_server':")
    server_rels = builder.find_table_relationships('cmdb_ci_server')
    if 'error' not in server_rels:
        print(f"  Incoming: {server_rels['total_incoming']} relationships")
        print(f"  Outgoing: {server_rels['total_outgoing']} relationships")
        
        if server_rels['incoming_relationships']:
            print("  Sample incoming relationships:")
            for rel in server_rels['incoming_relationships'][:3]:
                print(f"    {rel['source']} --[{rel['relationship']}]--> cmdb_ci_server")
        
        if server_rels['outgoing_relationships']:
            print("  Sample outgoing relationships:")
            for rel in server_rels['outgoing_relationships'][:3]:
                print(f"    cmdb_ci_server --[{rel['relationship']}]--> {rel['target']}")
    else:
        print(f"  {server_rels['error']}")


if __name__ == "__main__":
    main()