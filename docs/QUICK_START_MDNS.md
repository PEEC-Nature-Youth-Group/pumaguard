# Quick Start Guide: mDNS Discovery

This guide will help you quickly set up and use mDNS (multicast DNS) service discovery with PumaGuard, allowing easy connection without needing to know IP addresses.

## What is mDNS?

mDNS allows devices on a local network to discover each other using friendly names like `pumaguard.local` instead of IP addresses like `192.168.1.100`.

## Quick Setup (5 minutes)

### Step 1: Install mDNS on Server

**Ubuntu/Debian/Raspberry Pi:**
```bash
sudo apt update
sudo apt install avahi-daemon avahi-utils
sudo systemctl enable avahi-daemon
sudo systemctl start avahi-daemon
```

**macOS:**
Already installed! Skip to Step 2.

**Windows:**
Download and install [Bonjour Print Services](https://support.apple.com/kb/DL999).

### Step 2: Start PumaGuard with mDNS

```bash
# Install or update PumaGuard
pip install --upgrade pumaguard

# Start the web UI (mDNS is enabled by default)
pumaguard-webui --host 0.0.0.0 --port 5000
```

You should see output like:
```
INFO - mDNS service registered: pumaguard._http._tcp.local. at 192.168.1.100:5000
INFO - Server accessible at: http://pumaguard.local:5000
```

### Step 3: Connect from Client

**Option A: Use the hostname directly**

Open your browser and go to:
```
http://pumaguard.local:5000
```

**Option B: Use the server discovery feature**

1. Open the PumaGuard web UI
2. Click on "Server Discovery" or Settings
3. Click "Discover Servers"
4. Your server should appear in the list
5. Click "Connect"

**Option C: Test from command line**

```bash
# Verify the server is discoverable
ping pumaguard.local

# Test the API
curl http://pumaguard.local:5000/api/status
```

## Customization

### Use a Custom Hostname

```bash
pumaguard-webui --host 0.0.0.0 --mdns-name myserver
# Accessible at: http://myserver.local:5000
```

### Disable mDNS

If you don't want mDNS:
```bash
pumaguard-webui --no-mdns
```

## Common Issues & Solutions

### "Cannot resolve pumaguard.local"

**Linux:**
```bash
# Check if Avahi is running
sudo systemctl status avahi-daemon

# If not running, start it
sudo systemctl start avahi-daemon
```

**Windows:**
```
Check that Bonjour Service is running in Services (services.msc)
```

### Server not discovered in Flutter app

1. Make sure both devices are on the same network/subnet
2. Check firewall settings allow port 5353 (mDNS)
3. Try manual connection with IP address instead

### Firewall blocking mDNS

**Ubuntu/Debian:**
```bash
sudo ufw allow mdns
```

**Fedora/RHEL:**
```bash
sudo firewall-cmd --permanent --add-service=mdns
sudo firewall-cmd --reload
```

## Docker/Container Setup

If running in Docker, use host networking:

```bash
docker run --network host pumaguard
```

Or mount the Avahi socket:

```bash
docker run -v /var/run/avahi-daemon/socket:/var/run/avahi-daemon/socket \
  -p 5000:5000 \
  pumaguard
```

## Verification Commands

### Check if mDNS is working

**Linux:**
```bash
# Browse for all services
avahi-browse -a -t

# Browse for HTTP services
avahi-browse -t _http._tcp

# Resolve hostname
avahi-resolve -n pumaguard.local
```

**macOS:**
```bash
# Discover services
dns-sd -B _http._tcp

# Resolve hostname
dns-sd -G v4 pumaguard.local
```

**Windows (PowerShell):**
```powershell
ping pumaguard.local
```

### Check PumaGuard diagnostic endpoint

```bash
curl http://pumaguard.local:5000/api/diagnostic | jq .
```

This will show server info including mDNS status.

## Next Steps

- See [MDNS_SETUP.md](MDNS_SETUP.md) for detailed setup instructions
- Learn about advanced configuration options
- Set up mDNS in Docker/Kubernetes environments
- Configure cross-subnet discovery with Avahi reflector

## Troubleshooting Resources

If you encounter issues:

1. Check the [MDNS_SETUP.md](MDNS_SETUP.md) troubleshooting section
2. Verify network requirements (same subnet, multicast enabled)
3. Test basic network connectivity with `ping`
4. Check server logs for mDNS registration messages
5. Try disabling firewall temporarily to rule out firewall issues

## FAQ

**Q: Does mDNS work across different subnets/VLANs?**
A: No, mDNS is designed for local networks only. Use Avahi reflector or manual IP connection for cross-subnet access.

**Q: Can I use mDNS with HTTPS?**
A: Yes, but you'll need to configure SSL certificates. The mDNS service will advertise whatever port you configure.

**Q: What if I have multiple PumaGuard servers?**
A: Use different `--mdns-name` values for each:
```bash
# Server 1
pumaguard-webui --mdns-name pumaguard-cam1

# Server 2
pumaguard-webui --mdns-name pumaguard-cam2
```

**Q: Is mDNS secure?**
A: mDNS advertises service presence on the local network. It's designed for convenience, not security. For production, consider disabling auto-discovery and using manual configuration with proper authentication.

**Q: Why use mDNS instead of regular DNS?**
A: mDNS works without any DNS server configuration, making it perfect for home networks, development environments, and devices with changing IP addresses (DHCP).