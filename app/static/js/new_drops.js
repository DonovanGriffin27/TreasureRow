/*
    new_drops.js

    Treasure Row Campus Marketplace
    Added by Cameron Ridgley - 10/27/26

    New Drops page (new_drops.html):
    - "Just dropped this week" row: available items posted in the last 7 days
    - "All drops" grid: every listing, newest first, filtered by price range
      and by whether sold-out items are shown
    Uses browse_common.js for data loading and listing cards.
*/

const DROPS_LIMIT = 100;

const thisWeekSection = document.getElementById("thisWeekSection");
const thisWeekRow = document.getElementById("thisWeekRow");
const thisWeekCount = document.getElementById("thisWeekCount");
const dropGrid = document.getElementById("dropGrid");
const dropCount = document.getElementById("dropCount");
const priceFilter = document.getElementById("priceFilter");
const stockFilter = document.getElementById("stockFilter");

let drops = [];

// "25-50" -> [25, 50]; "50-" -> [50, Infinity]; "any" -> null
function parsePriceRange(value) {
    if (value === "any") return null;
    const [low, high] = value.split("-");
    return [Number(low) || 0, high ? Number(high) : Infinity];
}

function renderThisWeek() {
    const recent = drops.filter(item => brIsNew(item) && !brIsSoldOut(item));
    thisWeekSection.hidden = recent.length === 0;
    thisWeekCount.textContent = brPlural(recent.length, "new item");
    brRenderCards(thisWeekRow, recent, item => brCreateListingCard(item), "");
}

function renderAllDrops() {
    const range = parsePriceRange(priceFilter.value);
    const includeSoldOut = stockFilter.value === "all";
    const shown = drops.filter(item => {
        if (!includeSoldOut && brIsSoldOut(item)) return false;
        if (range && (item.price < range[0] || item.price >= range[1])) return false;
        return true;
    });

    dropCount.textContent = `(${shown.length})`;
    const empty = drops.length ? "No drops match these filters." : "No items have been listed yet. Check back soon.";
    brRenderCards(dropGrid, shown, item => brCreateListingCard(item), empty);
}

async function loadDrops() {
    try {
        drops = await brFetchListings("new", DROPS_LIMIT);
        renderThisWeek();
        renderAllDrops();
    } catch (error) {
        console.error("Could not load new drops:", error);
        brShowStatus(dropGrid, "Could not load new drops. Please try again.");
    }
}

priceFilter.addEventListener("change", renderAllDrops);
stockFilter.addEventListener("change", renderAllDrops);

loadDrops();
