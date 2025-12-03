# XDG Base Directory Migration Guide

## Overview

PumaGuard now follows the [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html) for storing configuration files. This provides a more organized and standard approach to configuration management on Linux and Unix-like systems.

## What Changed

### Previous Behavior
- Settings file location: `pumaguard-settings.yaml` in the current working directory
- No standard location for configuration files
- Log file location: Not standardized

### New Behavior
- Settings file location: `~/.config/pumaguard/settings.yaml` (or `$XDG_CONFIG_HOME/pumaguard/settings.yaml`)
- Log file location: `~/.cache/pumaguard/pumaguard.log` (or `$XDG_CACHE_HOME/pumaguard/pumaguard.log`)
- Follows XDG Base Directory Specification
- **Backwards compatible**: Legacy location is still supported

## Default File Locations

### Settings File

The new default location for the settings file is determined by:

1. **XDG Standard Location** (preferred): `$XDG_CONFIG_HOME/pumaguard/settings.yaml`
   - If `XDG_CONFIG_HOME` environment variable is set, it uses that directory
   - Otherwise defaults to `~/.config/pumaguard/settings.yaml`

2. **Legacy Location** (fallback): `pumaguard-settings.yaml` in the current directory
   - Still supported for backwards compatibility
   - A warning message will be logged recommending migration to XDG location

### Log File

The log file location follows XDG Base Directory Specification for cache:

1. **XDG Cache Location** (default): `$XDG_CACHE_HOME/pumaguard/pumaguard.log`
   - If `XDG_CACHE_HOME` environment variable is set, it uses that directory
   - Otherwise defaults to `~/.cache/pumaguard/pumaguard.log`

2. **Custom Location**: Use the `--log-file` command-line argument
   - Allows specifying any custom path for the log file
   - Example: `pumaguard --log-file /var/log/pumaguard.log server`

## Migration Steps

### Option 1: Manual Migration (Recommended)

If you have an existing `pumaguard-settings.yaml` file, you can migrate it to the XDG location:

```bash
# Create the config directory if it doesn't exist
mkdir -p ~/.config/pumaguard

# Move your settings file to the new location
mv pumaguard-settings.yaml ~/.config/pumaguard/settings.yaml
```

### Option 2: Continue Using Legacy Location

No action required! PumaGuard will continue to use your existing `pumaguard-settings.yaml` file if it exists. However, you'll see informational messages recommending migration to the XDG location.

### Option 3: Use Custom Location

You can still specify a custom settings file location using the `--settings` command-line argument:

```bash
pumaguard --settings /path/to/my-settings.yaml server
```

## Environment Variable Support

You can customize the config and cache directories by setting XDG environment variables:

```bash
# Use a custom config directory
export XDG_CONFIG_HOME=/my/custom/config
pumaguard server
# Settings will be looked for at: /my/custom/config/pumaguard/settings.yaml

# Use a custom cache directory
export XDG_CACHE_HOME=/my/custom/cache
pumaguard server
# Logs will be written to: /my/custom/cache/pumaguard/pumaguard.log

# Or specify log file directly
pumaguard --log-file /var/log/pumaguard/app.log server
```

## Benefits of XDG Compliance

- **Organization**: Configuration files and logs are stored in standard locations separate from application data
- **Portability**: Easy to backup and sync configuration files across systems
- **Multi-user**: Each user has their own configuration and log directories
- **Compatibility**: Follows Linux/Unix best practices used by many modern applications
- **Clean Home Directory**: Reduces clutter in the home directory
- **Flexible Logging**: Cache directory for logs can be easily changed or cleaned without affecting configuration

## Technical Details

### File Search Order

When PumaGuard starts, it searches for the settings file in the following order:

1. **Command-line specified**: `--settings /path/to/file.yaml` (highest priority)
2. **XDG location**: `$XDG_CONFIG_HOME/pumaguard/settings.yaml` or `~/.config/pumaguard/settings.yaml`
3. **Legacy location**: `./pumaguard-settings.yaml` in the current directory
4. **Default**: If no file exists, the XDG location is used and the directory is created

### Code Changes

The implementation adds two helper functions:

- `get_xdg_config_home()`: Returns the XDG config home directory
- `get_default_settings_file()`: Determines the default settings file location with backwards compatibility

## Troubleshooting

### I can't find my settings file

Check these locations in order:
1. `~/.config/pumaguard/settings.yaml`
2. `pumaguard-settings.yaml` in the directory where you run PumaGuard
3. Any custom location specified with `--settings`

### I can't find the log file

Check these locations:
1. `~/.cache/pumaguard/pumaguard.log` (default)
2. `$XDG_CACHE_HOME/pumaguard/pumaguard.log` (if `XDG_CACHE_HOME` is set)
3. Any custom location specified with `--log-file`
4. Use the API to get the current log location: `curl http://localhost:5000/api/diagnostic | jq -r '.server.log_file'`

### My settings aren't loading

- Check the log output for messages about which settings file is being used
- Verify the file exists at the expected location
- Ensure the file has correct YAML syntax
- Check file permissions (should be readable by your user)

### I want to use a different config directory

Set the `XDG_CONFIG_HOME` environment variable before running PumaGuard:

```bash
export XDG_CONFIG_HOME=/path/to/my/config
pumaguard server
```

## Examples

### Example 1: First-time Setup

```bash
# PumaGuard will automatically create directories
pumaguard server

# Configuration: ~/.config/pumaguard/settings.yaml
# Logs: ~/.cache/pumaguard/pumaguard.log
```

### Example 2: Migrating Existing Configuration

```bash
# You have: ./pumaguard-settings.yaml
# Move it to XDG location:
mkdir -p ~/.config/pumaguard
mv pumaguard-settings.yaml ~/.config/pumaguard/settings.yaml

# Run PumaGuard (will use new location)
pumaguard server
```

### Example 3: Custom Config Location

```bash
# Create config anywhere you want
mkdir -p /opt/pumaguard/config
cp pumaguard-settings.yaml /opt/pumaguard/config/settings.yaml

# Run with custom location
pumaguard --settings /opt/pumaguard/config/settings.yaml server
```

### Example 4: Custom Log File Location

```bash
# Log to a system log directory
pumaguard --log-file /var/log/pumaguard/app.log server

# Log to a custom location
pumaguard --log-file /tmp/pumaguard-debug.log server

# Combine custom settings and log locations
pumaguard --settings /opt/pumaguard/config.yaml --log-file /var/log/pumaguard.log server
```

### Example 5: Query Log Location via API

```bash
# Start the server
pumaguard server &

# Get the log file location
curl -s http://localhost:5000/api/diagnostic | jq -r '.server.log_file'
# Output: /home/user/.cache/pumaguard/pumaguard.log
```

## See Also

- [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html)
- [PumaGuard Documentation](http://pumaguard.rtfd.io/)