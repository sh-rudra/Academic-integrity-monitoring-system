# Academic Integrity Monitoring System

A client-server prototype for monitoring computer activity during supervised exams or assessments. A Windows agent collects selected activity signals and sends them to a central Flask server, where events are saved in SQLite and shown in a live browser dashboard for review by an authorized invigilator.

> This project does not automatically decide whether someone is cheating. It records activity indicators that require human review and context.

## Features

- Detects active-window changes and records the window title.
- Records the executable path for non-browser applications.
- Attempts to read the current URL from Chrome, Edge, Firefox, and Brave.
- Detects non-empty clipboard text changes.
- Detects USB controller device creation and removal events.
- Sends events from the monitored Windows computer to a central server.
- Stores events permanently in an SQLite database.
- Streams new events to a responsive live dashboard using Server-Sent Events (SSE).
- Includes a PyInstaller specification for building a standalone Windows agent.

## How it works

```text
Monitored Windows PC                          Monitoring PC
+------------------------+                  +--------------------------+
| agent.py / agent.exe   |  HTTP POST       | Flask server             |
|                        +----------------->| POST /log                |
| - active window        |                  |                          |
| - app path/browser URL |                  | SQLite database          |
| - clipboard changes    |                  | monitoring_data.db       |
| - USB changes          |                  |                          |
+------------------------+                  | Live dashboard + SSE     |
                                            | GET / and GET /stream    |
                                            +--------------------------+
```

Each event has this general shape:

```json
{
  "event_type": "WINDOW_CHANGE",
  "timestamp": "2026-11-05 10:30:00",
  "data": {
    "to_app": "Example window title",
    "source": "C:\\Path\\To\\Application.exe"
  }
}
```

The implemented event types are:

| Event type | Information collected |
| --- | --- |
| `WINDOW_CHANGE` | Active window title and either an application path or attempted browser URL |
| `CLIPBOARD` | Newly detected non-empty clipboard text |
| `USB_EVENT` | Whether a USB hardware change was detected as a connection or removal |

## Project structure

```text
.
|-- agent.py              # Windows monitoring agent
|-- server.py             # Flask API, live dashboard, and database setup
|-- agent.spec            # PyInstaller configuration for agent.exe
|-- requirements-agent.txt  # Agent runtime and build dependencies
|-- requirements-server.txt # Flask server dependency
|-- .gitignore            # Excludes generated and private runtime files
|-- monitoring_data.db    # Generated automatically; not tracked by Git
|-- build/                # Generated locally by PyInstaller; not tracked
`-- dist/agent.exe        # Generated locally by PyInstaller; not tracked
```

## Requirements

- Python 3.9 or newer is recommended.
- Windows is required for the monitoring agent because it uses WMI, Win32 APIs, and Windows UI Automation.
- The server and agent computers must be able to reach each other over the network.
- Administrator approval may be needed for firewall rules or endpoint-security software.

## Installation

### 1. Prepare the monitoring server

Open PowerShell in the project directory and create a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-server.txt
```

Find the monitoring computer's IPv4 address:

```powershell
ipconfig
```

The server listens on TCP port `5000`. If Windows Firewall blocks connections, allow inbound access to this port only on the trusted exam network.

### 2. Prepare the Windows agent

On the computer that will be monitored, install the agent dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-agent.txt
```

Open `agent.py` and replace `MONITORING_SERVER_IP` with the monitoring computer's IPv4 address:

```python
MONITORING_SERVER_IP = "192.168.1.10"
```

Use the actual address of the monitoring computer and ensure both computers are on the intended network. You do not normally need to put an IP address in `server.py`: it already listens on `0.0.0.0`, allowing connections through any network interface on port `5000`.

## Running the system

Start the server on the monitoring computer:

```powershell
python server.py
```

Open the dashboard in a browser:

```text
http://localhost:5000
```

From another computer on the same network, use:

```text
http://MONITORING_PC_IP:5000
```

Then start the agent on the authorized participant computer:

```powershell
python agent.py
```

New events should appear immediately in the dashboard. The page keeps the latest 50 live cards in the current browser session, while all accepted events remain in `monitoring_data.db`.

Stop either Python process with `Ctrl+C`. The prebuilt `dist/agent.exe` is windowless, so it must be stopped with Task Manager or another authorized process-management method.

## Building the Windows executable

The server address is compiled into the executable. Update `MONITORING_SERVER_IP` in `agent.py` before building, then run from an activated environment where `requirements-agent.txt` has been installed:

```powershell
python -m PyInstaller agent.spec --noconfirm
```

The standalone program will be written to `dist\agent.exe`. The existing executable must be rebuilt whenever the server address or agent code changes.

Only copy `dist\agent.exe` to an authorized Windows participant computer. The `build\` directory is temporary build output and is not required for deployment.

## Server endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/` | Displays the live monitoring dashboard |
| `POST` | `/log` | Receives an event, stores it, and publishes it to dashboard subscribers |
| `GET` | `/stream` | Provides the live SSE event stream |

The `logs` table in `monitoring_data.db` contains:

| Column | Type | Purpose |
| --- | --- | --- |
| `id` | `INTEGER` | Auto-incrementing primary key |
| `timestamp` | `TEXT` | Agent-provided local timestamp |
| `event_type` | `TEXT` | Event category |
| `details` | `TEXT` | JSON-encoded event details |

## Current limitations

- There is no authentication, encryption, role-based access, or device identity.
- The server accepts client-provided timestamps and event payloads without validation.
- Multiple agents would write into the same log without identifying which computer sent an event.
- The dashboard shows only events received after the page connects; it does not load database history.
- Browser URL capture depends on the browser's UI structure and may return `URL Hidden/Private`.
- USB events report a generic hardware change rather than a device name or serial number.
- Clipboard monitoring can capture highly sensitive information.
- The agent reports activity signals but does not score, classify, or prove academic misconduct.

Before production use, add authenticated agents, HTTPS, device/session identifiers, input limits, a historical review interface, audit controls, and a documented retention/deletion policy.

## Responsible use and privacy

Use this system only for an authorized assessment where participants have received clear notice and provided any consent required by institutional policy and applicable law. Collect only the data necessary for the assessment, restrict dashboard and database access, define a short retention period, and provide a review or appeal process. Do not deploy the current prototype over the public internet or use individual events as conclusive evidence of misconduct.

## Troubleshooting

- **The agent reports a connection failure:** Verify `SERVER_URL`, start the server first, confirm both computers can communicate, and check TCP port `5000` in the firewall.
- **No events appear on the dashboard:** Keep the dashboard open before generating a new event; it displays the live stream rather than existing database rows.
- **The browser source is hidden:** UI Automation could not access the address bar. Browser updates, permissions, private windows, or a different UI layout can cause this.
- **The executable sends events to the wrong server:** Change `MONITORING_SERVER_IP` in `agent.py` and rebuild `agent.exe`.
- **Endpoint security flags the agent:** Monitoring behavior and a windowless executable may look suspicious. Use code signing and obtain explicit administrator approval rather than bypassing security controls.
