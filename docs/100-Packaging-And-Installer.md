# Packaging And Installer

## Goal

Define a repeatable packaging path for Windows delivery before the codebase grows too large.

## Scope

### Included

- developer-facing packaging scripts
- PyInstaller spec for executable generation
- Windows installer script template
- documented output layout and expected artifacts

### Excluded

- signed production binaries
- CI release automation
- auto-update service

## Packaging Flow

### Local Developer Build

- sync dependencies with `uv`
- build the desktop executable with `PyInstaller`
- place outputs under `dist/`

### Windows Installer

- take the packaged executable output
- build an installer with Inno Setup
- create desktop and start-menu shortcuts

## Expected Artifacts

- unpacked executable directory for smoke testing
- installable Windows `.exe` installer

## Implementation Notes

- keep resource paths relative to the executable-friendly app layout
- prefer scripts that can be invoked from PowerShell on a Windows build machine
- document environment assumptions clearly because packaging cannot be fully validated from macOS
