#!/bin/sh
# BrainOS: the one line to start, on a Mac (or Linux) computer. Paste this into Terminal:
#
#   curl -fsSL https://raw.githubusercontent.com/adrianshedden/brainos-core/main/start.sh | sh
#
# What it does, and nothing more:
#   1. Downloads the BrainOS kit from GitHub as one zip file (no git needed).
#   2. Makes your brain folder: Documents/brain, or ~/brain when Documents is copied online
#      (iCloud, OneDrive and the like), so your brain stays on this computer. A brain made
#      earlier is found and used again.
#   3. Puts the kit in <brain>/kit, replacing an older kit there. Your own files are never touched.
#   4. Checks for Python. If it is missing, it says how to get it from python.org. It installs nothing.
#   5. If Claude Code, Codex or OpenCode is on this computer, starts it in the brain folder with the
#      set-up line. If not, opens the folder and prints the line to paste into your AI app.
# It needs no admin password, sends nothing about you anywhere, and changes nothing outside the brain
# folder except a temporary download folder, which it deletes.
#
# Settings for testing (nobody else needs these):
#   BRAINOS_REF  the kit branch to download (default: main)
#   BRAINOS_ZIP  a kit zip to use instead of downloading: a file on this computer, or a web address
#   BRAINOS_DIR  the brain folder to use instead of the default
#   BRAINOS_TTY  where the AI app reads the keyboard from (default: /dev/tty)
set -eu

# The AI-app line: the same words everywhere (SETUP.md, README, both start scripts, the tests).
LINE='Set up my brain from the BrainOS kit at github.com/adrianshedden/brainos-core (read its SETUP.md first and follow it). Ask me before you change anything, work only in my brain folder, and never send my files anywhere.'
REPO_ZIP='https://github.com/adrianshedden/brainos-core/archive/refs/heads'

say() {
  printf '%s\n' "$*"
}

fail() {
  say "$*" >&2
  exit 1
}

# Which online service copies <folder> (iCloud, OneDrive...), or nothing when it stays on this computer.
synced_service() {
  real=$(cd -P "$1" 2>/dev/null && pwd -P) || real=$1
  case $real in
    *"Mobile Documents"* | *CloudDocs* | *iCloud*) say "iCloud"; return 0 ;;
    *OneDrive*) say "OneDrive"; return 0 ;;
    *Dropbox*) say "Dropbox"; return 0 ;;
    *"Google Drive"* | *GoogleDrive*) say "Google Drive"; return 0 ;;
    */Library/CloudStorage/*) say "an online storage service"; return 0 ;;
  esac
  # A Mac with "Desktop & Documents Folders" turned on in iCloud keeps the copy here.
  if [ -d "$HOME/Library/Mobile Documents/com~apple~CloudDocs/Documents" ]; then
    say "iCloud"
  fi
}

# Sets BRAIN: the folder asked for, else a brain made earlier, else Documents/brain unless Documents
# is copied online, else ~/brain.
choose_brain() {
  if [ -n "${BRAINOS_DIR:-}" ]; then
    BRAIN=$BRAINOS_DIR
    return 0
  fi
  docs=$HOME/Documents
  for earlier in "$docs/brain" "$HOME/brain"; do
    if [ -f "$earlier/brain.yaml" ] || [ -d "$earlier/kit" ]; then
      BRAIN=$earlier
      return 0
    fi
  done
  BRAIN=$HOME/brain
  if [ -d "$docs" ]; then
    service=$(synced_service "$docs")
    if [ -n "$service" ]; then
      say "Your Documents folder is copied online by $service, so your brain goes in $HOME/brain instead, which stays on this computer."
    else
      BRAIN=$docs/brain
    fi
  fi
}

# Stops, changing nothing, when BRAIN already holds someone's own files and is not a brain.
refuse_other_folders() {
  if [ -e "$BRAIN" ] && [ ! -d "$BRAIN" ]; then
    fail "There is already a file called $BRAIN, so nothing was changed. Move or rename it, then run this line again."
  fi
  if [ ! -d "$BRAIN" ] || [ -f "$BRAIN/brain.yaml" ]; then
    return 0
  fi
  for item in "$BRAIN"/* "$BRAIN"/.[!.]* "$BRAIN"/..?*; do
    if [ ! -e "$item" ] && [ ! -L "$item" ]; then
      continue
    fi
    case ${item##*/} in
      kit | exports | setup.yaml | .DS_Store) ;;
      *) fail "There is already a folder at $BRAIN with other files in it, and it is not a brain. To keep those files safe, nothing was changed. Move or rename that folder, then run this line again." ;;
    esac
  done
}

cleanup() {
  if [ -n "${WORK:-}" ] && [ -d "$WORK" ]; then
    rm -rf "$WORK"
  fi
  if [ -n "${NEW_KIT:-}" ] && [ -d "$NEW_KIT" ]; then
    rm -rf "$NEW_KIT"
  fi
  # Stopped halfway through swapping the kit: put the old one back.
  if [ -n "${OLD_KIT:-}" ] && [ -d "$OLD_KIT" ]; then
    if [ -e "$BRAIN/kit" ]; then
      rm -rf "$OLD_KIT"
    else
      mv "$OLD_KIT" "$BRAIN/kit"
    fi
  fi
}

download_kit() {
  zip=$WORK/kit.zip
  src=${BRAINOS_ZIP:-$REPO_ZIP/${BRAINOS_REF:-main}.zip}
  if [ -f "$src" ]; then
    cp "$src" "$zip"
  elif command -v curl >/dev/null 2>&1; then
    curl -fsSL --retry 2 -o "$zip" "$src" \
      || fail "Could not download the BrainOS kit. Check this computer is online, then run this line again."
  elif command -v wget >/dev/null 2>&1; then
    wget -q -O "$zip" "$src" \
      || fail "Could not download the BrainOS kit. Check this computer is online, then run this line again."
  else
    fail "This computer has no download tool, so the kit could not be fetched. Use the line for your AI app instead."
  fi
  mkdir "$WORK/unzipped"
  if command -v unzip >/dev/null 2>&1; then
    unzip -q "$zip" -d "$WORK/unzipped" >/dev/null 2>&1 || fail "The kit download was damaged. Run this line again."
  elif command -v python3 >/dev/null 2>&1; then
    python3 -m zipfile -e "$zip" "$WORK/unzipped" >/dev/null 2>&1 || fail "The kit download was damaged. Run this line again."
  else
    tar -xf "$zip" -C "$WORK/unzipped" >/dev/null 2>&1 || fail "The kit download was damaged. Run this line again."
  fi
  set -- "$WORK/unzipped"/*
  if [ "$#" -ne 1 ] || [ ! -f "$1/SETUP.md" ] || [ ! -f "$1/create_brain.py" ]; then
    fail "The download does not look like the BrainOS kit, so nothing was changed. Run this line again."
  fi
  KIT_SOURCE=$1
}

# Puts the new kit in BRAIN/kit. Only kit/ is replaced: everything else in the brain stays as it is.
place_kit() {
  mkdir -p "$BRAIN"
  NEW_KIT=$BRAIN/.kit-new-$$
  OLD_KIT=$BRAIN/.kit-old-$$
  mv "$KIT_SOURCE" "$NEW_KIT"
  if [ -e "$BRAIN/kit" ] || [ -L "$BRAIN/kit" ]; then
    mv "$BRAIN/kit" "$OLD_KIT"
  fi
  mv "$NEW_KIT" "$BRAIN/kit"
  NEW_KIT=
  if [ -d "$OLD_KIT" ]; then
    rm -rf "$OLD_KIT"
  fi
  OLD_KIT=
}

# Says whether Python 3.8 or newer is here, and how to get it if not. Installs nothing.
check_python() {
  found=
  if command -v python3 >/dev/null 2>&1; then
    # On a Mac without Apple's developer tools, python3 is only a stand-in that offers to install them.
    if [ "$(command -v python3)" = /usr/bin/python3 ] && [ "$(uname -s)" = Darwin ] \
      && ! xcode-select -p >/dev/null 2>&1; then
      found=
    elif python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' >/dev/null 2>&1; then
      found=yes
    else
      found=old
    fi
  fi
  if [ "$found" = yes ]; then
    say "Python is ready."
    return 0
  fi
  if [ "$found" = old ]; then
    say "The Python on this computer is too old for the kit (it needs version 3.8 or newer). To get a new one, free:"
  else
    say "Python is not on this computer yet. The kit uses it to read your files. To get it, free:"
  fi
  say "  1. Go to python.org/downloads and click the yellow Download button."
  say "  2. Open the file you downloaded and follow its steps."
  say "  3. Run this same line again."
}

print_line() {
  say ""
  say "$1"
  say ""
  say "$LINE"
  say ""
}

open_folder() {
  if [ "$(uname -s)" = Darwin ] && command -v open >/dev/null 2>&1; then
    open "$BRAIN" >/dev/null 2>&1 || true
  elif command -v xdg-open >/dev/null 2>&1 && [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; then
    xdg-open "$BRAIN" >/dev/null 2>&1 || true
  fi
}

# The first AI app on this computer that can take the set-up line, or nothing.
find_ai() {
  for app in claude codex opencode; do
    if command -v "$app" >/dev/null 2>&1; then
      say "$app"
      return 0
    fi
  done
}

# Starts the AI app found in the brain folder with the set-up line. Returns 1 if there is none.
start_ai() {
  app=$(find_ai)
  if [ -z "$app" ]; then
    return 1
  fi
  case $app in
    claude) name="Claude Code" ;;
    codex) name="Codex" ;;
    *) name="OpenCode" ;;
  esac
  tty=${BRAINOS_TTY:-/dev/tty}
  if ! (: <"$tty") 2>/dev/null; then
    print_line "$name is on this computer. Open it in $BRAIN and paste this line:"
    return 0
  fi
  say "Starting $name in your brain folder with the set-up line. Answer its questions there."
  cleanup
  cd "$BRAIN"
  if [ "$app" = opencode ]; then
    exec opencode --prompt "$LINE" <"$tty"
  else
    exec "$app" "$LINE" <"$tty"
  fi
}

main() {
  say "BrainOS: getting your brain folder ready. This takes about a minute."
  choose_brain
  refuse_other_folders
  WORK=$(mktemp -d 2>/dev/null || mktemp -d -t brainos)
  trap cleanup EXIT
  trap 'exit 1' HUP INT TERM
  say "Downloading the BrainOS kit..."
  download_kit
  place_kit
  say "Your brain folder is $BRAIN, and the kit is in its kit folder."
  check_python
  if start_ai; then
    return 0
  fi
  open_folder
  say "Using the Claude app? Sign in inside the Claude app window. Signing in on the website does not sign in the app."
  print_line "Next, open your AI app (for example the Claude app), choose the folder $BRAIN, and paste this line:"
}

main "$@"
