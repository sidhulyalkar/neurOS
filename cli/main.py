# neuros/cli/main.py
"""
neurOS CLI Main Entry Point
"""

def main():
    """Main entry point"""
    from .complete_commands import main as complete_main
    complete_main()

if __name__ == "__main__":
    main()