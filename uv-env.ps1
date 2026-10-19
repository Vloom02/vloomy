# Cargalo antes de usar uv en este proyecto:  . .\uv-env.ps1
# shortcut: uv vive dentro del proyecto porque la app de Claude (MSIX) virtualiza AppData y rompe los Python de uv; si usás uv solo desde tu terminal podés ignorarlo.
$root = $PSScriptRoot
$env:UV_PYTHON_INSTALL_DIR = "$root\.uv\python"
$env:UV_CACHE_DIR = "$root\.uv\cache"
$env:UV_TOOL_DIR = "$root\.uv\tools"
$env:UV_TOOL_BIN_DIR = "$root\.uv\bin"
$env:UV_PYTHON_PREFERENCE = 'only-managed'
$env:ANONYMIZED_TELEMETRY = 'false'
