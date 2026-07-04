(() => {
  const params = new URLSearchParams(location.search);
  const nextUrl = params.get("next") || "/";
  const message = document.querySelector("#message");
  const form = document.querySelector("#apiKeyForm");
  const apiKeyInput = document.querySelector("#apiKeyInput");
  const googleLogin = document.querySelector("#googleLogin");

  function setMessage(text, kind = "") {
    message.textContent = text;
    message.className = `message ${kind}`.trim();
  }

  async function loadConfig() {
    try {
      const response = await fetch(`/auth/config?next=${encodeURIComponent(nextUrl)}`, { cache: "no-store" });
      if (!response.ok) throw new Error("Không tải được cấu hình đăng nhập.");
      const config = await response.json();
      if (!config.enabled) {
        location.href = nextUrl;
        return;
      }
      if (config.authenticated) {
        location.href = config.next || nextUrl;
        return;
      }
      if (config.providers.api_key) form.classList.remove("hidden");
      if (config.providers.google) {
        googleLogin.href = config.google_start_url;
        googleLogin.classList.remove("hidden");
      }
      if (!config.providers.api_key && !config.providers.google) {
        setMessage("Server đã bật auth nhưng chưa cấu hình provider đăng nhập hợp lệ.", "error");
      } else if (!config.providers.google && config.google_configured === false) {
        setMessage("Có thể đăng nhập bằng API key. Google chỉ hiện khi OAuth đã cấu hình đủ.", "");
      } else {
        setMessage("Chọn một phương thức đăng nhập.", "");
      }
    } catch (error) {
      setMessage(error.message || "Không thể tải cấu hình đăng nhập.", "error");
    }
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const apiKey = apiKeyInput.value.trim();
    if (!apiKey) {
      setMessage("Hãy nhập API key.", "error");
      apiKeyInput.focus();
      return;
    }
    setMessage("Đang đăng nhập...");
    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: apiKey, next: nextUrl }),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || `Đăng nhập lỗi HTTP ${response.status}.`);
      }
      const data = await response.json();
      localStorage.removeItem("voxLocalApiKey");
      localStorage.removeItem("voxApiKey");
      setMessage("Đăng nhập thành công.", "success");
      location.href = data.next || nextUrl;
    } catch (error) {
      setMessage(error.message || "Không thể đăng nhập.", "error");
    }
  });

  loadConfig();
})();
