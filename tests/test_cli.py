"""
Unit tests for the CLI functionality.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
from io import StringIO

from sn_cmdb_map.cli import main


class TestCLI:
    """Test cases for CLI functionality."""

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

    def test_main_shortest_path(self, test_data_dir):
        """Test main function with shortest path option."""
        # Mock sys.argv
        test_args = [
            'create_relationship_graph',
            '--generate-single-table-graph', 'table_e',
            '--target-table', 'table_c',
            '--shortest-path'
        ]
        
        with patch.object(sys, 'argv', test_args):
            # Create a mock builder instance
            mock_builder = MagicMock()
            mock_graph = MagicMock()
            mock_builder.build_graph.return_value = mock_graph
            mock_builder.visualize_table_graph.return_value = True
            mock_builder.output_base_dir = Path("test_output")
            
            with patch('sn_cmdb_map.cli.CMDBGraphBuilder', return_value=mock_builder):
                # Capture stdout
                captured_output = StringIO()
                with patch('sys.stdout', captured_output):
                    main()
                
                # Verify the method calls
                mock_builder.build_graph.assert_called_once()
                mock_builder.visualize_table_graph.assert_called_once_with(
                    'table_e',
                    output_dir="path_graphs",
                    target_table='table_c',
                    shortest_path_only=True
                )

    def test_main_all_paths(self):
        """Test main function without shortest path option."""
        # Mock sys.argv
        test_args = [
            'create_relationship_graph',
            '--generate-single-table-graph', 'table_e',
            '--target-table', 'table_c'
        ]
        
        with patch.object(sys, 'argv', test_args):
            # Create a mock builder instance
            mock_builder = MagicMock()
            mock_graph = MagicMock()
            mock_builder.build_graph.return_value = mock_graph
            mock_builder.visualize_table_graph.return_value = True
            mock_builder.output_base_dir = Path("test_output")
            
            with patch('sn_cmdb_map.cli.CMDBGraphBuilder', return_value=mock_builder):
                main()
                
                # Verify shortest_path_only is False
                mock_builder.visualize_table_graph.assert_called_once_with(
                    'table_e',
                    output_dir="path_graphs",
                    target_table='table_c',
                    shortest_path_only=False
                )

    def test_main_build_graph_failure(self):
        """Test main function when graph building fails."""
        test_args = [
            'create_relationship_graph',
            '--generate-single-table-graph', 'table_e',
            '--target-table', 'table_c'
        ]
        
        with patch.object(sys, 'argv', test_args):
            mock_builder = MagicMock()
            mock_builder.build_graph.return_value = None
            
            with patch('sn_cmdb_map.cli.CMDBGraphBuilder', return_value=mock_builder):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                
                assert exc_info.value.code == 1

    def test_main_visualization_failure(self):
        """Test main function when visualization fails."""
        test_args = [
            'create_relationship_graph',
            '--generate-single-table-graph', 'table_e',
            '--target-table', 'table_c'
        ]
        
        with patch.object(sys, 'argv', test_args):
            mock_builder = MagicMock()
            mock_graph = MagicMock()
            mock_builder.build_graph.return_value = mock_graph
            mock_builder.visualize_table_graph.return_value = False  # Visualization fails
            
            with patch('sn_cmdb_map.cli.CMDBGraphBuilder', return_value=mock_builder):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                
                assert exc_info.value.code == 1

    def test_argument_parser_help(self):
        """Test that help works correctly."""
        test_args = ['create_relationship_graph', '--help']
        
        with patch.object(sys, 'argv', test_args):
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            # Help should exit with code 0
            assert exc_info.value.code == 0

    def test_argument_parser_missing_required(self):
        """Test that missing required arguments cause failure."""
        # Missing target-table
        test_args = [
            'create_relationship_graph',
            '--generate-single-table-graph', 'table_e'
        ]
        
        with patch.object(sys, 'argv', test_args):
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            # Should exit with code 2 (argparse error)
            assert exc_info.value.code == 2

    def test_argument_parser_missing_source_table(self):
        """Test that missing source table argument causes failure."""
        test_args = [
            'create_relationship_graph',
            '--target-table', 'table_c'
        ]
        
        with patch.object(sys, 'argv', test_args):
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            # Should exit with code 2 (argparse error)
            assert exc_info.value.code == 2

    def test_main_output_message(self):
        """Test that success message is printed correctly."""
        test_args = [
            'create_relationship_graph',
            '--generate-single-table-graph', 'table_e',
            '--target-table', 'table_c'
        ]
        
        with patch.object(sys, 'argv', test_args):
            mock_builder = MagicMock()
            mock_graph = MagicMock()
            mock_builder.build_graph.return_value = mock_graph
            mock_builder.visualize_table_graph.return_value = True
            mock_builder.output_base_dir = Path("test_output_dir")
            
            with patch('sn_cmdb_map.cli.CMDBGraphBuilder', return_value=mock_builder):
                # Capture stdout
                captured_output = StringIO()
                with patch('sys.stdout', captured_output):
                    main()
                
                output = captured_output.getvalue()
                assert "Graph saved to: test_output_dir/path_graphs/" in output