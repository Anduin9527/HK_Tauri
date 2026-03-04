# Backend API Documentation

This document describes the REST API endpoints provided by the backend service.

**Base URL**: `http://localhost:8000`

## Camera Management

### Discover Cameras
Enumerates all available Hikvision cameras (GigE and USB) connected to the system.

- **URL**: `/cameras/discover`
- **Method**: `GET`
- **Response**:
  ```json
  {
    "cameras": [
      {
        "index": 0,
        "name": "Camera Name",
        "model": "Model Number",
        "serial": "Serial Number",
        "type": "GIGE/USB"
      }
    ]
  }
  ```

### Connect Camera
Connects a specific physical camera to a logical slot (0-3).

- **URL**: `/cameras/{slot_id}/connect`
- **Method**: `POST`
- **Path Parameters**:
  - `slot_id`: Integer (0-3), the logical slot to bind the camera to.
- **Body**:
  ```json
  {
    "camera_index": 0
  }
  ```
  - `camera_index`: The index of the camera returned by the discovery API.

### Disconnect Camera
Disconnects the camera currently bound to the specified slot.

- **URL**: `/cameras/{slot_id}/disconnect`
- **Method**: `POST`
- **Path Parameters**:
  - `slot_id`: Integer (0-3).

### Video Feed
Streams the real-time video feed from a connected camera (MJPEG format).

- **URL**: `/video_feed/{camera_id}`
- **Method**: `GET`
- **Path Parameters**:
  - `camera_id`: Integer (0-3), corresponding to the slot ID.
- **Note**: This endpoint returns a continuous multipart stream (`multipart/x-mixed-replace`).

## System Control

### Get System Status
Returns the current status of the backend, including model loading state and camera connection statuses.

- **URL**: `/status`
- **Method**: `GET`
- **Response**:
  ```json
  {
    "model_loaded": true,
    "device": "cuda:0",
    "cameras": [
      { "id": 0, "connected": true, "index": 0 },
      ...
    ]
  }
  ```

### Get Operation Mode
Gets the current operation mode (Real-time Auto Detection vs Manual Trigger).

- **URL**: `/config/mode`
- **Method**: `GET`
- **Response**:
  ```json
  {
    "manual_mode": false
  }
  ```

### Set Operation Mode
Sets the operation mode.

- **URL**: `/config/mode`
- **Method**: `POST`
- **Body**:
  ```json
  {
    "manual_mode": true
  }
  ```

### Trigger Detection
Manually triggers a detection cycle on all connected cameras. Useful in "Manual Mode".

- **URL**: `/trigger/detect`
- **Method**: `POST`
- **Response**:
  ```json
  {
    "message": "Detection completed",
    "results": [
      {
        "slot": 0,
        "detections": 2,
        "image_url": "http://localhost:8000/history/..."
      }
    ]
  }
  ```

## Configuration

### Get Settings
Gets the current detection model settings.

- **URL**: `/config/settings`
- **Method**: `GET`
- **Response**:
  ```json
  {
    "conf": 0.25,
    "imgsz": 640
  }
  ```

### Update Settings
Updates the detection model settings.

- **URL**: `/config/settings`
- **Method**: `POST`
- **Body**:
  ```json
  {
    "conf": 0.5,
    "imgsz": 640
  }
  ```

## Logs & Debug

### Get Logs
Retrieves the latest system logs.

- **URL**: `/logs`
- **Method**: `GET`
- **Query Parameters**:
  - `lines`: Number of recent log lines to return (default: 50).

### Predict Image (Debug)
Upload a local image file to test the detection model.

- **URL**: `/predict/image`
- **Method**: `POST`
- **Body**: `multipart/form-data` with key `file`.
- **Response**:
  ```json
  {
    "message": "Success",
    "detections": 1,
    "image_url": "http://localhost:8000/history/..."
  }
  ```
