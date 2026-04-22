(function () {
  const SIDEBAR_SCROLL_KEY = "sidebar.scrollTop";

  const sidebar = document.getElementById("sidebar");
  const sidebarInner = document.querySelector(".sidebar-inner");
  const backdrop = document.getElementById("mobileBackdrop");

  const openMenuButton = document.getElementById("openMenuButton");
  const mobileTitle = document.querySelector(".mobile-title");

  const menuSearchInput = document.getElementById("menuSearchInput");
  const menuSearchEmpty = document.getElementById("menuSearchEmpty");
  const searchableMenuLinks = Array.from(document.querySelectorAll("[data-search-item]"));
  const menuGroups = Array.from(document.querySelectorAll(".menu-group"));

  const anchorLinks = Array.from(
    document.querySelectorAll('.menu-nav a[href^="#"]')
  );
  const sectionTargets = Array.from(
    new Map(
      anchorLinks
        .map((link) => {
          const hash = link.getAttribute("href");
          const section = hash ? document.querySelector(hash) : null;
          return section ? [hash, section] : null;
        })
        .filter(Boolean)
    ).values()
  );

  const desktopMedia = window.matchMedia("(min-width: 897px)");
  const defaultHash = "#valkommen-till-tullinge-gymnasium-datorklubb";
  let currentHash = window.location.hash || defaultHash;
  let lastTrigger = null;

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

  function focusFirstInteractiveElement(container) {
    if (!container) {
      return;
    }

    const firstFocusable = container.querySelector('input, a[href], button:not([disabled])');
    if (firstFocusable) {
      firstFocusable.focus();
    }
  }

  function updateMobileTitle(hash) {
    if (!mobileTitle) {
      return;
    }

    if (!hash || hash === defaultHash) {
      mobileTitle.textContent = mobileTitle.dataset.defaultTitle || "Introduktion";
      return;
    }

    const section = hash ? document.querySelector(hash) : null;
    const title = section
      ? section.textContent.trim()
      : mobileTitle.dataset.defaultTitle || "Introduktion";

    mobileTitle.textContent = title;
  }

  function syncNavigationState(hash) {
    currentHash = hash || defaultHash;
    setActiveAnchorLinks();
    updateMobileTitle(currentHash);
  }

  function updateBackdropAndBody() {
    const sidebarOpen = sidebar && sidebar.classList.contains("is-open");
    const anyPanelOpen = sidebarOpen;

    if (backdrop) {
      backdrop.hidden = !anyPanelOpen;
    }

    document.body.classList.toggle("is-panel-open", anyPanelOpen);

    setButtonState(openMenuButton, !!sidebarOpen);
  }

  function closePanels({ restoreFocus = false } = {}) {
    if (sidebar) {
      sidebar.classList.remove("is-open");
    }

    updateBackdropAndBody();

    if (restoreFocus && lastTrigger) {
      lastTrigger.focus();
    }
  }

  function toggleSidebar() {
    if (!sidebar) {
      return;
    }

    const willOpen = !sidebar.classList.contains("is-open");
    sidebar.classList.toggle("is-open", willOpen);
    lastTrigger = openMenuButton;

    updateBackdropAndBody();

    if (willOpen) {
      focusFirstInteractiveElement(sidebar);
    }
  }

  function setActiveAnchorLinks() {
    anchorLinks.forEach((link) => {
      const isActive = link.getAttribute("href") === currentHash;
      link.classList.toggle("is-active", isActive);
    });
  }

  function filterMenuLinks() {
    if (!menuSearchInput) {
      return;
    }

    const searchTerm = menuSearchInput.value.trim().toLowerCase();
    let visibleLinkCount = 0;

    searchableMenuLinks.forEach((link) => {
      const listItem = link.closest("li");
      if (!listItem) {
        return;
      }

      const label = link.textContent.trim().toLowerCase();
      const shouldShow = searchTerm.length === 0 || label.includes(searchTerm);
      listItem.hidden = !shouldShow;

      if (shouldShow) {
        visibleLinkCount += 1;
      }
    });

    menuGroups.forEach((group) => {
      const hasVisibleLinks = Array.from(group.querySelectorAll("[data-search-item]")).some((link) => {
        const listItem = link.closest("li");
        return listItem && !listItem.hidden;
      });

      group.hidden = !hasVisibleLinks;
    });

    if (menuSearchEmpty) {
      menuSearchEmpty.hidden = visibleLinkCount > 0;
    }
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

  if (backdrop) {
    backdrop.addEventListener("click", () => closePanels({ restoreFocus: true }));
  }

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closePanels({ restoreFocus: true });
      return;
    }

    focusSearchInputWithHotkey(event);
  });

  if (menuSearchInput) {
    menuSearchInput.addEventListener("input", filterMenuLinks);
  }

  window.addEventListener("hashchange", () => {
    syncNavigationState(window.location.hash || defaultHash);
  });

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

  if ("IntersectionObserver" in window) {
    const visibleSections = new Map();
    const sectionObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            visibleSections.set(entry.target.id, Math.abs(entry.boundingClientRect.top));
          } else {
            visibleSections.delete(entry.target.id);
          }
        });

        const closestSection = Array.from(visibleSections.entries()).sort((a, b) => a[1] - b[1])[0];
        if (closestSection) {
          syncNavigationState(`#${closestSection[0]}`);
        }
      },
      {
        rootMargin: "-18% 0px -60% 0px",
        threshold: [0, 1]
      }
    );

    sectionTargets.forEach((section) => {
      sectionObserver.observe(section);
    });
  }

  syncNavigationState(currentHash);
})();
