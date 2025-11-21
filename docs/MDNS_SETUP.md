# mDNS Setup Guide for PumaGuard

This guide explains how to set up mDNS (multicast DNS) / Zeroconf / Bonjour on your PumaGuard server, allowing clients to discover and connect to the server using a friendly hostname like `pumaguard.local` instead of having to know the IP address.

## Table of Contents

- [Overview](#overview)
- [Benefits of mDNS](#benefits-of-mdns)
- [Linux Setup (Avahi)](#linux-setup-avahi)
- [macOS Setup](#macos-setup)
- [Windows Setup (Bonjour)](#windows-setup-bonjour)
- [Docker/Container Setup](#dockercontainer-setup)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)
- [Configuration Options](#configuration-options)

## Overview

mDNS (multicast DNS) is a protocol that allows devices on a local network to advertise and discover services without requiring a central DNS server. When enabled, your PumaGuard server will be accessible at:

```
http://pumaguard.local:5000
```

The Python web server automatically advertises itself via mDNS when started (unless disabled with `--no-mdns`). However, the underlying mDNS service must be installed and running on the operating system.

## Benefits of mDNS

- **No IP Address Needed**: Connect using a memorable hostname instead of an IP address
- **Automatic Discovery**: Clients can discover available servers on the network
- **DHCP-Friendly**: Works even when the server's IP address changes
- **Zero Configuration**: Works out of the box once installed

## Linux Setup (Avahi)

Avahi is the standard mDNS implementation for Linux systems.

### Ubuntu/Debian

1. **Install Avahi daemon and utilities:**

   ```bash
   sudo apt update
   sudo apt install avahi-daemon avahi-utils
   ```

2. **Enable and start the service:**

   ```bash
   sudo systemctl enable avahi-daemon
   sudo systemctl start avahi-daemon
   ```

3. **Verify the service is running:**

   ```bash
   sudo systemctl status avahi-daemon
   ```

   You should see "active (running)" in the output.

4. **Test hostname resolution:**

   ```bash
   # Get your hostname
   hostname
   
   # Try to resolve it (should return your local IP)
   avahi-resolve -n $(hostname).local
   ```

### Red Hat/CentOS/Fedora

1. **Install Avahi:**

   ```bash
   sudo dnf install avahi avahi-tools
   # or for older versions:
   sudo yum install avahi avahi-tools
   ```

2. **Enable and start the service:**

   ```bash
   sudo systemctl enable avahi-daemon
   sudo systemctl start avahi-daemon
   ```

3. **Configure firewall (if needed):**

   ```bash
   sudo firewall-cmd --permanent --add-service=mdns
   sudo firewall-cmd --reload
   ```

### Arch Linux

1. **Install Avahi:**

   ```bash
   sudo pacman -S avahi nss-mdns
   ```

2. **Enable and start the service:**

   ```bash
   sudo systemctl enable avahi-daemon
   sudo systemctl start avahi-daemon
   ```

3. **Configure NSS (Name Service Switch):**

   Edit `/etc/nsswitch.conf` and add `mdns_minimal [NOTFOUND=return]` before `resolve` and `dns`:

   ```
   hosts: mymachines mdns_minimal [NOTFOUND=return] resolve [!UNAVAIL=return] files myhostname dns
   ```

### Raspberry Pi (Raspbian/Raspberry Pi OS)

Avahi is usually pre-installed on Raspberry Pi OS. If not:

```bash
sudo apt update
sudo apt install avahi-daemon
sudo systemctl enable avahi-daemon
sudo systemctl start avahi-daemon
```

Test that your Pi is discoverable:

```bash
avahi-browse -a -t
```

## macOS Setup

macOS has mDNS (Bonjour) built-in and enabled by default. No additional setup is required!

To verify mDNS is working:

```bash
# Discover services on the network
dns-sd -B _http._tcp

# Resolve a .local hostname
dns-sd -G v4 pumaguard.local
```

## Windows Setup (Bonjour)

Windows does not include mDNS by default, but you can install Bonjour Print Services.

### Option 1: Bonjour Print Services (Recommended)

1. **Download Bonjour Print Services from Apple:**
   - Visit: https://support.apple.com/kb/DL999
   - Or search for "Bonjour Print Services for Windows"

2. **Install the downloaded executable**

3. **Verify installation:**
   - Open Services (services.msc)
   - Look for "Bonjour Service" - it should be running

### Option 2: iTunes Installation

Installing iTunes automatically includes Bonjour:

1. Download and install iTunes from Apple
2. Bonjour will be installed as a component

### Option 3: Manual Installation (Advanced)

1. Extract Bonjour64.msi from the Bonjour Print Services installer
2. Install using: `msiexec /i Bonjour64.msi`

## Docker/Container Setup

When running PumaGuard in a Docker container, special configuration is needed for mDNS to work properly.

### Method 1: Host Network Mode (Recommended)

Run the container with host networking:

```bash
docker run --network host \
  -v ./settings:/settings \
  pumaguard
```

### Method 2: Avahi Socket Forwarding

Mount the Avahi socket into the container:

```bash
docker run -d \
  -p 5000:5000 \
  -v /var/run/avahi-daemon/socket:/var/run/avahi-daemon/socket \
  pumaguard
```

### Method 3: Dedicated Avahi Container

Use a sidecar Avahi container to handle mDNS:

```yaml
# docker-compose.yml
version: '3'
services:
  pumaguard:
    image: pumaguard
    ports:
      - "5000:5000"
    networks:
      - pumaguard-net
    depends_on:
      - avahi

  avahi:
    image: flungo/avahi
    network_mode: host
    volumes:
      - ./avahi-services:/etc/avahi/services
```

Create a service definition file:

```xml
<!-- avahi-services/pumaguard.service -->
<?xml version="1.0" standalone='no'?>
<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
<service-group>
  <name replace-wildcards="yes">PumaGuard on %h</name>
  <service>
    <type>_http._tcp</type>
    <port>5000</port>
    <txt-record>version=1.0.0</txt-record>
    <txt-record>path=/</txt-record>
    <txt-record>app=pumaguard</txt-record>
  </service>
</service-group>
```

### Kubernetes Setup

For Kubernetes deployments, consider using:
- **hostNetwork: true** in pod spec
- Or use a DaemonSet with mDNS capabilities on each node

## Verification

### Check PumaGuard Server

When you start the PumaGuard web server, you should see:

```
INFO - mDNS service registered: pumaguard._http._tcp.local. at 192.168.1.100:5000
INFO - Server accessible at: http://pumaguard.local:5000
```

### Test from Command Line

**On Linux/macOS:**

```bash
# Browse for HTTP services
avahi-browse -t _http._tcp

# Should show something like:
# + eth0 IPv4 pumaguard    _http._tcp    local

# Resolve the hostname
ping pumaguard.local

# Test the API
curl http://pumaguard.local:5000/api/status
```

**On macOS:**

```bash
# Discover services
dns-sd -B _http._tcp

# Look up hostname
dns-sd -G v4 pumaguard.local

# Test API
curl http://pumaguard.local:5000/api/status
```

**On Windows (with Bonjour):**

```powershell
# Test with PowerShell
ping pumaguard.local

# Or use curl (if available)
curl http://pumaguard.local:5000/api/status
```

### Test from Flutter App

1. Open the PumaGuard web UI
2. Go to Settings or Server Discovery screen
3. Click "Discover Servers"
4. You should see your server listed with name "pumaguard"
5. Click "Connect"

## Troubleshooting

### Server Not Discoverable

**Check if mDNS is enabled:**

```bash
# On the server machine
sudo systemctl status avahi-daemon

# Check if port 5353 (mDNS) is listening
sudo netstat -ulnp | grep 5353
# or
sudo ss -ulnp | grep 5353
```

**Check firewall rules:**

```bash
# Ubuntu/Debian
sudo ufw status
sudo ufw allow mdns

# Red Hat/CentOS/Fedora
sudo firewall-cmd --list-services
sudo firewall-cmd --permanent --add-service=mdns
sudo firewall-cmd --reload
```

**Test with avahi-browse:**

```bash
# Browse all services
avahi-browse -a -t

# Browse HTTP services specifically
avahi-browse -t _http._tcp
```

### Hostname Not Resolving

**Check NSS configuration (Linux):**

Edit `/etc/nsswitch.conf` and ensure `mdns_minimal` or `mdns4_minimal` is present:

```
hosts: files mdns4_minimal [NOTFOUND=return] dns
```

**Flush DNS cache:**

```bash
# Linux
sudo systemctl restart systemd-resolved

# macOS
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder

# Windows
ipconfig /flushdns
```

### Cross-Subnet Discovery Fails

mDNS is designed for local networks only. It uses multicast and typically doesn't cross router boundaries.

**Solutions:**
- Use Avahi reflector to bridge networks:
  ```bash
  sudo apt install avahi-daemon
  # Edit /etc/avahi/avahi-daemon.conf
  # Set: enable-reflector=yes
  sudo systemctl restart avahi-daemon
  ```
- Or use manual IP address connection in the Flutter app

### Container mDNS Not Working

**Use host networking:**

```bash
docker run --network host pumaguard
```

**Or disable mDNS in container and run Avahi on host:**

```bash
# Start server without mDNS
docker run -p 5000:5000 pumaguard --no-mdns

# Manually advertise service on host
cat > /etc/avahi/services/pumaguard.service <<EOF
<?xml version="1.0" standalone='no'?>
<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
<service-group>
  <name>PumaGuard</name>
  <service>
    <type>_http._tcp</type>
    <port>5000</port>
  </service>
</service-group>
EOF

sudo systemctl restart avahi-daemon
```

### Python zeroconf Errors

If you see errors about zeroconf:

```bash
# Ensure zeroconf is installed
pip install zeroconf

# Or reinstall pumaguard
pip install --upgrade --force-reinstall pumaguard
```

## Configuration Options

### Customize Service Name

Use the `--mdns-name` argument:

```bash
pumaguard-webui --mdns-name my-pumaguard
# Server will be accessible at: my-pumaguard.local
```

### Disable mDNS

If you don't want mDNS:

```bash
pumaguard-webui --no-mdns
```

### Change Port

The mDNS service will automatically use the port you specify:

```bash
pumaguard-webui --port 8080
# Advertised as: pumaguard.local:8080
```

### Programmatic Usage

```python
from pumaguard.web_ui import WebUI
from pumaguard.presets import Preset

presets = Preset()

# With mDNS enabled (default)
web_ui = WebUI(
    presets=presets,
    host='0.0.0.0',
    port=5000,
    mdns_enabled=True,
    mdns_name='pumaguard'
)

# Without mDNS
web_ui = WebUI(
    presets=presets,
    host='0.0.0.0',
    port=5000,
    mdns_enabled=False
)

web_ui.start()
```

## Network Requirements

For mDNS to work:

- **Port 5353 UDP**: Must be open for multicast DNS
- **Multicast address**: 224.0.0.251 (IPv4) or ff02::fb (IPv6)
- **Local network**: Devices must be on the same subnet (unless using reflector)
- **Multicast enabled**: Network switches/routers must allow multicast traffic

## Security Considerations

- mDNS advertises service presence on the local network
- Consider using firewall rules to restrict access
- For production, consider disabling auto-discovery and using manual configuration
- mDNS only works on local networks by design (it's not routable)

## References

- [Avahi Documentation](https://www.avahi.org/)
- [Apple Bonjour](https://developer.apple.com/bonjour/)
- [RFC 6762 - Multicast DNS](https://tools.ietf.org/html/rfc6762)
- [RFC 6763 - DNS-Based Service Discovery](https://tools.ietf.org/html/rfc6763)
- [Python zeroconf](https://github.com/python-zeroconf/python-zeroconf)