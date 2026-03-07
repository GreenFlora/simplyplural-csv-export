# Simply Plural CSV Exporter

A Python script that exports Simply Plural system members to a CSV file using the Simply Plural API.

The script retrieves system members, resolves custom fields and privacy buckets, and outputs the data in a clean CSV format.

## Requirements

Python 3.12+

Install dependencies using the included requirements.txt:

```shell
pip install -r requirements.txt
```

## Usage

Run the script with your Simply Plural API key:

```shell
python export_members.py --api-key YOUR_API_KEY
```

Specify a custom output file:

```shell
python export_members.py --api-key YOUR_API_KEY --output my_members.csv
```

Default output file:

members.csv