"""
Utility module for suppressing known harmless warnings
in the Rush Royale Bot Python 3.13 environment.
"""

import warnings

def suppress_harmless_warnings():
    """
    Suppress known harmless warnings that don't affect functionality.
    
    Currently suppresses:
    - pkg_resources deprecation warning from adbutils
    """
    warnings.filterwarnings(
        "ignore", 
        message="pkg_resources is deprecated", 
        category=UserWarning
    )
    
def configure_warnings():
    """Configure warning filters for clean bot operation."""
    suppress_harmless_warnings()
