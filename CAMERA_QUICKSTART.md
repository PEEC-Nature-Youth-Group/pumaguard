# Camera URL Feature - Quick Start Guide

**Ready to use NOW!** The UI has been rebuilt with all fixes applied.

---

## 🚀 Start Using It (3 Steps)

### Step 1: Restart Server

```bash
# Press Ctrl+C to stop current server (if running)
uv run pumaguard-webui --host 0.0.0.0
```

### Step 2: Configure Camera

1. Open browser: `http://192.168.51.104:5000` or `http://pumaguard.local:5000`
2. **Hard refresh** (important!): `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (Mac)
3. Click **Settings**
4. Scroll to **System Settings** section
5. Enter camera IP: `192.168.52.96`
6. Wait 1 second → See green **"Settings saved successfully"**

### Step 3: Open Camera

1. Go back to **Home** screen
2. Click **Camera** button (in Quick Actions)
3. Camera opens in new tab! 🎉

---

## ✅ What's Working

- ✅ Settings save to YAML file
- ✅ Camera button opens camera web interface
- ✅ Auto-save after 1 second of typing
- ✅ Works with IP addresses or hostnames
- ✅ Automatically adds `http://` if needed

---

## 🔍 Verify It Works

### Check Settings File
```bash
cat ~/.config/pumaguard/pumaguard-settings.yaml | grep camera-url
# Should show: camera-url: 192.168.52.96
```

### Test API
```bash
curl http://localhost:5000/api/camera/url
# Should return: {"camera_url":"192.168.52.96"}
```

---

## 💡 Tips

### Supported Formats
- `192.168.52.96` → Opens as `http://192.168.52.96`
- `192.168.52.96:8080` → Opens as `http://192.168.52.96:8080`
- `http://192.168.52.96` → Opens as-is
- `camera.local` → Opens as `http://camera.local`

### Recommended: DHCP Reservation
Set up DHCP reservation on your router so camera IP never changes:
- Camera MAC: `2C:C3:E6:0A:54:53`
- Fixed IP: `192.168.52.96`

---

## 🐛 Troubleshooting

### Camera URL not saving?
- Wait 1 second after typing (auto-saves)
- Check for green "Settings saved successfully" message
- Verify: `cat ~/.config/pumaguard/pumaguard-settings.yaml | grep camera`

### Camera button shows "not configured"?
- Make sure you entered the IP in Settings
- Wait for green confirmation message
- Refresh home screen

### Camera opens but "Connection refused"?
```bash
# Check camera is reachable:
ping 192.168.52.96

# Test HTTP connection:
curl http://192.168.52.96

# Try with port 8080:
curl http://192.168.52.96:8080
```

### Still see old error?
Hard refresh browser to clear cache:
- Windows/Linux: `Ctrl + Shift + R`
- Mac: `Cmd + Shift + R`

---

## 📋 Debug Mode

Open browser console (F12) to see debug messages:

**Successful output:**
```
[HomeScreen._openCamera] Starting camera open...
[ApiService.getCameraUrl] Parsed camera_url: "192.168.52.96"
[HomeScreen._openCamera] URL to open: "http://192.168.52.96"
[HomeScreen._openCamera] Using window.open() for web...
[HomeScreen._openCamera] URL opened successfully
```

---

## 📚 More Help

- **Complete Guide**: `docs/CAMERA_INTEGRATION.md`
- **Troubleshooting**: `docs/CAMERA_URL_TROUBLESHOOTING.md`
- **Implementation Details**: `CAMERA_URL_COMPLETE.md`

---

**That's it! Your camera button is ready to use.** 📹✨