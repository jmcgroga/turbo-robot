"""
ServiceNow CMDB Table Relationship Mapper

A Python library for creating directed graph visualizations of ServiceNow 
Configuration Management Database (CMDB) table relationships, showing both 
CI relationships and class inheritance hierarchies.
"""

from .graph_builder import CMDBGraphBuilder
from .cli import main

__version__ = "0.1.0"
__author__ = "ServiceNow CMDB Mapper"
__email__ = ""

__all__ = [
    "CMDBGraphBuilder",
    "main",
]