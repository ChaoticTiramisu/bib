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
    except subprocess.CalledProcessError as e:
        print(f"Error creating virtual environment '{venv_name}': {e}")
        sys.exit(1)

def activate_venv(venv_name):
    """
    Simulate activation of the virtual environment.
    """
    if os.name == 'nt':
        # Windows: use the activate.bat script
        activate_script = os.path.join(venv_name, 'Scripts', 'activate.bat')
        command = f'cmd.exe /c "{activate_script}"'
    else:
        # POSIX (Linux, macOS): use the activate script inside bin
        activate_script = os.path.join(venv_name, 'bin', 'activate')
        command = f'source {activate_script} && echo "Activated"'
    
    if not os.path.exists(activate_script):
        print(f"Activation script not found: {activate_script}")
        sys.exit(1)

    try:
        output = subprocess.check_output(command, shell=True, text=True)
        print(f"Virtual environment '{venv_name}' activation simulated: {output.strip()}")
    except subprocess.CalledProcessError as e:
        print(f"Error activating virtual environment '{venv_name}': {e}")
        sys.exit(1)

def install_dependencies(venv_name, requirements_file):
    """
    Install dependencies from the requirements.txt file.
    """
    # Determine the correct folder (Windows: Scripts, Linux: bin)
    venv_dir = 'Scripts' if os.name == 'nt' else 'bin'
    pip_path = os.path.join(venv_name, venv_dir, 'pip')

    if not os.path.exists(pip_path):
        print(f"Pip not found in virtual environment: {pip_path}")
        print("Attempting to install pip...")
        try:
            subprocess.check_call([os.path.join(venv_name, venv_dir, 'python'), '-m', 'ensurepip'])
            subprocess.check_call([os.path.join(venv_name, venv_dir, 'python'), '-m', 'pip', 'install', '--upgrade', 'pip'])
            print("Pip installed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Error installing pip: {e}")
            sys.exit(1)

    if not os.path.exists(requirements_file):
        print(f"Requirements file not found: {requirements_file}")
        sys.exit(1)

    try:
        subprocess.check_call([pip_path, 'install', '-r', requirements_file])
        print("Dependencies installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        sys.exit(1)

if __name__ == '__main__':
    venv_name = 'env'
    requirements_file = 'requirements.txt'

    # Create the virtual environment.
    create_venv(venv_name)

    # "Activate" the virtual environment (for demonstration only).
    activate_venv(venv_name)

    # Install dependencies using the venv's pip.
    install_dependencies(venv_name, requirements_file)
