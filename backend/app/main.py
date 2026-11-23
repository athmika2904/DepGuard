
import json
import os
import tempfile
from pathlib import Path

import networkx as nx
import uvicorn

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from .models.scan_result import ScanResultModel
from .services.phase3 import run_scan
from .services.lockfile_parser import LockfileParseError

app = FastAPI(title="DepGuard API")

# Allow the React dev server to call the API
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

MAX_UPLOAD_SIZE = 5 * 1024 * 1024
CHUNK_SIZE = 64 * 1024


@app.get("/health")
async def health_check():
    return {"status": "ok"}


def serialize_graph(graph: nx.DiGraph) -> dict:
    nodes = []

    for node_id, attrs in graph.nodes(data=True):
        nodes.append({
            "id": node_id,
            **{
                key: sorted(value) if isinstance(value, set) else value
                for key, value in attrs.items()
            }
        })

    edges = []

    for source, target, attrs in graph.edges(data=True):
        edges.append({
            "source": source,
            "target": target,
            **{
                key: sorted(value) if isinstance(value, set) else value
                for key, value in attrs.items()
            }
        })

    return {"nodes": nodes, "edges": edges}


@app.post("/api/scan", response_model=ScanResultModel)
async def scan_endpoint(lockfile: UploadFile = File(...)):
    temp_path = None
    total_size = 0
    content = bytearray()

    try:
        # Read in chunks to enforce the limit without loading
        # an arbitrarily large upload into memory.
        while True:
            chunk = await lockfile.read(CHUNK_SIZE)

            if not chunk:
                break

            total_size += len(chunk)

            if total_size > MAX_UPLOAD_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail="Lockfile exceeds the 5 MiB upload limit"
                )

            content.extend(chunk)

        try:
            data = json.loads(content)
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is not valid JSON"
            )

        # Accept only supported npm lockfile formats.
        if not isinstance(data, dict):
            raise HTTPException(
                status_code=400,
                detail="Lockfile must contain a JSON object"
            )

        if data.get("lockfileVersion") not in (2, 3):
            raise HTTPException(
                status_code=400,
                detail="Only npm lockfile versions 2 and 3 are supported"
            )

        if not isinstance(data.get("packages"), dict):
            raise HTTPException(
                status_code=400,
                detail="Lockfile must contain a packages object"
            )

        if "" not in data["packages"]:
            raise HTTPException(
                status_code=400,
                detail="Lockfile is missing the root package entry"
            )

        # Use a unique temporary file for each request.
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            encoding="utf-8",
            delete=False
        ) as temp_file:
            json.dump(data, temp_file)
            temp_path = temp_file.name

        try:
            result = await run_scan(temp_path)
        except (LockfileParseError, ValueError) as exc:
            raise HTTPException(
                status_code=400,
                detail="Invalid or unsupported npm lockfile"
            ) from exc
        except Exception as exc:
            # Log the actual exception on the server, not to the client.
            import logging
            logging.exception("DepGuard scan failed")
            raise HTTPException(
                status_code=500,
                detail="Internal scan error"
            ) from exc

        response = ScanResultModel(
            status=result.status,
            vulnerabilities=result.vulnerabilities,
            errors={
                f"{name}@{version}": message
                for (name, version), message in result.errors.items()
            },
            graph=serialize_graph(result.graph),
            risk_summary=getattr(result, "risk_summary", None) or {
                "critical": 0, "high": 0, "medium": 0,
                "low": 0, "unknown": 0, "total": 0,
            },
        )

        return JSONResponse(
            content=jsonable_encoder(response.model_dump())
        )

    finally:
        await lockfile.close()

        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

# Serve frontend static files (built by Vite)
from fastapi.staticfiles import StaticFiles
import pathlib

# Assume frontend build output is placed in '../frontend/dist' relative to this file
static_path = pathlib.Path(__file__).resolve().parents[2] / "frontend" / "dist"
if static_path.is_dir():
    app.mount("/", StaticFiles(directory=str(static_path), html=True), name="frontend")

