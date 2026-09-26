# One-command local startup

After the existing backend and frontend dependencies are installed, run from the
repository root:

```bash
python3 scripts/dev.py
```

Open **http://127.0.0.1:5173** when the launcher prints `প্রস্তুত`.
The API is at **http://127.0.0.1:8000**, with health at `/health` and API docs at
`/docs`. Press **Ctrl+C** in the launcher terminal to stop both servers.
SIGTERM to the launcher also stops both services.

## Setup and behavior

- Supported environment: Linux, Python 3.11/3.12 and Node.js 22.12+. Follow the
  [root setup](../README.md#local-backend-setup), then run
  `npm --prefix apps/web ci`. The launcher does not install dependencies.
- No virtual-environment activation is needed: it selects the repository's
  `.venv/bin/python` and installed Vite directly. It starts one Uvicorn worker
  and one Vite server; their logs remain visible in the same terminal.
- Both servers bind only to `127.0.0.1`. Ports stay fixed at 8000 and 5173 to match
  the current client API URL and API CORS configuration. The launcher does not
  silently select another port or terminate a server that already owns a port.
- Both ports and dependencies/settings are checked before launching. Vite also
  uses `--strictPort`; Uvicorn rejects a bind conflict. A process that races to
  occupy a port after the precheck causes startup failure and sibling cleanup.
- The ready message follows HTTP 200 responses from API `/health` and web `/`.
  Local probes bypass HTTP proxy environment variables. Readiness checks do not
  open the database; normal project requests use the existing database behavior.
- A server's unexpected exit, including exit 0, stops its sibling and returns 1.
  Readiness has a 30-second deadline after spawning; failed startup returns 1.
  Dependency prechecks each have a 10-second timeout. Ctrl+C/SIGTERM during normal
  serving returns 0 after cleanup.
- Child services run in their own process groups. Shutdown signals only groups
  started by this launcher, allows up to five seconds for graceful shutdown,
  then kills remaining processes in those groups. It does not search for or kill
  unrelated Python, Node or port-owning processes.
- Vite provides its usual frontend hot updates. API auto-reload is not enabled;
  stop and rerun the command after changing Python source.

The script resolves paths from its own location, so an absolute invocation works
from another directory:

```bash
python3 /path/to/animation/scripts/dev.py
```

The API's working directory is always the repository root. `ANIMATION_DB_PATH`
is inherited; a relative override is therefore relative to that root. Use an
absolute path for disposable data or an existing database outside the repository:

```bash
ANIMATION_DB_PATH=/tmp/animation-demo.db python3 scripts/dev.py
```

The normal default remains `data/animation.db`. The launcher does not request a
sample job or load an AI model. It preserves the current application's settings
and database migration behavior when you use the API/UI.

## Troubleshooting and limits

- `port ব্যস্ত`: stop the server currently using the named port, then rerun. The
  legacy `web_app.py` also uses 8000 and cannot run alongside this API there.
- Missing `.venv`, Node or Vite: follow the setup commands in the READMEs.
  Invalid backend dependencies/settings produce a startup error before either
  server is launched; check the installed requirements and `ANIMATION_DB_PATH`.
- If a server exits or readiness times out, inspect its terminal log. The launcher
  shuts down the other service before exiting.
- This is a foreground development command, not a daemon, production deployment
  or crash-recovery service. SIGKILL of the launcher itself, power loss, or a child
  deliberately escaping its process group cannot guarantee orderly cleanup.
  Forced worker termination does not add job recovery/resume support.
- Windows/macOS support, configurable ports and API auto-reload are outside this
  step. Separate server commands remain documented in the READMEs.

Verification and current limitations: [startup checkpoint](startup-checkpoint.md).
