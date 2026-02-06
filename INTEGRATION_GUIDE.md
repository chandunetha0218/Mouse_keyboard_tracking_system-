# HRMS Integration Guide

To connect the Desktop Activity Tracker with your HRMS website, your web developers need to expose the following API Endpoints on your server.

## 1. Authentication
The desktop app needs to log in to link the installed app with a specific employee.

- **Endpoint**: `POST /api/v1/auth/login`
- **Request**:
  ```json
  {
    "username": "sagar@example.com",
    "password": "secret_password"
  }
  ```
- **Response**:
  ```json
  {
    "token": "secure_jwt_token_abc123",
    "employee_id": 45
  }
  ```

## 2. Check Punch Status
The desktop app polls this endpoint every 2 seconds to see if it should be recording or not. This connects the "Punch In" button on the website to the desktop app.

- **Endpoint**: `GET /api/v1/employee/{employee_id}/status`
- **Headers**: `Authorization: Bearer <token>`
- **Response**:
  ```json
  {
    "status": "PUNCHED_IN" 
  }
  ```
  *(Or returns `"PUNCHED_OUT"` if they are off the clock)*

## 3. Upload Activity Logs
The desktop app sends small chunks of data (e.g., every 5-10 seconds) describing what the user was doing. The Admin Report is generated from this data.

- **Endpoint**: `POST /api/v1/activity/log`
- **Headers**: `Authorization: Bearer <token>`
- **Request**:
  ```json
  {
    "employee_id": 45,
    "status": "WORKING", 
    "duration": 5,
    "timestamp": 1706605000
  }
  ```
  *(Status can be "WORKING" or "IDLE")*

## Architecture Flow
1. Employee clicks **Punch In** on HRMS Website -> Website updates Database (`status='PUNCHED_IN'`).
2. Desktop App (running in background) asks API: "Status?" -> API replies "PUNCHED_IN".
3. Desktop App starts monitoring Mouse/Keyboard.
4. Desktop App pushes logs ("Working for 5s", "Idle for 30s") to the API.
5. HRMS Website Admin Dashboard reads these logs to generate the report.

## Deployment on Netlify
If your HRMS is hosted on **Netlify**, you likely need to use **Netlify Functions** to handle these requests.

1. Create a function file (e.g., `netlify/functions/api.js`).
2. Inside that function, handle the `GET /status` and `POST /log` logic by connecting to your database (MongoDB, Supabase, etc.).
3. The **Server URL** you will enter into the Desktop App will be:
   `https://your-site.netlify.app/.netlify/functions/api`

Ensure your function handles **CORS** if necessary, though desktop apps usually bypass standard browser CORS restrictions.
