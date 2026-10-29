/*
    categories.js

    Treasure Row Campus Marketplace
    Added by Cameron Ridgley - 10/27/26

    All Categories page (categories.html):
    - Builds one tile per category from the categories each storefront chose,
      with a cover image from one of its brands and a brand count
    - An "All styles" tile shows every brand
    - Clicking a tile lists that category's brands and saves the choice in
      the address (?category=Name)
    Uses browse_common.js for data loading and brand cards.
*/

const categoryGrid = document.getElementById("categoryGrid");
const categoryBrandGrid = document.getElementById("categoryBrandGrid");
const categoryBrandsHeading = document.getElementById("categoryBrandsHeading");
const categoryBrandsCount = document.getElementById("categoryBrandsCount");

const ALL_STYLES = "";   // tile value for "every brand"

let brands = [];
let categories = [];     // [{ name, brands: [...] }]
let selected = ALL_STYLES;

// Group brands by category name (case-insensitive), most brands first.
function buildCategories(list) {
    const groups = new Map();
    list.forEach(brand => {
        brand.categories.forEach(name => {
            const key = name.toLowerCase();
            if (!groups.has(key)) groups.set(key, { name, brands: [] });
            groups.get(key).brands.push(brand);
        });
    });
    return Array.from(groups.values())
        .sort((a, b) => b.brands.length - a.brands.length || a.name.localeCompare(b.name));
}

// First brand in the group that has a cover image.
function coverFor(group) {
    const withCover = group.brands.find(brand => brand.cover);
    return withCover ? withCover.cover : "";
}

function createTile(name, label, count, cover) {
    const tile = document.createElement("button");
    tile.type = "button";
    tile.className = "br-category-tile";
    tile.dataset.category = name;
    tile.setAttribute("aria-pressed", "false");
    tile.innerHTML = `
        <div>
            <strong>${escapeHtml(label)}</strong>
            <span>${escapeHtml(brPlural(count, "brand"))}</span>
        </div>
    `;
    brSetCover(tile, cover);
    tile.addEventListener("click", () => selectCategory(name, true));
    return tile;
}

function renderTiles() {
    categoryGrid.innerHTML = "";
    const firstCover = (brands.find(brand => brand.cover) || {}).cover || "";
    categoryGrid.appendChild(createTile(ALL_STYLES, "All styles", brands.length, firstCover));
    categories.forEach(group => {
        categoryGrid.appendChild(createTile(group.name, group.name, group.brands.length, coverFor(group)));
    });
}

function selectCategory(name, updateAddress) {
    const group = categories.find(c => c.name.toLowerCase() === String(name).toLowerCase());
    selected = group ? group.name : ALL_STYLES;

    categoryGrid.querySelectorAll(".br-category-tile").forEach(tile => {
        const isActive = tile.dataset.category === selected;
        tile.classList.toggle("active", isActive);
        tile.setAttribute("aria-pressed", isActive ? "true" : "false");
    });

    const shown = (group ? group.brands : brands)
        .slice()
        .sort((a, b) => a.name.localeCompare(b.name));

    categoryBrandsHeading.textContent = group ? `${group.name} brands` : "All brands";
    categoryBrandsCount.textContent = brPlural(shown.length, "brand");
    brRenderCards(categoryBrandGrid, shown, brCreateBrandCard, "No brands in this category yet.");

    if (updateAddress) {
        const url = new URL(window.location.href);
        if (selected) url.searchParams.set("category", selected);
        else url.searchParams.delete("category");
        window.history.replaceState(null, "", url);
    }
}

async function loadCategories() {
    try {
        brands = await brFetchBrands();
        categories = buildCategories(brands);
        renderTiles();
        selectCategory(new URLSearchParams(window.location.search).get("category") || ALL_STYLES, false);
    } catch (error) {
        console.error("Could not load categories:", error);
        brShowStatus(categoryGrid, "Could not load categories. Please try again.");
        categoryBrandGrid.innerHTML = "";
    }
}

loadCategories();
