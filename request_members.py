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


def get_history_for_document(doc_id, doc_name, headers):
    url = f"{BASE_URL}/frontHistory/member/{doc_id}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    histories = []

    for history in response.json():
        if "content" in history:
            content = normalize_content(history)

            content["member"] = doc_name

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

def get_polls(sys_id, headers):
    url = f"{BASE_URL}/polls/{sys_id}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    polls = []

    for poll in response.json():
        if "content" in poll:
            content = normalize_content(poll)
            resolve_timestamps(
                content,
                ["endTime"]
            )
            polls.append(content)

    return polls

def get_chat_channels(headers):
    url = f"{BASE_URL}/chat/channels"
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    channels = []
    for channel in response.json():
        if "content" in channel:
            content = normalize_content(channel)
            channels.append(content)

    return channels

def get_chat_messages_of_channel(channel_id, channel_name, member_id_name_map, headers):
    url = f"{BASE_URL}/chat/messages/{channel_id}?limit=100&sortBy=writtenAt&sortOrder=1"
    all_chat_messages = []

    while url:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        if not data:
            break

        for msg in data:
            if "content" in msg:
                content = normalize_content(msg)
                content["writer"] = member_id_name_map.get(content.get("writer"), content.get("writer"))
                resolve_timestamps(content, ["writtenAt"])
                content["channel"] = channel_name
                all_chat_messages.append(content)

        # next page
        url = f"{BASE_URL}/chat/messages/{channel_id}?limit=100&skipTo={data[-1]['id']}&sortBy=writtenAt&sortOrder=1"

    return all_chat_messages

def export_csv(data, path):
    df = pd.json_normalize(data)
    df = sanitize_newlines_in_dataframe(df)

    df.to_csv(
        path,
        sep=",",
        encoding="utf-8",
        index=False
    )

    print(f"Export complete: {path}")


def export_history(df: DataFrame, custom_fronts: DataFrame, headers, output_history, output_comments):
    all_history = []

    for row in df.itertuples():
        history = get_history_for_document(row.id, row.name, headers)
        all_history.extend(history)

    if custom_fronts is not None:
        for row in custom_fronts.itertuples():
            history = get_history_for_document(row.id, row.name, headers)
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

    return df_custom_fronts

def export_polls(sys_id, headers, member_id_name_map, output_votes, output_options):
    polls = get_polls(sys_id, headers)

    vote_rows = []
    option_rows = []

    for poll in polls:

        base_poll = {
            k: v for k, v in poll.items()
            if k not in ["votes", "options"]
        }

        # votes
        for vote in poll.get("votes", []):
            row = base_poll.copy()

            voter_id = vote.get("id")

            row["vote.id"] = member_id_name_map.get(
                voter_id,
                voter_id
            )

            row["vote.vote"] = vote.get("vote")
            row["vote.comment"] = vote.get("comment")

            vote_rows.append(row)

        for option in poll.get("options", []):
            row = base_poll.copy()

            row["option.name"] = option.get("name")
            row["option.color"] = option.get("color")

            option_rows.append(row)

    if output_votes:
        export_csv(vote_rows, output_votes)

    if output_options:
        export_csv(option_rows, output_options)

def export_chat(member_id_name_map, headers, output_chat_channel, output_chat_messages):
    channels = get_chat_channels(headers)

    chat_messages = []

    for channel in channels:
        chat_messages_of_channel = get_chat_messages_of_channel(channel["id"], channel["name"], member_id_name_map, headers)
        chat_messages.extend(chat_messages_of_channel)

    if output_chat_messages:
        export_csv(chat_messages, output_chat_messages)

    if output_chat_channel:
        export_csv(channels, output_chat_channel)

def replace_bucket_names(df_custom_fronts: DataFrame, bucket_lookup):
    df_custom_fronts["buckets"] = df_custom_fronts["buckets"].apply(
        lambda ids: [
            bucket_lookup.get(i, i)
            for i in ids
        ] if isinstance(ids, list) else ids
    )


def sanitize_newlines_in_dataframe(df: DataFrame) -> DataFrame:
    return df.apply(
        lambda col: col.map(
            lambda value: value.replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n")
            if isinstance(value, str)
            else value
        )
    )


def main():
    parser = argparse.ArgumentParser(
        description="Export Simply Plural data to CSV"
    )

    parser.add_argument(
        "--api-key",
        required=True,
        help="Simply Plural API key used to authenticate all requests"
    )

    parser.add_argument(
        "--output",
        default="members.csv",
        help="CSV file to export the member list"
    )

    parser.add_argument(
        "--output-history",
        default=None,
        help="CSV file to export member front history (optional)"
    )

    parser.add_argument(
        "--output-comments",
        default=None,
        help="CSV file to export comments associated with front history entries (optional)"
    )

    parser.add_argument(
        "--output-notes",
        default=None,
        help="CSV file to export notes of each member (optional)"
    )

    parser.add_argument(
        "--output-board",
        default=None,
        help="CSV file to export board messages of each member (optional)"
    )

    parser.add_argument(
        "--output-custom-fronts",
        default=None,
        help="CSV file to export custom front definitions (optional)"
    )

    parser.add_argument(
        "--output-poll-votes",
        default=None,
        help="CSV file to export poll votes for each poll (optional)"
    )

    parser.add_argument(
        "--output-poll-options",
        default=None,
        help="CSV file to export poll options for each poll (optional)"
    )

    parser.add_argument(
        "--output-chat-channels",
        default=None,
        help="CSV file to export chat channel metadata (optional)"
    )

    parser.add_argument(
        "--output-chat-messages",
        default=None,
        help="CSV file to export chat messages (optional)"
    )

    args = parser.parse_args()

    # Show summary of what will be exported
    print("\nExport Summary:")
    print(f"  Members list:          {args.output}")
    if args.output_history:
        print(f"  History:               {args.output_history}")
    if args.output_comments:
        print(f"  Comments:              {args.output_comments}")
    if args.output_notes:
        print(f"  Notes:                 {args.output_notes}")
    if args.output_board:
        print(f"  Board messages:        {args.output_board}")
    if args.output_custom_fronts:
        print(f"  Custom fronts:         {args.output_custom_fronts}")
    if args.output_poll_votes:
        print(f"  Poll votes:            {args.output_poll_votes}")
    if args.output_poll_options:
        print(f"  Poll options:          {args.output_poll_options}")
    if args.output_chat_channels:
        print(f"  Chat channels:         {args.output_chat_channels}")
    if args.output_chat_messages:
        print(f"  Chat messages:         {args.output_chat_messages}")
    print("\nStarting export...\n")

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

    df = sanitize_newlines_in_dataframe(df)

    df.to_csv(
        args.output,
        sep=",",
        encoding="utf-8",
        index=False
    )

    print(f"Export complete: {args.output}")

    custom_fronts = None

    if args.output_custom_fronts:
        custom_fronts = export_custom_fronts(sys_id, bucket_lookup, headers, args.output_custom_fronts)

    if args.output_history:
        export_history(
            df,
            custom_fronts,
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

    if args.output_poll_votes or args.output_poll_options:
        export_polls(
            sys_id,
            headers,
            member_id_name_map,
            args.output_poll_votes,
            args.output_poll_options
        )

    if args.output_chat_channels or args.output_chat_messages:
        export_chat(
            member_id_name_map, headers, args.output_chat_channels, args.output_chat_messages )

if __name__ == "__main__":
    main()

