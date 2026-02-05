"""
OpenClaw Gateway WebSocket Client
Handles connection, authentication, and agent messaging
"""

import json
import asyncio
import websockets
from typing import Optional, Dict, Any
import uuid


class OpenClawClient:
    """WebSocket client for OpenClaw Gateway"""
    
    def __init__(self, url: str = "ws://127.0.0.1:18789", token: Optional[str] = None):
        self.url = url
        self.token = token
        self.ws = None
        self.connected = False
        self.pending_requests = {}
        
    async def connect(self):
        """Connect and authenticate with the gateway"""
        try:
            self.ws = await websockets.connect(self.url)
            
            # Start message handler
            asyncio.create_task(self._handle_messages())
            
            # Wait for connect.challenge
            challenge = await self._wait_for_event("connect.challenge")
            
            # Send connect request
            connect_params = {
                "minProtocol": 3,
                "maxProtocol": 3,
                "client": {
                    "id": "voice-assistant",
                    "version": "1.0.0",
                    "platform": "macos",
                    "mode": "operator"
                },
                "role": "operator",
                "scopes": ["operator.read", "operator.write"],
                "caps": [],
                "commands": [],
                "permissions": {},
                "locale": "en-US",
                "userAgent": "openclaw-voice-assistant/1.0.0"
            }
            
            # Add auth if token provided
            if self.token:
                connect_params["auth"] = {"token": self.token}
            
            # Add device signature if challenge provided
            if challenge and "payload" in challenge:
                connect_params["device"] = {
                    "id": "voice-assistant-device",
                    "nonce": challenge["payload"].get("nonce")
                }
            
            response = await self._request("connect", connect_params)
            
            if response.get("ok"):
                self.connected = True
                print("✅ Connected to OpenClaw Gateway")
                return True
            else:
                print(f"❌ Connection failed: {response.get('error')}")
                return False
                
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from gateway"""
        if self.ws:
            await self.ws.close()
            self.connected = False
    
    async def send_message(self, text: str, to: Optional[str] = None, 
                          channel: str = "telegram") -> Optional[str]:
        """
        Send a message to the agent and get response
        
        Args:
            text: Message text
            to: Target user ID (optional, uses main session if not provided)
            channel: Channel name (telegram, whatsapp, etc.)
            
        Returns:
            Agent response text or None
        """
        if not self.connected:
            print("❌ Not connected to gateway")
            return None
        
        try:
            # Use agent.run method (matches CLI behavior)
            params = {
                "message": text,
                "channel": channel
            }
            
            if to:
                params["to"] = to
            
            # Send request and wait for response
            response = await self._request("agent.run", params, timeout=60)
            
            if response.get("ok"):
                payload = response.get("payload", {})
                reply = payload.get("reply", "")
                return reply
            else:
                error = response.get("error", {})
                print(f"❌ Agent error: {error.get('message', 'Unknown error')}")
                return None
                
        except asyncio.TimeoutError:
            print("❌ Request timeout")
            return None
        except Exception as e:
            print(f"❌ Error sending message: {e}")
            return None
    
    async def _request(self, method: str, params: Dict[str, Any], 
                      timeout: int = 30) -> Dict[str, Any]:
        """Send a request and wait for response"""
        request_id = str(uuid.uuid4())
        
        request = {
            "type": "req",
            "id": request_id,
            "method": method,
            "params": params
        }
        
        # Create future for response
        future = asyncio.Future()
        self.pending_requests[request_id] = future
        
        # Send request
        await self.ws.send(json.dumps(request))
        
        # Wait for response with timeout
        try:
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
        finally:
            # Clean up
            self.pending_requests.pop(request_id, None)
    
    async def _wait_for_event(self, event_name: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
        """Wait for a specific event"""
        future = asyncio.Future()
        self.pending_requests[f"event:{event_name}"] = future
        
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            return None
        finally:
            self.pending_requests.pop(f"event:{event_name}", None)
    
    async def _handle_messages(self):
        """Handle incoming messages"""
        try:
            async for message in self.ws:
                data = json.loads(message)
                msg_type = data.get("type")
                
                if msg_type == "res":
                    # Response to a request
                    request_id = data.get("id")
                    if request_id in self.pending_requests:
                        future = self.pending_requests[request_id]
                        if not future.done():
                            future.set_result(data)
                
                elif msg_type == "event":
                    # Event notification
                    event_name = data.get("event")
                    event_key = f"event:{event_name}"
                    if event_key in self.pending_requests:
                        future = self.pending_requests[event_key]
                        if not future.done():
                            future.set_result(data)
        
        except websockets.exceptions.ConnectionClosed:
            print("🔌 Connection closed")
            self.connected = False
        except Exception as e:
            print(f"❌ Message handler error: {e}")
            self.connected = False


async def test_client():
    """Test the WebSocket client"""
    client = OpenClawClient()
    
    print("Connecting to OpenClaw Gateway...")
    if await client.connect():
        print("Sending test message...")
        response = await client.send_message("Привіт, це тест WebSocket клієнта!", to="452675801")
        
        if response:
            print(f"✅ Got response: {response[:100]}...")
        else:
            print("❌ No response received")
        
        await client.disconnect()
    else:
        print("❌ Failed to connect")


if __name__ == "__main__":
    asyncio.run(test_client())
