# Data Contract

This document defines the CSV outputs produced by `request_members.py`.

## Scope

- Contract source of truth: `request_members.py`
- Format: CSV, comma-separated, UTF-8, header row, no index
- API base: `https://api.apparyllis.com/v1`

## Common Rules

- Records are flattened from API `content` objects.
- Exported rows include top-level document `id`.
- `uid` is removed when present.
- Timestamp fields listed below are converted from epoch milliseconds to datetime.
- Most string fields have newlines normalized:
  - `\r\n`, `\n`, `\r` -> literal `\\n`
- Privacy bucket ids are replaced with bucket names where implemented.
- Where a human-readable name is added for context, the corresponding source id is also exported when implemented. This avoids ambiguity when multiple members, channels, or documents have the same name.

## Output Files

### `members.csv` (always exported)

Source:
- `GET /me`
- `GET /members/{sysId}`
- `GET /customFields/{sysId}`
- `GET /privacyBuckets`

Columns:
- All member content fields (dynamic)
- `id`
- Custom fields under `info.<fieldId>` are renamed to custom field names
- `buckets` contains bucket names when mapping exists (falls back to id)

Notes:
- Column set is system-dependent due to custom fields.

### `history.csv` (when `--output-history` is set)

Source:
- `GET /frontHistory/member/{docId}` for each member
- Also for each custom front when `--output-custom-fronts` is set

Columns:
- All front history content fields (dynamic)
- `id`
- `member` — member/custom-front name used for lookup context
- `memberId` — id of the member/custom-front used for lookup context
- `documentName` — same contextual document name as `member`
- `documentId` — same contextual document id as `memberId`

Timestamp conversions:
- `startTime`
- `endTime`
- `lastOperationTime`

### `comments.csv` (when `--output-comments` is set)

Source:
- `GET /comments/frontHistory/{docId}` for front-history docs with `commentCount > 0`

Columns:
- All comment content fields (dynamic)
- `id`
- `documentId` — id of the document the comment belongs to
- `documentType` — document type used for the comments endpoint, currently `frontHistory`
- `lastOperationTime` (if present)

Notes:
- In current flow, comments are exported as front-history comments.

### `notes.csv` (when `--output-notes` is set)

Source:
- `GET /notes/{sysId}/{memberId}` for each member

Columns:
- All note content fields (dynamic)
- `id`
- `member` — member name
- `memberId` — member id
- `lastOperationTime` (if present)

### `board.csv` (when `--output-board` is set)

Source:
- `GET /board/member/{memberId}` for each member

Columns:
- All board message content fields (dynamic)
- `id`
- `writtenFor` — target member name
- `writtenForId` — target member id
- `writtenBy` — writer member id mapped to name when possible
- `writtenById` — original writer member id
- `writtenAt`
- `lastOperationTime` (if present)

Timestamp conversions:
- `writtenAt`
- `lastOperationTime`

### `custom_fronts.csv` (when `--output-custom-fronts` is set)

Source:
- `GET /customFronts/{sysId}`
- `GET /privacyBuckets`

Columns:
- All custom front content fields (dynamic)
- `id`
- `buckets` mapped to bucket names when mapping exists
- `lastOperationTime` (if present)

Notes:
- Newline sanitization is applied.

### `poll_votes.csv` (when `--output-poll-votes` is set)

Source:
- `GET /polls/{sysId}`

Columns:
- `pollId`
- `pollName`
- `voter` — voter member id mapped to name when possible
- `voterId` — original voter member id
- `vote`
- `comment`

Timestamp conversions:
- Not included in poll vote rows.

### `poll_options.csv` (when `--output-poll-options` is set)

Source:
- `GET /polls/{sysId}`

Columns:
- `pollId`
- `pollName`
- `optionName`
- `optionColor`

Timestamp conversions:
- Not included in poll option rows.

### `chat_channels.csv` (when `--output-chat-channels` is set)

Source:
- `GET /chat/channels`

Columns:
- All chat channel content fields (dynamic)
- `id`
- `lastOperationTime` (if present)

### `chat_messages.csv` (when `--output-chat-messages` is set)

Source:
- `GET /chat/channels`
- `GET /chat/messages/{channelId}?limit=100&sortBy=writtenAt&sortOrder=1`
- Pagination via `skipTo={lastMessageId}`

Columns:
- All chat message content fields (dynamic)
- `id`
- `channel` — channel name
- `channelId` — channel id
- `writer` — writer member id mapped to name when possible
- `writerId` — original writer member id
- `writtenAt`
- `lastOperationTime` (if present)

Timestamp conversions:
- `writtenAt`
- `lastOperationTime`

## Compatibility Guidance

- Python is the reference contract.
- Browser exporter (`docs/script.js`) should match this contract where platform constraints allow.
- Any divergence should be documented in README and this file.
