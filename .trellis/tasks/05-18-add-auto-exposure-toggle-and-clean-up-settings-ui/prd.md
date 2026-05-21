# Add Auto-Exposure Toggle and Clean Up Settings UI

## Goal

Add a per-camera exposure mode toggle (auto/manual) using Hikvision SDK's built-in `ExposureAuto` feature, and clean up the settings panel layout.

## Requirements

### Backend
1. Add `exposure_mode` field to camera params config: `"auto"` or `"manual"` (default: `"manual"`)
2. Add `set_exposure_mode()` method to `HikCameraDriver` that sets `ExposureAuto = 2` (continuous) or `0` (off)
3. Update `apply_params()` to handle exposure mode
4. Update `config/settings` endpoint to persist and return exposure mode
5. On camera connect, apply the saved exposure mode

### Frontend
6. Add exposure mode toggle per slot in SettingsPanel (auto/manual)
7. When mode is "auto", grey out or hide the exposure time slider
8. Clean up settings panel layout (group related controls, improve spacing)
9. Persist exposure mode via `/config/settings` API

## Acceptance Criteria

- [ ] `ExposureAuto` can be set to `2` (auto) via SDK
- [ ] `ExposureAuto` can be set to `0` (manual) via SDK
- [ ] Exposure mode persisted in config.json
- [ ] Settings UI shows toggle per camera slot
- [ ] Manual exposure slider hidden when auto mode selected
- [ ] `cargo check` passes (no Rust changes needed)
