/*
    edit_listing.js

    The Vault Campus Marketplace
    CSC 405 Sp 26'
    Updated by Day Ekoi - Iteration 5 4/22/26
    - One Size mode: loads correctly from existing data
    - Per-size quantity inputs
    - Made-to-Order toggle
    Updated by Day E - April 22nd - multi-image edit management using existing S3 and listing image routes
*/

document.addEventListener("DOMContentLoaded", async () => {
    const form = document.getElementById("editListingForm");
    const cancelBtn = document.getElementById("cancelBtn");
    const listingId = Number(window.location.pathname.split("/")[2]);

    const oneSizeToggle = document.getElementById("oneSizeToggle");
    const multiSizeGrid = document.getElementById("multiSizeGrid");
    const oneSizeQtyRow = document.getElementById("oneSizeQtyRow");
    const oneSizeQty = document.getElementById("oneSizeQty");
    const madeToOrderToggle = document.getElementById("madeToOrderToggle");
    const currentImageGallery = document.getElementById("currentImageGallery");
    const imageFallback = document.getElementById("imageFallback");
    const imageStatusNote = document.getElementById("imageStatusNote");

    const previewInputs = [1, 2, 3, 4].map((index) => document.getElementById(`previewImage${index}`));
    const selectedListingImages = [null, null, null, null];

    let currentUser = null;
    let existingImages = [];
    let sizesArray = [];

    if (cancelBtn) {
        cancelBtn.addEventListener("click", () => {
            window.location.href = "/storefronts/dashboard";
        });
    }

    function updateImageStatusNote() {
        if (!imageStatusNote) return;
        const pendingCount = selectedListingImages.filter(Boolean).length;
        const totalCount = existingImages.length + pendingCount;
        imageStatusNote.textContent = `${existingImages.length} saved image${existingImages.length === 1 ? "" : "s"} | ${pendingCount} queued upload${pendingCount === 1 ? "" : "s"} | ${totalCount}/4 total`;
    }

    function applyOneSizeMode(enabled) {
        if (!multiSizeGrid || !oneSizeQtyRow) return;
        if (enabled) {
            multiSizeGrid.style.display = "none";
            multiSizeGrid.querySelectorAll('input[name="sizes"]').forEach((cb) => {
                cb.checked = false;
            });
            multiSizeGrid.querySelectorAll(".size-qty-input").forEach((inp) => {
                inp.value = "";
                inp.style.display = "none";
            });
            oneSizeQtyRow.style.display = "block";
        } else {
            multiSizeGrid.style.display = "";
            oneSizeQtyRow.style.display = "none";
            if (oneSizeQty) oneSizeQty.value = "";
        }
    }

    if (oneSizeToggle) {
        oneSizeToggle.addEventListener("change", () => {
            applyOneSizeMode(oneSizeToggle.checked);
        });
    }

    if (multiSizeGrid) {
        multiSizeGrid.querySelectorAll('input[name="sizes"]').forEach((cb) => {
            cb.addEventListener("change", () => {
                const row = cb.closest(".size-qty-row");
                if (!row) return;
                const qtyInput = row.querySelector(".size-qty-input");
                if (qtyInput) {
                    qtyInput.style.display = cb.checked ? "inline-block" : "none";
                    if (!cb.checked) qtyInput.value = "";
                }
            });
        });
    }

    function renderSinglePreview(previewContainer, file, zone, slotIndex) {
        if (!previewContainer) return;

        previewContainer.innerHTML = "";
        if (!file) {
            if (zone) {
                zone.classList.remove("has-image");
                zone.style.backgroundImage = "";
                const existingBadge = zone.querySelector(".image-selected-badge");
                if (existingBadge) existingBadge.remove();
            }
            updateImageStatusNote();
            return;
        }

        const thumbWrap = document.createElement("div");
        thumbWrap.className = "thumb-wrap";

        const image = document.createElement("img");
        image.src = URL.createObjectURL(file);
        image.alt = file.name;
        image.onload = () => URL.revokeObjectURL(image.src);

        const fileName = document.createElement("p");
        fileName.className = "thumb-name";
        fileName.textContent = file.name;

        thumbWrap.appendChild(image);
        thumbWrap.appendChild(fileName);
        previewContainer.appendChild(thumbWrap);

        if (zone) {
            const zoneImageUrl = URL.createObjectURL(file);
            zone.style.backgroundImage = `url('${zoneImageUrl}')`;
            zone.classList.add("has-image");

            const existingBadge = zone.querySelector(".image-selected-badge");
            if (existingBadge) existingBadge.remove();

            const badge = document.createElement("span");
            badge.className = "image-selected-badge";
            badge.textContent = `Image ${slotIndex + 1} selected`;
            zone.appendChild(badge);
        }

        updateImageStatusNote();
    }

    function wireDropZone(zone, input, previewContainer, slotIndex) {
        if (!zone || !input) return;

        const assignFile = (chosenFile) => {
            const pendingCount = selectedListingImages.filter(Boolean).length;
            const replacingExistingPending = selectedListingImages[slotIndex] ? 1 : 0;
            const nextTotal = existingImages.length + pendingCount - replacingExistingPending + (chosenFile ? 1 : 0);

            if (nextTotal > 4) {
                alert("You can upload up to 4 listing images total.");
                input.value = "";
                return;
            }

            selectedListingImages[slotIndex] = chosenFile;
            renderSinglePreview(previewContainer, selectedListingImages[slotIndex], zone, slotIndex);
        };

        zone.addEventListener("click", () => input.click());

        zone.addEventListener("dragover", (event) => {
            event.preventDefault();
            zone.classList.add("dragover");
        });

        zone.addEventListener("dragleave", () => {
            zone.classList.remove("dragover");
        });

        zone.addEventListener("drop", (event) => {
            event.preventDefault();
            zone.classList.remove("dragover");
            const droppedFile = event.dataTransfer?.files?.[0];
            if (droppedFile && droppedFile.type.startsWith("image/")) {
                assignFile(droppedFile);
            }
        });

        input.addEventListener("change", () => {
            const chosenFile = input.files?.[0];
            assignFile(chosenFile && chosenFile.type.startsWith("image/") ? chosenFile : null);
        });
    }

    async function fetchListingImages() {
        const response = await fetch(`/api/listings/${listingId}/images`);
        if (!response.ok) {
            return [];
        }
        const images = await response.json();
        return Array.isArray(images) ? images.slice(0, 4) : [];
    }

    async function refreshListingImages() {
        existingImages = await fetchListingImages();
        renderExistingImages();
        updateImageStatusNote();
    }

    function renderExistingImages() {
        if (!currentImageGallery) return;

        currentImageGallery.innerHTML = "";

        if (!existingImages.length) {
            if (imageFallback) imageFallback.style.display = "block";
            return;
        }

        if (imageFallback) imageFallback.style.display = "none";

        existingImages.forEach((image, index) => {
            const card = document.createElement("div");
            card.className = "existing-image-card";
            card.innerHTML = `
                <p class="image-slot-label">${image.is_primary ? "Primary Image" : `Image ${index + 1}`}</p>
                <img src="${image.image_url}" alt="Listing image ${index + 1}">
                <div class="existing-image-actions">
                    <button type="button" class="mini-btn ${image.is_primary ? "is-active" : ""}" data-action="primary" ${image.is_primary || image.is_legacy ? "disabled" : ""}>${image.is_primary ? "Primary" : "Set Primary"}</button>
                    <button type="button" class="mini-btn is-danger" data-action="remove" ${existingImages.length <= 1 || image.is_legacy ? "disabled" : ""}>Remove</button>
                </div>
            `;

            const primaryBtn = card.querySelector('[data-action="primary"]');
            const removeBtn = card.querySelector('[data-action="remove"]');

            if (primaryBtn) {
                primaryBtn.addEventListener("click", async () => {
                    if (!currentUser) return;
                    try {
                        const response = await fetch(`/api/listings/${listingId}/images/${image.id}/primary`, {
                            method: "PATCH",
                            headers: {
                                "X-User-Id": currentUser.id,
                                "X-User-Role": currentUser.role
                            }
                        });
                        const result = await response.json().catch(() => ({}));
                        if (!response.ok) {
                            throw new Error(result.error || "Could not update the primary image.");
                        }
                        await refreshListingImages();
                    } catch (error) {
                        console.error("Unable to set primary image:", error);
                        alert(error.message || "Could not update the primary image.");
                    }
                });
            }

            if (removeBtn) {
                removeBtn.addEventListener("click", async () => {
                    if (!currentUser) return;
                    if (!window.confirm("Are you sure you want to remove this listing image?")) {
                        return;
                    }
                    try {
                        const response = await fetch(`/api/listings/${listingId}/images/${image.id}`, {
                            method: "DELETE",
                            headers: {
                                "X-User-Id": currentUser.id,
                                "X-User-Role": currentUser.role
                            }
                        });
                        const result = await response.json().catch(() => ({}));
                        if (!response.ok) {
                            throw new Error(result.error || "Could not remove the image.");
                        }
                        await refreshListingImages();
                    } catch (error) {
                        console.error("Unable to remove listing image:", error);
                        alert(error.message || "Could not remove the image.");
                    }
                });
            }

            currentImageGallery.appendChild(card);
        });
    }

    async function uploadListingImageFile(file) {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("folder", "listings");

        const response = await fetch("/api/storefronts/upload-image", {
            method: "POST",
            body: formData
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data.error || "Could not upload listing image.");
        }
        return data.url;
    }

    async function saveQueuedImages() {
        const queuedImages = selectedListingImages.filter(Boolean);
        if (!queuedImages.length) return;

        if (existingImages.length + queuedImages.length > 4) {
            throw new Error("You can upload up to 4 listing images total.");
        }

        for (let index = 0; index < queuedImages.length; index += 1) {
            const file = queuedImages[index];
            const imageUrl = await uploadListingImageFile(file);
            const response = await fetch(`/api/listings/${listingId}/images`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-User-Id": currentUser.id,
                    "X-User-Role": currentUser.role
                },
                body: JSON.stringify({
                    image_url: imageUrl,
                    is_primary: existingImages.length === 0 && index === 0
                })
            });
            const result = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(result.error || "Could not save listing image.");
            }
        }
    }

    [1, 2, 3, 4].forEach((index, arrayIndex) => {
        const zone = document.getElementById(`previewZone${index}`);
        const input = previewInputs[arrayIndex];
        const preview = document.getElementById(`previewPreview${index}`);
        wireDropZone(zone, input, preview, arrayIndex);
    });

    try {
        const userRes = await fetch("/auth/api/auth/me");
        if (!userRes.ok) {
            window.location.href = "/auth/login";
            return;
        }
        currentUser = await userRes.json();

        const [listingRes, sizesRes, myStorefrontRes] = await Promise.all([
            fetch(`/api/listings/${listingId}`),
            fetch(`/api/listings/${listingId}/sizes`),
            fetch("/api/storefronts/me", {
                headers: {
                    "X-User-Id": currentUser.id,
                    "X-User-Role": currentUser.role
                }
            })
        ]);

        if (!listingRes.ok) {
            throw new Error("Could not load listing.");
        }

        const listing = await listingRes.json();
        sizesArray = sizesRes.ok ? await sizesRes.json() : [];
        const myStorefront = myStorefrontRes.ok ? await myStorefrontRes.json() : null;

        document.getElementById("listingName").value = listing.title || "";
        document.getElementById("price").value = Number(listing.price || 0).toFixed(2);
        document.getElementById("storefrontName").value = myStorefront?.brand_name || `Storefront #${listing.storefront_id}`;

        if (madeToOrderToggle && listing.is_made_to_order) {
            madeToOrderToggle.checked = true;
        }

        await refreshListingImages();

        if (!existingImages.length && listing.image_url) {
            existingImages = [{
                id: `legacy-${listing.id}`,
                image_url: listing.image_url,
                is_primary: true,
                is_legacy: true
            }];
            renderExistingImages();
            updateImageStatusNote();
        }

        const isOneSize = Array.isArray(sizesArray) && sizesArray.length === 1 && sizesArray[0].size === "One Size";

        if (isOneSize) {
            if (oneSizeToggle) oneSizeToggle.checked = true;
            applyOneSizeMode(true);
            if (oneSizeQty) oneSizeQty.value = sizesArray[0].quantity || 0;
        } else {
            const sizeMap = {};
            sizesArray.forEach((sizeEntry) => {
                sizeMap[sizeEntry.size] = sizeEntry.quantity;
            });

            if (multiSizeGrid) {
                multiSizeGrid.querySelectorAll('input[name="sizes"]').forEach((cb) => {
                    if (Object.prototype.hasOwnProperty.call(sizeMap, cb.value)) {
                        cb.checked = true;
                        const row = cb.closest(".size-qty-row");
                        if (row) {
                            const qtyInput = row.querySelector(".size-qty-input");
                            if (qtyInput) {
                                qtyInput.style.display = "inline-block";
                                qtyInput.value = sizeMap[cb.value];
                            }
                        }
                    }
                });
            }
        }

        form.addEventListener("submit", async (event) => {
            event.preventDefault();

            const isOneSizeMode = oneSizeToggle && oneSizeToggle.checked;
            const isMadeToOrder = madeToOrderToggle && madeToOrderToggle.checked;
            const price = Number(document.getElementById("price").value);
            const title = document.getElementById("listingName").value.trim();
            const queuedImages = selectedListingImages.filter(Boolean);

            if (!title || price < 0) {
                alert("Please enter valid listing details.");
                return;
            }

            if (existingImages.length + queuedImages.length === 0) {
                alert("Please keep at least one listing image.");
                return;
            }

            if (existingImages.length + queuedImages.length > 4) {
                alert("You can upload up to 4 listing images total.");
                return;
            }

            let checkedSizes = [];
            const sizeQuantities = {};

            if (isOneSizeMode) {
                const qty = parseInt(oneSizeQty ? oneSizeQty.value : "0", 10);
                if (!isMadeToOrder && (isNaN(qty) || qty < 0)) {
                    alert("Please enter a valid quantity for One Size.");
                    return;
                }
                checkedSizes = ["One Size"];
                sizeQuantities["One Size"] = isMadeToOrder ? 0 : (qty || 0);
            } else {
                const checked = Array.from(document.querySelectorAll('input[name="sizes"]:checked'));
                checkedSizes = checked.map((cb) => cb.value);
                if (!checkedSizes.length) {
                    alert("Please select at least one size.");
                    return;
                }
                for (const size of checkedSizes) {
                    const qtyInput = multiSizeGrid
                        ? multiSizeGrid.querySelector(`.size-qty-input[data-size="${size}"]`)
                        : null;
                    const qty = qtyInput ? parseInt(qtyInput.value, 10) : NaN;
                    if (!isMadeToOrder && (isNaN(qty) || qty < 0)) {
                        alert(`Please enter a valid quantity for size ${size}.`);
                        return;
                    }
                    sizeQuantities[size] = isMadeToOrder ? 0 : (isNaN(qty) ? 0 : qty);
                }
            }

            const totalQty = isMadeToOrder
                ? 0
                : Object.values(sizeQuantities).reduce((a, b) => a + b, 0);

            const updateRes = await fetch(`/api/listings/${listingId}`, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                    "X-User-Id": currentUser.id,
                    "X-User-Role": currentUser.role
                },
                body: JSON.stringify({
                    title,
                    price,
                    quantity_on_hand: totalQty,
                    fulfillment_type: "IN_STOCK",
                    status: "ACTIVE",
                    sizes_available: checkedSizes,
                    is_made_to_order: isMadeToOrder,
                })
            });

            const updateData = await updateRes.json();
            if (!updateRes.ok) {
                throw new Error(updateData.error || "Failed to update listing.");
            }

            const existingSizeSet = new Set((Array.isArray(sizesArray) ? sizesArray : []).map((s) => String(s.size)));
            const newSizeSet = new Set(checkedSizes);

            for (const size of checkedSizes) {
                await fetch(`/api/listings/${listingId}/sizes`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-User-Id": currentUser.id,
                        "X-User-Role": currentUser.role
                    },
                    body: JSON.stringify({ size, quantity: sizeQuantities[size] || 0 })
                });
            }

            for (const existing of existingSizeSet) {
                if (newSizeSet.has(existing)) continue;
                await fetch(`/api/listings/${listingId}/sizes/${existing}`, {
                    method: "DELETE",
                    headers: {
                        "X-User-Id": currentUser.id,
                        "X-User-Role": currentUser.role
                    }
                });
            }

            await saveQueuedImages();
            window.location.href = "/storefronts/dashboard";
        });
    } catch (error) {
        console.error("Error loading edit listing page:", error);
        alert(error.message || "Something went wrong while loading this listing.");
        window.location.href = "/storefronts/dashboard";
    }
});
