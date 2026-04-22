from copy import deepcopy


DEFAULT_SITE_CONTENT = {
    "site": {
        "site_name": "Tullinge gymnasium datorklubb",
        "page_title": "Introduktion",
        "mobile_default_title": "Introduktion",
        "meta_description": "Tullinge gymnasium datorklubb",
        "theme_color": "#ffffff",
        "eyebrow": "Elevförening på Tullinge gymnasium",
    },
    "sidebar": {
        "start_card": {
            "kicker": "Starta här",
            "title": "Bli en del av klubben",
            "text": "Gratis medlemskap för elever som vill spela, programmera och bygga projekt tillsammans.",
            "button_label": "Bli medlem",
            "button_href": "#bli-medlem",
        },
        "facts_card": {
            "kicker": "Snabbfakta",
            "title": "Det viktigaste",
            "items": [
                "Grundad 2001",
                "LAN en gång per termin",
                "Gratis medlemskap",
            ],
        },
        "navigation_groups": [
            {
                "label": "Datorklubben",
                "items": [
                    {"label": "LAN", "href": "#lan"},
                    {"label": "Programmering", "href": "#programmering"},
                    {"label": "Minecraft", "href": "#minecraft"},
                ],
            },
            {
                "label": "Föreningen",
                "items": [
                    {"label": "Bli medlem", "href": "#bli-medlem"},
                    {"label": "Styrelsen", "href": "#styrelsen"},
                    {"label": "Dokument", "href": "#dokument"},
                    {"label": "Kontakta oss", "href": "#kontakta-oss"},
                ],
            },
        ],
    },
    "hero": {
        "title": "Välkommen till Tullinge gymnasium datorklubb",
        "lead": "Gemenskap för elever som gillar spel, programmering och att bygga saker tillsammans.",
        "actions": [
            {"label": "Bli medlem", "href": "#bli-medlem", "primary": True},
            {"label": "Utforska projekt", "href": "#programmering", "primary": False},
            {"label": "Kontakta oss", "href": "#kontakta-oss", "primary": False},
        ],
        "highlights": [
            "LAN en gång per termin",
            "Gratis medlemskap",
            "GitHub, Minecraft och programmering",
        ],
    },
    "intro": {
        "paragraphs": [
            "På Tullinge gymnasium har det sedan starten 2001 funnits en grupp för brädspels- och datorspelsintresserade, Tullinge gymnasium datorklubb. Föreningens syfte är bland annat att anordna LAN, men även andra aktiviteter för elever intresserade av datorspel och brädspel.",
            "Datorklubben vill även anordna andra programmeringsrelaterade evenemang, som t.ex. hackathon, programmeringsutmaningar och liknande!",
        ],
        "link": {
            "label": "True Purpose",
            "url": "https://www.youtube.com/watch?v=gBYnk438_zg&feature=youtu.be",
        },
    },
    "quick_links": {
        "title": "Snabbstart",
        "cards": [
            {
                "kicker": "Medlem",
                "title": "Bli medlem",
                "text": "Gratis medlemskap som hjälper föreningen att växa.",
                "href": "#bli-medlem",
            },
            {
                "kicker": "Spela",
                "title": "Gå med på servern",
                "text": "Bli medlem först och fyll sedan i formuläret för whitelist.",
                "href": "#minecraft",
            },
            {
                "kicker": "Bygg",
                "title": "Se våra projekt",
                "text": "Utforska datorklubbens GitHub-organisation och system.",
                "href": "#programmering",
            },
        ],
    },
    "club": {
        "title": "Datorklubben",
        "lead": "Vi samlar elever kring spel, programmering och projekt som går att bygga vidare på tillsammans.",
        "feature_cards": [
            {
                "kicker": "Event",
                "title": "LAN",
                "text": "Sociala träffar och spel på plats i skolan.",
                "href": "#lan",
            },
            {
                "kicker": "Projekt",
                "title": "Programmering",
                "text": "Bygg saker tillsammans och bidra till klubbens system.",
                "href": "#programmering",
            },
            {
                "kicker": "Spel",
                "title": "Minecraft",
                "text": "Egen server för medlemmar med enkel onboarding.",
                "href": "#minecraft",
            },
        ],
        "lan": {
            "title": "LAN",
            "paragraphs": [
                "Datorklubben anordnar ett LAN en gång per termin.",
            ],
        },
        "programming": {
            "title": "Programmering",
            "org_link_label": "Datorklubbens GitHub-organisation",
            "org_link_url": "https://github.com/tullingedk",
            "systems_title": "Egenutvecklade system",
            "systems": [
                {
                    "repo_label": "tullingedk/booking",
                    "repo_url": "https://github.com/tullingedk/booking",
                    "description": "Bokningssida för LAN. Körs på",
                    "site_label": "https://booking.tgdk.se",
                    "site_url": "https://booking.tgdk.se",
                },
                {
                    "repo_label": "tullingedk/member",
                    "repo_url": "https://github.com/tullingedk/member",
                    "description": "Medlemsregister. Körs på",
                    "site_label": "https://member.tgdk.se",
                    "site_url": "https://member.tgdk.se",
                },
            ],
        },
        "minecraft": {
            "title": "Minecraft",
            "paragraphs": [
                "Datorklubben har en egen Minecraftserver för dess medlemmar. För att gå med, bli först medlem och fyll sedan i formuläret för att bli insläppt på servern.",
                "När du fyllt i formuläret, kontakta någon i styrelsen som då whitelistar dig.",
                "Inga fusk är tillåtna. Endast OptiFine är tillåtet. Använd sunt förnuft, förstör inte för andra spelare.",
            ],
            "actions": [
                {"label": "Först: Bli medlem", "href": "#bli-medlem"},
                {
                    "label": "Sen: Fyll i detta formulär",
                    "href": "https://forms.gle/i7h1FiDFfL5TuunL8",
                },
            ],
            "server_address_label": "Serveradress",
            "server_address_intro": "IP:n till servern:",
            "server_address": "minecraft.tgdk.se",
            "videos_title": "Videor",
            "videos": [
                {
                    "embed_url": "https://www.youtube.com/embed/SLn-kBjlg70",
                    "title": "Valborgsfirande med DK 2021",
                },
            ],
        },
    },
    "association": {
        "title": "Föreningen",
        "lead": "Här hittar du hur medlemskap, styrelse, dokument och kontaktvägar fungerar.",
        "feature_cards": [
            {
                "kicker": "Medlemskap",
                "title": "Gå med gratis",
                "text": "Registrera dig och hjälp föreningen att växa.",
                "href": "#bli-medlem",
            },
            {
                "kicker": "Arkiv",
                "title": "Dokument",
                "text": "Protokoll, rapporter och stadgar samlade på ett ställe.",
                "href": "#dokument",
            },
            {
                "kicker": "Kontakt",
                "title": "Styrelsen",
                "text": "Kontakta ansvariga om du har frågor eller vill hjälpa till.",
                "href": "#kontakta-oss",
            },
        ],
        "membership": {
            "title": "Bli medlem",
            "link_intro": "Använd",
            "link_label": "denna sida",
            "link_url": "https://member.tgdk.se/",
            "link_outro": "för att bli medlem i Datorklubben! Ett medlemskap kostar ingenting men hjälper oss att söka bidrag och växa! Formuläret kräver inloggning.",
            "button_label": "Bli medlem",
            "button_url": "https://member.tgdk.se",
        },
        "board": {
            "title": "Styrelsen",
            "intro": "Styrelsen för verksamhetsåret 2020-07-01 till 2021-06-30.",
            "members": [
                {"name": "Fredrik Berzins", "details": "TE18", "role": "Ordförande"},
                {"name": "Tim Torndal", "details": "TE19", "role": "Vice ordförande"},
                {
                    "name": "Vilhelm Prytz",
                    "details": "TE18",
                    "role": "Ordinarie ledamot, ekonomiansvarig",
                },
                {"name": "Teo Akenine", "details": "NA19B", "role": "Ordinarie ledamot"},
                {"name": "David Törnqvist", "details": "TE19", "role": "Ordinarie ledamot"},
                {"name": "Walter Thorslund", "details": "TE19", "role": "Ordinarie ledamot"},
                {
                    "name": "Jonathan Lönnqvist",
                    "details": "TE19",
                    "role": "Ordinarie ledamot",
                },
                {
                    "name": "Christoffer Santala Andersson",
                    "details": "",
                    "role": "Suppleant till ledamot",
                },
            ],
        },
        "documents": {
            "title": "Dokument",
            "intro": "Här finner du ett arkiv med föreningens dokument.",
            "current_document_label": "Stadgar som gäller just nu, version 2020-04-24",
            "current_document_url": "/documents/2020/stadgar-2020-04-24.pdf",
            "years": [
                {
                    "year": "2021",
                    "events": [
                        {
                            "date_label": "22 september",
                            "title": "Årsmöte 2021",
                            "items": [
                                {
                                    "label": "Årsmötesprotokoll",
                                    "url": "/documents/2021/arsmote-2021.pdf",
                                },
                                {
                                    "label": "Konstituerande styrelsemöte (publiceras efter årsmötet)",
                                    "url": "",
                                },
                                {
                                    "label": "Balansrapport",
                                    "url": "/documents/2021/Balansrapport%202020-07-01-2021-06-30.pdf",
                                },
                                {
                                    "label": "Resultatrapport",
                                    "url": "/documents/2021/Resultatrapport%202020-07-01-2021-06-30.pdf",
                                },
                            ],
                        }
                    ],
                },
                {
                    "year": "2020",
                    "events": [
                        {
                            "date_label": "23 september",
                            "title": "Årsmöte 2020",
                            "items": [
                                {
                                    "label": "Årsmötesprotokoll",
                                    "url": "/documents/2020/arsmote-2020.pdf",
                                },
                                {
                                    "label": "Konstituerande styrelsemöte",
                                    "url": "/documents/2020/konstituerande-styrelsemote-2020-09-23.pdf",
                                },
                                {
                                    "label": "Balansrapport",
                                    "url": "/documents/2020/Balansrapport%202020-05-04-2020-06-30.pdf",
                                },
                                {
                                    "label": "Resultatrapport",
                                    "url": "/documents/2020/Resultatrapport%202020-05-04-2020-06-30.pdf",
                                },
                            ],
                        },
                        {
                            "date_label": "24 april",
                            "title": "Föreningens bildande",
                            "items": [
                                {
                                    "label": "Stadgarna antogs",
                                    "url": "/documents/2020/stadgar-2020-04-24.pdf",
                                },
                                {
                                    "label": "Konstituerande styrelsemöte",
                                    "url": "/documents/2020/konstituerande-styrelsemote-2020-04-24.pdf",
                                },
                            ],
                        },
                    ],
                },
            ],
        },
        "contact": {
            "title": "Kontakta oss",
            "discord_text": "Du når enklast styrelsen på datorklubbens officiella Discordserver.",
            "website_contact_text": "Vid frågor angående webbsidan, kontakta Charlie Arnerstål - Continental.",
            "address_lines": [
                "TULLINGE GYMNASIUM DATORKLUBB",
                "c/o TULLINGE GYMNASIUM",
                "ALFRED NOBELS ALLÉ 206",
                "146 80 Tullinge",
            ],
            "organization_number": "802530-4208",
            "email": "info@tgdk.se",
        },
    },
    "footer": {
        "edit_link_label": "Redigera denna sida",
        "credit_label": "Webbplatsuppdatering av",
        "credit_name": "Charlemagne404",
        "credit_url": "https://github.com/Charlemagne404",
        "note": "",
    },
    "meta": {
        "updated_at": "",
        "updated_by_name": "",
        "updated_by_email": "",
    },
}


def get_default_site_content():
    return deepcopy(DEFAULT_SITE_CONTENT)
