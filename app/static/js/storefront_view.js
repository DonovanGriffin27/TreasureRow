/*
    storefront_view.js

    The Vault Campus Marketplace
    CSC 405 Sp 26'
    Created by Day Ekoi - Iteration 4
    3/22/2026
    Updated by Day Ekoi - Iteration 5 4/9/26
    Updated by Day Ekoi - Iteration 5 - 4/20/26 - fixed wishlistIds undefined crash and isWishlisted undefined in createListingCard
    Updated by Day E - April 22nd - multi-image listing display, lightbox preview, and contain-based image handling

Description:
This file handles the functionality for the public storefront view page.
Fetches real storefront and listing data from the Flask API using the
storefront ID from the URL. Renders storefront banner, logo, description,
and listing cards dynamically.

Works with:
- storefront_view.html
- storefront_view.css
*/

const storefrontId = window.location.pathname.split("/").pop();
const AUTH_ME_ENDPOINT = "/auth/api/auth/me";
const LISTING_IMAGE_FALLBACK = "/static/images/placeholder-storefront.png";

const pageTitle = document.getElementById("pageTitle");
const contactInfo = document.getElementById("contactInfo");
const storeDescription = document.getElementById("storeDescription");
const storefrontLogo = document.getElementById("storefrontLogo");
const logoFallback = document.getElementById("logoFallback");
const listingGrid = document.getElementById("listingGrid");
const lightbox = document.getElementById("listingLightbox");
const lightboxImage = document.getElementById("lightboxImage");
const lightboxDots = document.getElementById("lightboxDots");
const lightboxClose = document.getElementById("lightboxClose");
const lightboxPrev = document.getElementById("lightboxPrev");
const lightboxNext = document.getElementById("lightboxNext");

const listingImagesCache = new Map();
const lightboxState = {
    images: [],
    index: 0
};

function ensureToastRoot() {
    let root = document.getElementById("cartToastRoot");
    if (!root) {
        root = document.createElement("div");
        root.id = "cartToastRoot";
        root.className = "cart-toast-root";
        document.body.appendChild(root);
    }
    return root;
}

function showCartToast(message, tone = "success") {
    const root = ensureToastRoot();
    const toast = document.createElement("div");
    toast.className = `cart-toast ${tone === "error" ? "error" : "success"}`;
    toast.textContent = message;
    root.appendChild(toast);

    window.setTimeout(() => {
        toast.classList.add("fade-out");
        window.setTimeout(() => toast.remove(), 220);
    }, 2200);
}

function toNumericPrice(priceValue) {
    if (typeof priceValue === "number") return priceValue;
    if (typeof priceValue === "string") {
        const cleaned = priceValue.replace(/\$/g, "").trim();
        const parsed = Number(cleaned);
        if (!Number.isNaN(parsed)) return parsed;
    }
    return 0;
}

function parseSizesFromListing(item) {
    const source = item.sizes_available;

    if (Array.isArray(source)) {
        return source.map((size) => String(size).trim()).filter(Boolean);
    }

    if (typeof source === "string" && source.trim()) {
        try {
            const parsed = JSON.parse(source);
            if (Array.isArray(parsed)) {
                return parsed.map((size) => String(size).trim()).filter(Boolean);
            }
        } catch (_error) {
            return source
                .split(",")
                .map((size) => size.trim())
                .filter(Boolean);
        }
    }

    return [];
}

async function getListingSizeOptions(listingId, item) {
    const inlineSizes = parseSizesFromListing(item);
    if (inlineSizes.length > 0) {
        return inlineSizes;
    }

    try {
        const response = await fetch(`/api/listings/${listingId}/sizes`);
        if (!response.ok) {
            return [];
        }

        const data = await response.json();
        if (!Array.isArray(data)) {
            return [];
        }

        return data
            .map((entry) => String(entry.size || "").trim())
            .filter(Boolean);
    } catch (error) {
        console.error("Unable to load listing sizes:", error);
        return [];
    }
}

async function fetchListingImages(listingId, fallbackImageUrl) {
    if (listingImagesCache.has(listingId)) {
        return listingImagesCache.get(listingId);
    }

    try {
        const response = await fetch(`/api/listings/${listingId}/images`);
        if (!response.ok) {
            throw new Error("Unable to load listing images.");
        }

        const images = await response.json();
        const normalized = Array.isArray(images)
            ? images
                .map((image) => String(image.image_url || "").trim())
                .filter(Boolean)
                .slice(0, 4)
            : [];

        if (normalized.length > 0) {
            listingImagesCache.set(listingId, normalized);
            return normalized;
        }
    } catch (error) {
        console.error(`Unable to load images for listing ${listingId}:`, error);
    }

    const fallback = [fallbackImageUrl || LISTING_IMAGE_FALLBACK];
    listingImagesCache.set(listingId, fallback);
    return fallback;
}

function getLocalWishlistItems() {
    try {
        const raw = localStorage.getItem("vaultWishlistLocalItems");
        return raw ? JSON.parse(raw) : [];
    } catch (error) {
        console.error("Unable to read local wishlist:", error);
        return [];
    }
}

function setLocalWishlistItems(items) {
    const normalized = items.map((item) => ({
        listing_id: Number(item.listing_id || item.id),
        title: item.title || item.name || item.listing?.title || "Untitled Listing",
        price: item.price ?? item.listing?.price ?? 0,
        image_url: item.image_url || item.listing?.image_url || item.storefront?.logo_url || "/static/images/logo.png",
        storefront_name: item.storefront_name || item.storefront?.brand_name || pageTitle?.textContent || "Storefront"
    }));

    localStorage.setItem("vaultWishlistLocalItems", JSON.stringify(normalized));
    localStorage.setItem("vaultWishlistListingIds", JSON.stringify(normalized.map((item) => String(item.listing_id))));
}

function addLocalWishlistItem(item) {
    const items = getLocalWishlistItems();
    const listingId = String(item.listing_id || item.id);
    const filtered = items.filter((existing) => String(existing.listing_id || existing.id) !== listingId);
    filtered.unshift({
        listing_id: Number(listingId),
        title: item.title || item.name || "Untitled Listing",
        price: item.price,
        image_url: item.image_url || "/static/images/logo.png",
        storefront_name: item.storefront_name || pageTitle?.textContent || "Storefront"
    });
    setLocalWishlistItems(filtered);
}

function removeLocalWishlistItem(listingId) {
    const updated = getLocalWishlistItems().filter((item) => String(item.listing_id || item.id) !== String(listingId));
    setLocalWishlistItems(updated);
}

async function getCurrentSessionUser() {
    try {
        const response = await fetch(AUTH_ME_ENDPOINT);
        if (!response.ok) return null;

        const user = await response.json();
        if (user && user.id) {
            localStorage.setItem("vaultUserId", String(user.id));
            sessionStorage.setItem("vaultUserId", String(user.id));
        }
        return user;
    } catch (error) {
        console.error("Unable to determine current user:", error);
        return null;
    }
}

async function getWishlistIdSet(userId) {
    if (!userId) {
        return new Set();
    }

    try {
        const response = await fetch("/api/wishlist", {
            headers: {
                "X-User-Id": String(userId)
            }
        });

        if (!response.ok) {
            throw new Error("Failed to load wishlist status");
        }

        const data = await response.json();
        const wishlistItems = Array.isArray(data.wishlist) ? data.wishlist : [];
        setLocalWishlistItems(wishlistItems);

        return new Set(wishlistItems.map((item) => String(item.listing_id || item.id)));
    } catch (error) {
        console.error("Unable to load wishlist ids:", error);
        return new Set(getLocalWishlistItems().map((item) => String(item.listing_id || item.id)));
    }
}

function renderEmpty(message) {
    listingGrid.innerHTML = `<p style="color:#c9c9c9; font-style:italic; text-align:center; grid-column: 1/-1;">${message}</p>`;
}

function updateDots(container, images, activeIndex, dotClassName, onSelect) {
    if (!container) return;

    container.innerHTML = "";
    if (!Array.isArray(images) || images.length <= 1) {
        return;
    }

    images.forEach((_image, index) => {
        const dot = document.createElement("button");
        dot.type = "button";
        dot.className = `${dotClassName} ${index === activeIndex ? "active" : ""}`;
        dot.setAttribute("aria-label", `Go to image ${index + 1}`);
        dot.addEventListener("click", () => onSelect(index));
        container.appendChild(dot);
    });
}

function renderLightbox() {
    if (!lightbox || !lightboxImage) return;

    const { images, index } = lightboxState;
    if (!images.length) return;

    lightboxImage.src = images[index];
    lightboxImage.alt = `Listing image ${index + 1}`;
    updateDots(lightboxDots, images, index, "lightbox-dot", (nextIndex) => {
        lightboxState.index = nextIndex;
        renderLightbox();
    });

    if (lightboxPrev) {
        lightboxPrev.style.display = images.length > 1 ? "inline-flex" : "none";
    }
    if (lightboxNext) {
        lightboxNext.style.display = images.length > 1 ? "inline-flex" : "none";
    }
}

function openLightbox(images, startIndex = 0) {
    if (!lightbox || !Array.isArray(images) || !images.length) return;
    lightboxState.images = images;
    lightboxState.index = startIndex;
    renderLightbox();
    lightbox.classList.add("is-open");
    document.body.style.overflow = "hidden";
}

function closeLightbox() {
    if (!lightbox) return;
    lightbox.classList.remove("is-open");
    document.body.style.overflow = "";
}

function shiftLightbox(step) {
    if (!lightboxState.images.length) return;
    lightboxState.index = (lightboxState.index + step + lightboxState.images.length) % lightboxState.images.length;
    renderLightbox();
}

function createListingImageCarousel(images, title) {
    const shell = document.createElement("div");
    shell.className = "listing-image-shell";

    const image = document.createElement("img");
    image.className = "listing-image";
    image.alt = title;

    const dots = document.createElement("div");
    dots.className = "listing-image-dots";

    const counter = document.createElement("div");
    counter.className = "listing-image-counter";

    let currentIndex = 0;

    const render = () => {
        image.src = images[currentIndex];
        counter.textContent = `${currentIndex + 1}/${images.length}`;
        updateDots(dots, images, currentIndex, "listing-image-dot", (nextIndex) => {
            currentIndex = nextIndex;
            render();
        });
    };

    image.addEventListener("click", () => openLightbox(images, currentIndex));
    shell.classList.add("is-clickable");
    shell.appendChild(image);

    if (images.length > 1) {
        const prevBtn = document.createElement("button");
        prevBtn.type = "button";
        prevBtn.className = "listing-image-nav listing-image-nav--left";
        prevBtn.setAttribute("aria-label", "Previous image");
        prevBtn.innerHTML = "&#10094;";
        prevBtn.addEventListener("click", (event) => {
            event.stopPropagation();
            currentIndex = (currentIndex - 1 + images.length) % images.length;
            render();
        });

        const nextBtn = document.createElement("button");
        nextBtn.type = "button";
        nextBtn.className = "listing-image-nav listing-image-nav--right";
        nextBtn.setAttribute("aria-label", "Next image");
        nextBtn.innerHTML = "&#10095;";
        nextBtn.addEventListener("click", (event) => {
            event.stopPropagation();
            currentIndex = (currentIndex + 1) % images.length;
            render();
        });

        shell.appendChild(prevBtn);
        shell.appendChild(nextBtn);
        shell.appendChild(dots);
        shell.appendChild(counter);
    }

    render();
    return { shell, getPrimaryImage: () => images[0] || LISTING_IMAGE_FALLBACK };
}

async function createListingCard(item, wishlistIds, currentUserId) {
    const card = document.createElement("div");
    card.className = "listing-card";

    const listingId = Number(item.id || item.listing_id);
    const title = item.title || item.name || "Untitled Listing";
    const numericPrice = toNumericPrice(item.price);
    const price = typeof item.price === "string" && item.price.includes("$")
        ? item.price
        : `$${numericPrice.toFixed(2)}`;
    const images = await fetchListingImages(listingId, item.image_url);
    const primaryImageUrl = images[0] || item.image_url || LISTING_IMAGE_FALLBACK;
    const isWishlisted = wishlistIds.has(String(listingId));
    const sizeOptions = await getListingSizeOptions(listingId, item);
    const hasSizes = sizeOptions.length > 0;
    const isOneSizeItem = hasSizes && sizeOptions.length === 1 && sizeOptions[0] === "One Size";
    const isMadeToOrder = Boolean(item.is_made_to_order);
    const maxQuantity = isMadeToOrder ? 999 : (item.quantity_on_hand || 1);
    const isSoldOut = !isMadeToOrder && (item.status === "SOLD_OUT" || item.quantity_on_hand === 0);

    let sizeFieldMarkup;
    if (isOneSizeItem) {
        sizeFieldMarkup = `
            <label class="field-label">Size</label>
            <span class="one-size-label" style="color:#d4af37;font-weight:600;padding:0.2rem 0;">One Size</span>
        `;
    } else if (hasSizes) {
        const sizeOptionsMarkup = sizeOptions
            .map((size, index) => `<option value="${size}" ${index === 0 ? "selected" : ""}>${size}</option>`)
            .join("");
        sizeFieldMarkup = `
            <label class="field-label" for="sizeSelect-${listingId}">Size</label>
            <select id="sizeSelect-${listingId}" class="size-select">${sizeOptionsMarkup}</select>
        `;
    } else {
        sizeFieldMarkup = `
            <label class="field-label">Size</label>
            <select class="size-select" disabled><option value="" disabled selected>No sizes available</option></select>
        `;
    }

    const madeToOrderBadge = isMadeToOrder
        ? `<span class="made-to-order-badge" style="display:inline-block;background:rgba(212,175,55,0.15);border:1px solid rgba(212,175,55,0.5);color:#d4af37;font-size:0.7rem;font-weight:700;letter-spacing:0.5px;padding:0.15rem 0.45rem;border-radius:999px;text-transform:uppercase;margin-top:2px;">Made to Order</span>`
        : "";

    const descriptionMarkup = item.description
        ? `<p class="listing-description">${item.description}</p>`
        : "";

    const carousel = createListingImageCarousel(images, title);

    card.innerHTML = `
        <div class="listing-info">
            <div class="listing-copy">
                <span class="item-name">${title}</span>
                <span class="item-price">${price}</span>
                ${madeToOrderBadge}
            </div>
            <div class="listing-actions">
                <button class="wishlist-lock-btn ${isWishlisted ? "active" : ""}" type="button" aria-label="${isWishlisted ? "Remove from wishlist" : "Add to wishlist"}" title="${isWishlisted ? "Remove from wishlist" : "Add to wishlist"}">
                    <svg viewBox="0 0 24 24" class="wishlist-lock-icon" aria-hidden="true">
                        <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="1.8"/>
                        <rect x="8.5" y="11" width="7" height="5.8" rx="1.2" fill="none" stroke="currentColor" stroke-width="1.8"/>
                        <path d="M10 11V9.7a2 2 0 1 1 4 0V11" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                    </svg>
                </button>
            </div>
        </div>
        ${descriptionMarkup}
        <div class="purchase-panel">
            <div class="purchase-fields">
                ${sizeFieldMarkup}
                <label class="field-label" for="countInput-${listingId}">Count</label>
                <input id="countInput-${listingId}" class="count-input" type="number" min="1" max="${maxQuantity}" step="1" value="1" inputmode="numeric">
            </div>
            ${isSoldOut
                ? `<span class="sold-out-label" style="display:block;width:100%;padding:0.6rem 1rem;background:#3a3a3a;color:#888888;font-size:0.85rem;font-weight:600;text-align:center;border-radius:6px;cursor:not-allowed;letter-spacing:0.5px;box-sizing:border-box;">Sold Out</span>`
                : `<button type="button" class="add-to-cart-btn" ${hasSizes ? "" : "disabled"}>Add to Cart</button>`
            }
        </div>
    `;

    card.prepend(carousel.shell);

    const wishlistBtn = card.querySelector(".wishlist-lock-btn");
    wishlistBtn.addEventListener("click", async () => {
        if (!currentUserId) {
            alert("Please log in to add items to your wishlist.");
            window.location.href = "/auth/login";
            return;
        }

        wishlistBtn.disabled = true;
        const isActive = wishlistBtn.classList.contains("active");

        try {
            const response = await fetch(isActive ? `/api/wishlist/${listingId}` : "/api/wishlist", {
                method: isActive ? "DELETE" : "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-User-Id": String(currentUserId)
                },
                body: isActive ? undefined : JSON.stringify({ listing_id: listingId })
            });

            const result = await response.json().catch(() => ({}));
            if (!response.ok && !(response.status === 400 && /already in wishlist/i.test(result.error || ""))) {
                throw new Error(result.error || "Unable to update wishlist.");
            }

            const nextState = !isActive;
            wishlistBtn.classList.toggle("active", nextState);
            wishlistBtn.setAttribute("aria-label", nextState ? "Remove from wishlist" : "Add to wishlist");
            wishlistBtn.setAttribute("title", nextState ? "Remove from wishlist" : "Add to wishlist");

            if (nextState) {
                wishlistIds.add(String(listingId));
                addLocalWishlistItem({
                    listing_id: listingId,
                    title,
                    price,
                    image_url: primaryImageUrl,
                    storefront_name: pageTitle?.textContent || "Storefront"
                });
            } else {
                wishlistIds.delete(String(listingId));
                removeLocalWishlistItem(listingId);
            }
        } catch (error) {
            console.error("Wishlist update failed:", error);
            alert(error.message || "Unable to update wishlist right now.");
        } finally {
            wishlistBtn.disabled = false;
        }
    });

    const sizeSelect = card.querySelector(".size-select");
    const countInput = card.querySelector(".count-input");
    const addToCartBtn = card.querySelector(".add-to-cart-btn");

    if (addToCartBtn) {
        addToCartBtn.addEventListener("click", async () => {
            if (!currentUserId) {
                alert("Please log in to add items to your cart.");
                window.location.href = "/auth/login";
                return;
            }

            const selectedSize = isOneSizeItem ? "One Size" : (sizeSelect ? sizeSelect.value : "");
            const selectedCount = Number.parseInt(countInput.value, 10);
            const effectiveMax = isMadeToOrder ? Number.POSITIVE_INFINITY : (item.quantity_on_hand || 1);

            if (!selectedSize) {
                showCartToast("Please select a size.", "error");
                return;
            }

            if (!Number.isInteger(selectedCount) || selectedCount < 1) {
                showCartToast("Count must be at least 1.", "error");
                countInput.value = "1";
                return;
            }

            if (!isMadeToOrder && selectedCount > effectiveMax) {
                showCartToast(`Maximum available quantity is ${effectiveMax}.`, "error");
                countInput.value = String(effectiveMax);
                return;
            }

            addToCartBtn.disabled = true;

            try {
                const formData = new FormData();
                formData.append("item_id", String(listingId));
                formData.append("item_name", title);
                formData.append("price", String(numericPrice));
                formData.append("quantity", String(selectedCount));
                formData.append("size", selectedSize);

                const response = await fetch("/auth/add_to_cart", {
                    method: "POST",
                    body: formData,
                    redirect: "follow"
                });

                if (!response.ok) {
                    let errorMsg = "Unable to add item to cart right now.";
                    try {
                        const errData = await response.json();
                        if (errData && errData.error) errorMsg = errData.error;
                    } catch (_) {}
                    throw new Error(errorMsg);
                }

                showCartToast(`${title} (${selectedSize}) x${selectedCount} added to cart.`);
            } catch (error) {
                console.error("Add to cart failed:", error);
                showCartToast(error.message || "Unable to add to cart.", "error");
            } finally {
                addToCartBtn.disabled = false;
            }
        });
    }

    return card;
}

async function loadStorefrontView() {
    let storefront;
    try {
        const sfRes = await fetch(`/api/storefronts/${storefrontId}`);
        if (!sfRes.ok) throw new Error("Storefront not found");
        storefront = await sfRes.json();
    } catch (error) {
        console.error("Error loading storefront:", error);
        if (pageTitle) pageTitle.textContent = "Storefront Unavailable";
        storeDescription.textContent = "Could not load storefront details. Please try again.";
        renderEmpty("Could not load listings.");
        return;
    }

    if (pageTitle) pageTitle.textContent = storefront.brand_name || "Unnamed Storefront";
    storeDescription.textContent = storefront.bio || storefront.description || "No description provided.";
    contactInfo.textContent = storefront.contact_info || "";

    if (storefront.logo_url) {
        storefrontLogo.src = storefront.logo_url;
        storefrontLogo.style.display = "block";
        logoFallback.style.display = "none";
    }

    if (storefront.banner_url) {
        document.getElementById("storefrontBanner").style.backgroundImage = `url('${storefront.banner_url}')`;
        document.getElementById("storefrontBanner").style.backgroundSize = "cover";
        document.getElementById("storefrontBanner").style.backgroundPosition = "center";
    }

    const sessionUser = await getCurrentSessionUser();
    const wishlistIds = await getWishlistIdSet(sessionUser?.id || null);

    try {
        const listRes = await fetch(`/api/storefronts/${storefrontId}/listings`);
        if (!listRes.ok) throw new Error("Could not load listings");
        const listings = await listRes.json();

        listingGrid.innerHTML = "";
        const activeListings = Array.isArray(listings)
            ? listings.filter((item) => item.status !== "DELETED" && item.status !== "INACTIVE")
            : [];

        if (!activeListings.length) {
            renderEmpty("No listings available for this storefront yet.");
            return;
        }

        const cards = await Promise.all(
            activeListings.map((item) => createListingCard(item, wishlistIds, sessionUser?.id || null))
        );
        cards.forEach((card) => listingGrid.appendChild(card));
    } catch (error) {
        console.error("Error loading listings:", error);
        renderEmpty("Could not load listings. Please try again.");
    }
}

if (lightboxClose) {
    lightboxClose.addEventListener("click", closeLightbox);
}

if (lightboxPrev) {
    lightboxPrev.addEventListener("click", () => shiftLightbox(-1));
}

if (lightboxNext) {
    lightboxNext.addEventListener("click", () => shiftLightbox(1));
}

if (lightbox) {
    lightbox.addEventListener("click", (event) => {
        if (event.target === lightbox) {
            closeLightbox();
        }
    });
}

document.addEventListener("keydown", (event) => {
    if (!lightbox || !lightbox.classList.contains("is-open")) return;
    if (event.key === "Escape") {
        closeLightbox();
    } else if (event.key === "ArrowLeft") {
        shiftLightbox(-1);
    } else if (event.key === "ArrowRight") {
        shiftLightbox(1);
    }
});

loadStorefrontView();
