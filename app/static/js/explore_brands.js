/*
    explore_brands.js

    Treasure Row Campus Marketplace
    Added by Cameron Ridgley - 10/27/26

    Explore Brands page (explore_brands.html):
    - Featured brand spotlight: the brand with the most items for sale
    - Grid of every active brand, filtered by the search box and sorted by
      A to Z, newest, or most items
    Uses browse_common.js for data loading and brand cards.
*/

const brandGrid = document.getElementById("brandGrid");
const brandSearch = document.getElementById("brandSearch");
const brandSort = document.getElementById("brandSort");
const brandCount = document.getElementById("brandCount");
const featuredSection = document.getElementById("featuredSection");
const featuredBrand = document.getElementById("featuredBrand");

let allBrands = [];

const BRAND_SORTS = {
    az: (a, b) => a.name.localeCompare(b.name),
    newest: (a, b) => (b.createdAt || 0) - (a.createdAt || 0),
    items: (a, b) => b.items - a.items || a.name.localeCompare(b.name),
};

function renderFeatured(brands) {
    const pick = brands
        .filter(brand => brand.items > 0)
        .sort(BRAND_SORTS.items)[0];
    if (!pick) {
        featuredSection.hidden = true;
        return;
    }

    featuredBrand.innerHTML = `
        <article class="br-feature">
            <div class="br-feature-media" role="img" aria-label="${escapeHtml(pick.name)} banner"></div>
            <div class="br-feature-body">
                <p class="br-kicker">Featured brand</p>
                <div class="br-feature-title">
                    <img src="${safeUrl(pick.logo)}" alt="">
                    <h3>${escapeHtml(pick.name)}</h3>
                </div>
                <p>${escapeHtml(pick.bio || "A student-run brand on Treasure Row.")}</p>
                ${pick.categories.length ? `<div class="br-tags">${pick.categories.map(c => `<span class="br-tag">${escapeHtml(c)}</span>`).join("")}</div>` : ""}
                <p class="br-meta-text">${escapeHtml(brPlural(pick.items, "item"))} for sale</p>
                <a class="tr-btn" href="/storefronts/${encodeURIComponent(pick.id)}">Visit storefront</a>
            </div>
        </article>
    `;
    brSetCover(featuredBrand.querySelector(".br-feature-media"), pick.cover);
    brUseFallbackImages(featuredBrand);
    featuredSection.hidden = false;
}

function renderBrandGrid() {
    const query = brandSearch.value.trim().toLowerCase();
    const sorter = BRAND_SORTS[brandSort.value] || BRAND_SORTS.az;
    const shown = allBrands
        .filter(brand => !query || brand.name.toLowerCase().includes(query))
        .sort(sorter);

    brandCount.textContent = `(${shown.length})`;
    const empty = query ? `No brands match "${brandSearch.value.trim()}".` : "No brands have opened a storefront yet.";
    brRenderCards(brandGrid, shown, brCreateBrandCard, empty);
}

async function loadBrands() {
    try {
        allBrands = await brFetchBrands();
        renderFeatured(allBrands);
        renderBrandGrid();
    } catch (error) {
        console.error("Could not load brands:", error);
        brShowStatus(brandGrid, "Could not load brands. Please try again.");
    }
}

brandSearch.addEventListener("input", renderBrandGrid);
brandSort.addEventListener("change", renderBrandGrid);

loadBrands();
