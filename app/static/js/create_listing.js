/*
create_listing.js

The Vault Campus Marketplace
CSC 405 Sp 26
Created by Elali McNair - Iteration 4
Updated by Day Ekoi - Iteration 5 4/9/26
Updated by Day Ekoi - Iteration 5 4/22/26 - One Size mode, per-size quantities, Made-to-Order

Purpose:
Handles form submission for Create Listing page. Supports:
- One Size mode (single quantity, no other sizes selectable)
- Multi-size mode (per-size quantity inputs)
- Made-to-Order flag (bypasses inventory limits)
*/

document.addEventListener('DOMContentLoaded', function() {

  function ensureToastRoot() {
    let root = document.getElementById("toastRoot");
    if (!root) {
      root = document.createElement("div");
      root.id = "toastRoot";
      root.className = "toast-root";
      document.body.appendChild(root);
    }
    return root;
  }

  function showListingToast(message, tone = "success") {
    const root = ensureToastRoot();
    const toast = document.createElement("div");
    toast.className = `toast ${tone === "success" ? "success" : "error"}`;
    toast.textContent = message;
    root.appendChild(toast);

    window.setTimeout(() => {
      toast.classList.add("fade-out");
      window.setTimeout(() => toast.remove(), 220);
    }, 2200);
  }

  const listingForm = document.getElementById("listingForm");
  const cancelBtn = document.getElementById("cancelBtn");
  const storefrontSelect = document.getElementById("storefrontSelect");
  const previewInputs = [1, 2, 3, 4].map((index) => document.getElementById(`previewImage${index}`));
  const selectedListingImages = [null, null, null, null];

  // ── Size mode elements ──────────────────────────────────────
  const oneSizeToggle = document.getElementById("oneSizeToggle");
  const multiSizeGrid = document.getElementById("multiSizeGrid");
  const oneSizeQtyRow = document.getElementById("oneSizeQtyRow");
  const oneSizeQty = document.getElementById("oneSizeQty");
  const madeToOrderToggle = document.getElementById("madeToOrderToggle");

  function applyOneSizeMode(enabled) {
    if (!multiSizeGrid || !oneSizeQtyRow) return;
    if (enabled) {
      // Hide multi-size grid, clear all checkboxes and qty inputs
      multiSizeGrid.style.display = "none";
      multiSizeGrid.querySelectorAll('input[name="sizes"]').forEach(cb => {
        cb.checked = false;
      });
      multiSizeGrid.querySelectorAll(".size-qty-input").forEach(inp => {
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

  // Show/hide per-size quantity input when a size checkbox is toggled
  if (multiSizeGrid) {
    multiSizeGrid.querySelectorAll('input[name="sizes"]').forEach(cb => {
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

  // ── Image preview / drop zone ────────────────────────────────

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
  }

  function wireDropZone(zone, input, previewContainer, slotIndex) {
    if (!zone || !input) return;

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
        selectedListingImages[slotIndex] = droppedFile;
        renderSinglePreview(previewContainer, droppedFile, zone, slotIndex);
      }
    });

    input.addEventListener("change", () => {
      const chosenFile = input.files?.[0];
      selectedListingImages[slotIndex] = chosenFile && chosenFile.type.startsWith("image/")
        ? chosenFile
        : null;
      renderSinglePreview(previewContainer, selectedListingImages[slotIndex], zone, slotIndex);
    });
  }

  [1, 2, 3, 4].forEach((index, arrayIndex) => {
    const zone = document.getElementById(`previewZone${index}`);
    const input = previewInputs[arrayIndex];
    const preview = document.getElementById(`previewPreview${index}`);
    wireDropZone(zone, input, preview, arrayIndex);
  });

  if (storefrontSelect) {
    loadUserStorefronts();
  }

  // ── Form submission ──────────────────────────────────────────

  if (listingForm) {
    listingForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const userRes = await fetch("/auth/api/auth/me");
      if (!userRes.ok) {
        alert("You must be logged in to create a listing.");
        window.location.href = "/auth/login";
        return;
      }
      const user = await userRes.json();

      const storefrontId = document.getElementById("storefrontSelect").value;
      const listingName = document.getElementById("listingName").value.trim();
      const price = parseFloat(document.getElementById("price").value);
      const isOneSizeMode = oneSizeToggle && oneSizeToggle.checked;
      const isMadeToOrder = madeToOrderToggle && madeToOrderToggle.checked;

      if (!storefrontId) {
        alert("Please select a storefront for this listing.");
        return;
      }

      if (!listingName || price < 0 || isNaN(price)) {
        alert("Please fill in all required fields with valid values.");
        return;
      }

      // Collect sizes and per-size quantities
      let sizes = [];
      const sizeQuantities = {};

      if (isOneSizeMode) {
        const qty = parseInt(oneSizeQty ? oneSizeQty.value : "0", 10);
        if (!isMadeToOrder && (isNaN(qty) || qty < 0)) {
          alert("Please enter a valid quantity for One Size.");
          return;
        }
        sizes = ["One Size"];
        sizeQuantities["One Size"] = isMadeToOrder ? 0 : (qty || 0);
      } else {
        const sizeCheckboxes = document.querySelectorAll("input[name='sizes']:checked");
        sizes = Array.from(sizeCheckboxes).map(cb => cb.value);
        if (sizes.length === 0) {
          alert("Please select at least one size.");
          return;
        }
        for (const size of sizes) {
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

      const totalQty = isMadeToOrder ? 0 : Object.values(sizeQuantities).reduce((a, b) => a + b, 0);

      const listingImages = selectedListingImages.filter(Boolean);
      if (listingImages.length === 0) {
        alert("Please upload at least one listing image.");
        return;
      }

      try {
        const formData = new FormData();
        formData.append("storefront_id", storefrontId);
        formData.append("title", listingName);
        formData.append("quantity_on_hand", totalQty);
        formData.append("price", price);
        formData.append("fulfillment_type", "IN_STOCK");
        formData.append("status", "ACTIVE");
        formData.append("is_made_to_order", isMadeToOrder ? "true" : "false");
        formData.append("sizes_available", JSON.stringify(sizes));
        formData.append("size_quantities", JSON.stringify(sizeQuantities));
        listingImages.forEach(file => formData.append("listing_images", file));
        formData.append("listing_image", listingImages[0]);

        const response = await fetch("/api/listings/create", {
          method: "POST",
          headers: {
            "X-User-Id": user.id,
            "X-User-Role": user.role
          },
          body: formData,
        });

        const result = await response.json();

        if (response.ok) {
          showListingToast(`Listing "${listingName}" created successfully!`);
          window.setTimeout(() => {
            window.location.href = "/my-storefront";
          }, 2500);
        } else {
          alert("Error creating listing: " + (result.error || "Unknown error"));
        }
      } catch (error) {
        console.error("Error submitting form:", error);
        alert("Error creating listing: " + error.message);
      }
    });
  }

  if (cancelBtn) {
    cancelBtn.addEventListener("click", () => {
      window.location.href = "/storefronts";
    });
  }

  async function loadUserStorefronts() {
    try {
      const userRes = await fetch("/auth/api/auth/me");
      if (!userRes.ok) {
        window.location.href = "/auth/login";
        return;
      }
      const user = await userRes.json();

      const response = await fetch("/api/storefronts/me", {
        method: "GET",
        headers: {
          "X-User-Id": user.id,
          "X-User-Role": user.role
        },
      });

      if (response.ok) {
        const storefrontData = await response.json();
        const storefronts = Array.isArray(storefrontData)
          ? storefrontData
          : storefrontData && storefrontData.id
            ? [storefrontData]
            : [];

        storefrontSelect.innerHTML = "";

        if (storefronts.length > 0) {
          const defaultOption = document.createElement("option");
          defaultOption.value = "";
          defaultOption.textContent = "Select a storefront";
          defaultOption.disabled = true;
          defaultOption.selected = true;
          storefrontSelect.appendChild(defaultOption);

          storefronts.forEach(storefront => {
            const option = document.createElement("option");
            option.value = storefront.id;
            option.textContent = storefront.brand_name || storefront.name || `Storefront #${storefront.id}`;
            storefrontSelect.appendChild(option);
          });
        } else {
          storefrontSelect.innerHTML = '<option value="" disabled>No storefronts found - create one first</option>';
          if (listingForm) {
            listingForm.querySelectorAll("input, select, button[type='submit']").forEach(el => {
              el.disabled = true;
            });
          }
          const messageDiv = document.createElement("div");
          messageDiv.style.cssText = "color: #d4af37; margin-top: 10px; font-weight: bold; text-align:center;";
          messageDiv.innerHTML = `You must create a storefront before creating listings. <a href="/storefronts/create" style="color:#fff; text-decoration:underline;">Create one here</a>`;
          storefrontSelect.parentNode.appendChild(messageDiv);
        }
      } else if (response.status === 404) {
        storefrontSelect.innerHTML = '<option value="" disabled>No storefronts found - create one first</option>';
        if (listingForm) {
          listingForm.querySelectorAll("input, select, button[type='submit']").forEach(el => {
            el.disabled = true;
          });
        }
        const messageDiv = document.createElement("div");
        messageDiv.style.cssText = "color: #d4af37; margin-top: 10px; font-weight: bold; text-align:center;";
        messageDiv.innerHTML = `You must create a storefront before creating listings. <a href="/storefronts/create" style="color:#fff; text-decoration:underline;">Create one here</a>`;
        storefrontSelect.parentNode.appendChild(messageDiv);
      } else {
        console.error("Failed to load storefronts");
        storefrontSelect.innerHTML = '<option value="">Error loading storefronts</option>';
      }
    } catch (error) {
      console.error("Error loading storefronts:", error);
      storefrontSelect.innerHTML = '<option value="">Error loading storefronts</option>';
    }
  }
});
