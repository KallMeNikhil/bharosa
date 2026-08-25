import { useEffect, useState } from "react";

import { clearLog, readLog, subscribeToLog } from "../../api/client";
import type { ApiLogEntry } from "../../api/client";
import { Badge, Button, Card, Empty } from "../../components/ui";

function statusTone(entry: ApiLogEntry) {
  if (entry.status === null) return "bad" as const;
  if (entry.status < 300) return "good" as const;
  if (entry.status < 500) return "warn" as const;
  return "bad" as const;
}

function LogEntry({ entry }: { entry: ApiLogEntry }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="log-entry">
      <button type="button" className="log-entry__head" onClick={() => setOpen(!open)}>
        <span className="log-entry__method">{entry.method}</span>
        <span className="log-entry__path">{entry.path}</span>
        <Badge tone={statusTone(entry)}>{entry.status ?? "network"}</Badge>
        <span className="log-entry__meta">{entry.durationMs} ms</span>
      </button>
      {open && (
        <pre>
          {JSON.stringify(
            { request: entry.requestBody ?? null, response: entry.responseBody },
            null,
            2,
          )}
        </pre>
      )}
    </div>
  );
}

export function ApiConsole() {
  const [entries, setEntries] = useState<ApiLogEntry[]>(readLog);

  useEffect(() => subscribeToLog(setEntries), []);

  return (
    <>
      <div className="page-head">
        <div>
          <h1>API console</h1>
          <p>
            Every request this client has made in this session, newest first, with the exact
            body sent and the exact body returned. The public verification endpoint appears here
            without an Authorization header, because it never carries one.
          </p>
        </div>
      </div>

      <Card
        title={`${entries.length} requests`}
        actions={
          <Button
            onClick={() => {
              clearLog();
              setEntries([]);
            }}
          >
            Clear
          </Button>
        }
      >
        {entries.length === 0 ? (
          <Empty>Nothing yet. Move around the console and the calls will land here.</Empty>
        ) : (
          entries.map((entry) => <LogEntry key={entry.id} entry={entry} />)
        )}
      </Card>
    </>
  );
}
