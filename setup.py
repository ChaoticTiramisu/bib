import subprocess
import sys
import os

def create_venv(venv_name):
    """
    Create a virtual environment.
    """
    try:
        subprocess.check_call([sys.executable, '-m', 'venv', venv_name])
        print(f"Virtual environment '{venv_name}' successfully created.")
    except subprocess.CalledProcessError:
        print(f"Error creating virtual environment '{venv_name}'.")
        sys.exit(1)

def activate_venv(venv_name):
    """
    "Activate" the virtual environment.
    Note: Activating a venv in a subprocess does not change the parent shell’s environment.
    For our purposes, we only simulate activation. The install_dependencies function uses the correct venv path.
    """
    if os.name == 'nt':
        # Windows: use the activate.bat script
        activate_script = os.path.join(venv_name, 'Scripts', 'activate.bat')
        command = [activate_script]
    else:
        # POSIX (Linux, macOS): use the activate script inside bin
        activate_script = os.path.join(venv_name, 'bin', 'activate')
        # Running 'source' in a subprocess won't affect the parent process.
        # We can run it just to check if the script exists.
        command = ['bash', '-c', f'source {activate_script} && echo "Activated"']
    try:
        output = subprocess.check_output(command, shell=False)
        print(f"Virtual environment '{venv_name}' activation simulated: {output.decode().strip()}")
    except subprocess.CalledProcessError:
        print(f"Error activating virtual environment '{venv_name}'.")
        sys.exit(1)

def install_dependencies(venv_name, requirements_file):
    """
    Install dependencies from the requirements.txt file.
    """
    # Determine the correct folder (Windows: Scripts, Linux: bin)
    venv_dir = 'Scripts' if os.name == 'nt' else 'bin'
    pip_path = os.path.join(venv_name, venv_dir, 'pip')
    
    try:
        subprocess.check_call([pip_path, 'install', '-r', requirements_file])
        print("Dependencies installed successfully.")
    except subprocess.CalledProcessError:
        print("Error installing dependencies.")
        sys.exit(1)

if __name__ == '__main__':
    venv_name = 'env'
    
    # Create the virtual environment.
    create_venv(venv_name)
    
    # "Activate" the virtual environment (for demonstration only).
    activate_venv(venv_name)
    
    # Install dependencies using the venv's pip.
    install_dependencies(venv_name, 'requirements.txt')
