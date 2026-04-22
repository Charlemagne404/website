import re
from urllib.parse import urlparse


DOCUMENT_YEAR_PATTERN = re.compile(r"^\d{4}$")
ANCHOR_PATTERN = re.compile(r"^#[A-Za-z][A-Za-z0-9\-_:.]*$")
RELATIVE_PATH_PATTERN = re.compile(r"^/(?!/)\S*$")
HEX_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_STRING_LENGTH = 10000
YOUTUBE_EMBED_HOSTS = {"www.youtube.com", "youtube.com", "www.youtube-nocookie.com"}


class ContentValidationError(ValueError):
    pass


def validate_email_address(email, field_name="email"):
    normalized = str(email or "").strip()
    if not normalized:
        raise ContentValidationError(f"{field_name} is required")
    if not EMAIL_PATTERN.fullmatch(normalized):
        raise ContentValidationError(f"{field_name} must be a valid email address")
    return normalized


def validate_site_content(content, defaults):
    _validate_structure("content", content, defaults)
    _validate_semantics(content)
    return content


def _validate_structure(path, value, schema):
    if isinstance(schema, dict):
        if not isinstance(value, dict):
            raise ContentValidationError(f"{path} must be an object")

        schema_keys = set(schema.keys())
        value_keys = set(value.keys())
        missing = sorted(schema_keys - value_keys)
        extra = sorted(value_keys - schema_keys)

        if missing:
            raise ContentValidationError(f"{path} is missing required fields: {', '.join(missing)}")
        if extra:
            raise ContentValidationError(f"{path} contains unexpected fields: {', '.join(extra)}")

        for key, child_schema in schema.items():
            _validate_structure(f"{path}.{key}", value.get(key), child_schema)
        return

    if isinstance(schema, list):
        if not isinstance(value, list):
            raise ContentValidationError(f"{path} must be a list")

        if not schema:
            return

        item_schema = schema[0]
        for index, item in enumerate(value):
            _validate_structure(f"{path}[{index}]", item, item_schema)
        return

    if isinstance(schema, bool):
        if type(value) is not bool:
            raise ContentValidationError(f"{path} must be true or false")
        return

    if isinstance(schema, str):
        if not isinstance(value, str):
            raise ContentValidationError(f"{path} must be a string")
        if len(value) > MAX_STRING_LENGTH:
            raise ContentValidationError(f"{path} is too long")
        return

    raise ContentValidationError(f"{path} uses an unsupported schema type")


def _validate_semantics(content):
    _validate_hex_color(content["site"]["theme_color"], "site.theme_color")
    validate_email_address(content["association"]["contact"]["email"], "association.contact.email")

    _validate_anchor_or_url(content["sidebar"]["start_card"]["button_href"], "sidebar.start_card.button_href")

    for index, item in enumerate(content["sidebar"]["navigation_groups"]):
        for item_index, child in enumerate(item["items"]):
            _validate_anchor_or_url(
                child["href"],
                f"sidebar.navigation_groups[{index}].items[{item_index}].href",
            )

    for index, action in enumerate(content["hero"]["actions"]):
        _validate_anchor_or_url(action["href"], f"hero.actions[{index}].href")

    _validate_optional_url(content["intro"]["link"]["url"], "intro.link.url")

    for index, card in enumerate(content["quick_links"]["cards"]):
        _validate_anchor_or_url(card["href"], f"quick_links.cards[{index}].href")

    for index, card in enumerate(content["club"]["feature_cards"]):
        _validate_anchor_or_url(card["href"], f"club.feature_cards[{index}].href")

    _validate_optional_url(
        content["club"]["programming"]["org_link_url"],
        "club.programming.org_link_url",
    )
    for index, system in enumerate(content["club"]["programming"]["systems"]):
        _validate_optional_url(system["repo_url"], f"club.programming.systems[{index}].repo_url")
        _validate_optional_url(system["site_url"], f"club.programming.systems[{index}].site_url")

    for index, action in enumerate(content["club"]["minecraft"]["actions"]):
        _validate_anchor_or_url(action["href"], f"club.minecraft.actions[{index}].href")
    for index, video in enumerate(content["club"]["minecraft"]["videos"]):
        _validate_youtube_embed_url(video["embed_url"], f"club.minecraft.videos[{index}].embed_url")

    for index, card in enumerate(content["association"]["feature_cards"]):
        _validate_anchor_or_url(card["href"], f"association.feature_cards[{index}].href")

    _validate_optional_url(
        content["association"]["membership"]["link_url"],
        "association.membership.link_url",
    )
    _validate_optional_url(
        content["association"]["membership"]["button_url"],
        "association.membership.button_url",
    )
    _validate_optional_url(
        content["association"]["documents"]["current_document_url"],
        "association.documents.current_document_url",
        allow_anchor=False,
    )
    for index, year in enumerate(content["association"]["documents"]["years"]):
        if year["year"] and not DOCUMENT_YEAR_PATTERN.fullmatch(year["year"]):
            raise ContentValidationError(
                f"association.documents.years[{index}].year must use four digits"
            )
        for event_index, event in enumerate(year["events"]):
            for item_index, item in enumerate(event["items"]):
                _validate_optional_url(
                    item["url"],
                    f"association.documents.years[{index}].events[{event_index}].items[{item_index}].url",
                    allow_anchor=False,
                )

    _validate_optional_url(content["footer"]["credit_url"], "footer.credit_url")


def _validate_hex_color(value, field_name):
    if not HEX_COLOR_PATTERN.fullmatch(value):
        raise ContentValidationError(f"{field_name} must be a six-digit hex color")


def _validate_anchor_or_url(value, field_name):
    _validate_optional_url(value, field_name, allow_anchor=True)


def _validate_optional_url(value, field_name, allow_anchor=False):
    if not value:
        return

    if allow_anchor and ANCHOR_PATTERN.fullmatch(value):
        return

    if RELATIVE_PATH_PATTERN.fullmatch(value):
        return

    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        raise ContentValidationError(
            f"{field_name} must use https/http, a site-relative path, or a page anchor"
        )

    if not parsed.netloc:
        raise ContentValidationError(f"{field_name} must include a hostname")


def _validate_youtube_embed_url(value, field_name):
    if not value:
        raise ContentValidationError(f"{field_name} is required")

    parsed = urlparse(value)
    if parsed.scheme not in {"https", "http"}:
        raise ContentValidationError(f"{field_name} must use https/http")
    if parsed.netloc not in YOUTUBE_EMBED_HOSTS:
        raise ContentValidationError(f"{field_name} must use an approved YouTube embed host")
    if not parsed.path.startswith("/embed/"):
        raise ContentValidationError(f"{field_name} must use a YouTube embed URL")
