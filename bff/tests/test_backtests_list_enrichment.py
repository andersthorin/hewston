"""List Enrichment Tests (Epic 15.2).

Validates that the BFF list enrichment logic attaches summary metrics
for terminal runs. This test calls the endpoint function directly to
avoid router conflicts with the generic proxy route for GET /backtests.
"""

from unittest.mock import MagicMock

import pytest

from bff.api.backtests import list_backtests


def create_mock_response(data: dict, status_code: int = 200):
    """Create a minimal MagicMock HTTP response with JSON body."""
    resp = MagicMock()
    resp.status_code = status_code
    import json

    payload = json.dumps(data).encode()
    resp.content = payload
    resp.body = payload
    return resp


class TestBacktestsListEnrichment:
    """Tests for enriched backtests list returned by the BFF."""

    @pytest.mark.asyncio
    async def test_enriches_terminal_runs_with_metrics(
        self,
        mock_backend_client,
        mock_backend_response,
    ):
        """Attaches summary metrics for COMPLETED runs in the list response."""
        # Arrange: backend returns a COMPLETED run in the list, then metrics for that run
        backend_list = {
            "items": [
                {
                    "id": "run-1",
                    "status": "COMPLETED",
                    "strategy_id": "sma",
                    "created_at": "2025-01-01T00:00:00Z",
                }
            ],
            "total": 1,
            "limit": 20,
            "offset": 0,
        }
        metrics = {
            "total_return": 0.1234,
            "sharpe_ratio": 1.23,
            "max_drawdown": -0.055,
            "win_rate": 0.55,
        }

        mock_backend_client.request.side_effect = [
            create_mock_response(backend_list),
            create_mock_response(metrics),
        ]

        # Call the enriched list function directly with mocked deps
        result = await list_backtests(
            limit=20,
            offset=0,
            symbol=None,
            strategy_id=None,
            run_from=None,
            run_to=None,
            order="-created_at",
            backend_client=mock_backend_client,
            redis_client=None,
        )

        # Assert
        assert result["total"] == 1
        assert len(result["items"]) == 1
        row = result["items"][0]
        assert row["backtest_id"] == "run-1"
        assert row["status"].upper() == "COMPLETED"
        # Metrics attached
        assert row["total_return"] == metrics["total_return"]
        assert row["sharpe_ratio"] == metrics["sharpe_ratio"]
        assert row["max_drawdown"] == metrics["max_drawdown"]
        assert row["win_rate"] == metrics["win_rate"]
        # Meta includes fan-out call
        backend_calls_min_2 = 2
        assert result["meta"]["backend_calls"] >= backend_calls_min_2
