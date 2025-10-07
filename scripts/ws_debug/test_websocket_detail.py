#!/usr/bin/env python3
"""
Test script to simulate WebSocket connections to run detail pages
and reproduce the websocket.message_error spam issue.
"""

import asyncio
import websockets
import json
import time


async def test_run_detail_websocket():
    """Test WebSocket connection to a specific run detail page."""

    # Test both demo-run and a real run ID
    test_runs = ["demo-run", "05a0b0f6e429450f95d2598db225778b"]

    for run_id in test_runs:
        print(f"\n=== Testing WebSocket for run: {run_id} ===")

        uri = f"ws://127.0.0.1:8001/api/v1/backtests/{run_id}/stream"

        try:
            async with websockets.connect(uri) as websocket:
                print(f"Connected to {uri}")

                # Send control message like the frontend does
                control_msg = {"t": "ctrl", "cmd": "play"}
                await websocket.send(json.dumps(control_msg))
                print(f"Sent control message: {control_msg}")

                # Wait for responses and potential errors
                try:
                    for i in range(5):  # Listen for 5 messages or timeout
                        message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        print(f"Received: {message}")
                except asyncio.TimeoutError:
                    print("No more messages received (timeout)")

                # Send another control message
                pause_msg = {"t": "ctrl", "cmd": "pause"}
                await websocket.send(json.dumps(pause_msg))
                print(f"Sent control message: {pause_msg}")

                # Wait a bit more
                await asyncio.sleep(1)

        except Exception as e:
            print(f"Error connecting to {run_id}: {e}")

        print(f"=== Finished testing {run_id} ===")
        await asyncio.sleep(2)  # Wait between tests


if __name__ == "__main__":
    asyncio.run(test_run_detail_websocket())
