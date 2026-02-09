// ==UserScript==
// @name         HRMS Tracker Sync (v5.1 WORKED)
// @namespace    http://tampermonkey.net/
// @version      5.1
// @description  Syncs "WORKED" column. Pop-up confirms installation.
// @author       Antigravity
// @match        *://hrms-420.netlify.app/*
// @match        *://hrms-ask-1.onrender.com/*
// @grant        GM_xmlhttpRequest
// @connect      127.0.0.1
// @run-at       document-start
// ==/UserScript==

(function () {
    'use strict';

    // CONFIGURATION
    const APP_BASE = "http://127.0.0.1:12345";

    // DIAGNOSTIC ALERT (Runs once to prove script is active)
    if (!sessionStorage.getItem('hrms_tracker_alert_shown_v51')) {
        alert("Tracker Script v5.1 (WORKED SYNC) is INSTALLED and ACTIVE.\n\nLook for the black box in the bottom right corner.");
        sessionStorage.setItem('hrms_tracker_alert_shown_v51', 'true');
    }

    /* -------------------- UI ENGINE -------------------- */
    // Uses Shadow DOM or aggressive insertion to prevent removal
    function ensureUI() {
        let container = document.getElementById('hrms-sync-container');

        if (!container) {
            container = document.createElement('div');
            container.id = 'hrms-sync-container';
            Object.assign(container.style, {
                position: 'fixed',
                bottom: '20px',
                right: '20px',
                zIndex: '2147483647',
                fontFamily: 'Segoe UI, Arial, sans-serif',
                pointerEvents: 'none' // Allow clicking through if needed
            });

            // Inner Box
            const box = document.createElement('div');
            box.id = 'hrms-status-box';
            Object.assign(box.style, {
                backgroundColor: '#222',
                color: '#fff',
                padding: '12px 20px',
                borderRadius: '8px',
                border: '2px solid orange', // Default: Searching
                boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
                fontSize: '14px',
                fontWeight: 'bold',
                display: 'flex',
                alignItems: 'center',
                gap: '10px'
            });
            box.innerText = "Tracker: Initializing...";

            container.appendChild(box);
            (document.body || document.documentElement).appendChild(container);
        }
        return document.getElementById('hrms-status-box');
    }

    function updateStatus(text, color) {
        const box = ensureUI();
        if (box) {
            box.innerText = text;
            box.style.borderColor = color;
        }
    }

    /* -------------------- TIME PARSER -------------------- */
    function getPunchTimeObj() {
        // STRATEGY: Find "First In", "Last Out", and "WORKED" columns
        const headers = Array.from(document.querySelectorAll('th'));
        const inHeader = headers.find(h => /FIRST IN|PUNCH IN|IN TIME/i.test(h.innerText));
        const outHeader = headers.find(h => /LAST OUT|PUNCH OUT|OUT TIME/i.test(h.innerText));
        const workHeader = headers.find(h => /WORKED|DURATION|TOTAL TIME/i.test(h.innerText));

        if (inHeader) {
            const table = inHeader.closest('table');
            // Get Indices
            const headerRow = inHeader.parentElement;
            const inIndex = Array.from(headerRow.children).indexOf(inHeader);
            const outIndex = outHeader ? Array.from(headerRow.children).indexOf(outHeader) : -1;
            const workIndex = workHeader ? Array.from(headerRow.children).indexOf(workHeader) : -1;

            // Find the *LAST* valid row (assuming chronological order)
            // Or usually the first row is the latest? It depends on the sorting.
            // Let's assume ROW 1 is the relevant one for today.
            const rows = table.querySelectorAll('tbody tr');
            if (rows.length > 0) {
                const row = rows[0]; // First data row
                if (row.children[inIndex]) {
                    let tIn = row.children[inIndex].innerText.trim();
                    let tOut = (outIndex > -1 && row.children[outIndex]) ? row.children[outIndex].innerText.trim() : null;
                    let tWorked = (workIndex > -1 && row.children[workIndex]) ? row.children[workIndex].innerText.trim() : null;

                    // Clean data
                    if (["--", "-", "", "null"].includes(tIn)) tIn = null;
                    if (["--", "-", "", "null"].includes(tOut)) tOut = null;
                    if (["--", "-", "", "null"].includes(tWorked)) tWorked = null;

                    if (tIn) return { in: tIn, out: tOut, worked: tWorked };
                }
            }
        }
        return null; // Not found
    }

    // Legacy Wrapper
    function getPunchTime() {
        const obj = getPunchTimeObj();
        return obj ? obj.in : null;
    }

    /* -------------------- CORE LOOP -------------------- */
    let isConnected = false;

    function loop() {
        // 1. Ensure UI is visible (Fix for SPAs clearing the DOM)
        ensureUI();

        // 2. Parsers
        const punchIn = getPunchTime();

        // 3. Status Update on Screen
        if (!punchIn) {
            // Check context to give helpful messages
            if (/login/i.test(document.title)) {
                updateStatus("Tracker: User Logged Out", "#FF4444");
                // Send Logout Signal
                GM_xmlhttpRequest({
                    method: "GET",
                    url: `${APP_BASE}/sync?status=logged_out`,
                    onload: () => isConnected = true,
                    onerror: () => isConnected = false
                });
            } else if (!/attendance/i.test(window.location.href)) {
                updateStatus("Tracker: Go to 'Attendance'", "#FFA500");
                // Send Heartbeat (Still logged in, just navigating)
                GM_xmlhttpRequest({
                    method: "GET",
                    url: `${APP_BASE}/sync?status=logged_in`, // Just heartbeat
                    onload: () => isConnected = true,
                    onerror: () => isConnected = false
                });
            } else {
                updateStatus("Tracker: Searching Table...", "#FFA500");
                GM_xmlhttpRequest({
                    method: "GET",
                    url: `${APP_BASE}/sync?status=logged_in&punch_in=null`,
                    onload: () => isConnected = true,
                    onerror: () => isConnected = false
                });
            }
        } else {
            // 4. Sync
            const today = new Date().toISOString().split('T')[0];

            // Check for Punch Out in the same row/table if possible. 
            // Current getPunchTime() only gets "First In". 
            // Ideally we need "Last Out" too. 
            // For now, if we found Punch In, we assume we are "Logged In + Punched In".
            // We need to upgrade getPunchTime to return an object {in, out}

            const punchData = getPunchTimeObj(); // UPGRADED FUNCTION CALL
            const pIn = punchData ? punchData.in : null;
            const pOut = punchData ? punchData.out : null;
            const pWork = punchData ? punchData.worked : null;

            if (pIn) {
                const url = `${APP_BASE}/sync?punch_in=${encodeURIComponent(pIn)}&punch_out=${encodeURIComponent(pOut || "")}&worked=${encodeURIComponent(pWork || "")}&date=${encodeURIComponent(today)}&status=logged_in`;

                GM_xmlhttpRequest({
                    method: "GET",
                    url: url,
                    onload: () => {
                        let display = `In: ${pIn}`;
                        if (pOut) {
                             display += ` | Out: ${pOut}`;
                        } else {
                             display += ` | Running...`;
                        }
                        if (pWork) display += ` | Worked: ${pWork}`;
                        
                        updateStatus(display, pOut ? "#FFA500" : "#00C851"); // Orange if Out, Green if In
                        isConnected = true;
                    },
                    onerror: () => {
                        updateStatus("Tracker: App Error", "#FF4444");
                        isConnected = false;
                    }
                });
            }
        }

        // Heartbeat if idle (to keep "Waiting" status away on App)
        if (!punchIn && !isConnected) {
            GM_xmlhttpRequest({
                method: "GET",
                url: `${APP_BASE}/heartbeat`,
                onload: () => isConnected = true,
                onerror: () => isConnected = false
            });
        }
    }

    // Run often to combat React re-renders
    setInterval(loop, 2000);

})();