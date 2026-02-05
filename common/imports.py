# common/imports.py
"""
Centralized imports for the Altris QC Neware Reader.
Supports lazy loading of heavy dependencies to improve startup time.
"""

# ============================================================================
# EAGER IMPORTS (always loaded - fast, essential)
# ============================================================================
import os
import sys
import time
import logging
import logging.config
import hashlib
import pickle
import re
import traceback
from pathlib import Path
from io import StringIO
import datetime
from typing import Dict, List, Optional, Tuple, Union, Any

import yaml

# ============================================================================
# LAZY IMPORT CACHE (module-level singletons)
# ============================================================================
_cached_modules = {}


def _get_lazy_module(module_name, import_statement):
    """Get a lazily-loaded module, caching it for subsequent calls."""
    if module_name not in _cached_modules:
        # Use exec to evaluate the import statement dynamically
        namespace = {}
        exec(import_statement, namespace)
        # Extract the last assigned variable (the actual module/object)
        _cached_modules[module_name] = namespace[module_name.split('.')[-1]]
    return _cached_modules[module_name]


# ============================================================================
# LAZY MODULE ACCESSORS (triggered on first access)
# ============================================================================
class _LazyModuleProxy:
    """Proxy that lazily loads a module on first attribute access."""

    def __init__(self, module_name, import_stmt):
        self._module_name = module_name
        self._import_stmt = import_stmt
        self._module = None

    def _load(self):
        if self._module is None:
            self._module = _get_lazy_module(self._module_name, self._import_stmt)
        return self._module

    def __getattr__(self, name):
        if name.startswith('_'):
            return super().__getattribute__(name)
        return getattr(self._load(), name)

    def __call__(self, *args, **kwargs):
        return self._load()(*args, **kwargs)


# Create lazy proxy objects for heavy dependencies
np = _LazyModuleProxy('np', 'import numpy as np')
pd = _LazyModuleProxy('pd', 'import pandas as pd')
plt = _LazyModuleProxy('plt', 'import matplotlib.pyplot as plt')
gridspec = _LazyModuleProxy('gridspec', 'import matplotlib.gridspec as gridspec')
tk = _LazyModuleProxy('tk', 'import tkinter as tk')
Figure = _LazyModuleProxy('Figure', 'from matplotlib.figure import Figure')
filedialog = _LazyModuleProxy('filedialog', 'from tkinter import filedialog')
ttk = _LazyModuleProxy('ttk', 'from tkinter import ttk')
messagebox = _LazyModuleProxy('messagebox', 'from tkinter import messagebox')
NewareNDA = _LazyModuleProxy('NewareNDA', 'import NewareNDA')


def _get_FigureCanvasTkAgg():
    """Get FigureCanvasTkAgg class (lazy-loaded on first call)."""
    return _get_lazy_module('FigureCanvasTkAgg',
                           'from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg')


def _get_NavigationToolbar2Tk():
    """Get NavigationToolbar2Tk class (lazy-loaded on first call)."""
    return _get_lazy_module('NavigationToolbar2Tk',
                           'from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk')


# Create lazy proxies for matplotlib backend classes
FigureCanvasTkAgg = _LazyModuleProxy('FigureCanvasTkAgg',
                                     'from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg')
NavigationToolbar2Tk = _LazyModuleProxy('NavigationToolbar2Tk',
                                        'from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk')