# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python library named "sn-cmdb-map" that creates directed graph visualizations of ServiceNow CMDB (Configuration Management Database) table relationships using NetworkX. The project processes ServiceNow export data to map how different CMDB tables relate to each other through both CI relationships and class inheritance hierarchies.

## Development Setup

### Python Requirements
- Python 3.8+ (as specified in pyproject.toml)
- Uses uv for package management
- Key dependencies: networkx for graph operations, matplotlib for visualizations

### Package Installation

```bash
# Install dependencies
uv sync

# Install the package to enable the script
uv pip install -e .
```

### Common Commands

**Running the application:**
```bash
# Main CLI application (installed script)
uv run create_relationship_graph table_e table_c --shortest-path

# Alternative: Run as module
uv run python -m sn_cmdb_map table_e table_c --shortest-path

# Find all paths between tables (not just shortest)
uv run create_relationship_graph table_e table_c

# Specify data directory containing JSON files
uv run create_relationship_graph table_e table_c --data-dir /path/to/json/files

# Use environment variable for data directory
export CMDB_DATA_DIR=/path/to/json/files
uv run create_relationship_graph table_e table_c

# Use .env file for configuration
echo "CMDB_DATA_DIR=/path/to/json/files" > .env
uv run create_relationship_graph table_e table_c

# Specify layout algorithm
uv run create_relationship_graph table_e table_c --layout spring

# Generate graphs with all available layouts
uv run create_relationship_graph table_e table_c --layout all
```

**Package management:**
```bash
# Install dependencies
uv sync

# Add new dependencies
uv add <package-name>

# Add dev dependencies  
uv add --dev <package-name>
```

**Testing:**
```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=src/sn_cmdb_map --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_graph_builder.py
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
└── README.md                       # Complete documentation
```

## Architecture Notes

### Core Components

1. **CMDBGraphBuilder class** (`src/sn_cmdb_map/graph_builder.py`):
   - Loads table metadata, relationship definitions, and package information
   - Builds directed NetworkX graph from relationship data
   - Provides visualization capabilities with PNG export
   - Offers path finding methods between tables including inheritance chains
   - Generates visual graphs with human-readable labels and dual edge types

2. **CLI Interface** (`src/sn_cmdb_map/cli.py`):
   - Simplified command-line interface focused on path finding
   - Required arguments for source and target tables
   - Optional shortest-path flag
   - Timestamped output directories

### Simplified Interface

The project has been simplified to focus specifically on path finding between two tables:

- **Required**: `SOURCE_TABLE` and `TARGET_TABLE` as positional arguments
- **Optional**: `--shortest-path` to show only the shortest path
- **Optional**: `--data-dir` to specify directory containing JSON data files
- **Optional**: `--layout` to specify graph layout algorithm or 'all' for multiple layouts
- **Environment**: `CMDB_DATA_DIR` environment variable for data directory
- **Configuration**: `.env` file support for setting environment variables
- **Output**: Visual PNG graphs showing the relationship paths with timestamped directories

### Graph Structure

- **Nodes**: Tables with attributes (label, super_class, scope, package, etc.)
- **Edges**: Two types:
  - **CI Relationships**: Solid gray lines (e.g., "Relation 1", "Relation 2")
  - **Class Hierarchy**: Dotted blue lines ("parent of" relationships)
- **Direction**: Parent→Child relationships based on hierarchy
- **Layout**: Uses planar layout when possible, with intelligent fallbacks

### Data Requirements

The tool requires JSON files with table definitions, relationship types, and relationship mappings:

- `sys_db_object.json` - Table definitions with inheritance hierarchy
- `cmdb_rel_type.json` - Relationship type definitions  
- `cmdb_rel_type_suggest.json` - CI relationship mappings
- `em_suggested_relation_type.json` - Additional relationship mappings
- `sys_package.json` - Package information

**Data Directory Configuration (priority order):**
1. `--data-dir` command line option
2. `CMDB_DATA_DIR` environment variable
3. `.env` file with `CMDB_DATA_DIR` setting
4. Current working directory (default)

**Graph Layout Options:**
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

**Layout Positioning:**
- For path graphs between two tables, the source (root) table is automatically positioned in the upper-left area
- The layout algorithm positions nodes naturally, then the entire graph is translated to place the source table optimally
- This provides consistent, intuitive orientation regardless of the underlying layout algorithm used

For testing, obfuscated mock data is used with:
- Tables named as letters (`table_a`, `table_b`, etc.)
- Relationships named as numbers (`rel_type_1`, `rel_type_2`, etc.)
- Generic package names (`pkg_x`)

### Key Features Implemented

1. **Python Library Structure**: Proper package organization with `src/` layout
2. **Class Hierarchy Integration**: Adds inheritance relationships from `super_class` field
3. **Visual Distinction**: Different line styles for CI vs hierarchy relationships  
4. **Enhanced Path Finding**: Includes inheritance chains in path discovery
5. **Dual Interface**: Both command-line tool and Python API
6. **Clean Output**: Minimal console output showing only discovered paths
7. **Timestamped Output**: Each run creates dated directories to preserve results
8. **Comprehensive Testing**: Unit tests with obfuscated mock data

### Testing

- **25 unit tests** covering all functionality
- **Mock data** using obfuscated names to avoid ServiceNow-specific terminology
- **Comprehensive coverage** of graph building, CLI, and error handling
- **Pytest configuration** with fixtures and proper test structure

## Usage Notes

The library provides a focused interface for finding relationship paths between tables, showing both business relationships and object-oriented inheritance chains in visual graphs.