const BASE_URL = "https://api.apparyllis.com/v1";

const $ = (id) => document.getElementById(id);

const setStatus = (m) => ($("status").textContent = m);
const setProgress = (v) => ($("progressBar").style.width = v + "%");

function getFormat() {
  const el = document.querySelector('input[name="format"]:checked');
  return el ? el.value : "csv";
}

async function api(path, key) {
  const r = await fetch(BASE_URL + path, {
    headers: { Authorization: key },
  });

  if (!r.ok) {
    const txt = await r.text();
    throw new Error(`API ${r.status}: ${txt}`);
  }

  return r.json();
}

function flatten(member) {
  const flat = { ...member };

  if (member.info) {
    for (const [k, v] of Object.entries(member.info)) {
      flat["info." + k] = v;
    }
    delete flat.info;
  }

  if (member.frame) {
    for (const [k, v] of Object.entries(member.frame)) {
      flat["frame." + k] = v;
    }
    delete flat.frame;
  }

  return flat;
}

function toCSV(rows) {
  const headers = [...new Set(rows.flatMap((r) => Object.keys(r)))];

  const escape = (v) =>
    `"${String(v ?? "")
      .replace(/"/g, '""')}"`;

  const lines = [
    headers.join(","),
    ...rows.map((r) =>
      headers
        .map((h) =>
          escape(Array.isArray(r[h]) ? r[h].join(";") : r[h])
        )
        .join(",")
    ),
  ];

  return lines.join("\n");
}

function download(data, filename, type) {
  const blob = new Blob([data], { type });
  const url = URL.createObjectURL(blob);

  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();

  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function exportMembers() {
  const btn = $("exportBtn");
  const key = $("apikey").value.trim();
  const format = getFormat();

  if (!key) {
    alert("Please enter API key");
    return;
  }

  btn.disabled = true;

  try {
    setStatus("Fetching system...");
    setProgress(10);

    const { id: sysId } = await api("/me", key);

    setStatus("Fetching members...");
    setProgress(30);

    const membersRaw = await api(`/members/${sysId}`, key);
    const members = (membersRaw || [])
      .filter((m) => m?.content)
      .map((m) => m.content);

    setStatus("Fetching custom fields...");
    setProgress(50);

    const fields = await api(`/customFields/${sysId}`, key);
    const fieldLookup = Object.fromEntries(
      fields.filter((f) => f.content).map((f) => [f.id, f.content.name])
    );

    setStatus("Fetching privacy buckets...");
    setProgress(70);

    const buckets = await api("/privacyBuckets", key);
    const bucketLookup = Object.fromEntries(
      buckets.filter((b) => b.content).map((b) => [b.id, b.content.name])
    );

    setStatus("Processing...");
    setProgress(85);

    let rows = members.map(flatten).map((r) => {
      const out = {};

      for (const [k, v] of Object.entries(r)) {
        if (k.startsWith("info.")) {
          const id = k.slice(5);
          out[fieldLookup[id] || k] = v;
        } else {
          out[k] = v;
        }
      }

      if (Array.isArray(out.buckets)) {
        out.buckets = out.buckets.map((b) => bucketLookup[b] || b);
      }

      return out;
    });

    setProgress(100);

    if (format === "json") {
      download(JSON.stringify(rows, null, 2), "members.json", "application/json");
      setStatus("JSON download ready");
    } else {
      download(toCSV(rows), "members.csv", "text/csv");
      setStatus("CSV download ready");
    }
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