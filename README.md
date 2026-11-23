
# DepGuard — Dependency Risk Analysis Platform

DepGuard is an explainable software dependency security analysis platform.
It scans npm lockfiles, identifies known vulnerable dependencies using the
Open Source Vulnerabilities (OSV) database, visualizes dependency relationships,
and helps developers understand and prioritize remediation.

## Features

- **Dependency scanning:** Upload npm `package-lock.json` files.
- **Vulnerability discovery:** Query the public OSV vulnerability database.
- **Dependency graph:** Explore direct and transitive package relationships.
- **Risk analysis:** Review explainable risk scores and contributing factors.
- **Remediation guidance:** Inspect compatible fixed versions reported by OSV.
- **Scan history:** Review recent scans stored in browser local storage.
- **JSON export:** Export the latest scan response.

## Frontend technology

- React 18
- TypeScript
- Vite
- Tailwind CSS
- React Router
- Axios
- Recharts
- React Flow
- ELK.js
- Lucide React

## Requirements

Install the following before running the application:

- Node.js and npm
- Python environment with the backend dependencies installed
- A running DepGuard FastAPI backend

## Project structure

```text
frontend/
├── index.html
├── package.json
├── package-lock.json
├── postcss.config.js
├── tailwind.config.js
├── tsconfig.json
├── vite.config.ts
└── src/
    ├── api/
    │   └── client.ts
    ├── components/
    │   ├── EmptyState.tsx
    │   └── Sidebar.tsx
    ├── pages/
    │   ├── Dashboard.tsx
    │   ├── Scan.tsx
    │   ├── Vulnerabilities.tsx
    │   ├── DependencyGraph.tsx
    │   ├── RiskAnalysis.tsx
    │   ├── Remediation.tsx
    │   └── History.tsx
    ├── App.tsx
    ├── index.css
    ├── main.tsx
    └── types.ts
```

## Installation

Open PowerShell in the frontend directory:

```powershell
cd frontend
npm install
```

If dependencies have become inconsistent, remove the installed modules and
lockfile before reinstalling:

```powershell
Remove-Item -Recurse -Force node_modules -ErrorAction SilentlyContinue
Remove-Item -Force package-lock.json -ErrorAction SilentlyContinue
npm install
```

## Run the frontend

```powershell
npm run dev
```

The Vite development server runs at:

```text
http://127.0.0.1:5173
```

## Run the backend

The frontend requires the FastAPI backend to be running separately.

From the project root, activate the backend virtual environment and start
the API using the project's backend startup instructions.

The expected backend address is:

```text
http://127.0.0.1:8000
```

The frontend Vite configuration proxies:

- `/api` to `http://127.0.0.1:8000`
- `/health` to `http://127.0.0.1:8000`

Check backend availability:

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health
```

A successful health check should return HTTP 200.

## Build for production

```powershell
npm run build
```

The production frontend build is generated in:

```text
frontend/dist/
```

Preview the production build:

```powershell
npm run preview
```

## API integration

The frontend uses:

```text
POST /api/scan
```

The lockfile is sent as multipart form data using the field name:

```text
lockfile
```

The response is used to populate the dashboard, vulnerability findings,
dependency graph, risk analysis and remediation pages.

## Risk scoring

DepGuard uses a project-specific heuristic model that considers:

- CVSS severity — 70%
- Dependency directness — 20%
- Remediation availability — 10%

Available factor weights are normalized when some inputs are missing.
A finding without a supported CVSS score is classified as unknown.

These are DepGuard project heuristics, not an official industry-standard
risk formula. CVSS and DepGuard risk scores are different measures.

## Scan history

The frontend stores up to 20 recent scan summaries in browser local storage.
This is local browser history, not backend persistence.

The full scan response is held in application state. Refreshing the page
does not automatically restore the latest complete scan result.

## Important limitations

- The scanner currently targets npm lockfiles.
- Vulnerability information depends on OSV responses and availability.
- Partial scans can occur when some vulnerability lookups fail.
- A recommended fixed version should be reviewed and tested before upgrading.
- The frontend does not automatically modify package manifests or install fixes.
- GitHub integration is not currently included.

## Troubleshooting

### Backend connection error

1. Start the FastAPI backend.
2. Confirm `http://127.0.0.1:8000/health` returns HTTP 200.
3. Restart the Vite frontend if its proxy configuration has changed.

### Dependency installation error

Check the Node.js and npm versions:

```powershell
node --version
npm --version
```

Then reinstall dependencies using the installation instructions above.

### Frontend build error

Run:

```powershell
npm run build
```

Resolve TypeScript errors reported by the build before deploying.

---

DepGuard — Explainable Software Dependency Risk Analysis Platform.
