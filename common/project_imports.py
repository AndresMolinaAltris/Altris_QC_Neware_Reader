# common/project_imports.py
"""
Internal project imports to avoid circular dependencies.
"""
# Import this instead of directly importing project modules
from features import Features
from cell_database import CellDatabase, find_active_mass
from data_import import extract_active_mass, extract_cell_id, extract_sample_name
from neware_plotter import NewarePlotter
from logger_configurator import configure_logging
from file_selector import FileSelector