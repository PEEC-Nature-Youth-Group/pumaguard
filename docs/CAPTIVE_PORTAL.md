# Captive Portal Configuration

## Overview

The PumaGuard device is configured to act as a **captive portal** when devices connect to its WiFi hotspot. This means phones, tablets, and laptops will automatically detect the portal and prompt users to open the PumaGuard web interface.

## How It Works

The captive portal implementation uses a **selective DNS hijacking** approach that preserves internet connectivity while still triggering captive portal detection on client devices.

### Architecture

```
Phone/Device
    │
    ├─► Connects to "pumaguard" WiFi (wlan0)
    │
    ├─► Receives DHCP: IP=192.168.52.x, Gateway=192.168.52.1, DNS=192.168.52.1
    │
    ├─► Device queries captive portal detection URLs
    │   (connectivitycheck.gstatic.com, captive.apple.com, etc.)
    │
    ├─► dnsmasq intercepts these specific domains → returns 192.168.52.1
    │
    ├─► Device makes HTTP request to port 80
    │
    ├─► UFW NAT rule redirects: port 80 → port 5000
    │
    └─► PumaGuard web UI responds → Captive portal detected!
```

### Components

1. **dnsmasq** (`/etc/dnsmasq.d/10-pumaguard.conf`)
   - Hijacks only captive portal detection domains
   - Forwards all other DNS queries to upstream server (eth0)
   - Preserves internet connectivity

2. **UFW NAT rules** (`/etc/ufw/before.rules`)
   - Redirects port 80 → 5000
   - Ensures HTTP traffic reaches PumaGuard web UI

3. **hostapd** (`/etc/hostapd/hostapd.conf`)
   - Creates WiFi access point on wlan0
   - SSID: `pumaguard`

## Captive Portal Detection Domains

The following domains are hijacked to trigger captive portal detection:

### Android

- `connectivitycheck.gstatic.com`
- `www.google.com`
- `clients3.google.com`
- `play.googleapis.com`

### iOS/macOS

- `captive.apple.com`
- `www.apple.com`

### Windows

- `www.msftconnecttest.com`
- `www.msftncsi.com`

### Firefox

- `detectportal.firefox.com`

All other domains are resolved normally through the upstream DNS server.

## Network Topology

### Lab Setup (Internet Connectivity)

```
Internet
    │
Laptop (eth0) ←─── Raspberry Pi (eth0: 192.168.51.1)
                         │
                    Raspberry Pi (wlan0: 192.168.52.1)
                         │
                    WiFi Hotspot "pumaguard"
                         │
                    └─► Phone/Device (192.168.52.x)
```

In the lab:

- Raspberry Pi eth0 connected to laptop
- Traffic from wlan0 forwarded to eth0
- DNS queries forwarded to laptop via eth0
- Devices on hotspot have internet access

### Field Deployment (Isolated Network)

```
Raspberry Pi (wlan0: 192.168.52.1)
    │
WiFi Hotspot "pumaguard"
    │
└─► Phone/Device (192.168.52.x)
```

In the field:

- No eth0 connection
- Isolated network for camera trap monitoring
- DNS forwarding fails gracefully
- Captive portal still works (port 80 redirect)

## Testing the Captive Portal

### On Android

1. Connect to "pumaguard" WiFi
2. Enter password: `pumaguard`
3. Look for notification: "Sign in to network" or "Captive portal detected"
4. Tap notification → browser opens to PumaGuard UI

### On iOS/iPhone

1. Connect to "pumaguard" WiFi
2. Enter password: `pumaguard`
3. Captive portal sheet automatically appears
4. Shows PumaGuard web interface

### On macOS

1. Connect to "pumaguard" WiFi
2. Enter password: `pumaguard`
3. System Preferences may show "Log in" button
4. Click to open PumaGuard UI

### On Windows

1. Connect to "pumaguard" WiFi
2. Enter password: `pumaguard`
3. Action Center may show "Additional sign-in may be required"
4. Click to open PumaGuard UI

### Manual Access

If captive portal doesn't auto-trigger:

- Open browser to `http://192.168.52.1:5000`
- Or `http://pumaguard.local:5000`
- Or just `http://192.168.52.1` (redirects to port 5000)

## Troubleshooting

### Captive Portal Not Triggering

**Check DNS resolution:**

```bash
# From a device connected to the hotspot
nslookup connectivitycheck.gstatic.com
# Should return: 192.168.52.1
```

**Check dnsmasq logs:**

```bash
sudo journalctl -u dnsmasq -f
```

**Verify UFW port redirect:**

```bash
sudo iptables -t nat -L PREROUTING -n -v
# Should show: tcp dpt:80 redir ports 5000
```

### Internet Connectivity Issues

**Verify eth0 connection:**

```bash
ip addr show eth0
# Should have IP on 192.168.51.x network
```

**Check routing:**

```bash
ip route
# Should show routes for both 192.168.51.0/24 and 192.168.52.0/24
```

**Test upstream DNS:**

```bash
dig @192.168.51.1 google.com
# Should resolve to real Google IP
```

### Phone Shows "No Internet"

This is **normal** when captive portal detection domains are hijacked. The phone detects the portal is active. After interacting with the portal, some phones will show internet connectivity.

If actual internet is needed:

1. Ensure eth0 is connected to upstream network
2. Verify `server={{ dnsmasq_wired_gateway }}` is active in dnsmasq config
3. Check IP forwarding is enabled (handled by netplan configuration)

## Configuration Files

- **Ansible playbook:** `scripts/configure-device.yaml`
- **dnsmasq template:** `scripts/templates/dnsmasq-wlan0.conf.j2`
- **hostapd template:** `scripts/templates/hostapd.conf.j2`
- **Deployed dnsmasq config:** `/etc/dnsmasq.d/10-pumaguard.conf`
- **Deployed hostapd config:** `/etc/hostapd/hostapd.conf`
- **UFW rules:** `/etc/ufw/before.rules`

## Security Considerations

- Only port 80 (HTTP) triggers the portal - HTTPS traffic is not intercepted
- DNS hijacking limited to captive portal detection domains only
- Firewall (UFW) restricts access to only necessary services
- Hotspot password required (default: `pumaguard` - **change in production!**)

## Customization

### Change Hotspot SSID/Password

Edit `scripts/configure-device.yaml`:

```yaml
vars:
  hostapd_ssid: "my-custom-ssid"
  hostapd_passphrase: "my-secure-password"
```

### Disable Captive Portal (Full Internet Access)

Edit `scripts/templates/dnsmasq-wlan0.conf.j2`:

```bash
# Comment out all the address=/ lines for captive portal domains
# Keep only:
address=/pumaguard.local/{{ dnsmasq_gateway }}
server={{ dnsmasq_wired_gateway }}
```

### Change IP Range

Edit `scripts/configure-device.yaml`:

```yaml
vars:
  dnsmasq_dhcp_start: "192.168.52.50"
  dnsmasq_dhcp_end: "192.168.52.150"
  dnsmasq_gateway: "192.168.52.1"
```

## References

- **dnsmasq documentation:** https://thekelleys.org.uk/dnsmasq/doc.html
- **hostapd documentation:** https://w1.fi/hostapd/
- **Captive portal detection:**
  - Android: https://android.googlesource.com/platform/frameworks/base/+/master/services/core/java/com/android/server/connectivity/NetworkMonitor.java
  - iOS: https://www.apple.com/library/test/success.html
  - Windows: https://docs.microsoft.com/en-us/windows/win32/nativewifi/portal-detection
