"""Qo'shimcha demo kontent: kurslar, musiqa, ta'lim tarixi. Takror ishga tushirilsa dublikat yaratmaydi.

    python manage.py seed_extra
"""

from datetime import date
from urllib.parse import quote_plus

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core import placeholders as ph
from apps.education.models import Course, Lesson, LessonResource, Module
from apps.gallery.models import MediaCategory, Playlist, Track
from apps.portfolio.models import Experience, Skill
from apps.telegram_bot.models import BotSettings

from .seed_demo import tr


def tr_ure(obj, field, uz, ru, en):
    """Bu fayldagi kortejlar (uz, ru, en) tartibida yozilgan."""
    tr(obj, field, uz, en, ru)

YT = "https://www.youtube.com/watch?v=pg19Z8LL06w"

PY_CODE = '<pre><code class="language-python">def salom(ism: str) -&gt; str:\n    return f"Salom, {ism}!"\n\nprint(salom("WeliCoDev"))</code></pre>'
DJ_CODE = '<pre><code class="language-python">from django.urls import path\nfrom . import views\n\nurlpatterns = [\n    path("", views.home, name="home"),\n]</code></pre>'
SQL_CODE = '<pre><code class="language-sql">SELECT u.first_name, COUNT(e.id) AS kurslar\nFROM accounts_user u\nJOIN education_enrollment e ON e.user_id = u.id\nGROUP BY u.id\nORDER BY kurslar DESC;</code></pre>'
BOT_CODE = '<pre><code class="language-python">from aiogram import Router\nfrom aiogram.filters import CommandStart\n\nrouter = Router()\n\n@router.message(CommandStart())\nasync def start(message):\n    await message.answer("Salom!")</code></pre>'
GIT_CODE = '<pre><code class="language-bash">git checkout -b feature/login\ngit add .\ngit commit -m "feat: telegram login"\ngit push -u origin feature/login</code></pre>'

COURSES = [
    {
        "slug": "python-asoslari", "level": "beginner", "free": True, "order": 1, "seed": 4,
        "title": ("Python asoslari: noldan dasturchigacha", "Основы Python: с нуля до разработчика", "Python fundamentals: from zero to developer"),
        "subtitle": ("O'zgaruvchilar, funksiyalar, OOP va birinchi loyihangiz — o'zbek tilida.", "Переменные, функции, ООП и первый проект.", "Variables, functions, OOP and your first project."),
        "skills": ["Python", "Git"],
        "modules": [("Kirish", ["Python nima va nega aynan u?", "O'rnatish: Python, VS Code, terminal", "O'zgaruvchilar va ma'lumot turlari"]),
                    ("Asosiy tushunchalar", ["Shartlar va sikllar", "Funksiyalar", "Ro'yxat, lug'at va to'plamlar"]),
                    ("Amaliyot", ["OOP: klasslar va obyektlar", "Fayllar bilan ishlash va birinchi loyiha"])],
        "code": PY_CODE,
    },
    {
        "slug": "django-noldan-productiongacha", "level": "intermediate", "free": True, "order": 2, "seed": 1,
        "title": ("Django: noldan production'gacha", "Django: с нуля до продакшена", "Django: from zero to production"),
        "subtitle": ("Haqiqiy loyiha: modellar, admin, autentifikatsiya, REST API va deploy.", "Реальный проект: модели, админка, аутентификация, REST API и деплой.", "A real project: models, admin, auth, REST API and deployment."),
        "skills": ["Django", "Python", "PostgreSQL"],
        "modules": [("Poydevor", ["Loyiha tuzilmasi va sozlamalar", "Modellar va migratsiyalar", "Django admin'ni professional sozlash"]),
                    ("Veb qism", ["View, URL va shablonlar", "Formalar va validatsiya", "Autentifikatsiya: Telegram orqali kirish"]),
                    ("Production", ["Django REST Framework bilan API", "Celery va Redis: fon vazifalari", "Deploy: Docker, Nginx, SSL"])],
        "code": DJ_CODE,
    },
    {
        "slug": "postgresql-va-sql-amaliyoti", "level": "intermediate", "free": True, "order": 4, "seed": 3,
        "title": ("PostgreSQL va SQL amaliyoti", "PostgreSQL и практика SQL", "PostgreSQL and practical SQL"),
        "subtitle": ("So'rovlar, indekslar, tranzaksiyalar va Django ORM optimizatsiyasi.", "Запросы, индексы, транзакции и оптимизация Django ORM.", "Queries, indexes, transactions and Django ORM optimisation."),
        "skills": ["PostgreSQL", "Django"],
        "modules": [("SQL", ["SELECT, JOIN va GROUP BY", "Indekslar: qachon va qanday", "Tranzaksiyalar va izolyatsiya"]),
                    ("Django bilan", ["N+1 muammosi va select_related", "EXPLAIN ANALYZE bilan tahlil", "Backup va tiklash"])],
        "code": SQL_CODE,
    },
    {
        "slug": "telegram-bot-aiogram-3", "level": "intermediate", "free": True, "order": 5, "seed": 2,
        "title": ("Telegram bot yaratish: aiogram 3", "Создание Telegram-бота: aiogram 3", "Building Telegram bots with aiogram 3"),
        "subtitle": ("Ro'yxatdan o'tish, FSM, inline tugmalar, Mini App va webhook — @welicodevbot misolida.", "Регистрация, FSM, inline-кнопки, Mini App и webhook.", "Registration, FSM, inline buttons, Mini App and webhooks."),
        "skills": ["Python", "Redis", "Docker"],
        "modules": [("Asoslar", ["BotFather va birinchi bot", "Router, filter va handlerlar", "FSM: ro'yxatdan o'tish oqimi"]),
                    ("Professional", ["Inline tugmalar va callback", "Telegram Mini App", "Webhook, Docker va deploy"])],
        "code": BOT_CODE,
    },
    {
        "slug": "git-va-github", "level": "beginner", "free": True, "order": 6, "seed": 5,
        "title": ("Git va GitHub: jamoada ishlash", "Git и GitHub: работа в команде", "Git and GitHub: working in a team"),
        "subtitle": ("Commit, branch, pull request va code review — haqiqiy jamoa ish oqimi.", "Коммиты, ветки, pull request и code review.", "Commits, branches, pull requests and code review."),
        "skills": ["Git"],
        "modules": [("Git", ["Git nima va nega kerak", "Commit va tarix", "Branch va merge"]),
                    ("GitHub", ["Pull request va code review", "GitHub Actions bilan CI"])],
        "code": GIT_CODE,
    },
    {
        "slug": "system-design-asoslari", "level": "advanced", "free": False, "price": 299000, "order": 7, "seed": 0,
        "title": ("System Design asoslari", "Основы System Design", "System Design fundamentals"),
        "subtitle": ("Kengaytiriladigan tizimlar: kesh, navbatlar, ma'lumotlar bazasi va arxitektura qarorlari.", "Масштабируемые системы: кэш, очереди, БД и архитектура.", "Scalable systems: caching, queues, databases and architecture."),
        "skills": ["Redis", "PostgreSQL", "Docker"],
        "modules": [("Arxitektura", ["Monolit va mikroservislar", "Keshlash strategiyalari", "Navbatlar va asinxron ishlov"]),
                    ("Amaliy keys", ["NutriZone arxitekturasi tahlili", "Intervyu uchun dizayn masalalari"])],
        "code": SQL_CODE,
    },
]

FAVORITE_SONGS = [
    ("Time", "Hans Zimmer", "Inception", 2010, "Focus", "Kod yozayotganda diqqatni jamlaydi"),
    ("Experience", "Ludovico Einaudi", "In a Time Lapse", 2013, "Focus", "Uzun ish kunlari uchun"),
    ("Cornfield Chase", "Hans Zimmer", "Interstellar", 2014, "Focus", "Katta loyihalar boshlanishida"),
    ("Nuvole Bianche", "Ludovico Einaudi", "Una Mattina", 2004, "Chill", "Tinch kechalar uchun"),
    ("Clair de Lune", "Claude Debussy", "Suite bergamasque", 1905, "Chill", "Klassika — doim yaxshi"),
    ("Weightless", "Marconi Union", "Weightless", 2011, "Chill", "Stressni kamaytiradi"),
    ("Midnight City", "M83", "Hurry Up, We're Dreaming", 2011, "Travel", "Yo'lda tinglash uchun"),
]


class Command(BaseCommand):
    help = "Kurslar, musiqa va ta'lim tarixi bo'yicha demo kontent"

    @transaction.atomic
    def handle(self, *args, **opts):
        self.courses()
        self.music()
        self.education_history()
        self.stdout.write(self.style.SUCCESS("Qo'shimcha demo kontent tayyor"))

    def courses(self):
        skills = {s.name: s for s in Skill.objects.all()}
        for spec in COURSES:
            c = Course.objects.filter(slug=spec["slug"]).first()
            if c:
                continue
            c = Course(slug=spec["slug"], level=spec["level"], is_free=spec["free"], price=spec.get("price", 0),
                       status="published", is_featured=spec["order"] <= 2, sequential=True, order=spec["order"])
            tr_ure(c, "title", *spec["title"])
            tr_ure(c, "subtitle", *spec["subtitle"])
            tr(c, "description", f"<p>{spec['subtitle'][0]}</p><p>Har bir dars: video, konspekt, kod misollari va uyga vazifa. "
                                 "Keyingi dars oldingisi tugatilgandan keyin ochiladi.</p>",
               f"<p>{spec['subtitle'][2]}</p><p>Every lesson: video, notes, code samples and homework.</p>",
               f"<p>{spec['subtitle'][1]}</p><p>Каждый урок: видео, конспект, примеры кода и домашнее задание.</p>")
            tr(c, "what_you_learn", "<ul>" + "".join(f"<li>{t}</li>" for _m, ls in spec["modules"] for t in ls[:2]) + "</ul>")
            tr(c, "for_whom", "<ul><li>Dasturlashni o'rganayotganlar</li><li>Junior dasturchilar</li><li>Amaliy loyiha qilmoqchi bo'lganlar</li></ul>",
               "<ul><li>Programming learners</li><li>Junior developers</li><li>Anyone who wants a hands-on project</li></ul>",
               "<ul><li>Изучающие программирование</li><li>Junior-разработчики</li><li>Те, кто хочет практический проект</li></ul>")
            tr(c, "requirements", "<ul><li>Kompyuter va internet</li><li>O'rganishga ishtiyoq</li></ul>",
               "<ul><li>A computer and internet</li><li>Willingness to learn</li></ul>",
               "<ul><li>Компьютер и интернет</li><li>Желание учиться</li></ul>")
            c.cover.save(f"{spec['slug']}.jpg", ph.app_screenshot(spec["seed"], spec["title"][2].split(":")[0], spec["subtitle"][2][:40]), save=False)
            c.save()
            c.technologies.set([skills[n] for n in spec["skills"] if n in skills])
            order = 0
            for mi, (mtitle, lessons) in enumerate(spec["modules"], start=1):
                m = Module(course=c, order=mi)
                tr(m, "title", mtitle)
                m.save()
                for title in lessons:
                    order += 1
                    hw = "none" if order == 1 else ("submit" if order % 3 else "approval")
                    les = Lesson(course=c, module=m, order=order, status="published", is_preview=order == 1,
                                 video_url=YT, duration_seconds=360 + (order * 137) % 900, homework_mode=hw)
                    tr(les, "title", title)
                    tr(les, "summary", f"{order}-dars: {title}")
                    tr(les, "content", f"<h2>Dars rejasi</h2><p>Bu darsda «{title}» mavzusini amaliy misollar bilan ko'rib chiqamiz.</p>"
                                       f"<h2>Kod</h2>{spec['code']}<blockquote><p>Maslahat: kodni o'zingiz yozib ko'ring — nusxalamang.</p></blockquote>")
                    if hw != "none":
                        tr(les, "homework", "<p>Darsdagi misolni o'zgartirib, natijani GitHub'ga joylang va repo havolasini yuboring.</p>")
                    les.save()
                    r = LessonResource(lesson=les, kind="docs", url="https://docs.python.org/3/", order=0)
                    tr(r, "title", "Rasmiy hujjatlar")
                    r.save()
        bs = BotSettings.load()
        bs.save()

    def music(self):
        cats = {c.name_en or c.name: c for c in MediaCategory.objects.filter(kind="music")}
        for name in ("Focus", "Chill", "Travel", "Coding"):
            if name not in cats:
                c = MediaCategory(kind="music", slug=name.lower())
                tr(c, "name", name)
                c.save()
                cats[name] = c
        for i, (title, artist, album, year, cat, note) in enumerate(FAVORITE_SONGS):
            if Track.objects.filter(title=title, artist=artist).exists():
                continue
            t = Track(title=title, artist=artist, album=album, year=year, category=cats.get(cat), is_favorite=i < 3, order=10 + i,
                      external_url=f"https://open.spotify.com/search/{quote_plus(f'{title} {artist}')}")
            tr(t, "note", note)
            t.cover.save(f"fav-{i}.jpg", ph.landscape(120 + i, size=(400, 400)), save=False)
            t.save()
        # Pleyerni sinash uchun o'zimizning ambient treklar
        for i, title in enumerate(["Night Code", "Deep Work", "Mountain Air"]):
            if Track.objects.filter(title=title, artist="WeliCoDev Ambient").exists():
                continue
            t = Track(title=title, artist="WeliCoDev Ambient", album="Focus Sessions", year=2026, category=cats["Coding"], duration="0:18", order=20 + i)
            tr(t, "note", "Demo trek: o'zingizning musiqangiz bilan almashtiring")
            t.audio.save(f"ambient-{i}.wav", ph.ambient_wav(10 + i), save=False)
            t.cover.save(f"ambient-{i}.jpg", ph.landscape(140 + i, size=(400, 400)), save=False)
            t.save()
        if not Playlist.objects.filter(title_en="Deep Focus").exists():
            pl = Playlist(order=0)
            tr(pl, "title", "Chuqur fokus", "Deep Focus", "Глубокий фокус")
            pl.cover.save("deep-focus.jpg", ph.landscape(150, size=(500, 400)), save=False)
            pl.save()
            pl.tracks.set(Track.objects.filter(category__in=[cats["Focus"], cats["Coding"]]))

    def education_history(self):
        Experience.objects.filter(kind="education", company="Self Learning").delete()
        skills = {s.name: s for s in Skill.objects.all()}
        entries = [
            dict(
                company="Termiz shahar matematika va fizikaga ixtisoslashtirilgan maktab-internati", slug="termiz-maktab-internati",
                start=date(2014, 9, 1), end=date(2021, 6, 30), order=20,
                role=("O'quvchi", "Ученик", "Student"),
                degree=("Umumiy o'rta ta'lim", "Общее среднее образование", "Secondary education"),
                field=("Matematika va fizika", "Математика и физика", "Mathematics and Physics"),
                location=("Termiz, Surxondaryo", "Термез, Сурхандарья", "Termez, Surkhandarya"),
                summary=("Matematika va fizika chuqurlashtirilgan dastur asosida o'qidim. Mantiqiy fikrlash va masala yechish ko'nikmalarim shu yerda shakllandi.",
                         "Учился по углублённой программе математики и физики. Здесь сформировались навыки логического мышления и решения задач.",
                         "Studied an advanced mathematics and physics curriculum, where my logical thinking and problem-solving skills took shape."),
                tech=[],
            ),
            dict(
                company="Toshkent axborot texnologiyalari universiteti (TATU)", slug="tatu",
                start=date(2021, 9, 1), end=date(2025, 6, 30), order=10, website="https://tuit.uz",
                role=("Talaba", "Студент", "Student"),
                degree=("Bakalavr", "Бакалавр", "Bachelor's degree"),
                field=("Dasturiy injiniring fakulteti", "Факультет программной инженерии", "Faculty of Software Engineering"),
                location=("Toshkent", "Ташкент", "Tashkent"),
                summary=("Dasturiy injiniring yo'nalishida bakalavr. Algoritmlar, ma'lumotlar bazasi, tarmoqlar va dasturiy ta'minot arxitekturasini o'rgandim.",
                         "Бакалавриат по программной инженерии: алгоритмы, базы данных, сети и архитектура ПО.",
                         "Bachelor's in Software Engineering: algorithms, databases, networking and software architecture."),
                tech=["Python", "PostgreSQL", "Git", "Linux"],
            ),
        ]
        for e in entries:
            obj = Experience.objects.filter(slug=e["slug"]).first() or Experience(slug=e["slug"])
            obj.company, obj.kind, obj.start_date, obj.end_date, obj.order = e["company"], "education", e["start"], e["end"], e["order"]
            obj.website = e.get("website", "")
            tr_ure(obj, "role", *e["role"])
            tr_ure(obj, "degree", *e["degree"])
            tr_ure(obj, "field_of_study", *e["field"])
            tr_ure(obj, "location", *e["location"])
            tr_ure(obj, "summary", *e["summary"])
            tr(obj, "description", f"<p>{e['summary'][0]}</p>", f"<p>{e['summary'][2]}</p>", f"<p>{e['summary'][1]}</p>")
            if not obj.logo:
                obj.logo.save(f"{e['slug']}.jpg", ph.logo_tile(6 if e["slug"] == "tatu" else 4, "TATU" if e["slug"] == "tatu" else "TM"), save=False)
            obj.save()
            obj.technologies.set([skills[n] for n in e["tech"] if n in skills])
