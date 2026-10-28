/*
    hot.js

    Treasure Row Campus Marketplace
    Added by Cameron Ridgley - 10/27/26

    Hot! page (hot.html):
    - "Trending now": listings with any sales or wishlist saves, ranked by
      popularity (the server sorts: each unit sold counts 3, each save 1)
    - "Top brands": brands ranked by units sold across their trending items
    - "Fresh picks": newest drops, shown when fewer than MIN_TRENDING items
      are trending so the page never looks empty
    Uses browse_common.js for data loading and listing cards.
*/

const TRENDING_LIMIT = 24;
const MIN_TRENDING = 4;
const TOP_BRANDS = 5;

const trendingGrid = document.getElementById("trendingGrid");
const topBrandsSection = document.getElementById("topBrandsSection");
const topBrands = document.getElementById("topBrands");
const freshSection = document.getElementById("freshSection");
const freshGrid = document.getElementById("freshGrid");

// "2 sold · 1 save"
function popularityText(item) {
    const parts = [];
    if (item.units_sold > 0) parts.push(`${item.units_sold} sold`);
    if (item.wishlist_count > 0) parts.push(brPlural(item.wishlist_count, "save"));
    return parts.join(" · ");
}

function renderTrending(trending) {
    brRenderCards(
        trendingGrid,
        trending,
        (item, index) => brCreateListingCard(item, { rank: index + 1, metaText: popularityText(item) }),
        "Nothing is trending yet. Be the first to order or save an item!"
    );
}

function renderTopBrands(trending) {
    const byBrand = new Map();
    trending.forEach(item => {
        const entry = byBrand.get(item.storefront_id) || {
            id: item.storefront_id,
            name: item.brand_name,
            logo: item.brand_logo_url,
            sold: 0,
            saves: 0,
        };
        entry.sold += item.units_sold;
        entry.saves += item.wishlist_count;
        byBrand.set(item.storefront_id, entry);
    });

    const ranked = Array.from(byBrand.values())
        .filter(brand => brand.sold > 0)
        .sort((a, b) => b.sold - a.sold || b.saves - a.saves || a.name.localeCompare(b.name))
        .slice(0, TOP_BRANDS);

    topBrandsSection.hidden = ranked.length === 0;
    topBrands.innerHTML = ranked.map(brand => `
        <a class="br-top-brand" href="/storefronts/${encodeURIComponent(brand.id)}">
            <img src="${safeUrl(brand.logo)}" alt="">
            <div>
                <strong>${escapeHtml(brand.name)}</strong>
                <span>${escapeHtml(`${brand.sold} sold`)}</span>
            </div>
        </a>
    `).join("");
    brUseFallbackImages(topBrands);
}

async function renderFreshPicks(trending) {
    if (trending.length >= MIN_TRENDING) {
        freshSection.hidden = true;
        return;
    }
    const trendingIds = new Set(trending.map(item => item.id));
    const newest = (await brFetchListings("new", 12))
        .filter(item => !trendingIds.has(item.id) && !brIsSoldOut(item));
    freshSection.hidden = newest.length === 0;
    brRenderCards(freshGrid, newest, item => brCreateListingCard(item), "");
}

async function loadHot() {
    try {
        const ranked = await brFetchListings("hot", TRENDING_LIMIT);
        const trending = ranked.filter(item => item.popularity > 0);
        renderTrending(trending);
        renderTopBrands(trending);
        await renderFreshPicks(trending);
    } catch (error) {
        console.error("Could not load trending items:", error);
        brShowStatus(trendingGrid, "Could not load what's hot. Please try again.");
    }
}

loadHot();
