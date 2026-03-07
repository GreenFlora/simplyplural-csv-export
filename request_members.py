import argparse
import requests
import pandas as pd

BASE_URL = "https://api.apparyllis.com/v1"


def get_custom_fields(sys_id, headers):
    url = f"{BASE_URL}/customFields/{sys_id}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    data = response.json()

    return {
        field["id"]: field["content"]["name"]
        for field in data
        if "content" in field
    }


def get_buckets(headers):
    url = f"{BASE_URL}/privacyBuckets"
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    data = response.json()

    return {
        bucket["id"]: bucket["content"]["name"]
        for bucket in data
        if "content" in bucket
    }


def get_members(sys_id, headers):
    url = f"{BASE_URL}/members/{sys_id}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    data = response.json()

    return [
        member["content"]
        for member in data
        if "content" in member
    ]


def get_sys_id(headers):
    url = f"{BASE_URL}/me"
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    data = response.json()
    return data["id"]


def main():
    parser = argparse.ArgumentParser(description="Export Simply Plural members to CSV")
    parser.add_argument("--api-key", required=True, help="Simply Plural API key")
    parser.add_argument("--output", default="members.csv", help="Output CSV file")

    args = parser.parse_args()

    headers = {
        "Authorization": args.api_key
    }

    sys_id = get_sys_id(headers)

    if sys_id is None:
        raise Exception("System could not be found, check API Key")

    member_data = get_members(sys_id, headers)
    field_lookup = get_custom_fields(sys_id, headers)
    bucket_lookup = get_buckets(headers)

    df = pd.json_normalize(member_data)

    # Rename custom field columns (info.<id> -> field name)
    df = df.rename(
        columns=lambda c: field_lookup.get(c[5:], c) if c.startswith("info.") else c
    )

    # Replace bucket IDs with bucket names
    if "buckets" in df.columns:
        df["buckets"] = df["buckets"].apply(
            lambda ids: [bucket_lookup.get(i, i) for i in ids] if isinstance(ids, list) else ids
        )

    df.to_csv(
        args.output,
        sep=",",
        encoding="utf-8",
        index=False
    )

    print(f"Export complete: {args.output}")


if __name__ == "__main__":
    main()