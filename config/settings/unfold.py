from django.templatetags.static import static
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _


def _item(title, icon, model):
    app, name = model.split(".")
    return {"title": title, "icon": icon, "link": reverse_lazy(f"admin:{app}_{name}_changelist")}


UNFOLD = {
    "SITE_TITLE": "WeliCoDev Admin",
    "SITE_HEADER": "WeliCoDev",
    "SITE_SUBHEADER": "Build • Learn • Create",
    "SITE_URL": "/",
    "SITE_SYMBOL": "code",
    "SITE_FAVICONS": [{"rel": "icon", "type": "image/svg+xml", "href": lambda request: static("img/logo-mark.svg")}],
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "SHOW_LANGUAGES": True,
    "SHOW_BACK_BUTTON": True,
    "BORDER_RADIUS": "10px",
    "COLORS": {
        "base": {
            "50": "oklch(98.4% .005 255)",
            "100": "oklch(96.5% .009 255)",
            "200": "oklch(92.5% .015 255)",
            "300": "oklch(86.5% .022 255)",
            "400": "oklch(70.5% .035 258)",
            "500": "oklch(55% .045 260)",
            "600": "oklch(44.5% .05 262)",
            "700": "oklch(37% .055 263)",
            "800": "oklch(27.5% .055 264)",
            "900": "oklch(20.5% .05 265)",
            "950": "oklch(14% .04 266)",
        },
        "primary": {
            "50": "oklch(97% .014 254)",
            "100": "oklch(93.2% .032 255)",
            "200": "oklch(88.2% .059 254)",
            "300": "oklch(80.9% .105 252)",
            "400": "oklch(70.7% .165 254)",
            "500": "oklch(62.3% .214 259)",
            "600": "oklch(54.6% .245 263)",
            "700": "oklch(48.8% .243 264)",
            "800": "oklch(42.4% .199 266)",
            "900": "oklch(37.9% .146 266)",
            "950": "oklch(28.2% .091 268)",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": _("Asosiy"),
                "items": [
                    {"title": _("Dashboard"), "icon": "space_dashboard", "link": reverse_lazy("dashboard:home")},
                    {"title": _("Saytni ochish"), "icon": "open_in_new", "link": "/"},
                ],
            },
            {
                "title": _("Sayt"),
                "collapsible": True,
                "items": [
                    _item(_("Sayt sozlamalari"), "tune", "core.sitesettings"),
                    _item(_("Ijtimoiy tarmoqlar"), "share", "core.sociallink"),
                    _item(_("Sahifa sarlavhalari"), "view_quilt", "core.pagehero"),
                    _item(_("Hozirgi holat"), "radio_button_checked", "core.currentstatus"),
                    _item(_("FAQ"), "help", "core.faq"),
                    _item(_("Teglar"), "sell", "core.tag"),
                ],
            },
            {
                "title": _("Portfolio"),
                "collapsible": True,
                "items": [
                    _item(_("Loyihalar"), "folder_special", "portfolio.project"),
                    _item(_("Loyiha turkumlari"), "category", "portfolio.projectcategory"),
                    _item(_("Ko'nikmalar"), "bolt", "portfolio.skill"),
                    _item(_("Ko'nikma turkumlari"), "label", "portfolio.skillcategory"),
                    _item(_("Tajriba"), "work_history", "portfolio.experience"),
                    _item(_("Hayot yo'li"), "timeline", "portfolio.journeystep"),
                    _item(_("Qiziqishlar"), "interests", "portfolio.interest"),
                ],
            },
            {
                "title": _("Blog"),
                "collapsible": True,
                "items": [
                    _item(_("Maqolalar"), "article", "blog.article"),
                    _item(_("Turkumlar"), "topic", "blog.articlecategory"),
                    _item(_("Obunachilar"), "mark_email_read", "blog.subscriber"),
                ],
            },
            {
                "title": _("Media"),
                "collapsible": True,
                "items": [
                    _item(_("Fotolar"), "photo_library", "gallery.photo"),
                    _item(_("Albomlar"), "photo_album", "gallery.album"),
                    _item(_("Videolar"), "smart_display", "gallery.video"),
                    _item(_("Treklar"), "music_note", "gallery.track"),
                    _item(_("Pleylistlar"), "queue_music", "gallery.playlist"),
                    _item(_("Turkumlar"), "category", "gallery.mediacategory"),
                ],
            },
            {
                "title": _("Ta'lim"),
                "collapsible": True,
                "items": [
                    _item(_("Kurslar"), "school", "education.course"),
                    _item(_("Darslar"), "play_lesson", "education.lesson"),
                    _item(_("Uyga vazifalar"), "assignment_turned_in", "education.homeworksubmission"),
                    _item(_("O'quvchilar"), "group", "education.enrollment"),
                    _item(_("Sertifikatlar"), "workspace_premium", "education.certificate"),
                ],
            },
            {
                "title": _("Faollik"),
                "collapsible": True,
                "items": [
                    _item(_("Izohlar"), "chat", "interactions.comment"),
                    _item(_("Sharhlar"), "star", "interactions.review"),
                    _item(_("Xabarlar"), "mail", "interactions.contactmessage"),
                ],
            },
            {
                "title": _("Telegram bot"),
                "collapsible": True,
                "items": [
                    _item(_("Bot sozlamalari"), "smart_toy", "telegram_bot.botsettings"),
                    _item(_("Ommaviy xabarlar"), "campaign", "telegram_bot.broadcast"),
                    _item(_("Bot yozishmalari"), "forum", "telegram_bot.botmessage"),
                    _item(_("Bot hodisalari"), "monitoring", "telegram_bot.botevent"),
                ],
            },
            {
                "title": _("Foydalanuvchilar"),
                "collapsible": True,
                "items": [
                    _item(_("Foydalanuvchilar"), "person", "accounts.user"),
                    _item(_("Guruhlar"), "admin_panel_settings", "auth.group"),
                ],
            },
        ],
    },
}
