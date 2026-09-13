# How to run the audit on Windows

Three steps. Nothing to install beyond Python.

## Step 1 — check Python is there

Open PowerShell (Start menu, type "PowerShell", Enter) and run:

    python --version

If you get a version number, continue. If Windows opens the Microsoft Store
instead, install Python from python.org first, tick "Add python.exe to PATH"
during setup, then close and reopen PowerShell.

## Step 2 — get the scripts onto your machine

    cd C:\Users\Francis\Documents\Code
    git clone https://github.com/breezewood-77/filmar-backup-info.git _audit

That puts the scripts at `C:\Users\Francis\Documents\Code\_audit\tools\`.
The leading underscore keeps them out of the way of the real work, and
`_audit` can be deleted afterwards without touching anything else.

## Step 3 — run it

    cd C:\Users\Francis\Documents\Code
    python _audit\tools\bloat_audit.py "C:\Users\Francis\Documents\Code" --days 90

Read the output on screen. Then produce the file to paste back:

    python _audit\tools\bloat_audit.py "C:\Users\Francis\Documents\Code" --days 90 --json > audit-2026-09-13.json

Open `audit-2026-09-13.json` and paste its contents into the chat.
If it is too large to paste, send this smaller version instead:

    python _audit\tools\bloat_audit.py "C:\Users\Francis\Documents\Code" --days 90 > audit-summary.txt

## What it does and does not do

Reads files and prints numbers. It never writes, moves, renames or deletes
anything in the folder you point it at, and it makes no network calls.
`_audit` is the only thing it puts on disk, and that is git, not the script.

## Registry check (run after the audit)

    python _audit\tools\registry_check.py "C:\Users\Francis\Documents\Code" --registry _audit\tools\registry.tsv

Fails with exit code 1 and a list when a skill or task hands work to a
component that is not in `registry.tsv`. That is the check that stops
collision lines from coming back.
