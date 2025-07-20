# ServiceNow CMDB Table Relationship Mapper

A Python library for creating directed graph visualizations of ServiceNow Configuration Management Database (CMDB) table relationships, showing both CI relationships and class inheritance hierarchies. It processes ServiceNow export data to map how different CMDB tables relate to each other through both business relationships and object-oriented inheritance.

## Features

- **Path Finding**: Discovers relationship paths between CMDB tables including inheritance chains
- **Multiple Layout Algorithms**: Choose from 10 different graph layout algorithms for optimal visualization
- **Smart Root Positioning**: Automatically positions source tables in upper-left area for intuitive orientation
- **Class Hierarchy Visualization**: Shows parent-child relationships from ServiceNow table inheritance
- **CI Relationship Mapping**: Maps configuration item relationships between tables
- **Visual Distinction**: Uses dotted lines for class hierarchy and solid lines for CI relationships
- **Flexible Data Sources**: Support for custom data directories, environment variables, and .env files
- **Batch Generation**: Generate graphs with all layout algorithms simultaneously
- **Clean Output**: Simplified interface focused on path discovery between tables
- **PNG Graph Generation**: Creates visual graph files showing relationship paths

## Required Input Files

The tool requires JSON files exported from ServiceNow. These files can be placed in the current directory or a custom location:

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
# Basic usage with positional arguments
create_relationship_graph source_table target_table

# Show only shortest path
create_relationship_graph cmdb_ci_zone cmdb_ci_server --shortest-path

# Specify custom data directory
create_relationship_graph cmdb_ci_zone cmdb_ci_server --data-dir /path/to/json/files

# Use specific layout algorithm
create_relationship_graph cmdb_ci_zone cmdb_ci_server --layout spring

# Generate graphs with all available layouts
create_relationship_graph cmdb_ci_zone cmdb_ci_server --layout all

# Using environment variable for data directory
export CMDB_DATA_DIR=/path/to/json/files
create_relationship_graph cmdb_ci_zone cmdb_ci_server

# Using .env file for configuration
echo "CMDB_DATA_DIR=/path/to/json/files" > .env
create_relationship_graph cmdb_ci_zone cmdb_ci_server

# Using the module directly
python -m sn_cmdb_map cmdb_ci_zone cmdb_ci_server --shortest-path
```

### Data Directory Configuration

The tool supports multiple ways to specify where JSON data files are located (priority order):

1. **Command line**: `--data-dir /path/to/json/files`
2. **Environment variable**: `export CMDB_DATA_DIR=/path/to/json/files`
3. **`.env` file**: `CMDB_DATA_DIR=/path/to/json/files`
4. **Current directory**: Default behavior

### Layout Options

Choose from 10 different graph layout algorithms:

- `auto` - Automatic layout selection (tries planar → kamada_kawai → spring → circular)
- `spring` - Force-directed layout (Fruchterman-Reingold algorithm)
- `kamada_kawai` - Path-length based layout for aesthetic results (requires scipy)
- `planar` - Non-intersecting layout (when graph is planar)
- `circular` - Nodes arranged in a circle
- `random` - Random positioning
- `shell` - Concentric circle positioning
- `spectral` - Eigenvector-based layout
- `spiral` - Spiral pattern positioning
- `multipartite` - Layer-based layout for hierarchical data (requires node attributes)
- `all` - Generates graphs using all available layouts

### Root Node Positioning

For path graphs between two tables, the source (root) table is automatically positioned in the upper-left area. The layout algorithm positions nodes naturally, then the entire graph is translated to place the source table optimally. This provides consistent, intuitive orientation regardless of the underlying layout algorithm used.

### Python API Usage

```python
from sn_cmdb_map import CMDBGraphBuilder

# Initialize with custom data directory
builder = CMDBGraphBuilder(data_dir="/path/to/json/files")

# Build the graph from JSON files
graph = builder.build_graph()

# Find paths between tables
paths = builder.find_all_paths_between_tables("cmdb_ci_zone", "cmdb_ci_server", max_paths=5)

for i, (path, ancestor) in enumerate(paths, 1):
    path_labels = [builder.get_table_display_label(node) for node in path]
    print(f"Path {i}: {' → '.join(path_labels)}")

# Generate visual graph with specific layout
success = builder.visualize_table_graph(
    "cmdb_ci_zone", 
    target_table="cmdb_ci_server", 
    shortest_path_only=True,
    layout="spring"
)
```

### Command Line Options

- `source_table` - Source table name (required, positional)
- `target_table` - Target table name (required, positional)  
- `--data-dir DIR` - Directory containing JSON data files (optional)
- `--layout ALGORITHM` - Graph layout algorithm to use (optional, default: auto)
- `--shortest-path` - Show only shortest path (optional, default shows all paths)

## Output

### Console Output
The tool provides clean, minimal output showing only the discovered paths and the output location:

```
Path 1: Data Center Zone → Rack → Computer → Server
Path 2: Data Center Zone → Rack → Computer → Cisco UCS Blade → Server
Path 3: Data Center Zone → Rack → Computer → VMware Virtual Machine → Windows Server → Server

Graph saved to: cmdb_analysis_20250720_111030/path_graphs/
```

When using `--layout all`:
```
Generating graph with spring layout...
Path 1: Data Center Zone → Server
Path 2: Data Center Zone → Rack → Computer → Server

Generating graph with kamada_kawai layout...
Path 1: Data Center Zone → Server
Path 2: Data Center Zone → Rack → Computer → Server

[... output for each layout ...]

Graphs saved to: cmdb_analysis_20250720_111030/path_graphs/
Successfully generated 9/9 layouts
```

### Visual Graphs
- **Location**: Timestamped directories (e.g., `cmdb_analysis_20250720_111030/path_graphs/`)
- **Format**: PNG images with layout names in filenames (e.g., `source_to_target_spring.png`)
- **Organization**: Each run creates a new timestamped directory to avoid overwriting previous analyses
- **Content**: Visual graphs showing the relationship paths with:
  - **Solid gray lines**: CI relationships (e.g., "Contains", "Powers", "Located in")
  - **Dotted blue lines**: Class hierarchy relationships (e.g., "parent of")
  - **Color-coded nodes**: Different colors for different ServiceNow packages
  - **Human-readable labels**: Uses friendly names instead of technical table names
  - **Smart positioning**: Source tables positioned in upper-left area for intuitive orientation

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

The tool discovers paths through both CI relationships and class inheritance:

**Example**: `cmdb_ci_zone` to `cmdb_ci_server`
- **Direct Path**: Data Center Zone → Rack → Computer → Server
- **Shows inheritance**: Computer "parent of" Server (instead of skipping Computer)
- **Human readable**: Uses "Data Center Zone" instead of "cmdb_ci_zone"

## Example Use Cases

### Infrastructure Path Analysis
```bash
# How does a zone connect to servers?
create_relationship_graph cmdb_ci_zone cmdb_ci_server --shortest-path
# Output: Data Center Zone → Rack → Computer → Server

# What's the relationship between racks and servers?
create_relationship_graph cmdb_ci_rack cmdb_ci_server --shortest-path  
# Output: Rack → Computer → Server

# Compare different layout visualizations
create_relationship_graph cmdb_ci_zone cmdb_ci_server --layout all
```

### Class Hierarchy Understanding
```bash
# Direct inheritance relationship
create_relationship_graph cmdb_ci_computer cmdb_ci_server --shortest-path
# Output: Computer → Server (showing "parent of" relationship)

# Visualize with specific layout for clarity
create_relationship_graph cmdb_ci_computer cmdb_ci_server --layout planar
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
│   ├── data/                        # Mock data for testing (obfuscated)
│   │   ├── sys_db_object.json       # Test table definitions
│   │   ├── cmdb_rel_type.json       # Test relationship types
│   │   ├── cmdb_rel_type_suggest.json # Test CI relationships
│   │   ├── em_suggested_relation_type.json # Additional test relationships
│   │   └── sys_package.json         # Test package definitions
│   ├── test_graph_builder.py        # Tests for CMDBGraphBuilder class
│   └── test_cli.py                  # Tests for CLI functionality
├── pyproject.toml                   # Modern package configuration
├── pytest.ini                      # Pytest configuration
├── cmdb_analysis_YYYYMMDD_HHMMSS/   # Timestamped output directories
│   └── path_graphs/                 # Generated PNG graph visualizations
├── .env                             # Optional environment configuration
└── README.md                       # This documentation
```

## API Reference

### CMDBGraphBuilder Class

The main class for building and analyzing CMDB relationship graphs.

#### Methods

- `__init__(data_dir: str = None)` - Initialize with optional data directory path
- `build_graph() -> nx.DiGraph` - Build the complete graph from JSON files
- `find_all_paths_between_tables(source: str, target: str, max_paths: int = 10) -> List[Tuple[List[str], str]]` - Find paths between tables
- `visualize_table_graph(table_name: str, target_table: str = None, shortest_path_only: bool = False, layout: str = "auto") -> bool` - Generate visual graph
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
uv sync

# Run all tests
uv run pytest

# Run tests with verbose output
uv run pytest -v

# Run tests with coverage report
uv run pytest --cov=src/sn_cmdb_map --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_graph_builder.py

# Run specific test method
uv run pytest tests/test_cli.py::TestCLI::test_main_shortest_path
```

### Test Structure

```
tests/
├── __init__.py                    # Test package initialization
├── conftest.py                    # Shared fixtures and configuration
├── data/                          # Mock data for testing (obfuscated names)
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
- **CLI Interface**: Argument parsing, error handling, output formatting, layout options
- **Layout Algorithms**: All supported layout types and fallback behavior
- **Data Directory Configuration**: Command line, environment variables, .env files
- **Error Handling**: Missing files, invalid data, visualization failures
- **Data Processing**: Table loading, relationship processing, package handling

## Development

### Key Features Implemented

1. **Python Library Structure**: Proper package organization with `src/` layout
2. **Class Hierarchy Integration**: Adds inheritance relationships from `super_class` field
3. **Multiple Layout Algorithms**: 10 different graph layout options with intelligent fallbacks
4. **Smart Root Positioning**: Automatic positioning of source tables in upper-left area
5. **Flexible Data Sources**: Support for custom directories, environment variables, .env files
6. **Visual Distinction**: Different line styles for CI vs hierarchy relationships  
7. **Enhanced Path Finding**: Includes inheritance chains in path discovery
8. **Dual Interface**: Both command-line tool and Python API
9. **Clean Output**: Minimal console output showing only discovered paths
10. **Timestamped Output**: Each run creates dated directories to preserve results
11. **Comprehensive Testing**: 32 unit tests covering all functionality

### Technical Details

- **Graph Library**: NetworkX for directed graph operations
- **Visualization**: Matplotlib for PNG generation with custom styling
- **Coordinate Processing**: NumPy for efficient layout transformations
- **Layout Algorithms**: Auto-selection with graceful fallbacks
- **Node Attributes**: Includes table metadata, package info, inheritance data
- **Edge Attributes**: Distinguishes CI relationships from hierarchy relationships
- **Environment Configuration**: python-dotenv for .env file support

### Dependencies

- **matplotlib>=3.5.0**: Graph visualization and PNG export
- **networkx>=2.8**: Graph data structure and algorithms
- **networkx-viewer>=0.3.1**: Interactive graph viewing (optional)
- **python-dotenv>=0.19.0**: Environment variable loading from .env files
- **numpy>=1.21.0**: Efficient array operations for coordinate transformations

## Data Export from ServiceNow

To export the required JSON files from ServiceNow:

1. Navigate to **System Definition > Tables**
2. For each required table, export records as JSON
3. Ensure all fields are included in the export
4. Place JSON files in your chosen data directory

Required exports:
- `sys_db_object` → `sys_db_object.json`
- `cmdb_rel_type` → `cmdb_rel_type.json`  
- `cmdb_rel_type_suggest` → `cmdb_rel_type_suggest.json`
- `em_suggested_relation_type` → `em_suggested_relation_type.json`
- `sys_package` → `sys_package.json` (optional)

## License

This project is provided as-is for educational and analysis purposes. Ensure you have proper authorization to analyze ServiceNow data from your organization.