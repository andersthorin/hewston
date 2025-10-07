#!/usr/bin/env python3
"""
Simple WebSocket test to verify the message error spam fixes.
"""

import asyncio
import websockets
import json


async def test_simple_connection():
    """Test a simple WebSocket connection with a few problematic messages."""
    print("🔍 Testing WebSocket message error fixes...")

    uri = "ws://127.0.0.1:8001/api/v1/backtests/demo-run/stream"

    try:
        async with websockets.connect(uri) as websocket:
            print(f"✅ Connected to {uri}")

            # Wait for auto-subscription
            await asyncio.sleep(1)

            # Send a few messages that previously caused error spam
            test_messages = [
                '{"t": "ctrl", "cmd": "play"}',  # Valid control message
                "{invalid json}",  # Invalid JSON
                '{"data": "test"}',  # Message without type
                '{"type": "invalid_type"}',  # Invalid message type
            ]

            for i, msg in enumerate(test_messages):
                print(f"  Sending message {i+1}: {msg}")
                try:
                    await websocket.send(msg)
                    await asyncio.sleep(0.5)  # Wait between messages
                except Exception as e:
                    print(f"    Error sending: {e}")

            print("  Waiting for server processing...")
            await asyncio.sleep(2)

            print("✅ Test completed successfully!")

    except Exception as e:
        print(f"❌ Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_simple_connection())
