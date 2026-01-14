[![PyPI - Version](https://img.shields.io/pypi/v/keyring-wincred.svg)](https://pypi.org/project/keyring-wincred)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/keyring-wincred.svg)](https://pypi.org/project/keyring-wincred)

# keyring_wincred

Windows Credential Manager backend for [keyring](https://pypi.org/project/keyring/) for WSL.

This package allows Python applications running in WSL (Windows Subsystem for Linux) to store secrets in the Windows Credential Manager.

## Installation

```
pip install keyring-wincred
```

or

```bash
git clone https://github.com/ilpianista/keyring_wincred.git
cd keyring_wincred
pip install .
```

## Usage

Once installed, keyring should automatically detect and use this backend when running under WSL. To force it configure `~/.config/python_keyring/keyringrc.cfg` like so:

```
[backend]
default-keyring = keyring_wincred.WinCredKeyring
```

Instead, in Python:

```python
import keyring

# Store a password
keyring.set_password("myservice", "myuser", "secret123")

# Retrieve a password
password = keyring.get_password("myservice", "myuser")

# Delete a password
keyring.delete_password("myservice", "myuser")
```

You can also use the keyring CLI:

```bash
keyring set myservice myuser
keyring get myservice myuser
keyring del myservice myuser
```

## How it works

This backend uses PowerShell with inline C# code to call the Windows Credential Manager API (`advapi32.dll`). No external PowerShell modules are required.

Credentials are stored with target names in the format `service:username`.

## Requirements

- WSL (Windows Subsystem for Linux)
- Python 3.8+
- `keyring` package

## Donate

Donations via [Liberapay](https://liberapay.com/ilpianista) or Bitcoin (1Ph3hFEoQaD4PK6MhL3kBNNh9FZFBfisEH) are always welcomed, _thank you_!

## License

MIT
