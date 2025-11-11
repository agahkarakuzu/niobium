"""
Backward compatibility wrapper for niobium CLI.
The main CLI logic has been moved to anki_niobium.cli module.
"""
from anki_niobium.cli import main

if __name__ == "__main__":
    main()