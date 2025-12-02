# Image Grouping Feature Implementation

## Overview

This document describes the implementation of the image grouping feature in the PumaGuard UI, which allows users to organize images by day or week in the image browser.

## Changes Made

### 1. Fixed UI Version Generation for `dev-ui-web` Target

**Problem**: The `dev-ui-web` target was referenced in documentation but did not exist in the Makefile.

**Solution**: 
- Added `dev-ui-web` target to `pumaguard-ui/Makefile` that:
  - Generates version from git tags before starting dev server
  - Supports configurable `API_BASE_URL` parameter
  - Runs Flutter web dev server on port 8080
- Added convenience wrapper in main `Makefile` for easy access

**Files Changed**:
- `pumaguard-ui/Makefile` - Added `dev-ui-web` target
- `pumaguard/Makefile` - Added wrapper target with API_BASE_URL support

**Usage**:
```bash
# Start UI dev server (default API: http://localhost:5000)
make dev-ui-web

# With custom API URL
make dev-ui-web API_BASE_URL=http://192.168.1.50:5000

# For Android emulator
make dev-ui-web API_BASE_URL=http://10.0.2.2:5000
```

### 2. Implemented Image Grouping Feature

**Problem**: The UI had incomplete grouping functionality with compilation errors:
- `ImageGrouping` enum was undefined
- Preference loading/saving methods were missing
- No actual grouping logic was implemented

**Solution**: Added complete image grouping implementation to `lib/screens/image_browser_screen.dart`:

#### ImageGrouping Enum
```dart
enum ImageGrouping { none, day, week }
```

#### Preference Management
- `_loadGroupingPreference()` - Loads saved grouping preference from SharedPreferences on screen init
- `_saveGroupingPreference(ImageGrouping)` - Persists grouping selection across app restarts

#### Grouping Algorithm (`_groupImages()`)
The algorithm handles three modes:

**None**: Returns images as-is without modification

**Day**: 
- Groups images by calendar day (YYYY-MM-DD format)
- Includes day of week in header (e.g., "2024-01-15 Monday")
- Sorts groups with most recent day first

**Week**:
- Groups images by ISO week (Monday-Sunday)
- Calculates week boundaries based on weekday
- Formats header as "MMM d - MMM d, yyyy" (e.g., "Jan 15 - Jan 21, 2024")
- Sorts groups with most recent week first

**Key Features**:
- Handles null/missing timestamps gracefully (skips those images)
- Maintains original image order within each group
- Inserts header items with metadata:
  - `is_header: true` - Identifies header rows
  - `header_text` - Display string for the group
  - `image_count` - Number of images in group

#### UI Improvements
- Refactored image rendering into `_buildImageItem()` helper method
- Changed from `GridView` to `CustomScrollView` with `SliverList` for flexible layout
- Headers display with:
  - Bold title showing date/week range
  - Badge showing image count
  - Consistent Material Design styling

**Files Changed**:
- `pumaguard-ui/lib/screens/image_browser_screen.dart` - Complete grouping implementation

### 3. Comprehensive Test Suite

Created `test/screens/image_browser_grouping_test.dart` with 12 test cases covering:

#### Core Functionality Tests
- ✅ No grouping returns images unchanged
- ✅ Day grouping creates correct headers with day-of-week
- ✅ Week grouping creates correct week range headers
- ✅ Proper header count and image count in each group

#### Sorting Tests
- ✅ Groups sorted by most recent first (descending order)
- ✅ Images within groups maintain original order
- ✅ Sorting works with unsorted input data

#### Edge Cases
- ✅ Handles images without timestamps (skips them)
- ✅ Empty image list returns empty result
- ✅ Single image creates single group
- ✅ Images in same week/day grouped correctly
- ✅ Year boundary handled correctly for week grouping

**Test Results**: All 12 tests pass ✓

**Files Created**:
- `pumaguard-ui/test/screens/image_browser_grouping_test.dart`

## Testing

### Running Tests

```bash
# Run grouping tests only
cd pumaguard-ui
flutter test test/screens/image_browser_grouping_test.dart

# Run all UI tests
flutter test

# Run full pre-commit validation
make pre-commit
```

### Manual Testing

1. Start backend: `make dev-backend`
2. Start UI: `make dev-ui-web`
3. Navigate to Image Browser screen
4. Select a folder with images from different dates
5. Test dropdown options:
   - **None**: Images displayed in flat grid
   - **Day**: Images grouped by calendar day with headers
   - **Week**: Images grouped by week with date ranges
6. Verify preference persists after page refresh

## Technical Details

### Date Handling

- Backend provides `modified` timestamp in Unix epoch seconds
- UI converts to milliseconds: `timestamp * 1000`
- Uses `intl` package's `DateFormat` for consistent formatting
- ISO week calculation: Week starts Monday (weekday = 1)

### Performance Considerations

- Grouping performed in-memory on already-loaded images
- O(n log n) complexity due to sorting (acceptable for typical image counts)
- Headers are lightweight metadata objects
- No additional API calls required

### Future Enhancements

Possible improvements for future versions:

1. **Additional Grouping Options**:
   - Month grouping
   - Year grouping
   - Custom date ranges

2. **UI Improvements**:
   - Collapsible groups
   - Jump-to-date navigation
   - Group statistics (file sizes, detection counts)

3. **Performance**:
   - Virtual scrolling for very large image sets
   - Lazy loading of image groups

## Validation

All quality checks pass:

```bash
✓ flutter analyze   - No issues found
✓ flutter test      - 42 tests passed
✓ dart format       - Code properly formatted
✓ flutter build web - Builds successfully
```

## References

- Issue tracking: Image grouping feature request
- UI Development Context: `pumaguard-ui/UI_DEVELOPMENT_CONTEXT.md`
- Contributing Guide: `CONTRIBUTING.md`
