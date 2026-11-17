import pytest
import asyncio
from backend.app.services.phase3 import run_scan

@pytest.mark.asyncio
async def test_scan_simple():
    result = await run_scan("tests/fixtures/lockfile_v2.json")
    # Expect no OSV errors; vulnerabilities may be empty.
    assert isinstance(result.vulnerabilities, dict)