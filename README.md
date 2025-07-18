# ServiceNow CMDB Table Relationship Mapper

A Python library for creating directed graph visualizations of ServiceNow Configuration Management Database (CMDB) table relationships, showing both CI relationships and class inheritance hierarchies. It processes ServiceNow export data to map how different CMDB tables relate to each other through both business relationships and object-oriented inheritance.

## Features

- **Path Finding**: Discovers relationship paths between CMDB tables including inheritance chains
- **Class Hierarchy Visualization**: Shows parent-child relationships from ServiceNow table inheritance
- **CI Relationship Mapping**: Maps configuration item relationships between tables
- **Visual Distinction**: Uses dotted lines for class hierarchy and solid lines for CI relationships
- **Clean Output**: Simplified interface focused on path discovery between tables
- **PNG Graph Generation**: Creates visual graph files showing relationship paths

## Required Input Files

The tool requires four JSON files exported from ServiceNow. These files must be present in the project directory:

### 1. `sys_db_object.json` (Required)
- **Content**: Table definitions and metadata for all ServiceNow tables
- **Key Fields**: `name`, `label`, `super_class`, `sys_package`, `scope`
- **Purpose**: Provides table hierarchy (inheritance) and human-readable labels
- **Export Query**: `sys_db_object` table
- **Size**: ~7,700 records (all ServiceNow tables)

### 2. `cmdb_rel_type.json` (Required)  
- **Content**: Relationship type definitions for CMDB relationships
- **Key Fields**: `name`, `parent_descriptor`, `child_descriptor`, `sys_id`
- **Purpose**: Defines the types of relationships that can exist between CI tables
- **Export Query**: `cmdb_rel_type` table
- **Size**: ~54 relationship types

### 3. `cmdb_rel_type_suggest.json` (Required)
- **Content**: Suggested relationships between CMDB tables
- **Key Fields**: `base_class`, `dependent_class`, `cmdb_rel_type`, `parent`
- **Purpose**: Primary source of CI relationships between tables
- **Export Query**: `cmdb_rel_type_suggest` table  
- **Size**: ~700 suggested relationships

### 4. `em_suggested_relation_type.json` (Required)
- **Content**: Additional suggested relationships from Event Management
- **Key Fields**: `base_class`, `dependent_class`, `cmdb_rel_type`, `parent`
- **Purpose**: Additional CI relationships, often from Event Management integrations
- **Export Query**: `em_suggested_relation_type` table
- **Size**: ~170 additional relationships

### 5. `sys_package.json` (Optional)
- **Content**: ServiceNow package definitions for enhanced visualization
- **Key Fields**: `source`, `name`, `version`, `sys_id`
- **Purpose**: Provides human-readable package names for graph legends
- **Export Query**: `sys_package` table
- **Size**: ~2,200 packages

## Installation

### From Source

```bash
# Clone or download the project
git clone https://github.com/your-org/sn-cmdb-map.git
cd sn-cmdb-map

# Install dependencies using uv (recommended)
uv sync

# Install the package to enable the script and library
uv pip install -e .
```

### From PyPI (when published)

```bash
pip install sn-cmdb-map
```

## Usage

The library provides both a command-line interface and a Python API for finding paths between CMDB tables:

### Command-Line Interface

```bash
# Using the installed script
create_relationship_graph --generate-single-table-graph cmdb_ci_zone --target-table cmdb_ci_server --shortest-path

# Using the module directly
python -m sn_cmdb_map --generate-single-table-graph cmdb_ci_zone --target-table cmdb_ci_server

# Find all paths between two tables  
create_relationship_graph --generate-single-table-graph cmdb_ci_zone --target-table cmdb_ci_server
```

### Python API Usage

```python
from sn_cmdb_map import CMDBGraphBuilder

# Initialize the graph builder
builder = CMDBGraphBuilder()

# Build the graph from JSON files
graph = builder.build_graph()

# Find paths between tables
paths = builder.find_all_paths_between_tables("cmdb_ci_zone", "cmdb_ci_server", max_paths=5)

for i, (path, ancestor) in enumerate(paths, 1):
    path_labels = [builder.get_table_display_label(node) for node in path]
    print(f"Path {i}: {' → '.join(path_labels)}")

# Generate visual graph
success = builder.visualize_table_graph(
    "cmdb_ci_zone", 
    target_table="cmdb_ci_server", 
    shortest_path_only=True
)
```

### Command Line Options

- `--generate-single-table-graph TABLE` - Source table name (required)
- `--target-table TABLE` - Target table name (required)  
- `--shortest-path` - Show only shortest path (optional, default shows all paths)

## Output

### Console Output
The tool provides clean, minimal output showing only the discovered paths and the output location:

```
Path 1: Data Center Zone → Rack → Computer → Server
Path 2: Data Center Zone → Rack → Computer → Cisco UCS Blade → Server
Path 3: Data Center Zone → Rack → Computer → VMware Virtual Machine → Windows Server → Server

Graph saved to: cmdb_analysis_20250717_205049/path_graphs/
```

### Visual Graphs
- **Location**: Timestamped directories (e.g., `cmdb_analysis_20250717_205049/path_graphs/`)
- **Format**: PNG images
- **Organization**: Each run creates a new timestamped directory to avoid overwriting previous analyses
- **Content**: Visual graphs showing the relationship paths with:
  - **Solid gray lines**: CI relationships (e.g., "Contains", "Powers", "Located in")
  - **Dotted blue lines**: Class hierarchy relationships (e.g., "parent of")
  - **Color-coded nodes**: Different colors for different ServiceNow packages
  - **Human-readable labels**: Uses friendly names instead of technical table names

## Graph Structure

### Relationship Types

The tool maps two distinct types of relationships:

#### 1. CI (Configuration Item) Relationships
- **Style**: Solid gray lines  
- **Source**: `cmdb_rel_type_suggest.json` and `em_suggested_relation_type.json`
- **Examples**: "Contains", "Powers", "Located in", "Runs on"
- **Purpose**: Business relationships between configuration items

#### 2. Class Hierarchy Relationships  
- **Style**: Dotted blue lines
- **Source**: `sys_db_object.json` (super_class field)
- **Label**: "parent of"
- **Purpose**: Object-oriented inheritance relationships (e.g., Computer → Server)

### Enhanced Path Finding

The tool now discovers paths through both CI relationships and class inheritance:

**Example**: `cmdb_ci_zone` to `cmdb_ci_server`
- **Direct Path**: Data Center Zone → Rack → Computer → Server
- **Shows inheritance**: Computer "parent of" Server (instead of skipping Computer)
- **Human readable**: Uses "Data Center Zone" instead of "cmdb_ci_zone"

## Example Use Cases

### Infrastructure Path Analysis
```bash
# How does a zone connect to servers?
create_relationship_graph --generate-single-table-graph cmdb_ci_zone --target-table cmdb_ci_server --shortest-path
# Output: Data Center Zone → Rack → Computer → Server

# What's the relationship between racks and servers?
create_relationship_graph --generate-single-table-graph cmdb_ci_rack --target-table cmdb_ci_server --shortest-path  
# Output: Rack → Computer → Server
```

### Class Hierarchy Understanding
```bash
# Direct inheritance relationship
create_relationship_graph --generate-single-table-graph cmdb_ci_computer --target-table cmdb_ci_server --shortest-path
# Output: Computer → Server (showing "parent of" relationship)
```

## Project Structure

```
sn-cmdb-map/
├── src/
│   └── sn_cmdb_map/                  # Main package directory
│       ├── __init__.py               # Package initialization and exports
│       ├── __main__.py               # Module execution entry point
│       ├── cli.py                    # Command-line interface
│       └── graph_builder.py          # Core graph building with hierarchy support
├── tests/                           # Test package
│   ├── __init__.py                  # Test package initialization
│   ├── conftest.py                  # Pytest configuration and fixtures
│   ├── data/                        # Mock data for testing
│   │   ├── sys_db_object.json       # Test table definitions
│   │   ├── cmdb_rel_type.json       # Test relationship types
│   │   ├── cmdb_rel_type_suggest.json # Test CI relationships
│   │   ├── em_suggested_relation_type.json # Additional test relationships
│   │   └── sys_package.json         # Test package definitions
│   ├── test_graph_builder.py        # Tests for CMDBGraphBuilder class
│   └── test_cli.py                  # Tests for CLI functionality
├── setup.py                         # Setup configuration (compatibility)
├── pyproject.toml                   # Modern package configuration
├── pytest.ini                      # Pytest configuration
├── cmdb_analysis_YYYYMMDD_HHMMSS/   # Timestamped output directories
│   └── path_graphs/                 # Generated PNG graph visualizations
├── sys_db_object.json              # ServiceNow table definitions (required)
├── cmdb_rel_type.json              # Relationship type definitions (required)  
├── cmdb_rel_type_suggest.json      # Suggested CI relationships (required)
├── em_suggested_relation_type.json # Additional CI relationships (required)
├── sys_package.json                # Package definitions (optional)
└── README.md                       # This documentation
```

## API Reference

### CMDBGraphBuilder Class

The main class for building and analyzing CMDB relationship graphs.

#### Methods

- `__init__(base_path: str = ".")` - Initialize with data directory path
- `build_graph() -> nx.DiGraph` - Build the complete graph from JSON files
- `find_all_paths_between_tables(source: str, target: str, max_paths: int = 10) -> List[Tuple[List[str], str]]` - Find paths between tables
- `visualize_table_graph(table_name: str, target_table: str = None, shortest_path_only: bool = False) -> bool` - Generate visual graph
- `get_table_display_label(table_name: str, max_length: int = 25) -> str` - Get human-readable table name
- `get_table_inheritance_chain(table_name: str) -> List[str]` - Get inheritance hierarchy for a table

#### Properties

- `graph` - The NetworkX directed graph object
- `tables` - Dictionary of table metadata
- `output_base_dir` - Timestamped output directory path

## Testing

This library includes comprehensive unit tests to ensure reliability and correctness.

### Running Tests

```bash
# Install with development dependencies
uv pip install -e ".[dev]"

# Run all tests
pytest

# Run tests with verbose output
pytest -v

# Run tests with coverage report
pytest --cov=src/sn_cmdb_map --cov-report=term-missing

# Run specific test file
pytest tests/test_graph_builder.py

# Run specific test method
pytest tests/test_cli.py::TestCLI::test_main_shortest_path
```

### Test Structure

```
tests/
├── __init__.py                    # Test package initialization
├── conftest.py                    # Shared fixtures and configuration
├── data/                          # Mock data for testing
│   ├── sys_db_object.json         # Test table definitions
│   ├── cmdb_rel_type.json         # Test relationship types
│   ├── cmdb_rel_type_suggest.json # Test CI relationships
│   ├── em_suggested_relation_type.json # Additional test relationships
│   └── sys_package.json          # Test package definitions
├── test_graph_builder.py          # Tests for CMDBGraphBuilder class
└── test_cli.py                   # Tests for CLI functionality
```

### Test Coverage

The test suite covers:

- **Graph Building**: Loading data, building relationships, class hierarchy
- **Path Finding**: Direct paths, inheritance paths, path visualization
- **CLI Interface**: Argument parsing, error handling, output formatting
- **Error Handling**: Missing files, invalid data, visualization failures
- **Data Processing**: Table loading, relationship processing, package handling

### Writing New Tests

When contributing new features:

1. Add test data to `tests/data/` if needed
2. Write unit tests in appropriate test files
3. Use pytest fixtures for shared setup
4. Mock external dependencies (matplotlib, file I/O)
5. Aim for good test coverage of new functionality

Example test structure:
```python
def test_new_feature(self, builder):
    """Test description."""
    # Setup
    builder.build_graph()
    
    # Execute
    result = builder.new_method()
    
    # Assert
    assert result is not None
    assert len(result) > 0
```

## Development

### Key Features Implemented

1. **Python Library Structure**: Proper package organization with `src/` layout
2. **Class Hierarchy Integration**: Adds inheritance relationships from `super_class` field
3. **Visual Distinction**: Different line styles for CI vs hierarchy relationships  
4. **Enhanced Path Finding**: Includes inheritance chains in path discovery
5. **Dual Interface**: Both command-line tool and Python API
6. **Clean Output**: Minimal console output showing only discovered paths
7. **Timestamped Output**: Each run creates dated directories to preserve results
8. **Comprehensive Testing**: Unit tests with 42% code coverage

### Technical Details

- **Graph Library**: NetworkX for directed graph operations
- **Visualization**: Matplotlib for PNG generation with custom styling
- **Layout**: Attempts planar layout, falls back to Kamada-Kawai or spring layouts
- **Node Attributes**: Includes table metadata, package info, inheritance data
- **Edge Attributes**: Distinguishes CI relationships from hierarchy relationships

## Data Export from ServiceNow

To export the required JSON files from ServiceNow:

1. Navigate to **System Definition > Tables**
2. For each required table, export records as JSON
3. Ensure all fields are included in the export
4. Place JSON files in the project root directory

Required exports:
- `sys_db_object` → `sys_db_object.json`
- `cmdb_rel_type` → `cmdb_rel_type.json`  
- `cmdb_rel_type_suggest` → `cmdb_rel_type_suggest.json`
- `em_suggested_relation_type` → `em_suggested_relation_type.json`
- `sys_package` → `sys_package.json` (optional)

## License

This project is provided as-is for educational and analysis purposes. Ensure you have proper authorization to analyze ServiceNow data from your organization.