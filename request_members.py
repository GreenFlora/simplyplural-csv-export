import argparse
from datetime import datetime
from typing import Any, Iterable

import requests
import pandas as pd
from pandas import DataFrame

BASE_URL = "https://api.apparyllis.com/v1"


def resolve_timestamps(obj: dict, fields: Iterable[str]):
    for field in fields:
        if obj.get(field):
            obj[field] = datetime.fromtimestamp(obj[field] / 1000)


def normalize_content(obj):
    content = obj["content"]

    content["id"] = obj["id"]
    content.pop("uid", None)

    if content.get("lastOperationTime"):
        content["lastOperationTime"] = datetime.fromtimestamp(
            content["lastOperationTime"] / 1000
        )

    return content


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
            content = normalize_content(member)
            members.append(content)

    return members

def get_custom_fronts(sys_id, headers):
    url = f"{BASE_URL}/customFronts/{sys_id}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    custom_fronts = []

    for custom_front in response.json():
        if "content" in custom_front:
            content = normalize_content(custom_front)
            custom_fronts.append(content)

    return custom_fronts

def get_sys_id(headers):
    url = f"{BASE_URL}/me"
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()["id"]


def get_history_for_member(member_id, member_name, headers):
    url = f"{BASE_URL}/frontHistory/member/{member_id}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    histories = []

    for history in response.json():
        if "content" in history:
            content = normalize_content(history)

            content["member"] = member_name

            resolve_timestamps(
                content,
                ["startTime", "endTime"]
            )

            histories.append(content)

    return histories


def get_notes_for_member(member_id, member_name, sys_id, headers):
    url = f"{BASE_URL}/notes/{sys_id}/{member_id}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    notes = []

    for note in response.json():
        if "content" in note:
            content = normalize_content(note)

            content["member"] = member_name

            notes.append(content)

    return notes


def get_board_of_member(member_id, member_name, member_id_name_map, headers):
    url = f"{BASE_URL}/board/member/{member_id}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    board_msgs = []

    for message in response.json():
        if "content" in message:
            content = normalize_content(message)

            content["writtenFor"] = member_name
            content["writtenBy"] = member_id_name_map.get(
                content["writtenBy"],
                content["writtenBy"]
            )

            resolve_timestamps(
                content,
                ["writtenAt"]
            )

            board_msgs.append(content)

    return board_msgs


def get_comments_for_document(doc_id, doc_type, headers):
    url = f"{BASE_URL}/comments/{doc_type}/{doc_id}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    comments = []

    for comment in response.json():
        if "content" in comment:
            content = normalize_content(comment)
            comments.append(content)

    return comments


def export_csv(data, path):
    df = pd.json_normalize(data)

    df.to_csv(
        path,
        sep=",",
        encoding="utf-8",
        index=False
    )

    print(f"Export complete: {path}")


def export_history(df: DataFrame, headers, output_history, output_comments):
    all_history = []

    for row in df.itertuples():
        history = get_history_for_member(row.id, row.name, headers)
        all_history.extend(history)

    export_csv(all_history, output_history)

    if output_comments is not None:
        docs_with_comments = {"frontHistory": []}

        for history in all_history:
            if history.get("commentCount", 0) > 0:
                docs_with_comments["frontHistory"].append(history["id"])

        export_comments(docs_with_comments, headers, output_comments)


def export_notes(df, headers, sys_id, output_notes):
    all_notes = []

    for row in df.itertuples():
        notes = get_notes_for_member(row.id, row.name, sys_id, headers)
        all_notes.extend(notes)

    export_csv(all_notes, output_notes)


def export_board(df, headers, member_id_name_map, output_board):
    all_board = []

    for row in df.itertuples():
        board = get_board_of_member(
            row.id,
            row.name,
            member_id_name_map,
            headers
        )
        all_board.extend(board)

    export_csv(all_board, output_board)


def export_comments(docs_with_comments, headers, output_comments):
    all_comments = []

    for doc_type in docs_with_comments:
        for doc_id in docs_with_comments[doc_type]:
            comments = get_comments_for_document(
                doc_id,
                doc_type,
                headers
            )
            all_comments.extend(comments)

    export_csv(all_comments, output_comments)

def export_custom_fronts(sys_id, bucket_lookup, headers, output_custom_fronts):
    custom_fronts = get_custom_fronts(sys_id, headers)

    df_custom_fronts = pd.json_normalize(custom_fronts)

    if "buckets" in df_custom_fronts.columns:
        replace_bucket_names(df_custom_fronts, bucket_lookup)

    df_custom_fronts.to_csv(
        output_custom_fronts,
        sep=",",
        encoding="utf-8",
        index=False
    )

    print(f"Export complete: {output_custom_fronts}")


def replace_bucket_names(df_custom_fronts: DataFrame, bucket_lookup):
    df_custom_fronts["buckets"] = df_custom_fronts["buckets"].apply(
        lambda ids: [
            bucket_lookup.get(i, i)
            for i in ids
        ] if isinstance(ids, list) else ids
    )


def main():
    parser = argparse.ArgumentParser(
        description="Export Simply Plural data to CSV"
    )

    parser.add_argument("--api-key", required=True)

    parser.add_argument("--output", default="members.csv")
    parser.add_argument("--output-history", default=None)
    parser.add_argument("--output-comments", default=None)
    parser.add_argument("--output-notes", default=None)
    parser.add_argument("--output-board", default=None)
    parser.add_argument("--output-custom-fronts", default="custom_fronts.csv")

    args = parser.parse_args()

    headers = {
        "Authorization": args.api_key
    }

    sys_id = get_sys_id(headers)

    if sys_id is None:
        raise Exception("System could not be found, check API Key")

    member_data = get_members(sys_id, headers)

    member_id_name_map = {
        m["id"]: m["name"]
        for m in member_data
    }

    field_lookup = get_custom_fields(sys_id, headers)
    bucket_lookup = get_buckets(headers)

    df = pd.json_normalize(member_data)

    df = df.rename(
        columns=lambda c: field_lookup.get(c[5:], c)
        if c.startswith("info.")
        else c
    )

    if "buckets" in df.columns:
        replace_bucket_names(df, bucket_lookup)

    df.to_csv(
        args.output,
        sep=",",
        encoding="utf-8",
        index=False
    )

    print(f"Export complete: {args.output}")

    if args.output_history:
        export_history(
            df,
            headers,
            args.output_history,
            args.output_comments
        )

    if args.output_notes:
        export_notes(
            df,
            headers,
            sys_id,
            args.output_notes
        )

    if args.output_board:
        export_board(
            df,
            headers,
            member_id_name_map,
            args.output_board
        )

    if args.output_custom_fronts:
        export_custom_fronts(sys_id, bucket_lookup, headers, args.output_custom_fronts)


if __name__ == "__main__":
    main()