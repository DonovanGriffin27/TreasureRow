// User-written values are escaped with escapeHtml/safeUrl (safe_html.js) - Donovan Griffin, Iteration 3

// USERS SECTION

/*
 * Fetch all users from backend and display them in table
 * Calls: GET /admin/users
 */
async function loadUsers() {
    const response = await fetch('/admin/users'); // API request
    const users = await response.json(); // Convert response to JSON

    const table = document.querySelector('#usersTable tbody');
    table.innerHTML = ""; // Clear existing rows

    // Loop through users and create table rows
    users.forEach(user => {
        const row = `
            <tr>
                <td>${escapeHtml(user.id)}</td>
                <td>${escapeHtml(user.username || "")}</td>
                <td>${escapeHtml(user.email)}</td>
                <td>${escapeHtml(user.role || "user")}</td>
                <td>${escapeHtml(user.created_at || "")}</td>
                <td>
                    <!-- Delete button calls deleteUser() -->
                    <button class="delete" onclick="deleteUser(${Number(user.id)})">Delete</button>
                </td>
            </tr>
        `;
        table.innerHTML += row;
    });
}

/*
 * Delete a user by ID
 * Calls: DELETE /admin/users/<id>
 */
async function deleteUser(userId) {
    await fetch(`/admin/users/${userId}`, {
        method: 'DELETE'
    });

    // Reload users after deletion
    loadUsers();
}


// LISTINGS SECTION

/*
 * Fetch all listings and display them
 * Calls: GET /admin/listings
 */
async function loadListings() {
    const response = await fetch('/admin/listings');
    const listings = await response.json();

    const table = document.querySelector('#listingsTable tbody');
    table.innerHTML = "";

    listings.forEach(listing => {
        const row = `
            <tr>
                <td>${escapeHtml(listing.id)}</td>
                <td>${escapeHtml(listing.storefront_id)}</td>
                <td>${escapeHtml(listing.title)}</td>
                <td>${escapeHtml(listing.price)}</td>
                <td>${escapeHtml(listing.quantity_on_hand)}</td>
                <td>${escapeHtml(listing.status || "ACTIVE")}</td>
                <td>${escapeHtml(listing.fulfillment_type || "")}</td>
                <td>${escapeHtml(listing.created_at || "")}</td>
                <td>
                    <button class="delete" onclick="deleteListing(${Number(listing.id)})">Delete</button>
                </td>
            </tr>
        `;
        table.innerHTML += row;
    });
}

/*
 * Delete a listing by ID
 * Calls: DELETE /admin/listings/<id>
 */
async function deleteListing(listingId) {
    await fetch(`/admin/listings/${listingId}`, {
        method: 'DELETE'
    });

    // Reload listings after deletion
    loadListings();
}


// STOREFRONTS SECTION

/*
 * Fetch all storefronts
 * Calls: GET /admin/storefronts
 */
async function loadStorefronts() {
    const response = await fetch('/admin/storefronts');
    const stores = await response.json();

    const table = document.querySelector('#storefrontsTable tbody');
    table.innerHTML = "";

    stores.forEach(store => {
        const row = `
            <tr>
                <td>${escapeHtml(store.id)}</td>
                <td>${escapeHtml(store.brand_name || store.name || "")}</td>
                <td>${escapeHtml(store.owner_id)}</td>
                <td>
                    <!-- Delete storefront button -->
                    <button class="delete" onclick="deleteStorefront(${Number(store.id)})">Delete</button>
                </td>
            </tr>
        `;
        table.innerHTML += row;
    });
}

/*
 * Delete a storefront by ID
 * Calls: DELETE /admin/storefronts/<id>
 */
async function deleteStorefront(storeId) {
    await fetch(`/admin/storefronts/${storeId}`, {
        method: 'DELETE'
    });

    // Reload storefronts after deletion
    loadStorefronts();
}


// RETURNS SECTION

async function loadReturns() {
    const response = await fetch('/admin/returns');
    const returns = await response.json();

    const table = document.querySelector('#returnsTable tbody');
    table.innerHTML = "";

    returns.forEach(item => {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${escapeHtml(item.id)}</td>
            <td>${escapeHtml(item.username || "")}<br><small>${escapeHtml(item.email || "")}</small></td>
            <td>${escapeHtml(item.order_number)}</td>
            <td>${escapeHtml(item.has_damage ? "Yes" : "No")}</td>
            <td>${item.damage_image_url ? `<a href="${safeUrl(item.damage_image_url)}" target="_blank" rel="noopener noreferrer">View</a>` : "—"}</td>
            <td>
                <select data-return-id="${Number(item.id)}">
                    <option value="pending" ${item.status === "pending" ? "selected" : ""}>Pending</option>
                    <option value="reviewed" ${item.status === "reviewed" ? "selected" : ""}>Reviewed</option>
                    <option value="resolved" ${item.status === "resolved" ? "selected" : ""}>Resolved</option>
                </select>
                <button onclick="saveReturnStatus(${Number(item.id)})">Save</button>
            </td>
            <td>${escapeHtml(item.reason)}</td>
        `;
        table.appendChild(row);
    });
}

async function saveReturnStatus(returnId) {
    const select = document.querySelector(`select[data-return-id="${returnId}"]`);
    if (!select) return;

    const response = await fetch(`/admin/returns/${returnId}`, {
        method: "PATCH",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ status: select.value })
    });

    if (!response.ok) {
        alert("Failed to update return status.");
        return;
    }

    loadReturns();
}


// ---------------- Treasure Tokens (admin) - Donovan Griffin, Iteration 3 ----------------

async function loadWallets() {
    const res = await fetch("/admin/wallets");
    const data = await res.json();
    const table = document.querySelector("#walletsTable tbody");
    table.innerHTML = "";

    data.forEach(w => {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${escapeHtml(w.user_id)}</td>
            <td>${escapeHtml(w.username || "")}</td>
            <td>${escapeHtml(w.email || "")}</td>
            <td>${w.balance === null ? "No wallet yet" : escapeHtml(Number(w.balance).toFixed(2))}</td>
            <td>
                <input type="number" min="0.01" max="10000" step="0.01" placeholder="Amount" style="width:90px;">
                <input type="text" maxlength="200" placeholder="Note (optional)" style="width:140px;">
                <button type="button">Grant</button>
            </td>`;
        const [amountInput, noteInput] = row.querySelectorAll("input");
        row.querySelector("button").addEventListener("click", () => grantTokens(w.user_id, amountInput.value, noteInput.value));
        table.appendChild(row);
    });
}

async function grantTokens(userId, amount, note) {
    const response = await fetch(`/admin/wallets/${Number(userId)}/grant`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ amount, note }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        alert(data.error || "Could not grant tokens.");
        return;
    }
    alert(`Granted ${Number(data.granted).toFixed(2)} TT. New balance: ${Number(data.balance).toFixed(2)} TT.`);
    loadWallets();
}

async function loadEscrow() {
    const res = await fetch("/admin/escrow");
    const data = await res.json();
    const table = document.querySelector("#escrowTable tbody");
    table.innerHTML = "";

    data.forEach(e => {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${escapeHtml(e.escrow_id)}</td>
            <td>${escapeHtml(e.confirmation_number)}</td>
            <td>${escapeHtml(e.buyer)}</td>
            <td>${escapeHtml(e.seller)}</td>
            <td>${escapeHtml(Number(e.amount).toFixed(2))}</td>
            <td>${escapeHtml(e.status)}</td>
            <td>${escapeHtml(e.failed_attempts)}</td>
            <td><button type="button" class="delete">Refund buyer</button></td>`;
        row.querySelector("button").addEventListener("click", () => refundEscrow(e.escrow_id, e.amount));
        table.appendChild(row);
    });
}

async function refundEscrow(escrowId, amount) {
    if (!confirm(`Refund ${Number(amount).toFixed(2)} TT to the buyer and cancel this pickup?`)) return;
    const response = await fetch(`/admin/escrow/${Number(escrowId)}/refund`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason: "Refunded by admin" }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        alert(data.error || "Could not refund.");
        return;
    }
    loadEscrow();
}
