# Keychain to Bitwarden Sync

A secure command-line tool for synchronizing passwords from macOS Keychain to Bitwarden vault. This tool enables one-way synchronization while prioritizing security and providing fine-grained control over the sync process.

![License](https://img.shields.io/badge/license-GPL--3.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.7%2B-blue)
![Platform](https://img.shields.io/badge/platform-macOS-lightgrey)

## Features

- 🔒 Secure password handling with no disk storage
- 📝 Detailed logging and verbose mode
- ✅ Dry-run mode (default) to preview changes
- 🔄 One-way sync from Keychain to Bitwarden
- 🏷️ Standardized entry naming and organization
- 📋 Comprehensive error handling

## Prerequisites

- macOS 10.13 or later
- Python 3.7 or later
- Bitwarden CLI
- Bitwarden account

## Installation

1. Install Bitwarden CLI:
```bash
brew install bitwarden-cli
```

2. Clone this repository:
```bash
git clone https://github.com/yourusername/keychain-bitwarden-sync.git
cd keychain-bitwarden-sync
```

3. Install required Python packages:
```bash
pip install -r requirements.txt
```

4. Make the script executable:
```bash
chmod +x keychain-bitwarden-sync.py
```

## Usage

### Basic Usage

Check for differences between Keychain and Bitwarden (dry-run):
```bash
./keychain-bitwarden-sync.py
```

Sync passwords from Keychain to Bitwarden:
```bash
./keychain-bitwarden-sync.py --write
```

Enable verbose logging:
```bash
./keychain-bitwarden-sync.py --write --verbose
```

### Command-line Options

| Option | Description |
|--------|-------------|
| `--write` | Enable writing updates to Bitwarden (disabled by default) |
| `--verbose`, `-v` | Enable verbose logging |

## Security Considerations

- No passwords are stored to disk
- All operations are performed in memory
- Bitwarden session tokens are temporary
- Keychain access requires system authentication
- Secure password input handling
- No modification of existing Bitwarden entries

## How It Works

1. Authenticates with Bitwarden CLI
2. Retrieves password entries from macOS Keychain
3. Fetches existing items from Bitwarden vault
4. Compares entries between the two stores
5. Creates new Bitwarden entries for passwords not present in vault
6. Logs all operations and any errors encountered

## Entry Format

Bitwarden entries are created with the following format:

- Name: `{service} - {account}`
- Username: Original Keychain account name
- Password: Original Keychain password
- URI: `https://{service}` (automatically generated)
- Notes: Includes import timestamp

## Error Handling

The tool includes comprehensive error handling for:
- Bitwarden authentication failures
- Keychain access issues
- Network connectivity problems
- Permission errors
- Invalid input data

## Logging

Logs include:
- Operation timestamps
- Success/failure status
- Error messages
- Entry details (excluding sensitive data)
- Sync statistics

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest

# Run linter
flake8 .
```

## Testing

```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/test_sync.py

# Run with coverage report
python -m pytest --cov=keychain_bitwarden_sync
```

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Bitwarden CLI developers
- macOS Keychain Access API developers
- Python keyring package maintainers

## Support

For support, please:
1. Check the [FAQ](docs/FAQ.md)
2. Search existing [Issues](https://github.com/yourusername/keychain-bitwarden-sync/issues)
3. Open a new issue if needed

## Roadmap

- [ ] Two-way synchronization
- [ ] Custom field mapping
- [ ] Folder organization support
- [ ] Configuration file support
- [ ] Multiple vault support
- [ ] GUI interface

## Version History

- 1.0.0 (2024-10-24)
  - Initial release
  - Basic one-way sync functionality
  - Command-line interface
  - Logging system
