import subprocess
import sys
import os

def create_venv(venv_name):
    """
    Create a virtual environment.
    """
    try:
        subprocess.check_call([sys.executable, '-m', 'venv', venv_name])
        print(f"Virtual environment {venv_name} created successfully.")
    except subprocess.CalledProcessError:
        print(f"Error creating virtual environment {venv_name}.")
        sys.exit(1)

def activate_venv(venv_name):
    """
    Activate the virtual environment on Windows.
    """
    venv_path = os.path.join(venv_name, 'Scripts')
    activate_script = os.path.join(venv_path, 'activate.bat')

    try:
        subprocess.check_call([activate_script], shell=True)
        print(f"Virtual environment {venv_name} activated.")
    except subprocess.CalledProcessError:
        print(f"Error activating virtual environment {venv_name}.")
        sys.exit(1)


def install_dependencies(venv_name, requirements_file):
    """
    Install dependencies from requirements.txt file.
    """
    venv_path = os.path.join(venv_name, 'bin' if os.name != 'nt' else 'Scripts')
    pip_path = os.path.join(venv_path, 'pip')
    
    try:
        subprocess.check_call([pip_path, 'install', '-r', requirements_file])
        print(f"Dependencies installed successfully.")
    except subprocess.CalledProcessError:
        print(f"Error installing dependencies.")
        sys.exit(1)

if __name__ == '__main__':
    # Define the virtual environment name
    venv_name = 'env'

    # Create virtual environment
    create_venv(venv_name)

    # Activate virtual environment
    activate_venv(venv_name)

    # Install dependencies from requirements.txt
    install_dependencies(venv_name, 'requirements.txt')
