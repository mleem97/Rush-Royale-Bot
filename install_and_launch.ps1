if (Test-Path -Path ".installed") {
    # Check if requirements are satisfied
    & .\bot_env\Scripts\Activate.ps1
    $requirements = Get-Content -Path "requirements.txt"
    $installed = pip freeze
    $missing = $requirements | Where-Object { $installed -notcontains $_ }
    
    if ($missing.Count -eq 0) {
        # Launch the application
        python Src\gui.py
    } else {
        # Install missing requirements
        pip install -r requirements.txt
        # Launch the application
        python Src\gui.py
    }
} else {
    # Installation process
    python -m venv .bot_env
    & $env:LOCALAPPDATA\Programs\Python\Python39\python -m venv .bot_env
    # if this does not work add the path to where your python installation is located.
    & .\bot_env\Scripts\activate.bat
    pip install -r requirements.txt
    # Create .installed file to indicate installation is complete
    New-Item -ItemType File -Path ".installed" -Force
    # Launch the application
    python Src\gui.py
}
