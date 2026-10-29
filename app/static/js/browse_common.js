/*
    browse_common.js

    Treasure Row Campus Marketplace
    Added by Cameron Ridgley - 10/27/26

    Shared helpers for the Discover pages (Explore Brands, All Categories,
    New Drops, Hot!): loading data, and building brand and listing cards.

    Load after safe_html.js (escapeHtml / safeUrl / cssUrl) and before the
    page's own script. User-written values always go through those helpers.
*/

const BR_FALLBACK_IMAGE = "/static/images/logo.png";
const BR_NEW_DAYS = 7;          // "New" badge and New Drops "This week" row
const BR_SELLING_FAST_MAX = 3;  // in-stock items with 1-3 left get "Selling fast"


/* ---------- Data loading ---------- */

// GET a JSON route. A signed-out session is sent to the login page.
async function brFetchJson(url) {
    const response = await fetch(url, { headers: { Accept: "application/json" } });
    if (response.status === 401) {
        window.location.href = "/auth/login";
        throw new Error("Please sign in.");
    }
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }
    return response.json();
}

// "Streetwear, vintage,Streetwear" -> ["Streetwear", "Vintage"]
function brParseCategories(raw) {
    const list = Array.isArray(raw) ? raw : String(raw || "").split(",");
    const seen = new Map();
    list.forEach(value => {
        const name = String(value || "").trim();
        if (!name) return;
        const key = name.toLowerCase();
        if (!seen.has(key)) {
            seen.set(key, name.charAt(0).toUpperCase() + name.slice(1));
        }
    });
    return Array.from(seen.values());
}

// Active storefronts from GET /api/storefronts, in a shape the pages share.
async function brFetchBrands() {
    const data = await brFetchJson("/api/storefronts");
    return (Array.isArray(data) ? data : []).map(store => {
        const previews = [
            store.preview_image_1,
            store.preview_image_2,
            store.preview_image_3,
            store.preview_image_4,
        ].filter(Boolean);
        return {
            id: store.id,
            name: store.brand_name || "Unnamed Storefront",
            bio: store.bio || "",
            logo: store.logo_url || "",
            cover: store.banner_url || previews[0] || "",
            categories: brParseCategories(store.categories),
            items: Number(store.item_count) || 0,
            createdAt: store.created_at ? new Date(store.created_at) : null,
        };
    });
}

// Listings from every brand. sort: "new" or "hot".
async function brFetchListings(sort, limit) {
    const params = new URLSearchParams({ sort });
    if (limit) params.set("limit", String(limit));
    const data = await brFetchJson(`/api/browse/listings?${params}`);
    return (Array.isArray(data) ? data : []).map(item => ({
        ...item,
        createdAt: item.created_at ? new Date(item.created_at) : null,
    }));
}


/* ---------- Formatting ---------- */

function brFormatPrice(value) {
    const number = Number(value);
    return Number.isFinite(number) ? `$${number.toFixed(2)}` : "";
}

function brPlural(count, word) {
    return `${count} ${count === 1 ? word : word + "s"}`;
}

// Date -> "Just now", "3 hours ago", "2 days ago", or "Oct 3"
function brTimeAgo(date) {
    if (!(date instanceof Date) || Number.isNaN(date.getTime())) return "";
    const minutes = Math.max(0, Math.round((Date.now() - date.getTime()) / 60000));
    if (minutes < 1) return "Just now";
    if (minutes < 60) return `${brPlural(minutes, "minute")} ago`;
    const hours = Math.round(minutes / 60);
    if (hours < 24) return `${brPlural(hours, "hour")} ago`;
    const days = Math.round(hours / 24);
    if (days < 30) return `${brPlural(days, "day")} ago`;
    return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function brIsNew(item) {
    if (!(item.createdAt instanceof Date)) return false;
    return Date.now() - item.createdAt.getTime() <= BR_NEW_DAYS * 24 * 60 * 60 * 1000;
}

function brIsSoldOut(item) {
    return item.status === "SOLD_OUT";
}

function brIsSellingFast(item) {
    const qty = Number(item.quantity_on_hand);
    return !brIsSoldOut(item)
        && item.fulfillment_type === "IN_STOCK"
        && !item.is_made_to_order
        && qty >= 1 && qty <= BR_SELLING_FAST_MAX;
}


/* ---------- Page states ---------- */

function brShowStatus(container, message) {
    if (!container) return;
    container.innerHTML = `<p class="br-status">${escapeHtml(message)}</p>`;
}

// Images that fail to load show the Treasure Row logo instead.
function brUseFallbackImages(root) {
    root.querySelectorAll("img").forEach(img => {
        img.addEventListener("error", () => {
            if (img.dataset.fallback) return;
            img.dataset.fallback = "1";
            img.src = BR_FALLBACK_IMAGE;
        });
        if (!img.getAttribute("src")) img.src = BR_FALLBACK_IMAGE;
    });
}


/* ---------- Cards ---------- */

// Background image for a banner area; without one, a faded logo is shown (CSS .is-empty).
function brSetCover(element, url) {
    if (!element) return;
    const value = url ? cssUrl(url) : "none";
    element.classList.toggle("is-empty", value === "none");
    if (value !== "none") element.style.backgroundImage = value;
}

// Brand card: banner, logo, name, item count, bio, category tags.
// The whole card links to the brand's storefront.
function brCreateBrandCard(brand) {
    const card = document.createElement("a");
    card.className = "br-brand-card";
    card.href = `/storefronts/${encodeURIComponent(brand.id)}`;
    card.setAttribute("aria-label", `Visit ${brand.name}`);

    const tags = brand.categories
        .map(category => `<span class="br-tag">${escapeHtml(category)}</span>`)
        .join("");

    card.innerHTML = `
        <div class="br-brand-banner"></div>
        <div class="br-brand-body">
            <img class="br-brand-logo" src="${safeUrl(brand.logo)}" alt="">
            <h3 class="br-brand-name">${escapeHtml(brand.name)}</h3>
            <p class="br-brand-count">${escapeHtml(brPlural(brand.items, "item"))}</p>
            ${brand.bio ? `<p class="br-brand-bio">${escapeHtml(brand.bio)}</p>` : ""}
            ${tags ? `<div class="br-tags">${tags}</div>` : ""}
        </div>
    `;

    brSetCover(card.querySelector(".br-brand-banner"), brand.cover);
    brUseFallbackImages(card);
    return card;
}

// Listing card: photo, badges, title, brand, price, and when it was posted.
// options.rank adds a numbered badge (Hot!); options.metaText replaces "posted ..." text.
// The whole card links to the brand's storefront, where the item can be bought.
function brCreateListingCard(item, options = {}) {
    const card = document.createElement("a");
    card.className = `br-listing-card${brIsSoldOut(item) ? " is-sold-out" : ""}`;
    card.href = `/storefronts/${encodeURIComponent(item.storefront_id)}`;
    card.setAttribute("aria-label", `${item.title} from ${item.brand_name}, ${brFormatPrice(item.price)}`);

    const badges = [];
    if (brIsSoldOut(item)) badges.push(`<span class="br-badge br-badge--sold">Sold out</span>`);
    if (!brIsSoldOut(item) && brIsNew(item)) badges.push(`<span class="br-badge br-badge--new">New</span>`);
    if (brIsSellingFast(item)) badges.push(`<span class="br-badge br-badge--hot">Selling fast</span>`);
    if (item.fulfillment_type === "PREORDER") badges.push(`<span class="br-badge br-badge--gold">Preorder</span>`);
    if (item.is_made_to_order) badges.push(`<span class="br-badge br-badge--gold">Made to order</span>`);

    const metaText = options.metaText !== undefined ? options.metaText : brTimeAgo(item.createdAt);

    card.innerHTML = `
        <div class="br-listing-media">
            <img src="${safeUrl(item.image_url)}" alt="" loading="lazy">
            ${badges.length ? `<div class="br-badges">${badges.join("")}</div>` : ""}
            ${options.rank ? `<span class="br-rank" aria-label="Rank ${options.rank}">${options.rank}</span>` : ""}
        </div>
        <div class="br-listing-body">
            <h3 class="br-listing-title" title="${escapeHtml(item.title)}">${escapeHtml(item.title)}</h3>
            <p class="br-listing-brand">${escapeHtml(item.brand_name)}</p>
            <div class="br-listing-meta">
                <span class="br-price">${escapeHtml(brFormatPrice(item.price))}</span>
                <span class="br-meta-text">${escapeHtml(metaText)}</span>
            </div>
        </div>
    `;

    brUseFallbackImages(card);
    return card;
}

// Replace a container's content with one card per item.
function brRenderCards(container, items, buildCard, emptyMessage) {
    if (!container) return;
    container.innerHTML = "";
    if (!items.length) {
        brShowStatus(container, emptyMessage);
        return;
    }
    items.forEach((item, index) => container.appendChild(buildCard(item, index)));
}
