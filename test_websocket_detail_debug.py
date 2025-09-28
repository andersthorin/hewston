#!/usr/bin/env python3
"""
Debug script to reproduce WebSocket message error spam on run detail pages.
This script simulates different WebSocket connection patterns and message types
that might occur when viewing individual run detail pages vs. the runs list.
"""

import asyncio
import websockets
import json
import time
import sys

async def test_websocket_connection(run_id: str, test_name: str):
    """Test WebSocket connection with different message patterns."""
    print(f"\n=== {test_name} for run: {run_id} ===")
    
    uri = f"ws://127.0.0.1:8001/api/v1/runs/{run_id}/stream"
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"✅ Connected to {uri}")
            
            # Wait a moment for auto-subscription
            await asyncio.sleep(0.5)
            
            # Test different message patterns that might cause errors
            test_messages = [
                # Valid control message (should work)
                '{"t": "ctrl", "cmd": "play"}',
                
                # Invalid JSON (should cause JSON decode error)
                '{invalid json}',
                
                # Empty message
                '',
                
                # Message without type field
                '{"data": "test"}',
                
                # Message with null type
                '{"type": null}',
                
                # Message with invalid type
                '{"type": "invalid_type"}',
                
                # Frontend-style message that might not be handled
                '{"action": "subscribe", "runId": "' + run_id + '"}',
                
                # Another control message
                '{"t": "ctrl", "cmd": "pause"}',
                
                # Malformed control message
                '{"t": "ctrl"}',  # missing cmd
                
                # Large message
                '{"type": "ping", "data": "' + 'x' * 1000 + '"}',
            ]
            
            for i, msg in enumerate(test_messages):
                print(f"  Sending message {i+1}: {msg[:50]}{'...' if len(msg) > 50 else ''}")
                try:
                    await websocket.send(msg)
                    await asyncio.sleep(0.1)  # Small delay between messages
                except Exception as e:
                    print(f"    ❌ Error sending message: {e}")
            
            # Wait for any responses
            print("  Waiting for responses...")
            try:
                # Try to receive messages for a short time
                await asyncio.wait_for(websocket.recv(), timeout=2.0)
            except asyncio.TimeoutError:
                print("  No responses received (timeout)")
            except Exception as e:
                print(f"  Response error: {e}")
                
    except Exception as e:
        print(f"❌ Connection failed: {e}")

async def test_multiple_connections(run_id: str):
    """Test multiple simultaneous connections to the same run."""
    print(f"\n=== Testing multiple connections to run: {run_id} ===")
    
    uri = f"ws://127.0.0.1:8001/api/v1/runs/{run_id}/stream"
    connections = []
    
    try:
        # Create multiple connections
        for i in range(3):
            ws = await websockets.connect(uri)
            connections.append(ws)
            print(f"✅ Connection {i+1} established")
            await asyncio.sleep(0.1)
        
        # Send messages from each connection
        for i, ws in enumerate(connections):
            await ws.send('{"t": "ctrl", "cmd": "play"}')
            print(f"  Sent play command from connection {i+1}")
            await asyncio.sleep(0.1)
        
        # Wait a bit
        await asyncio.sleep(1)
        
        # Close connections
        for i, ws in enumerate(connections):
            await ws.close()
            print(f"  Closed connection {i+1}")
            
    except Exception as e:
        print(f"❌ Multiple connection test failed: {e}")
        # Clean up any open connections
        for ws in connections:
            try:
                await ws.close()
            except:
                pass

async def test_rapid_messages(run_id: str):
    """Test rapid message sending that might overwhelm the server."""
    print(f"\n=== Testing rapid messages for run: {run_id} ===")
    
    uri = f"ws://127.0.0.1:8001/api/v1/runs/{run_id}/stream"
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"✅ Connected to {uri}")
            
            # Send many messages rapidly
            messages = [
                '{"t": "ctrl", "cmd": "play"}',
                '{"t": "ctrl", "cmd": "pause"}',
                '{"type": "ping"}',
                '{"invalid": "message"}',
            ]
            
            print("  Sending 20 rapid messages...")
            for i in range(20):
                msg = messages[i % len(messages)]
                await websocket.send(msg)
                # Very small delay
                await asyncio.sleep(0.01)
            
            print("  Waiting for server to process...")
            await asyncio.sleep(2)
            
    except Exception as e:
        print(f"❌ Rapid message test failed: {e}")

async def main():
    """Run all WebSocket tests."""
    print("🔍 WebSocket Detail Page Error Debugging")
    print("=" * 50)
    
    # Test with different run IDs
    test_runs = ["demo-run", "05a0b0f6e429450f95d2598db225778b"]
    
    for run_id in test_runs:
        # Test basic connection with various message types
        await test_websocket_connection(run_id, "Basic Message Tests")
        
        # Test multiple connections
        await test_multiple_connections(run_id)
        
        # Test rapid messages
        await test_rapid_messages(run_id)
        
        print(f"\n{'='*50}")
        print("Waiting 3 seconds before next test...")
        await asyncio.sleep(3)
    
    print("\n✅ All tests completed!")
    print("Check the BFF logs for any 'websocket.message_error' events.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        sys.exit(1)
