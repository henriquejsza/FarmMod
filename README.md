# FarmMod

![FarmMod logo](data/logo/io.github.henriquejsza.farmmod-hub.png)

Mod manager for Farming Simulator on Linux (Steam/Proton), with support for FS19, FS22, and FS25.

Language: English | [Portuguese (Brazil)](README.pt-BR.md)

## Features

- Drag-and-drop install or file picker install.
- Supports `.zip` files and mod folders.
- Validation before install (missing modDesc, corrupted zip, invalid name, zip/folder conflict, and more).
- Per-game profiles (no mixing between FS19/FS22/FS25).
- Profile backup and restore with `.zip`.
- `log.txt` diagnostics with suspect mod ranking.
- UI available in English and PT-BR.

## Installation

Arch Linux (AUR via `yay`):

```bash
yay -S farmmod-hub
```

Package page: `https://aur.archlinux.org/packages/farmmod-hub`

## Run From Source

Dependencies (Debian/Ubuntu):

```bash
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1
```

Run:

```bash
./run
```

Alternative:

```bash
PYTHONPATH=src python3 -m farmmod_hub
```

## Development

Run tests:

```bash
pytest
```

## License

AGPL-3.0-or-later. See `LICENSE`.

## Maintainer

- Henrique
- GitHub: `@henriquejsza`
- Email: `henriquejsza@gmail.com`
