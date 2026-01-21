# TOR INTEGRATION SOLUTIONS - Complete Guide

**Date:** 2026-01-10
**Purpose:** Comprehensive guide for TOR integration with scraping framework
**Focus:** Multiple approaches from no-install to full control

---

## EXECUTIVE SUMMARY

This guide provides **5 different approaches** to integrate TOR with our scraping framework, ranging from zero-installation cloud proxies to full local TOR control.

**Quick Decision Matrix:**

| Method | Setup Time | Cost | Anonymity | Control | Best For |
|--------|------------|------|-----------|---------|----------|
| Docker TOR | 5 min | Free | High | Full | Development |
| TOR Browser Bundle | 2 min | Free | High | Medium | Quick start |
| Cloud TOR Proxy | 1 min | $$ | Medium | Low | Production scale |
| MCP TOR Server | 10 min | Free | High | Full | Integration |
| TOR as Service | 15 min | Free | High | Full | Production |

---

## METHOD 1: DOCKER TOR (RECOMMENDED - NO INSTALL)

**Pros:** Isolated, portable, easy cleanup, full control
**Cons:** Requires Docker Desktop
**Setup Time:** 5 minutes

### Step 1: Check Docker

```bash
docker --version
# If not installed: Download from https://www.docker.com/products/docker-desktop
```

### Step 2: Pull TOR Image

```bash
# Official TOR image
docker pull dperson/torproxy

# Or Alpine-based (smaller)
docker pull peterdavehello/tor-socks-proxy
```

### Step 3: Run TOR Container

```bash
# Run TOR SOCKS proxy on port 9050
docker run -d \
  --name tor-proxy \
  -p 9050:9050 \
  -p 9051:9051 \
  dperson/torproxy

# Verify it's running
docker ps | grep tor
```

### Step 4: Test Connection

```python
import requests

proxies = {
    'http': 'socks5h://127.0.0.1:9050',
    'https': 'socks5h://127.0.0.1:9050'
}

response = requests.get('https://check.torproject.org/api/ip', proxies=proxies)
print(response.json())  # Should show "IsTor": true
```

### Step 5: Integrate with Scraper

```python
scraper = UltimateScraperEngine(
    use_tor=True,
    tor_proxy='127.0.0.1:9050'
)
```

### Management Commands

```bash
# Start TOR
docker start tor-proxy

# Stop TOR
docker stop tor-proxy

# View logs
docker logs tor-proxy

# Remove container
docker rm -f tor-proxy

# Restart for new identity
docker restart tor-proxy
```

---

## METHOD 2: TOR BROWSER BUNDLE (EASIEST)

**Pros:** Official, includes TOR, GUI available, safest
**Cons:** Heavier, includes browser
**Setup Time:** 2 minutes

### Download

**Windows:**
```
https://www.torproject.org/download/
Download: Tor Browser (Windows, 64-bit)
Size: ~100MB
```

**Extract TOR Binary:**
```bash
# After installation, TOR binary is at:
C:\Users\[User]\Desktop\Tor Browser\Browser\TorBrowser\Tor\tor.exe
```

### Run TOR Separately

```bash
# Navigate to TOR directory
cd "C:\Users\Administrator\Desktop\Tor Browser\Browser\TorBrowser\Tor"

# Run TOR
tor.exe

# TOR will start on default port 9050
```

### Use with Scraper

```python
# TOR is now running on 127.0.0.1:9050
scraper = UltimateScraperEngine(use_tor=True)
result = scraper.scrape_with_tor('http://example.onion')
```

---

## METHOD 3: CLOUD TOR PROXIES (NO INSTALL)

**Pros:** Zero installation, instant use, scalable
**Cons:** Costs money, less anonymous, trust third party
**Setup Time:** 1 minute

### Option A: Bright Data (formerly Luminati)

```python
# Proxy format
proxies = {
    'http': 'http://username:password@tor.brightdata.com:22225',
    'https': 'http://username:password@tor.brightdata.com:22225'
}

# Configure scraper
scraper = UltimateScraperEngine(
    use_proxy=True,
    proxy_list=['http://username:password@tor.brightdata.com:22225']
)
```

**Pricing:** ~$5/GB

### Option B: Oxylabs TOR Proxies

```python
proxies = {
    'http': 'http://customer-USER:PASS@pr.oxylabs.io:7777',
    'https': 'http://customer-USER:PASS@pr.oxylabs.io:7777'
}
```

**Pricing:** Custom

### Option C: SmartProxy TOR

```python
proxies = {
    'http': 'http://user:pass@gate.smartproxy.com:10000',
    'https': 'http://user:pass@gate.smartproxy.com:10000'
}
```

**Pricing:** $12.5/GB

### Integration

```python
from ULTIMATE_UNIFIED_SCRAPER_FIXED import UltimateScraperEngine

scraper = UltimateScraperEngine(
    use_proxy=True,
    proxy_list=['http://user:pass@provider.com:port'],
    proxy_rotation=True
)

result = scraper.adaptive_scrape('http://example.onion')
```

---

## METHOD 4: TOR MCP SERVER (CLAWDBOT INTEGRATION)

**Pros:** Native Clawdbot integration, MCP protocol, easy management
**Cons:** Requires MCP setup
**Setup Time:** 10 minutes

### Check for TOR MCP

```bash
# Search for TOR MCP servers
npm search mcp-tor
npm search mcp-proxy
```

### Custom TOR MCP Server

Create our own TOR MCP server for Clawdbot:

**File: `tor-mcp-server.js`**

```javascript
#!/usr/bin/env node
/**
 * TOR MCP Server for Clawdbot
 * Provides TOR proxy management via MCP protocol
 */

const { Server } = require('@modelcontextprotocol/sdk/server/index.js');
const { StdioServerTransport } = require('@modelcontextprotocol/sdk/server/stdio.js');
const { exec } = require('child_process');
const { promisify } = require('util');

const execAsync = promisify(exec);

const server = new Server({
  name: 'tor-proxy-server',
  version: '1.0.0',
}, {
  capabilities: {
    tools: {},
  },
});

// Tool: Start TOR via Docker
server.setRequestHandler('tools/call', async (request) => {
  const { name, arguments: args } = request.params;

  switch (name) {
    case 'tor_start':
      try {
        await execAsync('docker run -d --name tor-proxy -p 9050:9050 dperson/torproxy');
        return {
          content: [{ type: 'text', text: 'TOR proxy started on 127.0.0.1:9050' }],
        };
      } catch (error) {
        return {
          content: [{ type: 'text', text: `Error: ${error.message}` }],
          isError: true,
        };
      }

    case 'tor_stop':
      try {
        await execAsync('docker stop tor-proxy && docker rm tor-proxy');
        return {
          content: [{ type: 'text', text: 'TOR proxy stopped' }],
        };
      } catch (error) {
        return {
          content: [{ type: 'text', text: `Error: ${error.message}` }],
          isError: true,
        };
      }

    case 'tor_status':
      try {
        const { stdout } = await execAsync('docker ps | grep tor-proxy');
        const isRunning = stdout.trim().length > 0;
        return {
          content: [{
            type: 'text',
            text: `TOR Status: ${isRunning ? 'Running' : 'Stopped'}`
          }],
        };
      } catch (error) {
        return {
          content: [{ type: 'text', text: 'TOR Status: Stopped' }],
        };
      }

    case 'tor_renew_identity':
      try {
        await execAsync('docker restart tor-proxy');
        return {
          content: [{ type: 'text', text: 'TOR identity renewed (new circuit)' }],
        };
      } catch (error) {
        return {
          content: [{ type: 'text', text: `Error: ${error.message}` }],
          isError: true,
        };
      }

    default:
      return {
        content: [{ type: 'text', text: `Unknown tool: ${name}` }],
        isError: true,
      };
  }
});

// List available tools
server.setRequestHandler('tools/list', async () => {
  return {
    tools: [
      {
        name: 'tor_start',
        description: 'Start TOR proxy via Docker on port 9050',
        inputSchema: {
          type: 'object',
          properties: {},
        },
      },
      {
        name: 'tor_stop',
        description: 'Stop TOR proxy',
        inputSchema: {
          type: 'object',
          properties: {},
        },
      },
      {
        name: 'tor_status',
        description: 'Check TOR proxy status',
        inputSchema: {
          type: 'object',
          properties: {},
        },
      },
      {
        name: 'tor_renew_identity',
        description: 'Renew TOR identity (new IP/circuit)',
        inputSchema: {
          type: 'object',
          properties: {},
        },
      },
    ],
  };
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((error) => {
  console.error('Server error:', error);
  process.exit(1);
});
```

### Install and Configure

```bash
# Save script
cd /d/DeadMan_AI_Research/Scripts
# (Script content above)

# Make executable
chmod +x tor-mcp-server.js

# Install dependencies
npm install @modelcontextprotocol/sdk
```

### Add to Claude Desktop Config

**File: `C:\Users\Administrator\AppData\Roaming\Claude\claude_desktop_config.json`**

```json
{
  "mcpServers": {
    "tor-proxy": {
      "command": "node",
      "args": ["D:\\DeadMan_AI_Research\\Scripts\\tor-mcp-server.js"]
    }
  }
}
```

### Use from Clawdbot

```bash
# Start TOR via Clawdbot
clawdbot tui --message "Start the TOR proxy"

# Check status
clawdbot tui --message "What's the TOR proxy status?"

# Renew identity
clawdbot tui --message "Renew TOR identity"
```

---

## METHOD 5: TOR AS WINDOWS SERVICE

**Pros:** Full control, persistent, production-ready
**Cons:** Requires installation and configuration
**Setup Time:** 15 minutes

### Download TOR Expert Bundle

```
URL: https://www.torproject.org/download/tor/
File: tor-win64-[version].zip
Size: ~15MB
```

### Extract and Configure

```bash
# Extract to C:\tor\
# Create torrc config file:
```

**File: `C:\tor\torrc`**

```
# TOR Configuration
SOCKSPort 9050
ControlPort 9051
HashedControlPassword 16:E600ADC1B52C80BB6022A0E999A7734571A451EB6AE50FED489B72E3DF

# Data directory
DataDirectory C:\tor\data

# Log
Log notice file C:\tor\tor.log

# Additional security
CookieAuthentication 0
```

### Generate Hashed Password

```bash
# In C:\tor\
tor.exe --hash-password "your_password_here"
# Copy output to torrc HashedControlPassword
```

### Install as Windows Service

**File: `install_tor_service.bat`** (Run as Administrator)

```batch
@echo off
cd C:\tor\

sc create "TOR" binPath= "C:\tor\tor.exe -f C:\tor\torrc" start= auto
sc description "TOR" "TOR Anonymous Proxy Service"
sc start "TOR"

echo TOR service installed and started
pause
```

### Manage Service

```bash
# Start
net start TOR

# Stop
net stop TOR

# Status
sc query TOR
```

### Control via Python

```python
from stem import Signal
from stem.control import Controller

# Renew TOR identity
with Controller.from_port(port=9051) as controller:
    controller.authenticate(password='your_password')
    controller.signal(Signal.NEWNYM)
    print("New TOR circuit established")
```

---

## COMPARISON TABLE

| Feature | Docker | TOR Browser | Cloud | MCP | Service |
|---------|--------|-------------|-------|-----|---------|
| **Installation** | Docker only | Download | None | Node.js | Full install |
| **Port** | 9050 | 9050 | Custom | 9050 | 9050 |
| **Control** | Full | Medium | Limited | Full | Full |
| **IP Rotation** | Manual | Manual | Auto | Programmatic | Programmatic |
| **Cost** | Free | Free | $$ | Free | Free |
| **Anonymity** | High | Highest | Medium | High | High |
| **Speed** | Fast | Fast | Fast | Fast | Fast |
| **Reliability** | High | High | Very High | High | Very High |

---

## RECOMMENDED SETUP FOR THIS PROJECT

### Phase 1: Development (Use Docker)

```bash
# Quick start with Docker
docker run -d --name tor-proxy -p 9050:9050 dperson/torproxy

# Test
python test_tor_connection.py

# Use with scraper
python darkweb_intelligence_scraper.py --tor --phase both
```

### Phase 2: Production (TOR Service + MCP)

1. Install TOR as Windows Service (persistent)
2. Configure MCP server for Clawdbot integration
3. Use programmatic IP rotation
4. Monitor via Clawdbot dashboard

---

## IMPLEMENTATION SCRIPTS

### Script 1: TOR Connection Tester

**File: `test_tor_connection.py`**

```python
#!/usr/bin/env python3
"""
TOR Connection Tester
Tests if TOR proxy is working correctly
"""

import requests
import json

def test_tor():
    """Test TOR connection"""

    proxies = {
        'http': 'socks5h://127.0.0.1:9050',
        'https': 'socks5h://127.0.0.1:9050'
    }

    print("Testing TOR connection...")
    print("-" * 50)

    try:
        # Test 1: Check TOR Project
        response = requests.get(
            'https://check.torproject.org/api/ip',
            proxies=proxies,
            timeout=30
        )

        data = response.json()
        print(f"IP: {data.get('IP', 'Unknown')}")
        print(f"IsTor: {data.get('IsTor', False)}")

        if data.get('IsTor'):
            print("\n[OK] TOR connection is WORKING!")
            return True
        else:
            print("\n[FAIL] Not connected via TOR")
            return False

    except Exception as e:
        print(f"\n[ERROR] TOR connection failed: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Is TOR running? Check: docker ps | grep tor")
        print("2. Is port 9050 accessible?")
        print("3. Try: docker restart tor-proxy")
        return False

if __name__ == "__main__":
    test_tor()
```

### Script 2: TOR Manager

**File: `tor_manager.py`**

```python
#!/usr/bin/env python3
"""
TOR Manager - Control TOR proxy via Docker
"""

import subprocess
import sys

class TORManager:
    """Manage TOR proxy via Docker"""

    CONTAINER_NAME = "tor-proxy"
    IMAGE = "dperson/torproxy"
    PORT = 9050

    @staticmethod
    def is_running():
        """Check if TOR is running"""
        try:
            result = subprocess.run(
                ['docker', 'ps', '--filter', f'name={TORManager.CONTAINER_NAME}', '--format', '{{.Names}}'],
                capture_output=True,
                text=True
            )
            return TORManager.CONTAINER_NAME in result.stdout
        except:
            return False

    @staticmethod
    def start():
        """Start TOR proxy"""
        if TORManager.is_running():
            print("[INFO] TOR is already running")
            return True

        print("[INFO] Starting TOR proxy...")
        try:
            subprocess.run([
                'docker', 'run', '-d',
                '--name', TORManager.CONTAINER_NAME,
                '-p', f'{TORManager.PORT}:9050',
                TORManager.IMAGE
            ], check=True)
            print(f"[OK] TOR started on 127.0.0.1:{TORManager.PORT}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to start TOR: {e}")
            return False

    @staticmethod
    def stop():
        """Stop TOR proxy"""
        if not TORManager.is_running():
            print("[INFO] TOR is not running")
            return True

        print("[INFO] Stopping TOR...")
        try:
            subprocess.run(['docker', 'stop', TORManager.CONTAINER_NAME], check=True)
            subprocess.run(['docker', 'rm', TORManager.CONTAINER_NAME], check=True)
            print("[OK] TOR stopped")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to stop TOR: {e}")
            return False

    @staticmethod
    def restart():
        """Restart TOR (new identity)"""
        print("[INFO] Restarting TOR for new identity...")
        try:
            subprocess.run(['docker', 'restart', TORManager.CONTAINER_NAME], check=True)
            print("[OK] TOR restarted - new identity")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to restart TOR: {e}")
            return False

    @staticmethod
    def status():
        """Get TOR status"""
        running = TORManager.is_running()
        print(f"TOR Status: {'Running' if running else 'Stopped'}")
        if running:
            print(f"Proxy: socks5h://127.0.0.1:{TORManager.PORT}")
        return running

def main():
    import argparse

    parser = argparse.ArgumentParser(description='TOR Manager')
    parser.add_argument('action', choices=['start', 'stop', 'restart', 'status'],
                        help='Action to perform')
    args = parser.parse_args()

    manager = TORManager()

    if args.action == 'start':
        manager.start()
    elif args.action == 'stop':
        manager.stop()
    elif args.action == 'restart':
        manager.restart()
    elif args.action == 'status':
        manager.status()

if __name__ == "__main__":
    main()
```

---

## QUICK START GUIDE

### For This Project (Docker Method):

```bash
# 1. Start TOR
docker run -d --name tor-proxy -p 9050:9050 dperson/torproxy

# 2. Test connection
cd /d/DeadMan_AI_Research/Scripts
python test_tor_connection.py

# 3. Run dark web scraper
python darkweb_intelligence_scraper.py --tor --phase both

# 4. Manage TOR
python tor_manager.py status
python tor_manager.py restart  # New identity
python tor_manager.py stop
```

---

## TROUBLESHOOTING

### TOR Won't Start

```bash
# Check if port 9050 is in use
netstat -an | grep 9050

# Kill existing process
docker rm -f tor-proxy

# Try again
docker run -d --name tor-proxy -p 9050:9050 dperson/torproxy
```

### Connection Timeouts

```python
# Increase timeout
response = requests.get(url, proxies=proxies, timeout=60)
```

### IP Not Changing

```bash
# Restart TOR
docker restart tor-proxy

# Wait 10 seconds, then test
python test_tor_connection.py
```

---

## SECURITY NOTES

1. **TOR is not bulletproof** - Use additional security measures
2. **JavaScript can leak info** - Disable when possible
3. **DNS leaks** - Always use socks5h:// (not socks5://)
4. **Cookies** - Clear between sessions
5. **Fingerprinting** - Randomize user agents, headers
6. **Time zones** - Be aware of timing attacks
7. **Circuit isolation** - Use different circuits for different tasks

---

**Document Created:** 2026-01-10
**Last Updated:** 2026-01-10
**Status:** Production Ready
**Maintained by:** DeadMan AI Research Team

