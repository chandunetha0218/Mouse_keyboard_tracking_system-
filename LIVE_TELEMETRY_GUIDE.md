# Live Telemetry Implementation Guide (Backend)

This file was generated to save the context of the Live Tracking feature we implemented in the Desktop Tracker.

## What is already done in the Desktop App (`Mouse_keyboard_tracking_system-`):
In `api_client.py`, the desktop application is now configured to send a POST request every 30 seconds to the backend whenever the user is punched in.

**Payload sent by Desktop App:**
```json
{
    "employeeId": "INT2607",
    "status": "WORKING",     // or "IDLE"
    "duration_seconds": 30,  // time since last ping
    "timestamp": 1708671234.56
}
```
**Endpoint Called:** `POST https://hrms-ask-1.onrender.com/api/activity/live-status`

---

## What needs to be done in the HRMS Backend (`hrms-ask` folder):

When you open the HRMS backend project, you can ask me to guide you through these steps:

### 1. Create a `LiveTracking` Mongoose Model
We need a schema to store the current status of each employee.
* Fields: `employeeId`, `currentStatus` (WORKING/IDLE), `lastPing` (Date), `lastUpdated` (Date).

### 2. Create the Route and Controller (`POST /api/activity/live-status`)
We need to create the endpoint that the Desktop App is trying to hit.
* This route will receive the payload from the Desktop App and `findOneAndUpdate` the employee's `LiveTracking` record.

### 3. Create an Admin Route (`GET /api/activity/live-status/all`)
We need an endpoint for the Admin Dashboard to fetch the live status of all employees.
* This will fetch all records from the `LiveTracking` collection where the `lastPing` is within the last few minutes (to filter out disconnected users).

### 4. Admin Frontend Dashboard
Update the React frontend Admin panel to poll the `GET` route every 30-60 seconds and display a list or grid of employees with Green/Yellow dots showing who is currently "WORKING" or "IDLE".

***
*Note to AI Agent: If the user opens the `hrms-ask` folder and asks for the live telemetry guide, read this file if needed and begin guiding them through Step 1.*
