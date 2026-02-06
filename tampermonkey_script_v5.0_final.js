// ==UserScript==
// @name         HRMS Tracker Sync (v5.0 FINAL)
// @namespace    http://tampermonkey.net/
// @version      5.0
// @description  Syncs "FIRST IN" time. Pop-up confirms installation.
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
    if (!sessionStorage.getItem('hrms_tracker_alert_shown')) {
        alert("Tracker Script v5.0 is INSTALLED and ACTIVE.\n\nLook for the black box in the bottom right corner.");
        sessionStorage.setItem('hrms_tracker_alert_shown', 'true');
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
    function getPunchTime() {
        // STRATEGY 1: HEADER SEARCH (Most Accurate)
        // Find header containing "FIRST IN"
        const headers = Array.from(document.querySelectorAll('th'));
        const targetHeader = headers.find(h => /FIRST IN/i.test(h.innerText));

        if (targetHeader) {
            // Find the column index
            const headerRow = targetHeader.parentElement;
            const columnIndex = Array.from(headerRow.children).indexOf(targetHeader);

            // Find the data in the first row of the table body
            const table = targetHeader.closest('table');
            const firstDataRow = table.querySelector('tbody tr');

            if (firstDataRow && firstDataRow.children[columnIndex]) {
                return firstDataRow.children[columnIndex].innerText.trim();
            }
        }
        return null;
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
                updateStatus("Tracker: Please Login", "#FF4444"); // Red
            } else if (!/attendance/i.test(window.location.href)) {
                updateStatus("Tracker: Go to 'Attendance'", "#FFA500"); // Orange
            } else {
                updateStatus("Tracker: Searching Table...", "#FFA500");
            }
        } else {
            // 4. Sync
            const today = new Date().toISOString().split('T')[0];
            const url = `${APP_BASE}/sync?punch_in=${encodeURIComponent(punchIn)}&date=${encodeURIComponent(today)}`;

            GM_xmlhttpRequest({
                method: "GET",
                url: url,
                onload: () => {
                    updateStatus(`Synced: ${punchIn}`, "#00C851"); // Green
                    isConnected = true;
                },
                onerror: () => {
                    updateStatus("Tracker: App Error (Check Python)", "#FF4444");
                    isConnected = false;
                }
            });
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
