/*
    safe_html.js

    Treasure Row Campus Marketplace
    Created by Donovan Griffin - Iteration 3

    Shared helpers for putting user-written text (store names, listing titles,
    descriptions, usernames, return reasons, ...) into HTML built with template
    strings. Without them, a store named  <img src=x onerror=...>  runs its
    script in every visitor's browser (stored XSS).

    Load this file before any page script that builds HTML from API data.
*/

// Text -> safe HTML text (also safe inside quoted attributes).
function escapeHtml(value) {
    if (value === null || value === undefined) return "";
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

// URL for src / href attributes: blocks javascript: and other script schemes,
// then escapes it. Returns "" for anything unsafe.
function safeUrl(value) {
    const url = String(value ?? "").trim();
    if (!url) return "";
    const scheme = url.match(/^([a-z][a-z0-9+.-]*):/i);
    if (scheme && !["http", "https", "blob"].includes(scheme[1].toLowerCase())
            && !/^data:image\/(png|jpe?g|gif|webp);/i.test(url)) {
        return "";
    }
    return escapeHtml(url);
}

// URL for a CSS background-image: url("...") value (style.backgroundImage).
function cssUrl(value) {
    const url = String(value ?? "").trim();
    if (!url || safeUrl(url) === "") return "none";
    return `url("${url.replace(/["\\\n\r]/g, (c) => "\\" + c.charCodeAt(0).toString(16) + " ")}")`;
}
