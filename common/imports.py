# common/imports.py
"""
Centralized imports for the Altris QC Neware Reader.
Import this module to get access to commonly used libraries.
"""
# Standard library imports
import os
import sys
import time
import logging
import logging.config  # Add this explicit import
import hashlib
import pickle
import re
from pathlib import Path
from io import StringIO
import datetime
from typing import Dict, List, Optional, Tuple, Union, Any

# Third-party imports
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import yaml
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import NewareNDA  # Make sure this package is actually installed