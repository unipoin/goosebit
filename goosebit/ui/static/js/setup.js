const setupForm = document.getElementById("setup_form");
const setupError = document.getElementById("setup_error");

function showSetupError(message) {
    setupError.textContent = message;
    setupError.classList.remove("d-none");
}

async function setup() {
    const formData = new FormData(setupForm);

    // FormData values are only accessible via get(), not as properties
    if (formData.get("password") !== formData.get("password_confirm")) {
        showSetupError("Passwords do not match.");
        return;
    }

    try {
        const response = await fetch("/setup", {
            method: "POST",
            body: formData,
        });

        // the server redirects to the login page once a user exists
        if (response.redirected) {
            window.location.assign(response.url);
            return;
        }

        if (!response.ok) {
            showSetupError("Setup failed. Please try again.");
            return;
        }

        const tokenData = await response.json();
        document.cookie = `session_id=${tokenData.access_token}; path=/`;
        window.location.assign("/");
    } catch (e) {
        console.error(e);
        showSetupError("Network error. Please try again.");
    }
}

setupForm.addEventListener("submit", (event) => {
    event.preventDefault();
    setupError.classList.add("d-none");
    setup();
});
