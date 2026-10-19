# BrainOS: the one line to start, on Windows. Paste this into PowerShell:
#
#   irm https://raw.githubusercontent.com/adrianshedden/brainos-core/main/start.ps1 | iex
#
# What it does, and nothing more (the same steps as start.sh on a Mac):
#   1. Downloads the BrainOS kit from GitHub as one zip file (no git needed).
#   2. Makes your brain folder: Documents\brain, or your home folder's brain folder when Documents is
#      copied online (OneDrive and the like), so your brain stays on this computer. A brain made
#      earlier is found and used again.
#   3. Puts the kit in <brain>\kit, replacing an older kit there. Your own files are never touched.
#   4. Checks for Python (py, then python). If it is missing, it says how to get it from python.org.
#      It installs nothing.
#   5. If Claude Code, Codex or OpenCode is on this computer, starts it in the brain folder with the
#      set-up line. If not, opens the folder and prints the line to paste into your AI app.
# It needs no administrator rights, sends nothing about you anywhere, and changes nothing outside the
# brain folder except a temporary download folder, which it deletes. It never closes your window.
#
# Settings for testing (nobody else needs these):
#   BRAINOS_REF        the kit branch to download (default: main)
#   BRAINOS_ZIP        a kit zip to use instead of downloading: a file on this computer, or a web address
#   BRAINOS_DIR        the brain folder to use instead of the default
#   BRAINOS_DOCUMENTS  the Documents folder to look in instead of this computer's own

& {
    Set-StrictMode -Version Latest
    $ErrorActionPreference = 'Stop'
    $ProgressPreference = 'SilentlyContinue'

    # The AI-app line: the same words everywhere (SETUP.md, README, both start scripts, the tests).
    $Line = 'Set up my brain from the BrainOS kit at github.com/adrianshedden/brainos-core (read its SETUP.md first and follow it). Ask me before you change anything, work only in my brain folder, and never share, upload or post my files.'
    $RepoZip = 'https://github.com/adrianshedden/brainos-core/archive/refs/heads'
    $Allowed = @('kit', 'exports', 'setup.yaml', '.DS_Store', 'desktop.ini', '.git')

    function Say([string]$Text) { Write-Host $Text }

    function Show-Line([string]$Lead) {
        Say ''
        Say $Lead
        Say ''
        Say $Line
        Say ''
    }

    # Which online service copies <folder> (OneDrive...), or '' when it stays on this computer.
    function Get-SyncedService([string]$Folder) {
        foreach ($root in @($env:OneDrive, $env:OneDriveConsumer, $env:OneDriveCommercial)) {
            if ($root -and $Folder.StartsWith($root, [StringComparison]::OrdinalIgnoreCase)) { return 'OneDrive' }
        }
        if ($Folder -match 'OneDrive') { return 'OneDrive' }
        if ($Folder -match 'iCloud') { return 'iCloud' }
        if ($Folder -match 'Dropbox') { return 'Dropbox' }
        if ($Folder -match 'Google Drive') { return 'Google Drive' }
        return ''
    }

    # Is Python 3.8 or newer here as <Command>? The Microsoft Store stand-in for python fails this check.
    function Test-Python([string]$Command) {
        if (-not (Get-Command $Command -ErrorAction SilentlyContinue)) { return $false }
        try {
            $out = & $Command -c 'import sys; print(sys.version_info >= (3, 8))' 2>$null
            return ($LASTEXITCODE -eq 0) -and ("$out".Trim() -eq 'True')
        } catch {
            return $false
        }
    }

    function Open-Folder([string]$Folder) {
        try {
            if ($env:OS -eq 'Windows_NT') { Start-Process -FilePath 'explorer.exe' -ArgumentList "`"$Folder`"" }
            elseif (Get-Command 'open' -ErrorAction SilentlyContinue) { & open $Folder | Out-Null }
        } catch { }
    }

    Say 'BrainOS: getting your brain folder ready. This takes about a minute.'

    # 1. Choose the brain folder: the one asked for, else a brain made earlier, else Documents\brain
    #    unless Documents is copied online, else the brain folder in your home folder.
    $HomeDir = if ($env:USERPROFILE) { $env:USERPROFILE } else { $HOME }
    $Docs = if ($env:BRAINOS_DOCUMENTS) { $env:BRAINOS_DOCUMENTS } else { [Environment]::GetFolderPath('MyDocuments') }
    if (-not $Docs) { $Docs = Join-Path $HomeDir 'Documents' }
    $HomeBrain = Join-Path $HomeDir 'brain'
    $Brain = $null
    if ($env:BRAINOS_DIR) {
        $Brain = $env:BRAINOS_DIR
    } else {
        foreach ($earlier in @((Join-Path $Docs 'brain'), $HomeBrain)) {
            if ((Test-Path -LiteralPath (Join-Path $earlier 'brain.yaml')) -or
                (Test-Path -LiteralPath (Join-Path $earlier 'kit') -PathType Container)) {
                $Brain = $earlier
                break
            }
        }
        if (-not $Brain) {
            $Brain = $HomeBrain
            if (Test-Path -LiteralPath $Docs -PathType Container) {
                $service = Get-SyncedService $Docs
                if ($service) {
                    Say "Your Documents folder is copied online by $service, so your brain goes in $HomeBrain instead, which stays on this computer."
                } else {
                    $Brain = Join-Path $Docs 'brain'
                }
            }
        }
    }

    # Stop, changing nothing, when that folder already holds someone's own files and is not a brain.
    if ((Test-Path -LiteralPath $Brain) -and -not (Test-Path -LiteralPath $Brain -PathType Container)) {
        Say "There is already a file called $Brain, so nothing was changed. Move or rename it, then paste the line again."
        return
    }
    if ((Test-Path -LiteralPath $Brain -PathType Container) -and -not (Test-Path -LiteralPath (Join-Path $Brain 'brain.yaml'))) {
        $others = @(Get-ChildItem -LiteralPath $Brain -Force | Where-Object { $Allowed -notcontains $_.Name })
        if ($others.Count -gt 0) {
            Say "There is already a folder at $Brain with other files in it, and it is not a brain. To keep those files safe, nothing was changed. Move or rename that folder, then paste the line again."
            return
        }
    }

    # 2. Download the kit and 3. put it in <brain>\kit. Only kit is replaced.
    Say 'Downloading the BrainOS kit...'
    $Ref = if ($env:BRAINOS_REF) { $env:BRAINOS_REF } else { 'main' }
    $Source = if ($env:BRAINOS_ZIP) { $env:BRAINOS_ZIP } else { "$RepoZip/$Ref.zip" }
    $Work = Join-Path ([IO.Path]::GetTempPath()) ('brainos-' + [guid]::NewGuid().ToString('N'))
    $Stage = $null
    $OldKit = $null
    New-Item -ItemType Directory -Path $Work | Out-Null
    try {
        $Zip = Join-Path $Work 'kit.zip'
        if (Test-Path -LiteralPath $Source -PathType Leaf) {
            Copy-Item -LiteralPath $Source -Destination $Zip
        } else {
            try {
                [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
            } catch { }
            try {
                Invoke-WebRequest -Uri $Source -OutFile $Zip -UseBasicParsing
            } catch {
                Say 'Could not download the BrainOS kit. Check this computer is online, then paste the line again.'
                return
            }
        }
        New-Item -ItemType Directory -Force -Path $Brain | Out-Null
        # Unzip inside the brain folder, so the kit moves into place without crossing drives.
        $Stage = Join-Path $Brain ".kit-new-$PID"
        try {
            Expand-Archive -LiteralPath $Zip -DestinationPath $Stage -Force
        } catch {
            Say 'The kit download was damaged. Paste the line again.'
            return
        }
        $tops = @(Get-ChildItem -LiteralPath $Stage -Directory)
        if (($tops.Count -ne 1) -or -not (Test-Path -LiteralPath (Join-Path $tops[0].FullName 'SETUP.md')) -or
            -not (Test-Path -LiteralPath (Join-Path $tops[0].FullName 'create_brain.py'))) {
            Say 'The download does not look like the BrainOS kit, so nothing was changed. Paste the line again.'
            return
        }
        $Kit = Join-Path $Brain 'kit'
        if (Test-Path -LiteralPath $Kit) {
            $OldKit = Join-Path $Brain ".kit-old-$PID"
            Move-Item -LiteralPath $Kit -Destination $OldKit
        }
        Move-Item -LiteralPath $tops[0].FullName -Destination $Kit
        if ($OldKit) {
            Remove-Item -LiteralPath $OldKit -Recurse -Force
            $OldKit = $null
        }
    } finally {
        Remove-Item -LiteralPath $Work -Recurse -Force -ErrorAction SilentlyContinue
        if ($Stage -and (Test-Path -LiteralPath $Stage)) { Remove-Item -LiteralPath $Stage -Recurse -Force -ErrorAction SilentlyContinue }
        # Stopped halfway through swapping the kit: put the old one back.
        if ($OldKit -and (Test-Path -LiteralPath $OldKit)) {
            if (Test-Path -LiteralPath (Join-Path $Brain 'kit')) { Remove-Item -LiteralPath $OldKit -Recurse -Force -ErrorAction SilentlyContinue }
            else { Move-Item -LiteralPath $OldKit -Destination (Join-Path $Brain 'kit') -ErrorAction SilentlyContinue }
        }
    }
    Say "Your brain folder is $Brain, and the kit is in its kit folder."

    # 4. Check for Python: py first (from python.org), then python. Installs nothing.
    $Python = $null
    foreach ($command in @('py', 'python')) {
        if (Test-Python $command) { $Python = $command; break }
    }
    if ($Python) {
        Say 'Python is ready.'
    } else {
        Say 'Python is not on this computer yet. The kit uses it to read your files. To get it, free:'
        Say '  1. Go to python.org/downloads and click the yellow Download button.'
        Say '  2. Open the file you downloaded. On its first screen, tick "Add python.exe to PATH", then click Install Now.'
        Say '  3. Close this window, open PowerShell again, and paste the same line.'
    }

    # 5. Start the first AI app found in the brain folder with the set-up line, or open the folder and
    #    print the line to paste.
    foreach ($app in @(@('claude', 'Claude Code'), @('codex', 'Codex'), @('opencode', 'OpenCode'))) {
        if (Get-Command $app[0] -ErrorAction SilentlyContinue) {
            Say "Starting $($app[1]) in your brain folder with the set-up line. Answer its questions there."
            Set-Location -LiteralPath $Brain
            if ($app[0] -eq 'opencode') { & opencode --prompt $Line } else { & $app[0] $Line }
            return
        }
    }
    Open-Folder $Brain
    Say 'Using the Claude app? Sign in inside the Claude app window. Signing in on the website does not sign in the app.'
    Show-Line "Next, open your AI app (for example the Claude app), choose the folder $Brain, and paste this line:"
}
