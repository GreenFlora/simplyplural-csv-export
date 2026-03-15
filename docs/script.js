const BASE_URL = "https://api.apparyllis.com/v1";
const $ = (id) => document.getElementById(id);

const setStatus = (m) => ($("status").textContent = m);
const setProgress = (v) => ($("progressBar").style.width = v + "%");

function getFormat() {
  const el = document.querySelector('input[name="format"]:checked');
  return el ? el.value : "csv";
}

async function api(path, key) {
  const r = await fetch(BASE_URL + path, { headers: { Authorization: key } });
  if (!r.ok) {
    const txt = await r.text();
    throw new Error(`API ${r.status}: ${txt}`);
  }
  return r.json();
}

// Flatten helpers
function flatten(member) {
  const flat = { ...member };
  if (member.info) {
    for (const [k, v] of Object.entries(member.info)) flat["info." + k] = v;
    delete flat.info;
  }
  if (member.frame) {
    for (const [k, v] of Object.entries(member.frame)) flat["frame." + k] = v;
    delete flat.frame;
  }
  delete flat.uid;
  return flat;
}

function flattenCustomFront(front) {
  const flat = { ...front };
  if (front.frame) {
    for (const [k, v] of Object.entries(front.frame)) flat["frame." + k] = v;
    delete flat.frame;
  }
  delete flat.uid;
  return flat;
}

// CSV helper
function toCSV(rows) {
  const headers = [...new Set(rows.flatMap((r) => Object.keys(r)))];
  const escape = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const lines = [
    headers.join(","),
    ...rows.map((r) =>
      headers
        .map((h) => escape(Array.isArray(r[h]) ? r[h].join(";") : r[h]))
        .join(","),
    ),
  ];
  return lines.join("\n");
}

// Download
function download(data, filename, type) {
  const blob = new Blob([data], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// Progress wrapper
async function doWithProgress(stageName, progressStart, progressEnd, fn) {
  setStatus(stageName);
  setProgress(progressStart);
  const result = await fn();
  setProgress(progressEnd);
  return result;
}

// Fetch functions
async function getHistoryForMember(memberId, memberName, key) {
  const data = await api(`/frontHistory/member/${memberId}`, key);
  return (data || [])
    .filter((h) => h.content)
    .map((h) => {
      const content = { ...h.content };
      content.member = memberName;
      content.id = h.id;
      delete content.uid;
      ["startTime", "endTime", "lastOperationTime"].forEach((t) => {
        if (content[t]) content[t] = new Date(content[t]).toISOString();
      });
      return content;
    });
}

async function getNotesForMember(memberId, memberName, sysId, key) {
  const data = await api(`/notes/${sysId}/${memberId}`, key);
  return (data || [])
    .filter((n) => n.content)
    .map((n) => {
      const c = { ...n.content };
      c.member = memberName;
      delete c.uid;
      return c;
    });
}

async function getBoardForMember(memberId, memberName, memberIdNameMap, key) {
  const data = await api(`/board/member/${memberId}`, key);
  return (data || [])
    .filter((m) => m.content)
    .map((m) => {
      const c = { ...m.content };
      c.writtenFor = memberName;
      c.writtenBy = memberIdNameMap[c.writtenBy] || c.writtenBy;
      if (c.writtenAt) c.writtenAt = new Date(c.writtenAt).toISOString();
      delete c.uid;
      return c;
    });
}

async function getCustomFronts(sysId, key) {
  const data = await api(`/customFronts/${sysId}`, key);
  return (data || [])
    .filter((cf) => cf.content)
    .map((cf) => ({ ...cf.content, id: cf.id }));
}

async function getPolls(sysId, memberIdNameMap, key) {
  const data = await api(`/polls/${sysId}`, key);
  const votes = [],
    options = [];
  (data || [])
    .filter((p) => p.content)
    .forEach((p) => {
      const poll = { ...p.content };
      (poll.votes || []).forEach((v) => {
        votes.push({
          pollId: poll.id,
          pollName: poll.name,
          voter: memberIdNameMap[v.id] || v.id,
          vote: v.vote,
          comment: v.comment,
        });
      });
      (poll.options || []).forEach((o) => {
        options.push({
          pollId: poll.id,
          pollName: poll.name,
          optionName: o.name,
          optionColor: o.color,
        });
      });
    });
  return { votes, options };
}

async function getChatChannels(key) {
  const data = await api(`/chat/channels`, key);
  return (data || [])
    .filter((c) => c.content)
    .map((c) => ({ ...c.content, id: c.id }));
}

async function getChatMessages(channelId, channelName, memberIdNameMap, key) {
  let allMessages = [];
  let url = `/chat/messages/${channelId}?limit=100&sortBy=writtenAt&sortOrder=1`;
  while (url) {
    const data = await api(url, key);
    if (!data || !data.length) break;
    allMessages.push(
      ...data
        .filter((m) => m.content)
        .map((m) => {
          const c = { ...m.content };
          c.channel = channelName;
          c.writer = memberIdNameMap[c.writer] || c.writer;
          if (c.writtenAt) c.writtenAt = new Date(c.writtenAt).toISOString();
          delete c.uid;
          return c;
        }),
    );
    url = data.length
      ? `/chat/messages/${channelId}?limit=100&skipTo=${data[data.length - 1].id}&sortBy=writtenAt&sortOrder=1`
      : null;
  }
  return allMessages;
}

async function getCommentsForDocument(docId, docType, key) {
  const data = await api(`/comments/${docType}/${docId}`, key);
  return (data || [])
    .filter((c) => c.content)
    .map((c) => {
      const content = { ...c.content, docType, docId };
      delete content.uid;
      return content;
    });
}

// Main export (updated for history comments)
async function exportMembers() {
  const btn = $("exportBtn");
  const key = $("apikey").value.trim();
  const format = getFormat();

  const includeHistory = $("exportHistory").checked;
  const includeNotes = $("exportNotes").checked;
  const includeBoard = $("exportBoard").checked;
  const includeCustomFronts = $("exportCustomFronts").checked;
  const includePolls = $("exportPolls").checked;
  const includeChat = $("exportChat").checked;
  const includeComments = $("exportComments").checked;

  if (!key) {
    alert("Please enter API key");
    return;
  }
  btn.disabled = true;

  try {
    const { id: sysId } = await doWithProgress(
      "Fetching system...",
      0,
      5,
      async () => await api("/me", key),
    );
    const membersRaw = await doWithProgress(
      "Fetching members...",
      5,
      20,
      async () => await api(`/members/${sysId}`, key),
    );
    const members = (membersRaw || [])
      .filter((m) => m?.content)
      .map((m) => ({ ...m.content, id: m.id }));
    const memberIdNameMap = Object.fromEntries(
      members.map((m) => [m.id, m.name]),
    );
    const fields = await doWithProgress(
      "Fetching custom fields...",
      20,
      30,
      async () => await api(`/customFields/${sysId}`, key),
    );
    const fieldLookup = Object.fromEntries(
      fields.filter((f) => f.content).map((f) => [f.id, f.content.name]),
    );
    const buckets = await doWithProgress(
      "Fetching privacy buckets...",
      30,
      40,
      async () => await api("/privacyBuckets", key),
    );
    const bucketLookup = Object.fromEntries(
      buckets.filter((b) => b.content).map((b) => [b.id, b.content.name]),
    );

    // Process members
    const memberRows = await doWithProgress(
      "Processing members...",
      40,
      50,
      async () => {
        return members.map(flatten).map((r) => {
          const out = {};
          for (const [k, v] of Object.entries(r)) {
            if (k.startsWith("info.")) {
              const id = k.slice(5);
              out[fieldLookup[id] || k] = v;
            } else out[k] = v;
          }
          if (Array.isArray(out.buckets))
            out.buckets = out.buckets.map((b) => bucketLookup[b] || b);
          return out;
        });
      },
    );
    download(
      format === "json"
        ? JSON.stringify(memberRows, null, 2)
        : toCSV(memberRows),
      format === "json" ? "members.json" : "members.csv",
      format === "json" ? "application/json" : "text/csv",
    );
    setStatus("Download ready for members");

    // Progress step
    let progressStart = 50;
    const totalTasks =
      includeHistory +
      includeNotes +
      includeBoard +
      includeCustomFronts +
      includePolls +
      includeChat +
      includeComments;
    const progressStep = 50 / (totalTasks || 1);

    // History
    let allHistory = [];
    if (includeHistory) {
      for (let i = 0; i < members.length; i++) {
        allHistory.push(
          ...(await getHistoryForMember(members[i].id, members[i].name, key)),
        );
        setProgress(
          progressStart + Math.round(((i + 1) / members.length) * progressStep),
        );
        setStatus(`Fetching history: ${i + 1}/${members.length}`);
      }
      download(
        format === "json"
          ? JSON.stringify(allHistory, null, 2)
          : toCSV(allHistory),
        format === "json" ? "history.json" : "history.csv",
        format === "json" ? "application/json" : "text/csv",
      );
      setStatus("Download ready for history");
      progressStart += progressStep;
    }

    // History Comments
    if (includeComments && allHistory.length) {
      const docsWithComments = allHistory
        .filter((h) => h.commentCount > 0)
        .map((h) => h.id);
      console.log("docsWithComments", docsWithComments);
      const allComments = [];
      for (let i = 0; i < docsWithComments.length; i++) {
        const comments = await getCommentsForDocument(
          docsWithComments[i],
          "frontHistory",
          key,
        );
        allComments.push(...comments);
        setProgress(
          progressStart +
            Math.round(((i + 1) / docsWithComments.length) * progressStep),
        );
        setStatus(`Fetching comments: ${i + 1}/${docsWithComments.length}`);
      }
      if (allComments.length) {
        console.log("allComments", allComments);
        download(
          format === "json"
            ? JSON.stringify(allComments, null, 2)
            : toCSV(allComments),
          format === "json" ? "comments.json" : "comments.csv",
          format === "json" ? "application/json" : "text/csv",
        );
      }
      setStatus("Download ready for comments");
      progressStart += progressStep;
    }

    // Notes
    if (includeNotes) {
      const allNotes = [];
      for (let i = 0; i < members.length; i++) {
        allNotes.push(
          ...(await getNotesForMember(
            members[i].id,
            members[i].name,
            sysId,
            key,
          )),
        );
        setProgress(
          progressStart + Math.round(((i + 1) / members.length) * progressStep),
        );
        setStatus(`Fetching notes: ${i + 1}/${members.length}`);
      }
      download(
        format === "json" ? JSON.stringify(allNotes, null, 2) : toCSV(allNotes),
        format === "json" ? "notes.json" : "notes.csv",
        format === "json" ? "application/json" : "text/csv",
      );
      setStatus("Download ready for notes");
      progressStart += progressStep;
    }

    // Board
    if (includeBoard) {
      const allBoard = [];
      for (let i = 0; i < members.length; i++) {
        allBoard.push(
          ...(await getBoardForMember(
            members[i].id,
            members[i].name,
            memberIdNameMap,
            key,
          )),
        );
        setProgress(
          progressStart + Math.round(((i + 1) / members.length) * progressStep),
        );
        setStatus(`Fetching board messages: ${i + 1}/${members.length}`);
      }
      download(
        format === "json" ? JSON.stringify(allBoard, null, 2) : toCSV(allBoard),
        format === "json" ? "board.json" : "board.csv",
        format === "json" ? "application/json" : "text/csv",
      );
      setStatus("Download ready for board messages");
      progressStart += progressStep;
    }

    // Custom Fronts
    if (includeCustomFronts) {
      const cfRaw = await getCustomFronts(sysId, key);
      const customFronts = cfRaw.map(flattenCustomFront);
      download(
        format === "json"
          ? JSON.stringify(customFronts, null, 2)
          : toCSV(customFronts),
        format === "json" ? "customFronts.json" : "customFronts.csv",
        format === "json" ? "application/json" : "text/csv",
      );
      setStatus("Download ready for custom fronts");
      progressStart += progressStep;
    }

    // Polls
    if (includePolls) {
      const { votes, options } = await getPolls(sysId, memberIdNameMap, key);
      if (votes.length)
        download(
          format === "json" ? JSON.stringify(votes, null, 2) : toCSV(votes),
          format === "json" ? "pollVotes.json" : "pollVotes.csv",
          format === "json" ? "application/json" : "text/csv",
        );
      if (options.length)
        download(
          format === "json" ? JSON.stringify(options, null, 2) : toCSV(options),
          format === "json" ? "pollOptions.json" : "pollOptions.csv",
          format === "json" ? "application/json" : "text/csv",
        );
      setStatus("Download ready for polls");
      progressStart += progressStep;
    }

    // Chat
    if (includeChat) {
      const channels = await getChatChannels(key);
      const allMessages = [];
      for (let i = 0; i < channels.length; i++) {
        allMessages.push(
          ...(await getChatMessages(
            channels[i].id,
            channels[i].name,
            memberIdNameMap,
            key,
          )),
        );
        setProgress(
          progressStart +
            Math.round(((i + 1) / channels.length) * progressStep),
        );
        setStatus(`Fetching chat messages: ${i + 1}/${channels.length}`);
      }
      download(
        format === "json" ? JSON.stringify(channels, null, 2) : toCSV(channels),
        format === "json" ? "chatChannels.json" : "chatChannels.csv",
        format === "json" ? "application/json" : "text/csv",
      );
      download(
        format === "json"
          ? JSON.stringify(allMessages, null, 2)
          : toCSV(allMessages),
        format === "json" ? "chatMessages.json" : "chatMessages.csv",
        format === "json" ? "application/json" : "text/csv",
      );
      setStatus("Download ready for chat channels & messages");
      progressStart += progressStep;
    }

    setProgress(100);
  } catch (e) {
    console.error(e);
    setStatus("Error: " + e.message);
  }

  btn.disabled = false;
}

document.addEventListener("DOMContentLoaded", () => {
  $("exportBtn").addEventListener("click", exportMembers);
  $("apikey").addEventListener("keydown", (e) => {
    if (e.key === "Enter") exportMembers();
  });
});
