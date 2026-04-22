(function () {
  const config = window.adminAppConfig;
  const saveStatus = document.getElementById("saveStatus");
  const saveButton = document.getElementById("saveContentButton");

  let loadedContent = null;

  function formatDate(value) {
    if (!value) {
      return "Okänd tid";
    }

    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
      return value;
    }

    return parsed.toLocaleString("sv-SE");
  }

  function showStatus(message, isError = false) {
    if (!saveStatus) {
      return;
    }

    saveStatus.textContent = message;
    saveStatus.classList.toggle("is-error", isError);
  }

  function withCsrfHeaders(headers = {}) {
    return {
      ...headers,
      "X-CSRF-Token": config.csrfToken,
    };
  }

  function createFromTemplate(templateId) {
    const template = document.getElementById(templateId);
    return template.content.firstElementChild.cloneNode(true);
  }

  function setValue(id, value) {
    const element = document.getElementById(id);
    if (element) {
      element.value = value ?? "";
    }
  }

  function getValue(id) {
    const element = document.getElementById(id);
    return element ? element.value.trim() : "";
  }

  function clearChildren(container) {
    if (container) {
      container.innerHTML = "";
    }
  }

  function wireStandardRemover(element) {
    const removeButton = element.querySelector('[data-action="remove-item"]');
    if (removeButton) {
      removeButton.addEventListener("click", () => {
        element.remove();
      });
    }
  }

  function createTextListItem(value = "") {
    const element = createFromTemplate("textListItemTemplate");
    element.querySelector('[data-field="value"]').value = value;
    wireStandardRemover(element);
    return element;
  }

  function renderTextList(containerId, values) {
    const container = document.getElementById(containerId);
    clearChildren(container);
    values.forEach((value) => container.append(createTextListItem(value)));
  }

  function collectTextList(containerId) {
    const container = document.getElementById(containerId);
    return Array.from(container.querySelectorAll('[data-field="value"]'))
      .map((field) => field.value.trim())
      .filter(Boolean);
  }

  function createLinkItem(item = {}, options = {}) {
    const element = createFromTemplate("linkItemTemplate");
    element.querySelector('[data-field="label"]').value = item.label || "";
    element.querySelector('[data-field="href"]').value = item.href || "";

    const primaryField = element.querySelector('[data-field="primary"]');
    const primaryLabel = primaryField.closest("label");

    if (options.showPrimary) {
      primaryField.checked = Boolean(item.primary);
    } else {
      primaryField.checked = false;
      primaryLabel.hidden = true;
    }

    wireStandardRemover(element);
    return element;
  }

  function renderLinkList(containerId, items, options = {}) {
    const container = document.getElementById(containerId);
    clearChildren(container);
    items.forEach((item) => container.append(createLinkItem(item, options)));
  }

  function collectLinkList(containerId, options = {}) {
    const container = document.getElementById(containerId);

    return Array.from(container.children).map((element) => {
      const primaryField = element.querySelector('[data-field="primary"]');

      return {
        label: element.querySelector('[data-field="label"]').value.trim(),
        href: element.querySelector('[data-field="href"]').value.trim(),
        primary: options.showPrimary ? Boolean(primaryField.checked) : false,
      };
    }).filter((item) => item.label || item.href);
  }

  function createCardItem(item = {}) {
    const element = createFromTemplate("cardItemTemplate");
    element.querySelector('[data-field="kicker"]').value = item.kicker || "";
    element.querySelector('[data-field="title"]').value = item.title || "";
    element.querySelector('[data-field="text"]').value = item.text || "";
    element.querySelector('[data-field="href"]').value = item.href || "";
    wireStandardRemover(element);
    return element;
  }

  function renderCardList(containerId, items) {
    const container = document.getElementById(containerId);
    clearChildren(container);
    items.forEach((item) => container.append(createCardItem(item)));
  }

  function collectCardList(containerId) {
    const container = document.getElementById(containerId);

    return Array.from(container.children).map((element) => ({
      kicker: element.querySelector('[data-field="kicker"]').value.trim(),
      title: element.querySelector('[data-field="title"]').value.trim(),
      text: element.querySelector('[data-field="text"]').value.trim(),
      href: element.querySelector('[data-field="href"]').value.trim(),
    })).filter((item) => item.title || item.text || item.href || item.kicker);
  }

  function createNavigationItem(item = {}) {
    const element = createFromTemplate("navigationItemTemplate");
    element.querySelector('[data-field="label"]').value = item.label || "";
    element.querySelector('[data-field="href"]').value = item.href || "";
    wireStandardRemover(element);
    return element;
  }

  function createNavigationGroup(group = {}) {
    const element = createFromTemplate("navigationGroupTemplate");
    const itemsContainer = element.querySelector('[data-role="items"]');

    element.querySelector('[data-field="label"]').value = group.label || "";
    wireStandardRemover(element);

    const addButton = element.querySelector('[data-action="add-navigation-item"]');
    addButton.addEventListener("click", () => {
      itemsContainer.append(createNavigationItem({ label: "", href: "" }));
    });

    (group.items || []).forEach((item) => itemsContainer.append(createNavigationItem(item)));
    return element;
  }

  function renderNavigationGroups(groups) {
    const container = document.getElementById("navigationGroups");
    clearChildren(container);
    groups.forEach((group) => container.append(createNavigationGroup(group)));
  }

  function collectNavigationGroups() {
    const container = document.getElementById("navigationGroups");

    return Array.from(container.children).map((groupElement) => ({
      label: groupElement.querySelector('[data-field="label"]').value.trim(),
      items: Array.from(groupElement.querySelector('[data-role="items"]').children).map((itemElement) => ({
        label: itemElement.querySelector('[data-field="label"]').value.trim(),
        href: itemElement.querySelector('[data-field="href"]').value.trim(),
      })).filter((item) => item.label || item.href),
    })).filter((group) => group.label || group.items.length > 0);
  }

  function createSystemItem(item = {}) {
    const element = createFromTemplate("systemItemTemplate");
    element.querySelector('[data-field="repo_label"]').value = item.repo_label || "";
    element.querySelector('[data-field="repo_url"]').value = item.repo_url || "";
    element.querySelector('[data-field="description"]').value = item.description || "";
    element.querySelector('[data-field="site_label"]').value = item.site_label || "";
    element.querySelector('[data-field="site_url"]').value = item.site_url || "";
    wireStandardRemover(element);
    return element;
  }

  function renderSystemList(items) {
    const container = document.getElementById("programmingSystems");
    clearChildren(container);
    items.forEach((item) => container.append(createSystemItem(item)));
  }

  function collectSystemList() {
    const container = document.getElementById("programmingSystems");

    return Array.from(container.children).map((element) => ({
      repo_label: element.querySelector('[data-field="repo_label"]').value.trim(),
      repo_url: element.querySelector('[data-field="repo_url"]').value.trim(),
      description: element.querySelector('[data-field="description"]').value.trim(),
      site_label: element.querySelector('[data-field="site_label"]').value.trim(),
      site_url: element.querySelector('[data-field="site_url"]').value.trim(),
    })).filter((item) => item.repo_label || item.repo_url || item.site_url);
  }

  function createVideoItem(item = {}) {
    const element = createFromTemplate("videoItemTemplate");
    element.querySelector('[data-field="title"]').value = item.title || "";
    element.querySelector('[data-field="embed_url"]').value = item.embed_url || "";
    wireStandardRemover(element);
    return element;
  }

  function renderVideoList(items) {
    const container = document.getElementById("minecraftVideos");
    clearChildren(container);
    items.forEach((item) => container.append(createVideoItem(item)));
  }

  function collectVideoList() {
    const container = document.getElementById("minecraftVideos");

    return Array.from(container.children).map((element) => ({
      title: element.querySelector('[data-field="title"]').value.trim(),
      embed_url: element.querySelector('[data-field="embed_url"]').value.trim(),
    })).filter((item) => item.title || item.embed_url);
  }

  function createBoardMember(item = {}) {
    const element = createFromTemplate("boardMemberTemplate");
    element.querySelector('[data-field="name"]').value = item.name || "";
    element.querySelector('[data-field="details"]').value = item.details || "";
    element.querySelector('[data-field="role"]').value = item.role || "";
    wireStandardRemover(element);
    return element;
  }

  function renderBoardMembers(items) {
    const container = document.getElementById("boardMembers");
    clearChildren(container);
    items.forEach((item) => container.append(createBoardMember(item)));
  }

  function collectBoardMembers() {
    const container = document.getElementById("boardMembers");

    return Array.from(container.children).map((element) => ({
      name: element.querySelector('[data-field="name"]').value.trim(),
      details: element.querySelector('[data-field="details"]').value.trim(),
      role: element.querySelector('[data-field="role"]').value.trim(),
    })).filter((item) => item.name || item.role || item.details);
  }

  function createDocumentEntry(item = {}) {
    const element = createFromTemplate("documentEntryTemplate");
    element.dataset.itemType = "document-entry";
    element.querySelector('[data-field="label"]').value = item.label || "";
    element.querySelector('[data-field="url"]').value = item.url || "";
    wireStandardRemover(element);
    return element;
  }

  function createDocumentEvent(item = {}) {
    const element = createFromTemplate("documentEventTemplate");
    const itemsContainer = element.querySelector('[data-role="items"]');

    element.dataset.itemType = "document-event";
    element.querySelector('[data-field="date_label"]').value = item.date_label || "";
    element.querySelector('[data-field="title"]').value = item.title || "";
    wireStandardRemover(element);

    element.querySelector('[data-action="add-document-entry"]').addEventListener("click", () => {
      itemsContainer.append(createDocumentEntry({ label: "", url: "" }));
    });

    (item.items || []).forEach((entry) => itemsContainer.append(createDocumentEntry(entry)));
    return element;
  }

  function createDocumentYear(item = {}) {
    const element = createFromTemplate("documentYearTemplate");
    const eventsContainer = element.querySelector('[data-role="events"]');

    element.dataset.itemType = "document-year";
    element.querySelector('[data-field="year"]').value = item.year || "";
    wireStandardRemover(element);

    element.querySelector('[data-action="add-document-event"]').addEventListener("click", () => {
      eventsContainer.append(createDocumentEvent({ date_label: "", title: "", items: [] }));
    });

    (item.events || []).forEach((event) => eventsContainer.append(createDocumentEvent(event)));
    return element;
  }

  function renderDocumentYears(items) {
    const container = document.getElementById("documentYears");
    clearChildren(container);
    items.forEach((item) => container.append(createDocumentYear(item)));
  }

  function collectDocumentYears() {
    const container = document.getElementById("documentYears");

    return Array.from(container.children).map((yearElement) => ({
      year: yearElement.querySelector('[data-field="year"]').value.trim(),
      events: Array.from(yearElement.querySelector('[data-role="events"]').children).map((eventElement) => ({
        date_label: eventElement.querySelector('[data-field="date_label"]').value.trim(),
        title: eventElement.querySelector('[data-field="title"]').value.trim(),
        items: Array.from(eventElement.querySelector('[data-role="items"]').children).map((entryElement) => ({
          label: entryElement.querySelector('[data-field="label"]').value.trim(),
          url: entryElement.querySelector('[data-field="url"]').value.trim(),
        })).filter((entry) => entry.label || entry.url),
      })).filter((event) => event.date_label || event.title || event.items.length > 0),
    })).filter((year) => year.year || year.events.length > 0);
  }

  function createAdminEmailItem(email) {
    const element = createFromTemplate("adminEmailTemplate");
    element.dataset.email = email;
    element.querySelector('[data-field="email"]').textContent = email;

    element.querySelector('[data-action="remove-admin"]').addEventListener("click", async () => {
      if (!window.confirm(`Ta bort adminkontot ${email}?`)) {
        return;
      }

      try {
        const request = await fetch(config.adminsUrl, {
          method: "DELETE",
          headers: withCsrfHeaders({
            "Content-Type": "application/json",
          }),
          credentials: "same-origin",
          body: JSON.stringify({ email }),
        });

        const payload = await request.json();
        if (!request.ok) {
          throw new Error(payload.error || payload.message || "Kunde inte ta bort admin");
        }

        renderAdminEmails(payload.emails || []);
      } catch (error) {
        showStatus(error.message || "Kunde inte ta bort admin", true);
      }
    });

    return element;
  }

  function renderAdminEmails(emails) {
    const container = document.getElementById("adminEmailList");
    clearChildren(container);
    emails.forEach((email) => container.append(createAdminEmailItem(email)));
  }

  function createHistoryItem(item) {
    const element = createFromTemplate("historyItemTemplate");
    const title = element.querySelector('[data-field="title"]');
    const subtitle = element.querySelector('[data-field="subtitle"]');
    const actor = item.actor_name || item.actor_email || "Okänd användare";
    const reason = item.reason && item.reason.startsWith("restore:") ? "Återställd version" : "Sparad version";

    title.textContent = `${reason} ${formatDate(item.created_at)}`;
    subtitle.textContent = `${actor}`;

    element.querySelector('[data-action="restore-history"]').addEventListener("click", async () => {
      if (!window.confirm("Återställa den här versionen? Nuvarande innehåll sparas också i historiken.")) {
        return;
      }

      try {
        showStatus("Återställer tidigare version...");
        const request = await fetch(config.restoreHistoryUrl, {
          method: "POST",
          headers: withCsrfHeaders({
            "Content-Type": "application/json",
          }),
          credentials: "same-origin",
          body: JSON.stringify({ backup_id: item.id }),
        });

        const payload = await request.json();
        if (!request.ok) {
          throw new Error(payload.error || payload.message || "Kunde inte återställa versionen");
        }

        populateForm(payload.content);
        await loadHistory();
        showStatus("Versionen har återställts.");
      } catch (error) {
        showStatus(error.message || "Kunde inte återställa versionen", true);
      }
    });

    return element;
  }

  function renderHistory(items) {
    const container = document.getElementById("historyList");
    clearChildren(container);

    if (!items.length) {
      container.append(createTextListItem("Ingen historik ännu. Den första sparningen skapar en återställningsbar version."));
      const placeholder = container.lastElementChild;
      const textarea = placeholder.querySelector('[data-field="value"]');
      textarea.readOnly = true;
      placeholder.querySelector('[data-action="remove-item"]').remove();
      return;
    }

    items.forEach((item) => container.append(createHistoryItem(item)));
  }

  function populateForm(content) {
    loadedContent = content;

    setValue("siteName", content.site.site_name);
    setValue("pageTitle", content.site.page_title);
    setValue("mobileDefaultTitle", content.site.mobile_default_title);
    setValue("metaDescription", content.site.meta_description);
    setValue("themeColor", content.site.theme_color);
    setValue("siteEyebrow", content.site.eyebrow);

    setValue("sidebarStartKicker", content.sidebar.start_card.kicker);
    setValue("sidebarStartTitle", content.sidebar.start_card.title);
    setValue("sidebarStartText", content.sidebar.start_card.text);
    setValue("sidebarStartButtonLabel", content.sidebar.start_card.button_label);
    setValue("sidebarStartButtonHref", content.sidebar.start_card.button_href);
    setValue("sidebarFactsKicker", content.sidebar.facts_card.kicker);
    setValue("sidebarFactsTitle", content.sidebar.facts_card.title);
    renderTextList("sidebarFactsList", content.sidebar.facts_card.items || []);
    renderNavigationGroups(content.sidebar.navigation_groups || []);

    setValue("heroTitle", content.hero.title);
    setValue("heroLead", content.hero.lead);
    renderLinkList("heroActions", content.hero.actions || [], { showPrimary: true });
    renderTextList("heroHighlights", content.hero.highlights || []);

    renderTextList("introParagraphs", content.intro.paragraphs || []);
    setValue("introLinkLabel", content.intro.link.label);
    setValue("introLinkUrl", content.intro.link.url);

    setValue("quickLinksTitle", content.quick_links.title);
    renderCardList("quickLinkCards", content.quick_links.cards || []);

    setValue("clubTitle", content.club.title);
    setValue("clubLead", content.club.lead);
    renderCardList("clubFeatureCards", content.club.feature_cards || []);
    setValue("clubLanTitle", content.club.lan.title);
    renderTextList("clubLanParagraphs", content.club.lan.paragraphs || []);
    setValue("programmingTitle", content.club.programming.title);
    setValue("programmingOrgLabel", content.club.programming.org_link_label);
    setValue("programmingOrgUrl", content.club.programming.org_link_url);
    setValue("programmingSystemsTitle", content.club.programming.systems_title);
    renderSystemList(content.club.programming.systems || []);

    setValue("minecraftTitle", content.club.minecraft.title);
    setValue("minecraftServerLabel", content.club.minecraft.server_address_label);
    setValue("minecraftServerIntro", content.club.minecraft.server_address_intro);
    setValue("minecraftServerAddress", content.club.minecraft.server_address);
    setValue("minecraftVideosTitle", content.club.minecraft.videos_title);
    renderTextList("minecraftParagraphs", content.club.minecraft.paragraphs || []);
    renderLinkList("minecraftActions", content.club.minecraft.actions || [], { showPrimary: false });
    renderVideoList(content.club.minecraft.videos || []);

    setValue("associationTitle", content.association.title);
    setValue("associationLead", content.association.lead);
    renderCardList("associationFeatureCards", content.association.feature_cards || []);
    setValue("membershipTitle", content.association.membership.title);
    setValue("membershipLinkIntro", content.association.membership.link_intro);
    setValue("membershipLinkLabel", content.association.membership.link_label);
    setValue("membershipLinkUrl", content.association.membership.link_url);
    setValue("membershipLinkOutro", content.association.membership.link_outro);
    setValue("membershipButtonLabel", content.association.membership.button_label);
    setValue("membershipButtonUrl", content.association.membership.button_url);
    setValue("boardTitle", content.association.board.title);
    setValue("boardIntro", content.association.board.intro);
    renderBoardMembers(content.association.board.members || []);
    setValue("documentsTitle", content.association.documents.title);
    setValue("documentsIntro", content.association.documents.intro);
    setValue("currentDocumentLabel", content.association.documents.current_document_label);
    setValue("currentDocumentUrl", content.association.documents.current_document_url);
    renderDocumentYears(content.association.documents.years || []);
    setValue("contactTitle", content.association.contact.title);
    setValue("contactDiscordText", content.association.contact.discord_text);
    setValue("contactWebsiteText", content.association.contact.website_contact_text);
    setValue("contactOrganizationNumber", content.association.contact.organization_number);
    setValue("contactEmail", content.association.contact.email);
    renderTextList("contactAddressLines", content.association.contact.address_lines || []);

    setValue("footerEditLinkLabel", content.footer.edit_link_label);
    setValue("footerCreditLabel", content.footer.credit_label);
    setValue("footerCreditName", content.footer.credit_name);
    setValue("footerCreditUrl", content.footer.credit_url);
    setValue("footerNote", content.footer.note);

    if (content.meta && content.meta.updated_at) {
      showStatus(`Senast sparad ${new Date(content.meta.updated_at).toLocaleString("sv-SE")}`);
    } else {
      showStatus("Innehållet är laddat.");
    }
  }

  function collectContent() {
    return {
      site: {
        site_name: getValue("siteName"),
        page_title: getValue("pageTitle"),
        mobile_default_title: getValue("mobileDefaultTitle"),
        meta_description: getValue("metaDescription"),
        theme_color: getValue("themeColor"),
        eyebrow: getValue("siteEyebrow"),
      },
      sidebar: {
        start_card: {
          kicker: getValue("sidebarStartKicker"),
          title: getValue("sidebarStartTitle"),
          text: getValue("sidebarStartText"),
          button_label: getValue("sidebarStartButtonLabel"),
          button_href: getValue("sidebarStartButtonHref"),
        },
        facts_card: {
          kicker: getValue("sidebarFactsKicker"),
          title: getValue("sidebarFactsTitle"),
          items: collectTextList("sidebarFactsList"),
        },
        navigation_groups: collectNavigationGroups(),
      },
      hero: {
        title: getValue("heroTitle"),
        lead: getValue("heroLead"),
        actions: collectLinkList("heroActions", { showPrimary: true }),
        highlights: collectTextList("heroHighlights"),
      },
      intro: {
        paragraphs: collectTextList("introParagraphs"),
        link: {
          label: getValue("introLinkLabel"),
          url: getValue("introLinkUrl"),
        },
      },
      quick_links: {
        title: getValue("quickLinksTitle"),
        cards: collectCardList("quickLinkCards"),
      },
      club: {
        title: getValue("clubTitle"),
        lead: getValue("clubLead"),
        feature_cards: collectCardList("clubFeatureCards"),
        lan: {
          title: getValue("clubLanTitle"),
          paragraphs: collectTextList("clubLanParagraphs"),
        },
        programming: {
          title: getValue("programmingTitle"),
          org_link_label: getValue("programmingOrgLabel"),
          org_link_url: getValue("programmingOrgUrl"),
          systems_title: getValue("programmingSystemsTitle"),
          systems: collectSystemList(),
        },
        minecraft: {
          title: getValue("minecraftTitle"),
          paragraphs: collectTextList("minecraftParagraphs"),
          actions: collectLinkList("minecraftActions", { showPrimary: false }).map((item) => ({
            label: item.label,
            href: item.href,
          })),
          server_address_label: getValue("minecraftServerLabel"),
          server_address_intro: getValue("minecraftServerIntro"),
          server_address: getValue("minecraftServerAddress"),
          videos_title: getValue("minecraftVideosTitle"),
          videos: collectVideoList(),
        },
      },
      association: {
        title: getValue("associationTitle"),
        lead: getValue("associationLead"),
        feature_cards: collectCardList("associationFeatureCards"),
        membership: {
          title: getValue("membershipTitle"),
          link_intro: getValue("membershipLinkIntro"),
          link_label: getValue("membershipLinkLabel"),
          link_url: getValue("membershipLinkUrl"),
          link_outro: getValue("membershipLinkOutro"),
          button_label: getValue("membershipButtonLabel"),
          button_url: getValue("membershipButtonUrl"),
        },
        board: {
          title: getValue("boardTitle"),
          intro: getValue("boardIntro"),
          members: collectBoardMembers(),
        },
        documents: {
          title: getValue("documentsTitle"),
          intro: getValue("documentsIntro"),
          current_document_label: getValue("currentDocumentLabel"),
          current_document_url: getValue("currentDocumentUrl"),
          years: collectDocumentYears(),
        },
        contact: {
          title: getValue("contactTitle"),
          discord_text: getValue("contactDiscordText"),
          website_contact_text: getValue("contactWebsiteText"),
          address_lines: collectTextList("contactAddressLines"),
          organization_number: getValue("contactOrganizationNumber"),
          email: getValue("contactEmail"),
        },
      },
      footer: {
        edit_link_label: getValue("footerEditLinkLabel"),
        credit_label: getValue("footerCreditLabel"),
        credit_name: getValue("footerCreditName"),
        credit_url: getValue("footerCreditUrl"),
        note: getValue("footerNote"),
      },
      meta: loadedContent && loadedContent.meta ? loadedContent.meta : {},
    };
  }

  async function uploadPendingDocuments() {
    const uploadInputs = document.querySelectorAll('#documentYears input[type="file"]');

    for (const input of uploadInputs) {
      const file = input.files && input.files[0];
      if (!file) {
        continue;
      }

      const yearElement = input.closest('[data-item-type="document-year"]');
      const yearField = yearElement ? yearElement.querySelector('[data-field="year"]') : null;
      const year = yearField ? yearField.value.trim() : "";

      if (!year) {
        throw new Error("Välj år innan du laddar upp ett dokument");
      }

      const formData = new FormData();
      formData.append("year", year);
      formData.append("file", file);

      const request = await fetch(config.uploadUrl, {
        method: "POST",
        headers: withCsrfHeaders(),
        credentials: "same-origin",
        body: formData,
      });

      const payload = await request.json();
      if (!request.ok) {
        throw new Error(payload.error || payload.message || "Kunde inte ladda upp dokument");
      }

      const urlField = input.closest(".admin-list-item").querySelector('[data-field="url"]');
      urlField.value = payload.url;
      input.value = "";
    }
  }

  async function saveContent() {
    if (!loadedContent) {
      return;
    }

    saveButton.disabled = true;
    showStatus("Sparar...");

    try {
      await uploadPendingDocuments();

      const request = await fetch(config.saveUrl, {
        method: "PUT",
        headers: withCsrfHeaders({
          "Content-Type": "application/json",
        }),
        credentials: "same-origin",
        body: JSON.stringify(collectContent()),
      });

      const payload = await request.json();
      if (!request.ok) {
        throw new Error(payload.error || payload.message || "Kunde inte spara");
      }

      populateForm(payload.content);
      await loadHistory();
      showStatus("Ändringarna är sparade.");
    } catch (error) {
      showStatus(error.message || "Kunde inte spara ändringarna", true);
    } finally {
      saveButton.disabled = false;
    }
  }

  async function loadContent() {
    const request = await fetch(config.contentUrl, {
      credentials: "same-origin",
    });

    if (!request.ok) {
      throw new Error("Kunde inte läsa webbplatsens innehåll");
    }

    const payload = await request.json();
    populateForm(payload);
  }

  async function loadAdmins() {
    const request = await fetch(config.adminsUrl, {
      credentials: "same-origin",
    });

    if (!request.ok) {
      throw new Error("Kunde inte läsa adminkonton");
    }

    const payload = await request.json();
    renderAdminEmails(payload.emails || []);
  }

  async function loadHistory() {
    const request = await fetch(config.historyUrl, {
      credentials: "same-origin",
    });

    if (!request.ok) {
      throw new Error("Kunde inte läsa versionshistoriken");
    }

    const payload = await request.json();
    renderHistory(payload.items || []);
  }

  async function addAdminEmail() {
    const field = document.getElementById("newAdminEmail");
    const email = field.value.trim();
    if (!email) {
      showStatus("Ange en e-postadress för adminkontot", true);
      return;
    }

    try {
      const request = await fetch(config.adminsUrl, {
        method: "POST",
        headers: withCsrfHeaders({
          "Content-Type": "application/json",
        }),
        credentials: "same-origin",
        body: JSON.stringify({ email }),
      });

      const payload = await request.json();
      if (!request.ok) {
        throw new Error(payload.error || payload.message || "Kunde inte lägga till admin");
      }

      field.value = "";
      renderAdminEmails(payload.emails || []);
      showStatus("Adminkontot har lagts till.");
    } catch (error) {
      showStatus(error.message || "Kunde inte lägga till admin", true);
    }
  }

  function bindButtons() {
    saveButton.addEventListener("click", saveContent);

    document.querySelectorAll("[data-add-list-item]").forEach((button) => {
      button.addEventListener("click", () => {
        const container = document.getElementById(button.dataset.addListItem);
        container.append(createTextListItem(""));
      });
    });

    document.getElementById("addNavigationGroupButton").addEventListener("click", () => {
      document.getElementById("navigationGroups").append(createNavigationGroup({ label: "", items: [] }));
    });
    document.getElementById("addHeroActionButton").addEventListener("click", () => {
      document.getElementById("heroActions").append(createLinkItem({ label: "", href: "", primary: false }, { showPrimary: true }));
    });
    document.getElementById("addQuickLinkCardButton").addEventListener("click", () => {
      document.getElementById("quickLinkCards").append(createCardItem({ kicker: "", title: "", text: "", href: "" }));
    });
    document.getElementById("addClubFeatureCardButton").addEventListener("click", () => {
      document.getElementById("clubFeatureCards").append(createCardItem({ kicker: "", title: "", text: "", href: "" }));
    });
    document.getElementById("addProgrammingSystemButton").addEventListener("click", () => {
      document.getElementById("programmingSystems").append(createSystemItem({}));
    });
    document.getElementById("addMinecraftActionButton").addEventListener("click", () => {
      document.getElementById("minecraftActions").append(createLinkItem({ label: "", href: "" }, { showPrimary: false }));
    });
    document.getElementById("addMinecraftVideoButton").addEventListener("click", () => {
      document.getElementById("minecraftVideos").append(createVideoItem({ title: "", embed_url: "" }));
    });
    document.getElementById("addAssociationFeatureCardButton").addEventListener("click", () => {
      document.getElementById("associationFeatureCards").append(createCardItem({}));
    });
    document.getElementById("addBoardMemberButton").addEventListener("click", () => {
      document.getElementById("boardMembers").append(createBoardMember({}));
    });
    document.getElementById("addDocumentYearButton").addEventListener("click", () => {
      document.getElementById("documentYears").append(createDocumentYear({ year: "", events: [] }));
    });
    document.getElementById("addAdminEmailButton").addEventListener("click", addAdminEmail);
  }

  async function initialize() {
    bindButtons();
    showStatus("Laddar innehåll...");

    try {
      await Promise.all([loadContent(), loadAdmins(), loadHistory()]);
    } catch (error) {
      showStatus(error.message || "Kunde inte ladda adminpanelen", true);
    }
  }

  initialize();
})();
