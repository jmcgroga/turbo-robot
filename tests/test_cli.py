"""
Unit tests for the CLI functionality.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
import os
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
            'table_e',
            'table_c',
            '--shortest-path'
        ]
        
        with patch.object(sys, 'argv', test_args), \
             patch.dict(os.environ, {}, clear=True), \
             patch('sn_cmdb_map.cli.load_dotenv'):  # Mock dotenv loading
            # Create a mock builder instance
            mock_builder = MagicMock()
            mock_graph = MagicMock()
            mock_builder.build_graph.return_value = mock_graph
            mock_builder.visualize_table_graph.return_value = True
            mock_builder.output_base_dir = Path("test_output")
            
            with patch('sn_cmdb_map.cli.CMDBGraphBuilder') as mock_builder_class:
                mock_builder_class.return_value = mock_builder
                # Capture stdout
                captured_output = StringIO()
                with patch('sys.stdout', captured_output):
                    main()
                
                # Verify the builder was initialized with data_dir=None
                mock_builder_class.assert_called_once_with(data_dir=None)
                
                # Verify the method calls
                mock_builder.build_graph.assert_called_once()
                mock_builder.visualize_table_graph.assert_called_once_with(
                    'table_e',
                    output_dir="path_graphs",
                    target_table='table_c',
                    shortest_path_only=True,
                    layout='auto'
                )

    def test_main_all_paths(self):
        """Test main function without shortest path option."""
        # Mock sys.argv
        test_args = [
            'create_relationship_graph',
            'table_e',
            'table_c'
        ]
        
        with patch.object(sys, 'argv', test_args), \
             patch.dict(os.environ, {}, clear=True), \
             patch('sn_cmdb_map.cli.load_dotenv'):  # Mock dotenv loading
            # Create a mock builder instance
            mock_builder = MagicMock()
            mock_graph = MagicMock()
            mock_builder.build_graph.return_value = mock_graph
            mock_builder.visualize_table_graph.return_value = True
            mock_builder.output_base_dir = Path("test_output")
            
            with patch('sn_cmdb_map.cli.CMDBGraphBuilder') as mock_builder_class:
                mock_builder_class.return_value = mock_builder
                main()
                
                # Verify the builder was initialized with data_dir=None
                mock_builder_class.assert_called_once_with(data_dir=None)
                
                # Verify shortest_path_only is False
                mock_builder.visualize_table_graph.assert_called_once_with(
                    'table_e',
                    output_dir="path_graphs",
                    target_table='table_c',
                    shortest_path_only=False,
                    layout='auto'
                )

    def test_main_build_graph_failure(self):
        """Test main function when graph building fails."""
        test_args = [
            'create_relationship_graph',
            'table_e',
            'table_c'
        ]
        
        with patch.object(sys, 'argv', test_args), \
             patch.dict(os.environ, {}, clear=True), \
             patch('sn_cmdb_map.cli.load_dotenv'):  # Mock dotenv loading
            mock_builder = MagicMock()
            mock_builder.build_graph.return_value = None
            
            with patch('sn_cmdb_map.cli.CMDBGraphBuilder') as mock_builder_class:
                mock_builder_class.return_value = mock_builder
                with pytest.raises(SystemExit) as exc_info:
                    main()
                
                # Verify the builder was initialized with data_dir=None
                mock_builder_class.assert_called_once_with(data_dir=None)
                assert exc_info.value.code == 1

    def test_main_visualization_failure(self):
        """Test main function when visualization fails."""
        test_args = [
            'create_relationship_graph',
            'table_e',
            'table_c'
        ]
        
        with patch.object(sys, 'argv', test_args), \
             patch.dict(os.environ, {}, clear=True), \
             patch('sn_cmdb_map.cli.load_dotenv'):  # Mock dotenv loading
            mock_builder = MagicMock()
            mock_graph = MagicMock()
            mock_builder.build_graph.return_value = mock_graph
            mock_builder.visualize_table_graph.return_value = False  # Visualization fails
            
            with patch('sn_cmdb_map.cli.CMDBGraphBuilder') as mock_builder_class:
                mock_builder_class.return_value = mock_builder
                with pytest.raises(SystemExit) as exc_info:
                    main()
                
                # Verify the builder was initialized with data_dir=None
                mock_builder_class.assert_called_once_with(data_dir=None)
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
        # Missing target table
        test_args = [
            'create_relationship_graph',
            'table_e'
        ]
        
        with patch.object(sys, 'argv', test_args):
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            # Should exit with code 2 (argparse error)
            assert exc_info.value.code == 2

    def test_argument_parser_missing_source_table(self):
        """Test that missing source table argument causes failure."""
        test_args = [
            'create_relationship_graph'
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
            'table_e',
            'table_c'
        ]
        
        with patch.object(sys, 'argv', test_args), \
             patch.dict(os.environ, {}, clear=True), \
             patch('sn_cmdb_map.cli.load_dotenv'):  # Mock dotenv loading
            mock_builder = MagicMock()
            mock_graph = MagicMock()
            mock_builder.build_graph.return_value = mock_graph
            mock_builder.visualize_table_graph.return_value = True
            mock_builder.output_base_dir = Path("test_output_dir")
            
            with patch('sn_cmdb_map.cli.CMDBGraphBuilder') as mock_builder_class:
                mock_builder_class.return_value = mock_builder
                # Capture stdout
                captured_output = StringIO()
                with patch('sys.stdout', captured_output):
                    main()
                
                # Verify the builder was initialized with data_dir=None
                mock_builder_class.assert_called_once_with(data_dir=None)
                
                output = captured_output.getvalue()
                assert "Graph saved to: test_output_dir/path_graphs/" in output

    def test_data_dir_command_line_option(self):
        """Test that --data-dir command line option works."""
        test_args = [
            'create_relationship_graph',
            'table_e',
            'table_c',
            '--data-dir', '/test/data/dir'
        ]
        
        with patch.object(sys, 'argv', test_args):
            mock_builder = MagicMock()
            mock_graph = MagicMock()
            mock_builder.build_graph.return_value = mock_graph
            mock_builder.visualize_table_graph.return_value = True
            mock_builder.output_base_dir = Path("test_output")
            
            # Mock Path.exists and Path.is_dir to return True
            with patch('pathlib.Path.exists', return_value=True), \
                 patch('pathlib.Path.is_dir', return_value=True), \
                 patch('sn_cmdb_map.cli.CMDBGraphBuilder') as mock_builder_class:
                mock_builder_class.return_value = mock_builder
                main()
                
                # Verify the builder was initialized with the specified data_dir
                mock_builder_class.assert_called_once_with(data_dir='/test/data/dir')

    def test_environment_variable_data_dir(self):
        """Test that CMDB_DATA_DIR environment variable works."""
        test_args = [
            'create_relationship_graph',
            'table_e',
            'table_c'
        ]
        
        with patch.object(sys, 'argv', test_args), \
             patch.dict(os.environ, {'CMDB_DATA_DIR': '/env/data/dir'}):
            mock_builder = MagicMock()
            mock_graph = MagicMock()
            mock_builder.build_graph.return_value = mock_graph
            mock_builder.visualize_table_graph.return_value = True
            mock_builder.output_base_dir = Path("test_output")
            
            # Mock Path.exists and Path.is_dir to return True
            with patch('pathlib.Path.exists', return_value=True), \
                 patch('pathlib.Path.is_dir', return_value=True), \
                 patch('sn_cmdb_map.cli.CMDBGraphBuilder') as mock_builder_class:
                mock_builder_class.return_value = mock_builder
                main()
                
                # Verify the builder was initialized with the env var data_dir
                mock_builder_class.assert_called_once_with(data_dir='/env/data/dir')

    def test_data_dir_priority_cmdline_over_env(self):
        """Test that command line --data-dir takes priority over environment variable."""
        test_args = [
            'create_relationship_graph',
            'table_e',
            'table_c',
            '--data-dir', '/cmdline/data/dir'
        ]
        
        with patch.object(sys, 'argv', test_args), \
             patch.dict(os.environ, {'CMDB_DATA_DIR': '/env/data/dir'}):
            mock_builder = MagicMock()
            mock_graph = MagicMock()
            mock_builder.build_graph.return_value = mock_graph
            mock_builder.visualize_table_graph.return_value = True
            mock_builder.output_base_dir = Path("test_output")
            
            # Mock Path.exists and Path.is_dir to return True
            with patch('pathlib.Path.exists', return_value=True), \
                 patch('pathlib.Path.is_dir', return_value=True), \
                 patch('sn_cmdb_map.cli.CMDBGraphBuilder') as mock_builder_class:
                mock_builder_class.return_value = mock_builder
                main()
                
                # Verify the builder was initialized with cmdline data_dir, not env var
                mock_builder_class.assert_called_once_with(data_dir='/cmdline/data/dir')

    def test_invalid_data_dir_exits(self):
        """Test that invalid data directory causes program to exit."""
        test_args = [
            'create_relationship_graph',
            'table_e',
            'table_c',
            '--data-dir', '/nonexistent/dir'
        ]
        
        with patch.object(sys, 'argv', test_args):
            # Mock Path.exists to return False (directory doesn't exist)
            with patch('pathlib.Path.exists', return_value=False):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                
                assert exc_info.value.code == 1

    def test_layout_option_single(self):
        """Test that --layout option works with single layout."""
        test_args = [
            'create_relationship_graph',
            'table_e',
            'table_c',
            '--layout', 'spring'
        ]
        
        with patch.object(sys, 'argv', test_args):
            mock_builder = MagicMock()
            mock_graph = MagicMock()
            mock_builder.build_graph.return_value = mock_graph
            mock_builder.visualize_table_graph.return_value = True
            mock_builder.output_base_dir = Path("test_output")
            
            with patch('sn_cmdb_map.cli.CMDBGraphBuilder') as mock_builder_class:
                mock_builder_class.return_value = mock_builder
                main()
                
                # Verify the layout parameter was passed correctly
                mock_builder.visualize_table_graph.assert_called_once_with(
                    'table_e',
                    output_dir="path_graphs",
                    target_table='table_c',
                    shortest_path_only=False,
                    layout='spring'
                )

    def test_layout_option_all(self):
        """Test that --layout all generates multiple graphs."""
        test_args = [
            'create_relationship_graph',
            'table_e',
            'table_c',
            '--layout', 'all'
        ]
        
        with patch.object(sys, 'argv', test_args):
            mock_builder = MagicMock()
            mock_graph = MagicMock()
            mock_builder.build_graph.return_value = mock_graph
            mock_builder.visualize_table_graph.return_value = True
            mock_builder.output_base_dir = Path("test_output")
            
            with patch('sn_cmdb_map.cli.CMDBGraphBuilder') as mock_builder_class:
                mock_builder_class.return_value = mock_builder
                # Capture stdout
                captured_output = StringIO()
                with patch('sys.stdout', captured_output):
                    main()
                
                # Verify that visualize_table_graph was called 9 times (once for each layout)
                assert mock_builder.visualize_table_graph.call_count == 9
                
                # Verify some specific layout calls
                expected_layouts = ["spring", "kamada_kawai", "planar", "circular", "random", "shell", "spectral", "spiral", "multipartite"]
                actual_calls = [call.kwargs['layout'] for call in mock_builder.visualize_table_graph.call_args_list]
                assert set(actual_calls) == set(expected_layouts)
                
                # Verify output shows success count
                output = captured_output.getvalue()
                assert "Successfully generated 9/9 layouts" in output

    def test_data_dir_not_directory_exits(self):
        """Test that data directory that's not a directory causes program to exit."""
        test_args = [
            'create_relationship_graph',
            'table_e',
            'table_c',
            '--data-dir', '/path/to/file'
        ]
        
        with patch.object(sys, 'argv', test_args):
            # Mock Path.exists to return True but Path.is_dir to return False
            with patch('pathlib.Path.exists', return_value=True), \
                 patch('pathlib.Path.is_dir', return_value=False):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                
                assert exc_info.value.code == 1