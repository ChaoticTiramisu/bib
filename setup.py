import subprocess
import sys
import os

def create_venv(venv_name):
    """
    Creëer een virtual environment.
    """
    try:
        subprocess.check_call([sys.executable, '-m', 'venv', venv_name])
        print(f"Virtual environment {venv_name} succesvol gecreëerd.")
    except subprocess.CalledProcessError:
        print(f"Error creating virtual environment {venv_name}.")
        sys.exit(1)

def activate_venv(venv_name):
    """
    Activeerd de virtual environment op Windows.
    """
    venv_path = os.path.join(venv_name, 'Scripts')
    activate_script = os.path.join(venv_path, 'activate.bat')

    try:
        subprocess.check_call([activate_script], shell=True)
        print(f"Virtual environment {venv_name} geactiveerd.")
    except subprocess.CalledProcessError:
        print(f"Error activating virtual environment {venv_name}.")
        sys.exit(1)


def install_dependencies(venv_name, requirements_file):
    """
    Installeert dependencies van de requirements.txt file.
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
    
    venv_name = 'env'

    
    create_venv(venv_name)

    
    activate_venv(venv_name)

    
    install_dependencies(venv_name, 'requirements.txt')
