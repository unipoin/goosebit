// fix for datatable alignment issues with numbers
DataTable.type("num", "className", "");
DataTable.type("date", "className", "");
DataTable.type("datetime", "className", "");
DataTable.defaults.lengthMenu = [10, 25, 50, 100, { label: "All", value: -1 }];

// Escape a value for insertion into HTML. DataTables and innerHTML do not escape on their own, and many
// displayed values (device id, name, versions, hardware) are controlled by devices or users.
function escapeHtml(value) {
    if (value === null || value === undefined) {
        return "";
    }
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

// Default DataTables renderer: plain text with "-" as placeholder, escaped only for display
function renderText(data, type) {
    const value = data || "-";
    return type === "display" ? escapeHtml(value) : value;
}

function secondsToRecentDate(t) {
    if (t == null) {
        return null;
    }
    const time = Number(t);
    const d = Math.floor(time / 86400);
    const h = Math.floor((time % 86400) / 3600);
    const m = Math.floor(((time % 86400) % 3600) / 60);
    const s = Math.floor(((time % 86400) % 3600) % 60);

    if (d > 0) {
        return `${d}d`;
    }
    if (h > 0) {
        return `${h}h`;
    }
    if (m > 0) {
        return `${m}m`;
    }
    return `${s}s`;
}

async function updateSoftwareSelection(devices = null) {
    try {
        const url = new URL("/ui/bff/software", window.location.origin);
        if (devices != null) {
            for (const device of devices) {
                url.searchParams.append("ids", device.id);
            }
        }
        const response = await fetch(url.toString(), {
            method: "QUERY",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ order: [{ name: "version", dir: "desc" }] }),
        });
        if (!response.ok) {
            console.error("Retrieving software list failed.");
            return;
        }
        const data = (await response.json()).data;
        const selectElem = document.getElementById("selected-sw");
        selectElem.innerHTML = "";

        for (const item of data) {
            const optionElem = document.createElement("option");
            optionElem.value = item.id;
            optionElem.textContent = `${item.version}`;
            const models = [
                ...new Set(
                    item.compatibility.map((item) => (item.revision ? `${item.model} - ${item.revision}` : item.model)),
                ),
            ];
            optionElem.textContent = `${item.version} (${models})`;
            selectElem.appendChild(optionElem);
        }
        $("#selected-sw").selectpicker("destroy");
        if (data.length === 0) {
            selectElem.title = "No valid software found for selected device";
            if (devices != null) {
                if (devices.length > 1) {
                    selectElem.title += "s";
                }
            }
            selectElem.disabled = true;
        } else {
            selectElem.disabled = false;
            selectElem.title = "Select Software";
        }
        $("#selected-sw").selectpicker();
    } catch (error) {
        console.error("Failed to fetch device data:", error);
    }
}

async function get_request(url) {
    const response = await fetch(url, {
        method: "GET",
    });

    const result = await response.json();
    if (!response.ok) {
        if (result.detail) {
            Swal.fire({
                title: "Warning",
                text: result.detail,
                icon: "warning",
                confirmButtonText: "Understood",
                theme: "bootstrap-5",
            });
        }

        // do not include the request body: it may contain credentials (e.g. user passwords)
        throw new Error(`GET ${url} failed with status ${response.status}`);
    }
    return result;
}
async function post_request(url, object) {
    const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(object),
    });

    if (!response.ok) {
        const result = await response.json();
        if (result.detail) {
            Swal.fire({
                title: "Warning",
                text: result.detail,
                icon: "warning",
                confirmButtonText: "Understood",
                theme: "bootstrap-5",
            });
        }

        // do not include the request body: it may contain credentials (e.g. user passwords)
        throw new Error(`POST ${url} failed with status ${response.status}`);
    }
}
async function put_request(url, object) {
    const response = await fetch(url, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(object),
    });

    if (!response.ok) {
        const result = await response.json();
        if (result.detail) {
            Swal.fire({
                title: "Warning",
                text: result.detail,
                icon: "warning",
                confirmButtonText: "Understood",
                theme: "bootstrap-5",
            });
        }

        // do not include the request body: it may contain credentials (e.g. user passwords)
        throw new Error(`PUT ${url} failed with status ${response.status}`);
    }
}
async function patch_request(url, object) {
    const response = await fetch(url, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(object),
    });

    if (!response.ok) {
        const result = await response.json();
        if (result.detail) {
            Swal.fire({
                title: "Warning",
                text: result.detail,
                icon: "warning",
                confirmButtonText: "Understood",
                theme: "bootstrap-5",
            });
        }

        // do not include the request body: it may contain credentials (e.g. user passwords)
        throw new Error(`PATCH ${url} failed with status ${response.status}`);
    }
}
async function delete_request(url, object) {
    const response = await fetch(url, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(object),
    });

    if (!response.ok) {
        const result = await response.json();
        if (result.detail) {
            Swal.fire({
                title: "Warning",
                text: result.detail,
                icon: "warning",
                confirmButtonText: "Understood",
                theme: "bootstrap-5",
            });
        }

        // do not include the request body: it may contain credentials (e.g. user passwords)
        throw new Error(`DELETE ${url} failed with status ${response.status}`);
    }
}
function createColumnFooter() {
    const inputGroup = document.createElement("div");
    inputGroup.className = "input-group input-group-sm";
    inputGroup.style.width = "100%";

    const input = document.createElement("input");
    input.type = "text";
    input.placeholder = "-";
    input.className = "form-control form-control-sm";
    input.disabled = true;

    const iconSpan = document.createElement("span");
    iconSpan.className = "input-group-text";
    iconSpan.innerHTML = '<i class="bi bi-ban"></i>';

    inputGroup.appendChild(iconSpan);
    inputGroup.appendChild(input);
    return inputGroup;
}
