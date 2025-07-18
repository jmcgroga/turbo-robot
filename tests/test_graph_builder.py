"""
Unit tests for the CMDBGraphBuilder class.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import networkx as nx

from sn_cmdb_map.graph_builder import CMDBGraphBuilder


class TestCMDBGraphBuilder:
    """Test cases for CMDBGraphBuilder class."""

    @pytest.fixture
    def test_data_dir(self):
        """Create a temporary directory with test data."""
        # Get the test data directory
        test_dir = Path(__file__).parent / "data"
        
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
        temp_path = Path(temp_dir)
        
        # Copy test data files to temp directory
        for json_file in test_dir.glob("*.json"):
            shutil.copy(json_file, temp_path / json_file.name)
        
        yield temp_path
        
        # Cleanup
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def builder(self, test_data_dir):
        """Create a CMDBGraphBuilder instance with test data."""
        return CMDBGraphBuilder(base_path=str(test_data_dir))

    def test_init(self, test_data_dir):
        """Test CMDBGraphBuilder initialization."""
        builder = CMDBGraphBuilder(base_path=str(test_data_dir))
        
        assert builder.base_path == Path(test_data_dir)
        assert isinstance(builder.graph, nx.DiGraph)
        assert builder.tables == {}
        assert builder.relationship_types == {}
        assert builder.packages == {}
        assert builder.sys_id_to_table == {}
        assert builder.output_base_dir.exists()
        assert "cmdb_analysis_" in str(builder.output_base_dir)

    def test_load_tables(self, builder):
        """Test loading table definitions."""
        builder.load_tables()
        
        assert len(builder.tables) == 5
        assert "table_a" in builder.tables
        assert "table_c" in builder.tables
        
        # Test table hierarchy
        assert builder.tables["table_a"]["super_class"] == ""
        assert builder.tables["table_b"]["super_class"] == "table_a"
        assert builder.tables["table_c"]["super_class"] == "table_b"
        
        # Test sys_id mapping
        assert "table_a_id" in builder.sys_id_to_table
        assert builder.sys_id_to_table["table_a_id"] == "table_a"

    def test_load_relationship_types(self, builder):
        """Test loading relationship type definitions."""
        builder.load_relationship_types()
        
        assert len(builder.relationship_types) == 3
        assert "rel_type_1" in builder.relationship_types
        
        rel_1 = builder.relationship_types["rel_type_1"]
        assert rel_1["name"] == "Relation 1::Inverse 1"
        assert rel_1["parent_descriptor"] == "Relation 1"
        assert rel_1["child_descriptor"] == "Inverse 1"

    def test_load_packages(self, builder):
        """Test loading package definitions."""
        builder.load_packages()
        
        assert len(builder.packages) == 2  # indexed by both source and sys_id
        assert "pkg_x" in builder.packages
        assert builder.packages["pkg_x"]["name"] == "Package X"

    def test_add_suggested_relationships(self, builder):
        """Test adding CI relationships from suggestion files."""
        builder.load_tables()
        builder.load_relationship_types()
        
        # Add relationships from cmdb_rel_type_suggest.json
        count = builder.add_suggested_relationships("cmdb_rel_type_suggest.json")
        assert count == 2
        assert builder.graph.number_of_edges() == 2
        
        # Check specific relationships
        assert builder.graph.has_edge("table_e", "table_d")
        assert builder.graph.has_edge("table_d", "table_b")

    def test_add_class_hierarchy_edges(self, builder):
        """Test adding class hierarchy relationships."""
        builder.load_tables()
        
        count = builder.add_class_hierarchy_edges()
        assert count == 4  # 4 tables have super_class relationships
        
        # Check hierarchy relationships (parent -> child)
        assert builder.graph.has_edge("table_a", "table_b")
        assert builder.graph.has_edge("table_b", "table_c")
        assert builder.graph.has_edge("table_a", "table_d")
        assert builder.graph.has_edge("table_a", "table_e")
        
        # Check edge attributes
        edge_data = builder.graph.edges["table_a", "table_b"]
        assert edge_data["relationship_type"] == "class_hierarchy"
        assert edge_data["label"] == "parent of"
        assert edge_data["edge_type"] == "hierarchy"

    def test_build_graph(self, builder):
        """Test building the complete graph."""
        graph = builder.build_graph()
        
        assert isinstance(graph, nx.DiGraph)
        assert graph.number_of_nodes() > 0
        assert graph.number_of_edges() > 0
        
        # Should have both CI relationships and hierarchy relationships
        ci_edges = [(s, t, data) for s, t, data in graph.edges(data=True) 
                   if data.get("edge_type") != "hierarchy"]
        hierarchy_edges = [(s, t, data) for s, t, data in graph.edges(data=True) 
                          if data.get("edge_type") == "hierarchy"]
        
        assert len(ci_edges) > 0
        assert len(hierarchy_edges) > 0

    def test_get_table_display_label(self, builder):
        """Test getting human-readable table labels."""
        builder.load_tables()
        
        # Test with existing table
        label = builder.get_table_display_label("table_c")
        assert label == "Item C"
        
        # Test with table that has no label (uses name)
        label = builder.get_table_display_label("nonexistent_table")
        assert label == "Nonexistent Table"
        
        # Test with length limit
        label = builder.get_table_display_label("table_c", max_length=3)
        assert len(label) <= 3

    def test_get_table_inheritance_chain(self, builder):
        """Test getting inheritance chain for a table."""
        builder.load_tables()
        
        # Test inheritance chain for table_c
        chain = builder.get_table_inheritance_chain("table_c")
        assert chain == ["table_c", "table_b", "table_a"]
        
        # Test inheritance chain for base table
        chain = builder.get_table_inheritance_chain("table_a")
        assert chain == ["table_a"]
        
        # Test with nonexistent table
        chain = builder.get_table_inheritance_chain("nonexistent")
        assert chain == ["nonexistent"]

    def test_find_inherited_relationships(self, builder):
        """Test finding tables with applicable relationships via inheritance."""
        builder.build_graph()
        
        applicable = builder.find_inherited_relationships("table_c")
        assert "table_c" in applicable
        assert "table_b" in applicable
        assert "table_a" in applicable

    def test_find_all_paths_between_tables(self, builder):
        """Test finding paths between tables."""
        builder.build_graph()
        
        # Test finding paths with inheritance
        paths = builder.find_all_paths_between_tables("table_e", "table_c", max_paths=5)
        assert len(paths) > 0
        
        # Check that we get path tuples (path, ancestor)
        for path_info in paths:
            assert isinstance(path_info, tuple)
            assert len(path_info) == 2
            path, ancestor = path_info
            assert isinstance(path, list)
            assert len(path) > 0

    def test_create_path_graph_between_tables(self, builder):
        """Test creating a graph showing paths between tables."""
        builder.build_graph()
        
        path_graph = builder.create_path_graph_between_tables("table_e", "table_c")
        assert isinstance(path_graph, nx.DiGraph)
        assert path_graph.number_of_nodes() > 0
        assert path_graph.number_of_edges() > 0

    @patch('matplotlib.pyplot.close')
    @patch('matplotlib.pyplot.savefig')
    @patch('matplotlib.pyplot.figure')
    @patch('matplotlib.pyplot.legend')
    @patch('matplotlib.pyplot.axis')
    @patch('matplotlib.pyplot.title')
    @patch('matplotlib.pyplot.tight_layout')
    @patch('networkx.draw_networkx_edge_labels')
    @patch('networkx.draw_networkx_labels')
    @patch('networkx.draw_networkx_edges')
    @patch('networkx.draw_networkx_nodes')
    @patch('networkx.planar_layout')
    def test_visualize_table_graph(self, mock_layout, mock_nodes, mock_edges, 
                                   mock_labels, mock_edge_labels, mock_tight, 
                                   mock_title, mock_axis, mock_legend, 
                                   mock_figure, mock_savefig, mock_close, builder):
        """Test generating visualization graphs."""
        # Mock the layout to return valid positions
        mock_layout.return_value = {
            "table_e": (0, 0),
            "table_c": (1, 1),
            "table_b": (0.5, 0.5)
        }
        
        builder.build_graph()
        
        # Test successful visualization
        success = builder.visualize_table_graph(
            "table_e", 
            target_table="table_c", 
            shortest_path_only=True
        )
        assert success is True
        assert mock_figure.call_count >= 1
        mock_savefig.assert_called_once()

    def test_visualize_table_graph_no_paths(self, builder):
        """Test visualization when no paths exist."""
        builder.build_graph()
        
        # Test with tables that have no path
        success = builder.visualize_table_graph(
            "nonexistent_table", 
            target_table="another_nonexistent", 
            shortest_path_only=True
        )
        assert success is False

    def test_get_package_display_name(self, builder):
        """Test getting package display names."""
        builder.load_packages()
        
        # Test with existing package
        name = builder.get_package_display_name("pkg_x")
        assert name == "Package X"
        
        # Test with nonexistent package
        name = builder.get_package_display_name("nonexistent")
        assert name == "Unknown Package"
        
        # Test with empty string
        name = builder.get_package_display_name("")
        assert name == "Unknown Package"

    def test_node_attributes(self, builder):
        """Test node attributes are set correctly."""
        builder.load_tables()
        builder.load_packages()
        
        attrs = builder._get_node_attributes("table_c")
        assert attrs["label"] == "Item C"
        assert attrs["super_class"] == "table_b"
        assert attrs["scope"] == "global"
        assert attrs["type"] == "cmdb_table"

    def test_error_handling_missing_files(self, tmp_path):
        """Test error handling when data files are missing."""
        # Create builder with empty directory
        builder = CMDBGraphBuilder(base_path=str(tmp_path))
        
        # These should not raise exceptions
        builder.load_tables()
        builder.load_relationship_types() 
        builder.load_packages()
        
        # Tables should be empty
        assert len(builder.tables) == 0
        assert len(builder.relationship_types) == 0
        assert len(builder.packages) == 0