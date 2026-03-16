# Simply Plural Export Tools


Tools for exporting user data from the SimplyPlural API into CSV files.

This repository currently includes:
- A Python CLI exporter (`request_members.py`)
- A browser-based exporter in [`docs/`](docs/)

## Disclaimer

This is an **unofficial tool** and is not affiliated with or endorsed by SimplyPlural.

It uses the SimplyPlural API to allow users to export their own data for personal backup.

## Purpose

This project was created to help users export their SimplyPlural data without manually copying it from the interface.

## What It Can Export

The Python exporter can export:
- Members (always exported)
- Front history
- Comments for front history entries
- Member notes
- Member board messages
- Custom fronts
- Poll votes
- Poll options
- Chat channels
- Chat messages

Outputs are written as CSV files.

## Requirements

- Python 3.12+
- Dependencies in [`requirements.txt`](requirements.txt):
  - `requests`
  - `pandas`

Install:

```powershell
pip install -r requirements.txt
```

## Python CLI Usage

Basic export (members only):

```powershell
python request_members.py --api-key YOUR_API_KEY
```

This writes `members.csv` by default.

Specify custom members output:

```powershell
python request_members.py --api-key YOUR_API_KEY --output my_members.csv
```

Enable optional exports by passing output paths:

```powershell
python request_members.py `
  --api-key YOUR_API_KEY `
  --output members.csv `
  --output-history history.csv `
  --output-comments comments.csv `
  --output-notes notes.csv `
  --output-board board.csv `
  --output-custom-fronts custom_fronts.csv `
  --output-poll-votes poll_votes.csv `
  --output-poll-options poll_options.csv `
  --output-chat-channels chat_channels.csv `
  --output-chat-messages chat_messages.csv
```

Notes:
- `--output-comments` is mainly useful together with `--output-history`.
- Large systems may take time for history/chat exports due to pagination and per-item API calls.

## Browser Exporter (`docs/`)

The `docs/` folder contains a static web exporter (`index.html`, `script.js`, `styles.css`) that:
- Runs in the browser
- Accepts your API key at runtime
- Can export data as CSV or JSON

You can open `docs/index.html` directly in a browser or host `docs/` as a static site.

## API Usage

This tool uses the SimplyPlural API to export user data.

Please use it responsibly and avoid excessive requests. Large exports (such as history or chat messages) may take time due to pagination and API limits.

This project may be modified or removed if requested by the SimplyPlural maintainers.

## Development

When adding or changing features, use this policy:
- Implement features in both exporters when possible:
  - Python CLI: [`request_members.py`](request_members.py)
  - Browser exporter: [`docs/script.js`](docs/script.js)
- Treat the Python implementation as the point of reference for behavior and output shape.
- Keep option names and exported field semantics aligned across both implementations where platform constraints allow.
- If a feature cannot be mirrored in one implementation, document the limitation in this README.