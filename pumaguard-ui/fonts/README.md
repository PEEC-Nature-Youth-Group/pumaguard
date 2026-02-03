# Fonts Directory

This directory contains embedded fonts for the PumaGuard UI to work offline/air-gapped.

## Recommended Fonts

For optimal offline performance, download and place the following fonts in this directory:

### Roboto (Main UI Font)
- **Download**: https://fonts.google.com/download?family=Roboto
- **Files needed**:
  - `Roboto-Regular.ttf`
  - `Roboto-Medium.ttf`
  - `Roboto-Bold.ttf`
  - `Roboto-Light.ttf`

### Roboto Mono (Monospace Font)
- **Download**: https://fonts.google.com/download?family=Roboto+Mono
- **Files needed**:
  - `RobotoMono-Regular.ttf`
  - `RobotoMono-Medium.ttf`
  - `RobotoMono-Bold.ttf`

## Alternative: Use Material Icons Only

If you don't need custom fonts, the app will fall back to system fonts. The Material Icons font is already included via `uses-material-design: true` in pubspec.yaml.

## Installation Steps

1. Download the font files from Google Fonts
2. Extract the TTF files from the downloaded ZIP
3. Copy the TTF files to this directory
4. The fonts are already configured in `pubspec.yaml`
5. Run `flutter pub get` and rebuild

## License

Both Roboto and Roboto Mono are licensed under the Apache License 2.0, which allows for commercial use, modification, and distribution.