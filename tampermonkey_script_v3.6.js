// ==UserScript==
// @name         HRMS State-Based Tracker Sync (v3.6 FIXED)
// @namespace    http://tampermonkey.net/
// @version      3.6
// @description  Syncs "FIRST IN" time from the attendance table
// @author       Antigravity
// @match        *://hrms-420.netlify.app/*
// @match        *://hrms-ask-1.onrender.com/*
// @grant        GM_xmlhttpRequest
// @connect      localhost
// @run-at       document-idle
// ==/UserScript==

(function () {
    'use strict';
    console.log("[Tracker Sync v3.6] Table Mode Active");
    const APP_BASE = "http://127.0.0.1:12345";
    let lastSyncedState = null;

    /* -------------------- UI -------------------- */
    function updateStatus(text, color = "blue") {
        let div = document.getElementById('hrms-sync-indicator');
        if (!div) {
            div = document.createElement('div');
            div.id = 'hrms-sync-indicator';
            div.style.position = 'fixed';
            div.style.bottom = '15px';
            div.style.right = '15px';
            div.style.padding = '8px 12px';
            div.style.background = 'white';
            div.style.color = '#333';
            div.style.border = `2px solid ${color}`;
            div.style.borderRadius = '20px';
            div.style.zIndex = '999999';
            div.style.fontSize = '12px';
            div.style.fontWeight = '600';
            div.style.boxShadow = '0 3px 10px rgba(0,0,0,0.1)';
            div.style.pointerEvents = 'none';
            document.body.appendChild(div);
        }
        div.innerText = `Tracker: ${text}`;
        div.style.borderColor = color;
    }

    /* -------------------- PARSER -------------------- */
    function getPunchState() {
        let punchIn = null;
        const headers = Array.from(document.querySelectorAll('th'));
        const inHeader = headers.find(h => /FIRST IN/i.test(h.innerText));

        if (inHeader) {
            const row = inHeader.closest('tr');
            const dataRows = row.closest('table').querySelectorAll('tbody tr');
            if (dataRows.length > 0) {
                const index = Array.from(row.children).indexOf(inHeader);
                if (dataRows[0].children[index]) {
                    punchIn = dataRows[0].children[index].innerText.trim();
                }
            }
        }

        // Backup: Look for text like "10:21:45 AM"
        if (!punchIn) {
            const timeParams = /\d{1,2}:\d{2}(?::\d{2})?\s?(?:AM|PM)/i;
            const labelNode = Array.from(document.querySelectorAll('div, span, p'))
                .find(d => /FIRST IN/i.test(d.innerText) && d.innerText.length < 50);

            if (labelNode) {
                const match = labelNode.innerText.match(timeParams);
                if (match) punchIn = match[0];
                else if (labelNode.nextElementSibling && timeParams.test(labelNode.nextElementSibling.innerText)) {
                    punchIn = labelNode.nextElementSibling.innerText.match(timeParams)[0];
                }
            }
        }
        return { punchIn, date: new Date().toISOString().split('T')[0] };
    }

    /* -------------------- SYNC -------------------- */
    function sync() {
        try {
            const state = getPunchState();
            if (!state.punchIn) {
                updateStatus("Searching...", "orange");
                return;
            }

            const key = JSON.stringify(state);
            if (key === lastSyncedState) return;
            lastSyncedState = key;

            const url = `${APP_BASE}/sync?punch_in=${encodeURIComponent(state.punchIn)}&date=${encodeURIComponent(state.date)}`;

            GM_xmlhttpRequest({
                method: "GET",
                url,
                onload: () => updateStatus(`Synced: ${state.punchIn}`, "green"),
                onerror: () => updateStatus("App Offline", "red")
            });
        } catch (e) {
            console.error(e);
        }
    }

    // Heartbeat
    GM_xmlhttpRequest({
        method: "GET",
        url: `${APP_BASE}/heartbeat`,
        onload: () => console.log("Heartbeat OK"),
        onerror: () => console.warn("Heartbeat Fail")
    });
    setInterval(sync, 5000);
})();
