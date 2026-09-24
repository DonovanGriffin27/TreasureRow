/*
    my_storefront.js

    The Vault Campus Marketplace 
    CSC 405 Sp 26'
    Created by Day Ekoi - Iteration 4 - 3/22/2026
    Implemented & Updated by Day Ekoi - Iteration 5 - 4/9/2026
    Updated by Day Ekoi - Iteration 5 - 4/20/26 - added deactivate storefront button handler
    Updated by Day Ekoi - Iteration 5 - 4/20/26 - guarded optional dashboard buttons after layout cleanup

Description:
Fetches the current user's storefront from the API and renders
the banner, logo, brand name, and listings dynamically.
Handles Edit Storefront, Create Listing, View Public Storefront, and Deactivate Storefront.
*/


// get references
const pageTitle = document.getElementById("pageTitle");
const storeDescription = document.getElementById("storeDescription");
const contactInfo = document.getElementById("contactInfo");
const bannerBox = document.getElementById("bannerBox");
const bannerFallback = document.getElementById("bannerFallback");
const logoImg = document.getElementById("logoImg");
const logoFallback = document.getElementById("logoFallback");
const listingGrid = document.getElementById("listingGrid");
const storefrontStatusBanner = document.getElementById("storefrontStatusBanner");
const editStorefrontBtn = document.getElementById("editStorefrontBtn");
const createListingBtn = document.getElementById("createListingBtn");
const viewStorefrontBtn = document.getElementById("viewStorefrontBtn");
const deactivateStorefrontBtn = document.getElementById("deactivateStorefrontBtn");

let storefrontId = null;
let currentUser = null;


// renders empty state in listing grid
function renderEmpty(message) {
    listingGrid.innerHTML = `<p style="color:#888; font-style:italic; grid-column:1/-1; text-align:center;">${message}</p>`;
}


function closeListingMenus() {
    document.querySelectorAll(".listing-menu-dropdown.active").forEach((menu) => {
        menu.classList.remove("active");
    });
}


function setButtonDisabledState(button, disabled) {
    if (!button) return;
    button.disabled = disabled;
    button.classList.toggle("is-disabled", disabled);
}


// builds a single listing card
function createListingCard(item) {
    const card = document.createElement("div");
    card.className = "listing-card";

    const title = item.title || item.name || "Untitled";
    const price = `$${Number(item.price || 0).toFixed(2)}`;
    const imageUrl = item.image_url || null;
    const status = item.status || "ACTIVE";
    const stateActionLabel = status === "DELETED"
        ? "Restore Listing"
        : (status === "INACTIVE" ? "Reactivate Listing" : "Deactivate Listing");

    card.innerHTML = `
        ${imageUrl ? `<img class="listing-card-image" src="${imageUrl}" alt="${title}">` : `<div class="listing-card-image listing-card-image--empty"></div>`}
        <div class="listing-card-body">
            <p class="listing-card-title">${title}</p>
            <p class="listing-card-price">${price}</p>
            <p class="listing-card-meta">Status: ${status}</p>
            <div class="listing-menu-wrap">
                <button type="button" class="listing-menu-trigger" aria-label="Open listing actions">...</button>
                <div class="listing-menu-dropdown">
                    <button type="button" class="listing-menu-item listing-menu-edit">Edit Listing</button>
                    <button type="button" class="listing-menu-item listing-menu-toggle">${stateActionLabel}</button>
                    <button type="button" class="listing-menu-item listing-menu-delete">Delete Listing</button>
                </div>
            </div>
        </div>
    `;

    const trigger = card.querySelector(".listing-menu-trigger");
    const dropdown = card.querySelector(".listing-menu-dropdown");
    const editBtn = card.querySelector(".listing-menu-edit");
    const toggleBtn = card.querySelector(".listing-menu-toggle");
    const deleteBtn = card.querySelector(".listing-menu-delete");

    trigger.addEventListener("click", (event) => {
        event.stopPropagation();
        const isActive = dropdown.classList.contains("active");
        closeListingMenus();
        dropdown.classList.toggle("active", !isActive);
    });

    editBtn.addEventListener("click", () => {
        if (status === "DELETED") return;
        window.location.href = `/listings/${item.id}/edit`;
    });

    toggleBtn.addEventListener("click", async () => {
        const endpoint = status === "DELETED"
            ? "restore"
            : (status === "INACTIVE" ? "reactivate" : "deactivate");
        const actionLabel = status === "DELETED"
            ? "restore"
            : (status === "INACTIVE" ? "reactivate" : "deactivate");
        const confirmed = window.confirm(`Are you sure you want to ${actionLabel} this listing?`);
        if (!confirmed) return;

        try {
            const response = await fetch(`/api/listings/${item.id}/${endpoint}`, {
                method: "PATCH",
                headers: {
                    "X-User-Id": currentUser?.id || "",
                    "X-User-Role": currentUser?.role || "user"
                }
            });

            const result = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(result.error || `Failed to ${actionLabel} listing.`);
            }

            await loadMyStorefront();
        } catch (error) {
            alert(error.message || `Unable to ${actionLabel} listing.`);
        }
    });

    deleteBtn.addEventListener("click", async () => {
        if (status === "DELETED") return;
        const confirmed = window.confirm("Are you sure you want to delete this listing?");
        if (!confirmed) return;

        try {
            const response = await fetch(`/api/listings/${item.id}`, {
                method: "DELETE",
                headers: {
                    "X-User-Id": currentUser?.id || "",
                    "X-User-Role": currentUser?.role || "user"
                }
            });

            const result = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(result.error || "Failed to delete listing.");
            }

            await loadMyStorefront();
        } catch (error) {
            alert(error.message || "Unable to delete listing.");
        }
    });

    if (status === "DELETED") {
        editBtn.disabled = true;
        deleteBtn.disabled = true;
        editBtn.classList.add("is-disabled");
        deleteBtn.classList.add("is-disabled");
    }

    return card;
}


// fetches storefront and listings and renders the page
async function loadMyStorefront() {
    try {
        // get current user
        const userRes = await fetch("/auth/api/auth/me");
        if (!userRes.ok) {
            window.location.href = "/auth/login";
            return;
        }
        const user = await userRes.json();
        currentUser = user;

        // get user's storefront
        const sfRes = await fetch("/api/storefronts/me", {
            headers: {
                "X-User-Id": user.id,
                "X-User-Role": user.role
            }
        });

        if (!sfRes.ok) { // updated by Day E 4/9/26 - if user has no storefront, show empty state instead of redirecting to create page
            if (pageTitle) pageTitle.textContent = "No Storefront Found";
            renderEmpty(`
                <div style="text-align:center; padding:2rem;">
                    <p style="color:#888; font-style:italic; margin-bottom:1rem;">You don't have a storefront yet.</p>
                    <a href="/storefronts/create"><button class="action-btn">Create Your Storefront</button></a>
                </div>
            `);
            return;
            // no storefront — redirect to create
            // window.location.href = "/storefronts/create";
            // return;
        }

        const storefront = await sfRes.json();
        storefrontId = storefront.id;
        const storefrontIsActive = storefront.is_active !== false;

        // populate brand name, bio, contact info - Updated by Day Ekoi 4/20/26
        if (pageTitle) pageTitle.textContent = storefront.brand_name || "My Storefront";
        if (storefront.contact_info) contactInfo.textContent = storefront.contact_info;
        if (storefront.bio) storeDescription.textContent = storefront.bio;
        if (storefrontStatusBanner) {
            storefrontStatusBanner.style.display = storefrontIsActive ? "none" : "block";
        }

        // populate banner
        if (storefront.banner_url) {
            bannerBox.style.backgroundImage = `url('${storefront.banner_url}')`;
            bannerBox.style.backgroundSize = "cover";
            bannerBox.style.backgroundPosition = "center";
            bannerFallback.style.display = "none";
        }

        // populate logo
        if (storefront.logo_url) {
            logoImg.src = storefront.logo_url;
            logoImg.style.display = "block";
            logoFallback.style.display = "none";
        }

        // wire up buttons now that we have storefront ID
        if (editStorefrontBtn) {
            editStorefrontBtn.onclick = () => {
                window.location.href = `/storefronts/${storefrontId}/edit`;
            };
        }

        if (viewStorefrontBtn) {
            setButtonDisabledState(viewStorefrontBtn, !storefrontIsActive);
            viewStorefrontBtn.onclick = storefrontIsActive
                ? () => { window.location.href = `/storefronts/${storefrontId}`; }
                : null;
        }

        if (createListingBtn) {
            setButtonDisabledState(createListingBtn, !storefrontIsActive);
            createListingBtn.onclick = storefrontIsActive
                ? () => { window.location.href = "/listings/create"; }
                : null;
        }

        if (deactivateStorefrontBtn) {
            deactivateStorefrontBtn.onclick = async () => {
            const confirmed = confirm(
                "Are you sure you want to deactivate your storefront?\n\nIt will be hidden from the marketplace. You can reactivate it later by contacting support."
            );
            if (!confirmed) return;

            try {
                const res = await fetch(`/api/storefronts/${storefrontId}/deactivate`, {
                    method: "PATCH",
                    headers: {
                        "X-User-Id": user.id,
                        "X-User-Role": user.role
                    }
                });

                if (res.ok) {
                    alert("Your storefront has been deactivated.");
                    window.location.href = "/storefronts";
                } else {
                    const err = await res.json();
                    alert("Could not deactivate: " + (err.error || "Unknown error"));
                }
            } catch (e) {
                alert("Something went wrong. Please try again.");
            }
            };
        }

        // fetch listings
        const listRes = await fetch(`/api/listings/my?include_deleted=1`, {
            headers: {
                "X-User-Id": user.id,
                "X-User-Role": user.role
            }
        });

        if (!listRes.ok) {
            renderEmpty("Could not load listings.");
            return;
        }

        const listings = await listRes.json();
        const visibleListings = Array.isArray(listings)
            ? listings.filter((item) => item.status !== "DELETED")
            : [];

        listingGrid.innerHTML = "";
        if (!visibleListings.length) {
            renderEmpty("No listings yet. Create your first listing!");
            return;
        }

        visibleListings.forEach(item => listingGrid.appendChild(createListingCard(item)));

    } catch (error) {
        console.error("Error loading my storefront:", error);
        if (pageTitle) pageTitle.textContent = "Could not load storefront.";
        renderEmpty("Something went wrong.");
    }
}


// run on page load
loadMyStorefront();

document.addEventListener("click", () => {
    closeListingMenus();
});
