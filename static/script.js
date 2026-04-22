(function () {
  const SIDEBAR_SCROLL_KEY = "sidebar.scrollTop";
  const FOCUSABLE_SELECTOR = [
    "a[href]",
    "button:not([disabled])",
    "input:not([disabled])",
    "select:not([disabled])",
    "textarea:not([disabled])",
    "[tabindex]:not([tabindex='-1'])"
  ].join(", ");

  const sidebar = document.getElementById("sidebar");
  const sidebarInner = document.querySelector(".sidebar-inner");
  const backdrop = document.getElementById("mobileBackdrop");
  const openMenuButton = document.getElementById("openMenuButton");
  const mobileTitle = document.querySelector(".mobile-title");
  const mainContent = document.getElementById("mainContent");

  const menuSearchInput = document.getElementById("menuSearchInput");
  const menuSearchEmpty = document.getElementById("menuSearchEmpty");
  const searchableMenuLinks = Array.from(document.querySelectorAll("[data-search-item]"));
  const menuGroups = Array.from(document.querySelectorAll(".menu-group"));
  const anchorLinks = Array.from(document.querySelectorAll('.menu-nav a[href^="#"]'));

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

  const desktopMedia = window.matchMedia("(min-width: 56.0625rem)");
  const canUseInert = "inert" in document.createElement("div");
  const defaultHash = "#valkommen-till-tullinge-gymnasium-datorklubb";
  let currentHash = window.location.hash || defaultHash;
  let lastTrigger = null;

  function isInputElement(element) {
    return !!element && /^(INPUT|TEXTAREA|SELECT)$/i.test(element.tagName);
  }

  function isVisible(element) {
    return !!element && !element.hidden && element.getClientRects().length > 0;
  }

  function isDrawerOpen() {
    return !!sidebar && sidebar.classList.contains("is-open");
  }

  function setButtonState(button, isExpanded) {
    if (!button) {
      return;
    }

    button.setAttribute("aria-expanded", String(isExpanded));
  }

  function getFocusableElements(container) {
    if (!container) {
      return [];
    }

    return Array.from(container.querySelectorAll(FOCUSABLE_SELECTOR)).filter(isVisible);
  }

  function focusFirstInteractiveElement(container) {
    const [firstFocusable] = getFocusableElements(container);
    if (firstFocusable) {
      firstFocusable.focus();
    }
  }

  function setMainContentInteractivity(isDisabled) {
    if (!mainContent || desktopMedia.matches) {
      if (mainContent && canUseInert) {
        mainContent.inert = false;
      }
      if (mainContent) {
        mainContent.removeAttribute("aria-hidden");
      }
      return;
    }

    if (canUseInert) {
      mainContent.inert = isDisabled;
    }

    if (isDisabled) {
      mainContent.setAttribute("aria-hidden", "true");
    } else {
      mainContent.removeAttribute("aria-hidden");
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

    const section = document.querySelector(hash);
    mobileTitle.textContent = section
      ? section.textContent.trim()
      : mobileTitle.dataset.defaultTitle || "Introduktion";
  }

  function setActiveAnchorLinks() {
    anchorLinks.forEach((link) => {
      const isActive = link.getAttribute("href") === currentHash;
      link.classList.toggle("is-active", isActive);
      if (isActive) {
        link.setAttribute("aria-current", "true");
      } else {
        link.removeAttribute("aria-current");
      }
    });
  }

  function syncNavigationState(hash) {
    currentHash = hash || defaultHash;
    setActiveAnchorLinks();
    updateMobileTitle(currentHash);
  }

  function updateBackdropAndBody() {
    const drawerOpen = isDrawerOpen();

    if (backdrop) {
      backdrop.hidden = !drawerOpen;
    }

    document.body.classList.toggle("is-panel-open", drawerOpen);
    setButtonState(openMenuButton, drawerOpen);
    setMainContentInteractivity(drawerOpen);
  }

  function closePanels(options = {}) {
    const { restoreFocus = false } = options;

    if (sidebar) {
      sidebar.classList.remove("is-open");
    }

    updateBackdropAndBody();

    if (restoreFocus && lastTrigger) {
      lastTrigger.focus();
    }
  }

  function openSidebar() {
    if (!sidebar) {
      return;
    }

    sidebar.classList.add("is-open");
    updateBackdropAndBody();
    focusFirstInteractiveElement(sidebar);
  }

  function toggleSidebar() {
    if (!sidebar) {
      return;
    }

    lastTrigger = openMenuButton;

    if (isDrawerOpen()) {
      closePanels({ restoreFocus: true });
      return;
    }

    openSidebar();
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

  function focusSearchInput() {
    if (!menuSearchInput) {
      return;
    }

    if (desktopMedia.matches) {
      menuSearchInput.focus();
      menuSearchInput.select();
      return;
    }

    if (!isDrawerOpen()) {
      lastTrigger = openMenuButton;
      openSidebar();
    }

    window.requestAnimationFrame(() => {
      menuSearchInput.focus();
      menuSearchInput.select();
    });
  }

  function focusSearchInputWithHotkey(event) {
    if (isInputElement(event.target) || event.metaKey || event.ctrlKey || event.altKey) {
      return;
    }

    if (event.key === "s" || event.key === "/") {
      event.preventDefault();
      focusSearchInput();
    }
  }

  function trapFocusWithinSidebar(event) {
    if (desktopMedia.matches || !isDrawerOpen() || event.key !== "Tab") {
      return;
    }

    const focusableElements = getFocusableElements(sidebar);
    if (focusableElements.length === 0) {
      event.preventDefault();
      return;
    }

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    if (event.shiftKey && document.activeElement === firstElement) {
      event.preventDefault();
      lastElement.focus();
      return;
    }

    if (!event.shiftKey && document.activeElement === lastElement) {
      event.preventDefault();
      firstElement.focus();
    }
  }

  function restoreSidebarScroll() {
    if (!sidebarInner) {
      return;
    }

    try {
      const savedScroll = localStorage.getItem(SIDEBAR_SCROLL_KEY);
      if (savedScroll !== null) {
        sidebarInner.scrollTop = Number(savedScroll);
      }
    } catch (error) {
      return;
    }
  }

  function persistSidebarScroll() {
    if (!sidebarInner) {
      return;
    }

    try {
      localStorage.setItem(SIDEBAR_SCROLL_KEY, String(sidebarInner.scrollTop));
    } catch (error) {
      return;
    }
  }

  restoreSidebarScroll();
  window.addEventListener("beforeunload", persistSidebarScroll);

  if (openMenuButton) {
    openMenuButton.addEventListener("click", toggleSidebar);
  }

  if (backdrop) {
    backdrop.addEventListener("click", () => closePanels({ restoreFocus: true }));
  }

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && isDrawerOpen()) {
      closePanels({ restoreFocus: true });
      return;
    }

    trapFocusWithinSidebar(event);
    focusSearchInputWithHotkey(event);
  });

  if (menuSearchInput) {
    menuSearchInput.addEventListener("input", filterMenuLinks);
  }

  window.addEventListener("hashchange", () => {
    syncNavigationState(window.location.hash || defaultHash);
  });

  desktopMedia.addEventListener("change", (event) => {
    if (event.matches) {
      closePanels();
      return;
    }

    updateBackdropAndBody();
  });

  document.addEventListener("click", (event) => {
    const clickedSidebarLink = event.target.closest("#sidebar a[href]");
    if (clickedSidebarLink && !desktopMedia.matches) {
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
        rootMargin: "-18% 0px -55% 0px",
        threshold: [0, 1]
      }
    );

    sectionTargets.forEach((section) => {
      sectionObserver.observe(section);
    });
  }

  syncNavigationState(currentHash);
  updateBackdropAndBody();
})();
