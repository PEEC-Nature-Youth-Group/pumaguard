# XDG Base Directory Migration Guide

## Overview

PumaGuard now follows the [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html) for storing configuration files. This provides a more organized and standard approach to configuration management on Linux and Unix-like systems.

## What Changed

### Previous Behavior
- Settings file location: `pumaguard-settings.yaml` in the current working directory
- No standard location for configuration files

### New Behavior
- Settings file location: `~/.config/pumaguard/settings.yaml` (or `$XDG_CONFIG_HOME/pumaguard/settings.yaml`)
- Follows XDG Base Directory Specification
- **Backwards compatible**: Legacy location is still supported

## Default Settings File Location

The new default location for the settings file is determined by:

1. **XDG Standard Location** (preferred): `$XDG_CONFIG_HOME/pumaguard/settings.yaml`
   - If `XDG_CONFIG_HOME` environment variable is set, it uses that directory
   - Otherwise defaults to `~/.config/pumaguard/settings.yaml`

2. **Legacy Location** (fallback): `pumaguard-settings.yaml` in the current directory
   - Still supported for backwards compatibility
   - A warning message will be logged recommending migration to XDG location

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

You can customize the config directory by setting the `XDG_CONFIG_HOME` environment variable:

```bash
# Use a custom config directory
export XDG_CONFIG_HOME=/my/custom/config
pumaguard server

# Settings will be looked for at: /my/custom/config/pumaguard/settings.yaml
```

## Benefits of XDG Compliance

- **Organization**: Configuration files are stored in a standard location separate from application data
- **Portability**: Easy to backup and sync configuration files across systems
- **Multi-user**: Each user has their own configuration directory
- **Compatibility**: Follows Linux/Unix best practices used by many modern applications
- **Clean Home Directory**: Reduces clutter in the home directory

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
# PumaGuard will automatically create ~/.config/pumaguard/ directory
pumaguard server

# Save settings through the web UI or manually create:
# ~/.config/pumaguard/settings.yaml
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

## See Also

- [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html)
- [PumaGuard Documentation](http://pumaguard.rtfd.io/)