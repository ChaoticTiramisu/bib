# Importeren van subprocess(bestanden laten uitvoeren), sys(systeem) en os(operating system(routes))
import subprocess
import sys
import os

# maken van virtuele omgeving, proberen met try and except voor error op te vangen.
def create_venv(venv_name):
    """
    Creëer een virtual environment.
    """
    try:
        # voert dit commando uit voor jou, voor het aanmaken van een virtuele omgeving en print message met naam van venv
        subprocess.check_call([sys.executable, '-m', 'venv', venv_name])
        print(f"Virtual environment {venv_name} succesvol gecreëerd.")
        # bij error print hij, dat er een error is gebeurd, sys.exit, hij gaat uit dit proces
    except subprocess.CalledProcessError:
        print(f"Error creating virtual environment {venv_name}.")
        sys.exit(1)
# activeren van je virtuele omgeving
def activate_venv(venv_name):
    """
    Activeerd de virtual environment op Windows.
    """
    # het zoekt het pad voor de venv en dan gaat hij in de script
    venv_path = os.path.join(venv_name, 'Scripts')
    # in script folder, zoekt hij de route naar activate.bat in een variable
    activate_script = os.path.join(venv_path, 'activate.bat')
# runt bestand activate script, print nadien als het geactiveerd is, indien errror sys.exit
    try:
        subprocess.check_call([activate_script], shell=True)
        print(f"Virtual environment {venv_name} geactiveerd.")
    except subprocess.CalledProcessError:
        print(f"Error activating virtual environment {venv_name}.")
        sys.exit(1)

# alle dependencies(afhankelijk als het programma gaat runnen bv. random is een dependecie) installeren
def install_dependencies(venv_name, requirements_file):
    """
    Installeert dependencies van de requirements.txt file.
    """
    # zelfde als script zie hierboven, als name niet gelijk is aan nt gaat hij naar script folder
    venv_path = os.path.join(venv_name, 'bin' if os.name != 'nt' else 'Scripts')
    #pip is package installeren voor python en de route naar het bestand
    pip_path = os.path.join(venv_path, 'pip')
    
    # hij runt de pip en installeert alle depencendies indien error stop hij weer en print code
    try:
        subprocess.check_call([pip_path, 'install', '-r', requirements_file])
        print(f"Dependencies installed successfully.")
    except subprocess.CalledProcessError:
        print(f"Error installing dependencies.")
        sys.exit(1)

# altijd nodig voor bestand te runnen.
if __name__ == '__main__':
    
    venv_name = 'env'

    # alle definities worden hier uitgevoerd.
    create_venv(venv_name)

    
    activate_venv(venv_name)

    
    install_dependencies(venv_name, 'requirements.txt')
