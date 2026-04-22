(function () {
  const config = window.adminLoginConfig;
  const loginStatus = document.getElementById("loginStatus");
  const buttonContainer = document.getElementById("googleLoginButton");

  function showStatus(message, isError = false) {
    if (!loginStatus) {
      return;
    }

    loginStatus.hidden = false;
    loginStatus.textContent = message;
    loginStatus.classList.toggle("is-error", isError);
  }

  async function handleGoogleCredentialResponse(response) {
    showStatus("Loggar in...");

    try {
      const request = await fetch(config.loginUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "same-origin",
        body: JSON.stringify({
          credential: response.credential,
        }),
      });

      const payload = await request.json().catch(() => ({}));

      if (!request.ok) {
        throw new Error(payload.error || payload.message || "Kunde inte logga in");
      }

      window.location.assign("/admin");
    } catch (error) {
      showStatus(error.message || "Kunde inte logga in", true);
    }
  }

  function initializeGoogleLogin() {
    if (!window.google || !window.google.accounts || !buttonContainer) {
      window.setTimeout(initializeGoogleLogin, 150);
      return;
    }

    window.google.accounts.id.initialize({
      client_id: config.clientId,
      callback: handleGoogleCredentialResponse,
    });

    window.google.accounts.id.renderButton(buttonContainer, {
      theme: "outline",
      size: "large",
      shape: "pill",
      width: 320,
      text: "continue_with",
    });
  }

  if (config && config.clientId) {
    initializeGoogleLogin();
  }
})();
