# Implementation Plan

[Overview]
Create a bash script `llm/install_cline.sh` that installs Cline CLI on Ubuntu, defaulting to the latest v2 release with an option to install v1.

The script follows the same pattern as existing `install_*.sh` scripts in the project. It installs nvm (Node Version Manager), then Node.js LTS, then the `cline` npm package globally. By default it installs the latest v2.x (currently 2.18.0). With `-v 1` or `--version 1` it installs v1.0.10. The script is idempotent — it detects existing installations and skips redundant steps.

[Types]
No new types, classes, or data structures — this is a bash script.

The script accepts these parameters:
- `-v <version>` or `--version <version>`: Version to install. `1` → cline@1.0.10, `2` (default) → cline@latest
- `--dry-run`: Print what would be done without executing
- `-h` or `--help`: Print usage

[Files]
One file to create, no existing files to modify.

- **New file:** `llm/install_cline.sh` — the installation script
- **No existing files modified**

[Functions]
No functions in the traditional sense — the script is a linear bash script with helper sections:

- **Usage/help section:** Prints usage info when `-h` or invalid args given
- **nvm installation:** Installs nvm if not already present (`~/.nvm` directory check)
- **Node.js installation:** Installs latest LTS via nvm if not already present
- **Cline installation:** `npm install -g cline` (v2 default) or `npm install -g cline@1.0.10` (v1)
- **Verification:** Runs `cline --version` to confirm installation

[Classes]
No classes.

[Dependencies]
No new project dependencies. The script requires:
- `curl` (for nvm install script)
- `bash` (>= 4.0)
- Standard Ubuntu utilities (`wget`, `apt` — for nvm system dependencies if needed)

[Testing]
Manual testing only — run the script on a clean Ubuntu system and verify:
- `./llm/install_cline.sh` installs cline v2 and `cline --version` shows 2.x
- `./llm/install_cline.sh -v 1` installs cline v1 and `cline --version` shows 1.x
- `./llm/install_cline.sh --dry-run` prints steps without executing
- `./llm/install_cline.sh -h` prints usage
- Running again is idempotent (skips already-installed components)

[Implementation Order]
Single step — create the script file.
