"""
Backward compatibility wrapper for niobium CLI.
The main CLI logic has been moved to niobium.cli module.
"""
from niobium.cli import main

if __name__ == "__main__":
    main()