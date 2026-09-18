<#
===============================================================================
FILE: create_shortcut.ps1
===============================================================================
WHAT IS THIS FILE FOR? (Intent & Big Picture)
Not everyone wants to open a terminal or type command lines to run their
Knowledge Management library!

This PowerShell automation script automatically creates 4 friendly desktop
shortcuts on your Windows Desktop (with custom Windows shell icons) so you can
run each step of the pipeline with a single double-click directly from your desktop:
  1. Run Full Pipeline (End-to-End)
  2. Ingest Books Only
  3. Consolidate Taxonomy Only
  4. Render Markdown Index Only

-------------------------------------------------------------------------------
KEY PROCESSES CARRIED OUT:
1. Obtains the current user's Windows Desktop directory path.
2. Uses the Windows Script Host COM object (`WScript.Shell`) to generate `.lnk` shortcut files.
3. Sets target path, launch arguments, working directory, and icon for each shortcut.
4. Saves the shortcuts to the desktop.
===============================================================================
#>

# Initialize the Windows Script Host COM object to create .lnk shortcuts
$WshShell = New-Object -ComObject WScript.Shell

# Get the absolute path to the current user's Desktop folder
$DesktopPath = [System.Environment]::GetFolderPath('Desktop')

# Set the working directory where the library project is located
$WorkDir = "d:\Firedancerx\OneDrive\My Library - 2021"

# Define the 4 shortcuts with their names, target scripts, descriptions, and icon resources
$Shortcuts = @(
    @{
        Name = "1. Run Full Pipeline.lnk"
        Script = "scripts\1_Full_Pipeline.cmd"
        Desc = "Run full taxonomy pipeline end-to-end"
        Icon = "shell32.dll,43"
    },
    @{
        Name = "2. Ingest Books Only.lnk"
        Script = "scripts\2_Ingest_Books.cmd"
        Desc = "Scan and queue new books"
        Icon = "shell32.dll,3"
    },
    @{
        Name = "3. Consolidate Taxonomy.lnk"
        Script = "scripts\3_Consolidate_Taxonomy.cmd"
        Desc = "Re-align and consolidate leader node hierarchy"
        Icon = "shell32.dll,130"
    },
    @{
        Name = "4. Render Markdown Index.lnk"
        Script = "scripts\4_Render_Markdown.cmd"
        Desc = "Re-render inline links and master index"
        Icon = "shell32.dll,71"
    }
)

# Loop through each shortcut definition and save it on the user's Desktop
foreach ($item in $Shortcuts) {
    $ShortcutPath = Join-Path -Path $DesktopPath -ChildPath $item.Name
    $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = "cmd.exe"
    $Shortcut.Arguments = "/c `"$WorkDir\$($item.Script)`""
    $Shortcut.WorkingDirectory = $WorkDir
    $Shortcut.WindowStyle = 1
    $Shortcut.Description = $item.Desc
    $Shortcut.IconLocation = $item.Icon
    $Shortcut.Save()
    Write-Host "Created Desktop Shortcut: $($item.Name)"
}
