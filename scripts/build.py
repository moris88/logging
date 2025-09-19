# Run this script from the project root directory (e.g., python scripts/build.py)
import PyInstaller.__main__
import os
import shutil
import customtkinter

if __name__ == "__main__":
    app_name = "CalendarLogger"
    spec_file = f"{app_name}.spec"
    build_dir = "build"

    # Trova il percorso degli asset di customtkinter
    customtkinter_path = os.path.dirname(customtkinter.__file__)
    assets_path = os.path.join(customtkinter_path, "assets")

    # Configura i parametri per PyInstaller
    params = [
        'main.py',
        f'--name={app_name}',
        '--windowed',
        '--noconfirm',
        f'--add-data={assets_path}{os.pathsep}customtkinter/assets/'
    ]

    print(f"Avvio di PyInstaller...")
    PyInstaller.__main__.run(params)

    print("\n--- Pulizia dei file di build ---")
    try:
        if os.path.isdir(build_dir):
            shutil.rmtree(build_dir)
            print(f"- Cartella '{build_dir}' rimossa.")
        
        if os.path.exists(spec_file):
            os.remove(spec_file)
            print(f"- File '{spec_file}' rimosso.")
    except Exception as e:
        print(f"Errore durante la pulizia: {e}")
    
    print("---------------------------------")
    print(f"\nBuild completata. L'applicazione si trova nella cartella 'dist/{app_name}'.")
