(function () {
  const SIDEBAR_SCROLL_KEY = "sidebar.scrollTop";

  const sidebar = document.getElementById("sidebar");
  const sidebarInner = document.querySelector(".sidebar-inner");
  const tocPanel = document.getElementById("tocPanel");
  const backdrop = document.getElementById("mobileBackdrop");

  const openMenuButton = document.getElementById("openMenuButton");
  const openTocButton = document.getElementById("openTocButton");

  const menuSearchInput = document.getElementById("menuSearchInput");
  const searchableMenuLinks = Array.from(document.querySelectorAll("[data-search-item]"));

  const anchorLinks = Array.from(
    document.querySelectorAll('.menu-nav a[href^="#"], .toc-nav a[href^="#"]')
  );

  const desktopMedia = window.matchMedia("(min-width: 897px)");

  if (sidebarInner) {
    const savedScroll = localStorage.getItem(SIDEBAR_SCROLL_KEY);
    if (savedScroll !== null) {
      sidebarInner.scrollTop = Number(savedScroll);
    }

    window.addEventListener("beforeunload", () => {
      localStorage.setItem(SIDEBAR_SCROLL_KEY, String(sidebarInner.scrollTop));
    });
  }

  function isInputElement(element) {
    return !!element && /^(INPUT|TEXTAREA|SELECT)$/i.test(element.tagName);
  }

  function setButtonState(button, isExpanded) {
    if (!button) {
      return;
    }
    button.setAttribute("aria-expanded", String(isExpanded));
  }

  function updateBackdropAndBody() {
    const sidebarOpen = sidebar && sidebar.classList.contains("is-open");
    const tocOpen = tocPanel && tocPanel.classList.contains("is-open");
    const anyPanelOpen = sidebarOpen || tocOpen;

    if (backdrop) {
      backdrop.hidden = !anyPanelOpen;
    }

    document.body.classList.toggle("is-panel-open", anyPanelOpen);

    setButtonState(openMenuButton, !!sidebarOpen);
    setButtonState(openTocButton, !!tocOpen);
  }

  function closePanels() {
    if (sidebar) {
      sidebar.classList.remove("is-open");
    }

    if (tocPanel) {
      tocPanel.classList.remove("is-open");
    }

    updateBackdropAndBody();
  }

  function toggleSidebar() {
    if (!sidebar) {
      return;
    }

    const willOpen = !sidebar.classList.contains("is-open");
    sidebar.classList.toggle("is-open", willOpen);

    if (tocPanel && willOpen) {
      tocPanel.classList.remove("is-open");
    }

    updateBackdropAndBody();
  }

  function toggleToc() {
    if (!tocPanel) {
      return;
    }

    const willOpen = !tocPanel.classList.contains("is-open");
    tocPanel.classList.toggle("is-open", willOpen);

    if (sidebar && willOpen) {
      sidebar.classList.remove("is-open");
    }

    updateBackdropAndBody();
  }

  function setActiveAnchorLinks() {
    const hash = window.location.hash || "#valkommen-till-tullinge-gymnasium-datorklubb";

    anchorLinks.forEach((link) => {
      const isActive = link.getAttribute("href") === hash;
      link.classList.toggle("is-active", isActive);
    });
  }

  function filterMenuLinks() {
    if (!menuSearchInput) {
      return;
    }

    const searchTerm = menuSearchInput.value.trim().toLowerCase();

    searchableMenuLinks.forEach((link) => {
      const listItem = link.closest("li");
      if (!listItem) {
        return;
      }

      const label = link.textContent.trim().toLowerCase();
      const shouldShow = searchTerm.length === 0 || label.includes(searchTerm);
      listItem.hidden = !shouldShow;
    });
  }

  function focusSearchInputWithHotkey(event) {
    if (isInputElement(event.target)) {
      return;
    }

    if (event.key === "s" || event.key === "/") {
      event.preventDefault();
      if (menuSearchInput) {
        menuSearchInput.focus();
      }
    }
  }

  if (openMenuButton) {
    openMenuButton.addEventListener("click", toggleSidebar);
  }

  if (openTocButton) {
    openTocButton.addEventListener("click", toggleToc);
  }

  if (backdrop) {
    backdrop.addEventListener("click", closePanels);
  }

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closePanels();
      return;
    }

    focusSearchInputWithHotkey(event);
  });

  if (menuSearchInput) {
    menuSearchInput.addEventListener("input", filterMenuLinks);
  }

  window.addEventListener("hashchange", setActiveAnchorLinks);

  if (desktopMedia.matches) {
    closePanels();
  }

  desktopMedia.addEventListener("change", (event) => {
    if (event.matches) {
      closePanels();
    }
  });

  document.addEventListener("click", (event) => {
    const clickedAnchor = event.target.closest('a[href^="#"]');
    if (clickedAnchor) {
      closePanels();
    }
  });

  setActiveAnchorLinks();
})();
