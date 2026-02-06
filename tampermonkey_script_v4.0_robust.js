// ==UserScript==
// @name         HRMS Tracker Sync (v4.0 ROBUST)
// @namespace    http://tampermonkey.net/
// @version      4.0
// @description  Syncs "FIRST IN" time to local tracker
// @author       Antigravity
// @match        *://hrms-420.netlify.app/*
// @match        *://hrms-ask-1.onrender.com/*
// @grant        GM_xmlhttpRequest
// @connect      127.0.0.1
// @run-at       document-end
// ==/UserScript==

(function () {
    'use strict';
    console.log(">>> TRACKER SCRIPT STARTED <<<");

    const APP_BASE = "http://127.0.0.1:12345";
    let statusDiv = null;

    // 1. Force UI Creation immediately
    function createUI() {
        if (document.getElementById('hrms-sync-indicator')) return;

        const div = document.createElement('div');
        div.id = 'hrms-sync-indicator';
        div.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            min-width: 150px;
            padding: 12px;
            background-color: #333;
            color: white;
            border: 3px solid orange;
            border-radius: 10px;
            z-index: 2147483647;
            font-family: Arial, sans-serif;
            font-size: 14px;
            font-weight: bold;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        `;

        div.innerHTML = "Tracker: Looking for Table...";

        if (document.body) {
            document.body.appendChild(div);
            statusDiv = div;
            console.log(">>> UI CREATED <<<");
        } else {
            console.log(">>> BODY NOT READY <<<");
        }
    }

    function updateStatus(text, color) {
        if (!statusDiv) createUI();
        if (statusDiv) {
            statusDiv.innerText = text;
            statusDiv.style.borderColor = color;
        }
    }

    // Try multiple times to ensure it appears
    setTimeout(createUI, 500);
    setTimeout(createUI, 2000);

    /* -------------------- PARSER -------------------- */
    function getPunchState() {
        let punchIn = null;

        // Strategy 1: Table
        const headers = Array.from(document.querySelectorAll('th'));
        const inHeader = headers.find(h => /FIRST IN/i.test(h.innerText));
        if (inHeader) {
            const row = inHeader.closest('tr');
            const table = row.closest('table');
            const dataRow = table.querySelector('tbody tr');
            if (dataRow) {
                const index = Array.from(row.children).indexOf(inHeader);
                if (dataRow.children[index]) {
                    punchIn = dataRow.children[index].innerText.trim();
                }
            }
        }

        // Strategy 2: Text Search (Backup)
        if (!punchIn) {
            // Look for "10:00:00 AM" pattern near keywords
            const timeRegex = /\d{1,2}:\d{2}(?::\d{2})?\s?(?:AM|PM)/i;
            const nodes = document.querySelectorAll('*');
            for (let node of nodes) {
                if (node.children.length === 0 && node.innerText) {
                    // Check if this node has time
                    if (timeRegex.test(node.innerText)) {
                        // Check if "First In" is nearby (parent/sibling)
                        // This is loose, but might catch it if table fails
                        if (/first in|login/i.test(document.body.innerText)) {
                            // Only grab if it looks like a time
                            // punchIn = node.innerText.match(timeRegex)[0]; // Too risky to auto-grab without context
                        }
                    }
                }
            }
        }

        return { punchIn };
    }

    function sync() {
        const state = getPunchState();
        const dateStr = new Date().toISOString().split('T')[0];

        if (state.punchIn) {
            const url = `${APP_BASE}/sync?punch_in=${encodeURIComponent(state.punchIn)}&date=${encodeURIComponent(dateStr)}`;

            GM_xmlhttpRequest({
                method: "GET",
                url: url,
                onload: function () {
                    updateStatus(`Synced: ${state.punchIn}`, "#00FF00"); // Green
                },
                onerror: function (err) {
                    console.error("Sync Error:", err);
                    updateStatus("App Disconnected", "#FF0000"); // Red
                }
            });
        } else {
            updateStatus("Open 'Attendance' Page", "orange");
        }
    }

    // Check every 3 seconds
    setInterval(sync, 3000);

})();
