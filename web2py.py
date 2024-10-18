from __future__ import print_function
import os
import sys
from multiprocessing import freeze_support

def get_script_path():
    """Determine the script's directory."""
    if hasattr(sys, 'frozen'):
        # For frozen applications (like those created with PyInstaller)
        return os.path.dirname(os.path.abspath(sys.executable))
    elif '__file__' in globals():
        # For normal scripts
        return os.path.dirname(os.path.abspath(__file__))
    return os.getcwd()  # Fallback to current working directory

def parse_folder_argument():
    """Parse the folder argument from command line."""
    folder_index = None
    if '-f' in sys.argv:
        folder_index = sys.argv.index('-f')
    elif '--folder' in sys.argv:
        folder_index = sys.argv.index('--folder')

    if folder_index is not None and folder_index + 1 < len(sys.argv):
        return sys.argv[folder_index + 1]
    return None

def validate_folder(folder):
    """Validate the existence of the 'gluon' directory within the specified folder."""
    gluon_path = os.path.join(folder, 'gluon')
    if not os.path.isdir(gluon_path):
        print(f"{sys.argv[0]}: error: bad folder {folder}. Expected 'gluon' directory not found.", file=sys.stderr)
        sys.exit(1)

def update_feature():
    """Simulate the update feature for the Web2py application."""
    print("Updating Web2py...")
    
    # Display a flash message with a red background
    print("\033[41mUpdate Complete!\033[0m")  # ANSI escape code for red background

    # Change button text to "Restart"
    print("Button text changed to: Restart")

    # Display checklist for server restart
    display_checklist()

def display_checklist():
    """Display a checklist of tasks to perform between server shutdown and restart."""
    print("Checklist for Restart:")
    checklist = [
        "1. Clear sessions (required for 2.8.1+)",
        "2. Backup your database",
        "3. Check for any pending migrations",
        "4. Review the release notes for breaking changes"
    ]
    for item in checklist:
        print(item)

def main():
    """Main execution flow."""
    freeze_support()

    # Set the working directory
    path = get_script_path()
    folder = parse_folder_argument()

    if folder:
        folder = os.path.abspath(folder)
        validate_folder(folder)
        path = folder

    os.chdir(path)
    sys.path.insert(0, path)  # Add the path at the start of sys.path

    # Import after changing directory to ensure correct imports
    import gluon.widget

    # Coverage support if applicable
    if 'COVERAGE_PROCESS_START' in os.environ:
        try:
            import coverage
            coverage.process_startup()
        except ImportError:
            print('Coverage is not available', file=sys.stderr)

    # Start services
    gluon.widget.start()

    # Simulate the update feature when the script runs
    update_feature()

if __name__ == '__main__':
    main()
