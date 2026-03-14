import argparse
from argparse import Namespace
from datetime import datetime
from typing import Any

import requests
import pandas as pd
from pandas import DataFrame

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

    members = []
    for member in response.json():
        if "content" in member:
            content = member["content"]
            content["id"] = member.get("id")
            content.pop("uid", None)
            members.append(content)
    return members


def get_sys_id(headers):
    url = f"{BASE_URL}/me"
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    data = response.json()
    return data["id"]

def get_history_for_member(member_id, headers):
    url = f"{BASE_URL}/frontHistory/member/{member_id}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    data = response.json()

    return [
        history["content"]
        for history in data
        if "content" in history
    ]

def main():
    parser = argparse.ArgumentParser(description="Export Simply Plural members to CSV")
    parser.add_argument("--api-key", required=True, help="Simply Plural API key")
    parser.add_argument("--output", default="members.csv", help="Output CSV file")
    parser.add_argument("--output-history", default=None, help="Output CSV file for history")

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

    if args.output_history is not None:
        export_history(args, df, headers)


def export_history(args: Namespace, df: DataFrame, headers: dict[str, Any]):
    all_history = []
    for row in df.itertuples():
        history = get_history_for_member(row.id, headers)
        for hist in history:
            hist["member"] = row.id
            hist.pop("uid", None)
            for t in ["startTime", "endTime", "lastOperationTime"]:
                if hist.get(t):
                    hist[t] = datetime.fromtimestamp(hist[t] / 1000)
        all_history.extend(history)

    df_history = pd.json_normalize(all_history)
    df_history.to_csv(
        args.output_history,
        sep=",",
        encoding="utf-8",
        index=False
    )
    print(f"Export complete: {args.output_history}")


if __name__ == "__main__":
    main()