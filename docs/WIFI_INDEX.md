# WiFi Configuration Documentation Index

## Quick Start

New to the WiFi configuration feature? Start here:

1. **[Quick Reference Guide](WIFI_QUICK_REFERENCE.md)** - Fast setup and common tasks
   - How to connect to existing WiFi
   - How to create a hotspot
   - Common troubleshooting
   - Command examples

## Complete Documentation

### For Users

- **[Migration Guide](WIFI_MIGRATION_GUIDE.md)** - For existing PumaGuard users
  - What changed and what stayed the same
  - When to use AP mode vs Client mode
  - How to switch between modes
  - Troubleshooting connection issues
  - FAQ

### For Developers & Administrators

- **[WiFi Configuration Guide](WIFI_CONFIGURATION.md)** - Complete technical documentation
  - Architecture overview
  - REST API specifications
  - System requirements
  - Security considerations
  - Development guidelines
  - Advanced troubleshooting

- **[Feature Summary](WIFI_FEATURE_SUMMARY.md)** - Implementation details
  - What was added (files, features, tests)
  - Technical specifications
  - Integration notes
  - Testing information

## Documentation Structure

```
docs/
├── WIFI_INDEX.md                 ← You are here
├── WIFI_QUICK_REFERENCE.md       ← Start here for quick tasks
├── WIFI_MIGRATION_GUIDE.md       ← For existing users
├── WIFI_CONFIGURATION.md         ← Complete technical guide
└── WIFI_FEATURE_SUMMARY.md       ← Implementation overview
```

## Quick Links

### Common Tasks

- [Scan for WiFi networks](#scanning) → See Quick Reference Guide
- [Connect to existing WiFi](#client-mode) → See Quick Reference Guide
- [Create a hotspot](#ap-mode) → See Quick Reference Guide
- [Troubleshoot connection issues](#troubleshooting) → See Migration Guide
- [API endpoints](#api) → See Configuration Guide
- [Security best practices](#security) → See Configuration Guide

### By User Type

**Field Operators**
- Start with: [Quick Reference Guide](WIFI_QUICK_REFERENCE.md)
- If issues: [Migration Guide - Troubleshooting](WIFI_MIGRATION_GUIDE.md#troubleshooting)

**System Administrators**
- Start with: [Migration Guide](WIFI_MIGRATION_GUIDE.md)
- Deep dive: [Configuration Guide](WIFI_CONFIGURATION.md)

**Developers**
- Start with: [Feature Summary](WIFI_FEATURE_SUMMARY.md)
- API specs: [Configuration Guide - Architecture](WIFI_CONFIGURATION.md#architecture)
- Tests: See `tests/test_wifi_routes.py`

## Key Concepts

### WiFi Modes

**Access Point (AP) Mode**
- Device creates its own WiFi network
- Cameras connect directly to PumaGuard
- No internet access
- Fixed IP: 192.168.52.1
- Default mode from Ansible deployment

**Client Mode**
- Device connects to existing WiFi network
- Shares network with other devices
- Internet access (if network provides it)
- IP assigned by router (use mDNS: `pumaguard.local`)

### When to Use Each Mode

| Scenario | Recommended Mode |
|----------|------------------|
| Remote field deployment | AP Mode |
| Cameras only connecting to PumaGuard | AP Mode |
| Home/office with existing WiFi | Client Mode |
| Need internet access | Client Mode |
| Multiple PumaGuard devices | Client Mode |

## Getting Help

1. **Quick answers**: Check [Quick Reference](WIFI_QUICK_REFERENCE.md)
2. **Setup issues**: See [Migration Guide](WIFI_MIGRATION_GUIDE.md)
3. **Technical details**: Read [Configuration Guide](WIFI_CONFIGURATION.md)
4. **Can't find answer**: Check the troubleshooting sections in each guide

## Related Documentation

- **Main Documentation**: See `docs/` folder index
- **API Reference**: `docs/API_REFERENCE.md` (add WiFi endpoints)
- **Web UI Structure**: `docs/WEB_UI_STRUCTURE.md`
- **Contributing**: `CONTRIBUTING.md`

## Version Information

WiFi configuration feature added in: v[version]
Compatible with: PumaGuard v1.0+
Requires: NetworkManager, hostapd, dnsmasq

## Support

For issues or questions:
- Review troubleshooting sections in the guides
- Check system requirements in Configuration Guide
- Verify Ansible deployment completed successfully
- Review logs: `journalctl -u hostapd -f` or `journalctl -u NetworkManager -f`
