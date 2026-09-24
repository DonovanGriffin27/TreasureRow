/*
    create_storefront.js

    The Vault Campus Marketplace
    CSC 405 Sp 26'
    Created by Day Ekoi - Iteration 4 - 3/22/2026
    Updated by Day Ekoi - Iteration 5 4/9/26
    Updated by Day Ekoi - Iteration 5 4/16/26 - S3 image upload integration
    Updated by Day Ekoi - Iteration 5 - 4/20/26 - drag-drop zones, image preview thumbnails, preview_image_1-4 upload support
*/

const form = document.getElementById("storefrontForm");
const cancelBtn = document.getElementById("cancelBtn");
const categoryCheckboxes = Array.from(document.querySelectorAll('input[name="categories"]'));
const categoryValidationMessage = document.getElementById("categoryValidationMessage");
const MAX_CATEGORY_SELECTIONS = 3;

cancelBtn.addEventListener("click", () => {
    window.location.href = "/storefronts";
});


function getSelectedCategories() {
    return categoryCheckboxes.filter((checkbox) => checkbox.checked).map((checkbox) => checkbox.value);
}


function showCategoryValidation(message = "") {
    if (!categoryValidationMessage) return;
    categoryValidationMessage.textContent = message;
}


function validateCategoryLimit() {
    const selected = getSelectedCategories();
    if (selected.length > MAX_CATEGORY_SELECTIONS) {
        showCategoryValidation(`You can select up to ${MAX_CATEGORY_SELECTIONS} categories.`);
        return false;
    }
    showCategoryValidation("");
    return true;
}


function setupCategoryLimitGuard() {
    categoryCheckboxes.forEach((checkbox) => {
        checkbox.addEventListener("change", () => {
            if (getSelectedCategories().length > MAX_CATEGORY_SELECTIONS) {
                checkbox.checked = false;
                showCategoryValidation(`You can select up to ${MAX_CATEGORY_SELECTIONS} categories.`);
                return;
            }
            validateCategoryLimit();
        });
    });
}


// Guard: redirect away if user already has a storefront - Added by Day Ekoi 4/20/26
(async () => {
    try {
        const userRes = await fetch("/auth/api/auth/me");
        if (!userRes.ok) return;
        const user = await userRes.json();

        const sfRes = await fetch("/api/storefronts/me", {
            headers: { "X-User-Id": user.id, "X-User-Role": user.role }
        });

        if (sfRes.ok) {
            alert("You already have a storefront. Redirecting to your dashboard.");
            window.location.href = "/storefronts/dashboard";
        }
    } catch (err) {
        // silently allow page to load if check fails
    }
})();


// shows thumbnail + filename in a preview container
function showPreview(containerId, files, max = 1) {
    const container = document.getElementById(containerId);
    container.innerHTML = "";
    Array.from(files).slice(0, max).forEach(file => {
        const reader = new FileReader();
        reader.onload = e => {
            const wrap = document.createElement("div");
            wrap.className = "thumb-wrap";

            const img = document.createElement("img");
            img.src = e.target.result;

            const name = document.createElement("span");
            name.className = "thumb-name";
            name.textContent = file.name;

            wrap.appendChild(img);
            wrap.appendChild(name);
            container.appendChild(wrap);
        };
        reader.readAsDataURL(file);
    });
}


// wires up a drop zone: click to browse, drag-and-drop to select, shows preview
function setupDropZone(zoneId, inputId, previewId, max = 1) {
    const zone = document.getElementById(zoneId);
    const input = document.getElementById(inputId);

    zone.addEventListener("click", () => input.click());

    zone.addEventListener("dragover", e => {
        e.preventDefault();
        zone.classList.add("dragover");
    });

    zone.addEventListener("dragleave", () => zone.classList.remove("dragover"));

    zone.addEventListener("drop", e => {
        e.preventDefault();
        zone.classList.remove("dragover");
        const dt = new DataTransfer();
        Array.from(e.dataTransfer.files).slice(0, max).forEach(f => dt.items.add(f));
        input.files = dt.files;
        showPreview(previewId, dt.files, max);
    });

    input.addEventListener("change", () => showPreview(previewId, input.files, max));
}


// set up drop zones - Updated by Day Ekoi 4/20/26 - 4 individual preview slots
setupDropZone("bannerZone", "bannerUpload", "bannerPreview", 1);
setupDropZone("logoZone", "logoUpload", "logoPreview", 1);
setupDropZone("previewZone1", "previewImage1", "previewPreview1", 1);
setupDropZone("previewZone2", "previewImage2", "previewPreview2", 1);
setupDropZone("previewZone3", "previewImage3", "previewPreview3", 1);
setupDropZone("previewZone4", "previewImage4", "previewPreview4", 1);
setupCategoryLimitGuard();


// uploads a file to S3 via the Flask backend
async function uploadImageToS3(file, folder) {
    const uploadData = new FormData();
    uploadData.append("file", file);
    uploadData.append("folder", folder);

    const res = await fetch("/api/storefronts/upload-image", {
        method: "POST",
        body: uploadData
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Upload failed");
    return data.url;
}


// form submission
form.addEventListener("submit", async (event) => {
    event.preventDefault();

    try {
        const userRes = await fetch("/auth/api/auth/me");
        if (!userRes.ok) {
            alert("You must be logged in to create a storefront.");
            window.location.href = "/auth/login";
            return;
        }
        const user = await userRes.json();

        const formData = new FormData(form);

        // upload logo
        let logoUrl = null;
        const logoFile = document.getElementById("logoUpload").files[0];
        if (logoFile) {
            try { logoUrl = await uploadImageToS3(logoFile, "storefronts/logos"); }
            catch (err) { alert("Failed to upload logo image. Please try again."); return; }
        }

        // upload banner
        let bannerUrl = null;
        const bannerFile = document.getElementById("bannerUpload").files[0];
        if (bannerFile) {
            try { bannerUrl = await uploadImageToS3(bannerFile, "storefronts/banners"); }
            catch (err) { alert("Failed to upload banner image. Please try again."); return; }
        }

        // upload 4 individual preview images - Updated by Day Ekoi 4/20/26
        const previewUrls = [null, null, null, null];
        for (let i = 0; i < 4; i++) {
            const file = document.getElementById(`previewImage${i + 1}`).files[0];
            if (file) {
                try {
                    previewUrls[i] = await uploadImageToS3(file, "storefronts/previews");
                } catch (err) {
                    alert(`Failed to upload preview image ${i + 1}. Please try again.`);
                    return;
                }
            }
        }

        const checkedCategories = Array.from(document.querySelectorAll('input[name="categories"]:checked')).map(cb => cb.value);
        if (!validateCategoryLimit()) {
            return;
        }

        const payload = {
            brand_name: formData.get("brand_name"),
            bio: formData.get("description"),
            contact_info: formData.get("contact_info") || null,
            logo_url: logoUrl,
            banner_url: bannerUrl,
            preview_image_1: previewUrls[0] || null,
            preview_image_2: previewUrls[1] || null,
            preview_image_3: previewUrls[2] || null,
            preview_image_4: previewUrls[3] || null,
            categories: checkedCategories.length > 0 ? checkedCategories.join(",") : null,
        };

        const res = await fetch("/api/storefronts", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-User-Id": user.id,
                "X-User-Role": user.role
            },
            body: JSON.stringify(payload)
        });

        const data = await res.json();

        if (!res.ok) {
            alert(data.error || "Failed to create storefront.");
            return;
        }

        window.location.href = "/storefronts/dashboard";

    } catch (err) {
        console.error("Error creating storefront:", err);
        alert("Something went wrong. Please try again.");
    }
});
