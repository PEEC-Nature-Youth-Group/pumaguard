# Camera Feature - Quick Reference Card

## 🚀 Quick Start (5 Minutes)

```bash
# 1. Start server
uv run pumaguard-webui --host 0.0.0.0

# 2. Add test cameras (new terminal)
python3 scripts/add_fake_cameras.py

# 3. Open browser
# http://localhost:5000
# Scroll to "Detected Cameras" section
```

---

## 📡 REST API Endpoints

### List All Cameras
```bash
curl http://localhost:5000/api/dhcp/cameras
```

### Get Specific Camera
```bash
curl http://localhost:5000/api/dhcp/cameras/aa:bb:cc:dd:ee:ff
```

### Add Camera (Testing)
```bash
curl -X POST http://localhost:5000/api/dhcp/cameras \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "TestCam",
    "ip_address": "192.168.52.200",
    "mac_address": "aa:bb:cc:dd:ee:ff",
    "status": "connected"
  }'
```

### Clear All Cameras
```bash
curl -X DELETE http://localhost:5000/api/dhcp/cameras
```

---

## 🛠️ Camera Management Commands

### Python Script (Recommended)
```bash
# Add 3 default cameras
python3 scripts/add_fake_cameras.py

# List all cameras
python3 scripts/add_fake_cameras.py list

# Clear all cameras
python3 scripts/add_fake_cameras.py clear

# Add specific camera
python3 scripts/add_fake_cameras.py add MyCam 192.168.52.200 aa:bb:cc:dd:ee:ff

# Custom API URL
python3 scripts/add_fake_cameras.py --api-url http://192.168.52.1:5000/api/dhcp/cameras
```

### Bash Script (Linux/macOS)
```bash
# Same commands as Python script
./scripts/add_fake_cameras.sh
./scripts/add_fake_cameras.sh list
./scripts/add_fake_cameras.sh clear
./scripts/add_fake_cameras.sh add MyCam 192.168.52.200 aa:bb:cc:dd:ee:ff connected
```

---

## 🧪 Running Tests

### Backend Tests (12 tests)
```bash
cd pumaguard
uv run pytest tests/test_dhcp_routes.py -v
```

### Frontend Tests (69 tests)
```bash
cd pumaguard-ui
flutter test
```

### Specific Test Files
```bash
# Backend - single test
uv run pytest tests/test_dhcp_routes.py::test_add_camera_manually -v

# Frontend - specific file
flutter test test/models/camera_test.dart
flutter test test/services/api_service_cameras_test.dart
```

### Pre-commit Validation
```bash
# Backend
cd pumaguard && make pre-commit

# Frontend
cd pumaguard-ui && make pre-commit
```

---

## 📁 Key Files

### Backend
- `pumaguard/web_routes/dhcp.py` - API endpoints
- `pumaguard/web_ui.py` - Camera storage (WebUI.cameras)
- `pumaguard/presets.py` - Settings persistence
- `tests/test_dhcp_routes.py` - Unit tests (12 tests)

### Frontend
- `pumaguard-ui/lib/models/camera.dart` - Camera model
- `pumaguard-ui/lib/services/api_service.dart` - API client
- `pumaguard-ui/lib/screens/home_screen.dart` - UI display
- `pumaguard-ui/test/models/camera_test.dart` - Model tests (35 tests)
- `pumaguard-ui/test/services/api_service_cameras_test.dart` - Service tests (34 tests)

### Scripts
- `scripts/add_fake_cameras.py` - Python management tool
- `scripts/add_fake_cameras.sh` - Bash management tool
- `scripts/demo_camera_workflow.sh` - Interactive demo
- `scripts/templates/pumaguard-dhcp-notify.sh.j2` - DHCP handler

### Settings
- `~/.config/pumaguard/pumaguard-settings.yaml` - Persistent camera storage

---

## 📦 Camera Data Structure

### Camera Model (JSON)
```json
{
  "hostname": "Microseven-Cam1",
  "ip_address": "192.168.52.101",
  "mac_address": "aa:bb:cc:dd:ee:01",
  "last_seen": "2024-01-15T10:30:00Z",
  "status": "connected"
}
```

### API Response (List)
```json
{
  "cameras": [
    {
      "hostname": "Microseven-Cam1",
      "ip_address": "192.168.52.101",
      "mac_address": "aa:bb:cc:dd:ee:01",
      "last_seen": "2024-01-15T10:30:00Z",
      "status": "connected"
    }
  ],
  "count": 1
}
```

### Status Values
- `"connected"` - Camera is online
- `"disconnected"` - Camera is offline
- `"unknown"` - Status unclear

---

## 🔍 Common Tasks

### View Current Cameras
```bash
# Via API
curl -s http://localhost:5000/api/dhcp/cameras | python3 -m json.tool

# Via script
python3 scripts/add_fake_cameras.py list

# Via settings file
cat ~/.config/pumaguard/pumaguard-settings.yaml | grep -A 20 cameras
```

### Add Multiple Test Cameras
```bash
# Method 1: Default 3 cameras
python3 scripts/add_fake_cameras.py

# Method 2: Custom script
for i in {1..5}; do
  python3 scripts/add_fake_cameras.py add \
    "Camera-$i" \
    "192.168.52.$((100+i))" \
    "aa:bb:cc:dd:ee:0$i"
done
```

### Clear and Reset
```bash
# Clear all cameras
python3 scripts/add_fake_cameras.py clear

# Verify empty
python3 scripts/add_fake_cameras.py list

# Add fresh set
python3 scripts/add_fake_cameras.py
```

### Debug Camera Issues
```bash
# Check server is running
curl -f http://localhost:5000/api/dhcp/cameras

# Check server logs
tail -f ~/.cache/pumaguard/pumaguard.log | grep camera

# Check settings file
cat ~/.config/pumaguard/pumaguard-settings.yaml

# Clear and re-add
python3 scripts/add_fake_cameras.py clear
python3 scripts/add_fake_cameras.py
```

---

## 🎯 Test Coverage

### Backend Tests (12)
- DHCP event processing (add/old/del)
- Camera CRUD operations
- Error handling and validation
- Settings persistence

### Frontend Tests (69)
- Camera model JSON serialization (35 tests)
- API service integration (34 tests)
- Edge cases and error handling
- Real-world scenarios

**Total: 81 tests, 100% pass rate ✅**

---

## 📚 Documentation

- **QUICKSTART_CAMERA_UI.md** - 5-minute guide
- **CAMERA_DETECTION_SUMMARY.md** - Full implementation
- **TEST_COVERAGE_SUMMARY.md** - Test documentation
- **CAMERA_FEATURE_COMPLETE.md** - Complete overview
- **scripts/README_CAMERA_TESTING.md** - Testing guide

---

## 🐛 Troubleshooting

### Cameras Not Appearing
1. Check server is running: `curl http://localhost:5000/api/dhcp/cameras`
2. Verify cameras were added: `python3 scripts/add_fake_cameras.py list`
3. Hard refresh browser: Ctrl+F5 or Cmd+Shift+R
4. Check browser console for errors

### API Connection Error
1. Verify server is running on correct port
2. Check firewall settings
3. Try explicit host: `--api-url http://localhost:5000/api/dhcp/cameras`

### Test Failures
1. Backend: `uv run pytest tests/test_dhcp_routes.py -v`
2. Frontend: `cd pumaguard-ui && flutter test`
3. Check for port conflicts (5000)
4. Clear cameras: `python3 scripts/add_fake_cameras.py clear`

---

## 💡 Tips & Tricks

### Interactive Demo
```bash
# Watch the complete workflow
./scripts/demo_camera_workflow.sh
```

### Custom API Server
```bash
# Set via environment variable
export PUMAGUARD_API=http://192.168.52.1:5000/api/dhcp/cameras
python3 scripts/add_fake_cameras.py
```

### Quick Test Cycle
```bash
# One-liner: clear, add, list
python3 scripts/add_fake_cameras.py clear && \
  python3 scripts/add_fake_cameras.py && \
  python3 scripts/add_fake_cameras.py list
```

### Watch Live Updates
```bash
# Terminal 1: Server
uv run pumaguard-webui --host 0.0.0.0

# Terminal 2: Add cameras periodically
watch -n 5 'python3 scripts/add_fake_cameras.py add \
  "Camera-$(date +%s)" \
  "192.168.52.$((RANDOM % 200 + 1))" \
  "aa:bb:cc:dd:ee:$(date +%M)"'
```

---

## 🎓 Learning Path

1. **Start Here**: `QUICKSTART_CAMERA_UI.md`
2. **Try It**: Run `python3 scripts/add_fake_cameras.py`
3. **Explore**: View cameras at http://localhost:5000
4. **Understand**: Read `CAMERA_DETECTION_SUMMARY.md`
5. **Test**: Run `uv run pytest tests/test_dhcp_routes.py -v`
6. **Dive Deep**: Review `TEST_COVERAGE_SUMMARY.md`

---

## ✅ Checklist for New Developers

- [ ] Server starts successfully
- [ ] Can add cameras via script
- [ ] Cameras appear in UI
- [ ] Can click cameras to open web interface
- [ ] Can list cameras via API
- [ ] Can clear cameras
- [ ] Backend tests pass (12/12)
- [ ] Frontend tests pass (69/69)
- [ ] Read documentation
- [ ] Understand data flow

---

**Need Help?** Check the comprehensive documentation in the files listed above.
**Found a Bug?** Run tests first, then file an issue with details.
**Want to Contribute?** See `CONTRIBUTING.md` for guidelines.