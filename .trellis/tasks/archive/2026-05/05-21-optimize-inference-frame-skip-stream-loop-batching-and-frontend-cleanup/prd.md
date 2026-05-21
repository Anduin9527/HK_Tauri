# Optimization: Inference Frame-Skip, Stream Loop Batching, Frontend Cleanup

## Goal
Improve real-time performance and code quality across backend and frontend.

## Scope

### 1. Backend: Inference Frame-Skip Strategy
**Problem**: `detector.py` `predict()` holds a global lock. With 4 cameras competing, each camera's FPS drops to ~5.
**Solution**: Add a frame-skip mechanism in the stream worker — if inference is still running for a camera, skip the current frame instead of blocking. This keeps the stream responsive even under heavy load.
- Track per-slot "inference in progress" state
- If busy, skip inference for the current frame (still grab and display raw frame)
- Only trigger inference when the previous one has completed

### 2. Backend: Stream Loop Batching
**Problem**: Each stream loop iteration makes 4-6 `asyncio.to_thread()` calls, causing excessive thread pool scheduling overhead.
**Solution**: Batch the synchronous operations (resize, encode, draw) into a single function called via one `to_thread()`.
- Create `_process_frame(frame, detections, ...)` that does resize + draw + encode in one call
- Reduce per-frame `to_thread` calls from 4-6 to 1-2 (one for processing, one for inference if needed)

### 3. Frontend: Dead Code Cleanup + VideoFeed Reconnect
**Problem**:
- Empty `setInterval` (line 34) — dead code
- Duplicate `toggleScene` / `toggleSceneMode` — two functions doing the same thing
- `VideoFeed` has no reconnection on stream error
- Unused dependencies (`autoprefixer`, `postcss`, `tailwind-merge`)
**Solution**:
- Remove dead `setInterval`
- Consolidate to single `toggleScene` function
- Add retry with exponential backoff to `VideoFeed` on error
- Remove unused deps from `package.json`

## Out of Scope
- App.jsx full refactor (separate task)
- Socket.IO replacement (separate task)
- Rust crate-type cleanup (minor, separate)

## Acceptance Criteria
- [ ] 4-camera stream maintains higher FPS under load (skip frame when inference busy)
- [ ] Stream worker uses 1-2 `to_thread` calls per frame instead of 4-6
- [ ] No dead code in App.jsx (empty setInterval, duplicate toggle)
- [ ] VideoFeed auto-reconnects on stream error with backoff
- [ ] Unused npm deps removed
