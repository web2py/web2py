from __future__ import print_function
import os
import sys
from multiprocessing import freeze_support

def get_script_path():
    """Determine the script's directory."""
    if hasattr(sys, 'frozen'):
        return os.path.dirname(os.path.abspath(sys.executable))  # For frozen applications
    elif '__file__' in globals():
        return os.path.dirname(os.path.abspath(__file__))  # For normal scripts
    else:
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
    if not os.path.isdir(os.path.join(folder, 'gluon')):
        print(f"{sys.argv[0]}: error: bad folder {folder}", file=sys.stderr)
        sys.exit(1)

def update_feature():
    """Simulate the update feature for the Web2py application."""
    # Here you would implement the logic for updating the application
    print("Updating Web2py...")
    
    # Display a flash message
    print("\033[41mUpdate Complete!\033[0m")  # Red background for flash message

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
    sys.path = [path] + [p for p in sys.path if p != path]

    # Import after changing directory
    import gluon.widget

    # Coverage support
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