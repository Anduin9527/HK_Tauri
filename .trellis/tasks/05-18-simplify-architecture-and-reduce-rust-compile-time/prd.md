# Simplify Architecture and Reduce Rust Compile Time

## Goal

Reduce Rust compile time and code complexity by removing all Tauri plugins, dead code, and unnecessary dependencies. Replace plugin functionality with native Rust (`std::process::Command`).

## What I already know

- Rust Cargo.lock has **493 crates** — compile time is long
- Frontend only calls **1 Rust command**: `invoke('open_path', ...)`
- `greet` and `open_data_dir` are dead code (never called from frontend)
- `tauri-plugin-opener` — only for file opening, replaceable with `explorer.exe`
- `tauri-plugin-shell` — only for sidecar management, replaceable with `std::process::Command`
- `serde_json` — imported but unused in `lib.rs`
- `tauri` core — essential, must keep
- Project is **Windows-only** (Hikvision SDK) — no cross-platform concerns

## Requirements

### Remove dead code
1. Remove `greet` function and its handler registration
2. Remove `open_data_dir` function and its handler registration
3. Remove `serde_json` from Cargo.toml

### Remove `tauri-plugin-opener`
4. Remove `tauri-plugin-opener` from Cargo.toml and `lib.rs`
5. Reimplement `open_path` with `std::process::Command::new("explorer").arg(path).spawn()`

### Remove `tauri-plugin-shell` (sidecar management)
6. Remove `tauri-plugin-shell` from Cargo.toml and `lib.rs`
7. Implement sidecar spawning with `std::process::Command`:
   - Resolve `backend-{target_triple}.exe` path (dev: `src-tauri/bin/`, prod: next to exe)
   - Set env vars: `HK_TAURI_DATA_DIR`, `HK_TAURI_CONFIG_DIR`, `HK_TAURI_PARENT_PID`
   - Capture stdout/stderr to `backend.log`
   - Kill process on window close and app exit
8. Remove `tauri.conf.json` → `bundle.externalBin` if no longer needed

### Verify
9. `cargo check` passes
10. `npm run tauri dev` launches backend and frontend correctly
11. Settings → "打开文件夹" still works
12. Closing the window kills backend process cleanly

## Acceptance Criteria

- [ ] `tauri-plugin-opener` removed from Cargo.toml
- [ ] `tauri-plugin-shell` removed from Cargo.toml
- [ ] `serde_json` removed from Cargo.toml
- [ ] `greet` and `open_data_dir` removed from lib.rs
- [ ] `open_path` uses `std::process::Command`
- [ ] Sidecar spawned with `std::process::Command` + env vars
- [ ] Backend process killed on app exit
- [ ] `cargo check` passes with no errors
- [ ] `cargo tauri dev` works end-to-end

## Definition of Done

- `cargo check` passes clean
- `npm run tauri dev` starts backend + frontend
- Camera connect/disconnect works (backend is alive)
- Opening data folder from Settings works
- Closing window kills backend.log shows clean shutdown
- Cargo.lock crate count reduced by ~40-60 crates vs baseline

## Out of Scope

- Replacing Tauri with another framework
- Modifying Python backend
- Modifying React frontend
- Build script changes (build_windows.ps1)
- Cargo profile optimizations (follow-up)
- Cross-platform support (Windows-only project)

## Technical Notes

### Sidecar path resolution
- **Dev mode** (`cargo tauri dev`): binary at `src-tauri/bin/backend-x86_64-pc-windows-msvc.exe`
- **Production** (installed app): binary next to the main `.exe`
- Use `std::env::current_exe()` for production, relative path for dev
- Rust target triple: `x86_64-pc-windows-msvc` (hardcoded or detected via `std::env::consts`)

### Security: `open_path` check
- Current code validates path contains `\hk_tauri_data` (case-insensitive)
- Preserve this security check in the new implementation

### `serde` dependency
- Still needed: Tauri command parameters require `serde::Deserialize`
- Only `serde_json` can be removed
