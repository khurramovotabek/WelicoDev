"""Otabekning haqiqiy profili: ko'nikmalar, ta'lim, ish tajribasi, loyihalar, hayot yo'li va kurslar.

Takror ishga tushirilsa ma'lumotlarni yangilaydi (dublikat yaratmaydi). Demo loyiha/tajribalar o'chiriladi.

    python manage.py seed_profile
"""

from datetime import date

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core import placeholders as ph
from apps.core.models import PageHero, Role, SiteSettings, SocialLink
from apps.education.models import Course, Lesson, LessonResource, Module
from apps.portfolio.models import (
    Experience, JourneyStep, Milestone, Project, ProjectCategory, ProjectFeature, Responsibility, Skill, SkillCategory,
)

from .seed_demo import tags, tr

YT = "https://www.youtube.com/watch?v=pg19Z8LL06w"

# (nom, devicon, daraja, %, yil, asosiy, qisqa izoh uz/en/ru)
SKILLS = [
    (("Dasturlash tillari", "Programming Languages", "Языки программирования"), "languages", [
        ("C++", "cplusplus", "advanced", 80, 5, False, ("Algoritmlar va OOP", "Algorithms & OOP", "Алгоритмы и ООП")),
        ("Python", "python", "expert", 92, 5, True, ("Asosiy til", "Primary language", "Основной язык")),
        ("JavaScript", "javascript", "advanced", 80, 4, True, ("Veb va interaktivlik", "Web & interactivity", "Веб и интерактив")),
        ("TypeScript", "typescript", "intermediate", 68, 2, False, ("Tiplangan JavaScript", "Typed JavaScript", "Типизированный JS")),
        ("SQL", "wcd:sql", "advanced", 85, 4, False, ("So'rovlar va optimizatsiya", "Queries & optimisation", "Запросы и оптимизация")),
    ]),
    (("Backend", "Backend Development", "Backend-разработка"), "backend", [
        ("Django", "django-plain", "expert", 92, 4, True, ("Web Framework", "Web Framework", "Веб-фреймворк")),
        ("Django REST Framework", "djangorest-original", "advanced", 88, 3, True, ("REST API'lar", "REST APIs", "REST API")),
        ("REST API", "wcd:rest-api", "advanced", 88, 4, False, ("API dizayn", "API design", "Проектирование API")),
        ("PostgreSQL", "postgresql", "advanced", 85, 4, True, ("Ma'lumotlar bazasi", "Database", "База данных")),
        ("Redis", "redis", "advanced", 78, 3, False, ("Kesh va navbatlar", "Cache & queues", "Кэш и очереди")),
        ("Celery", "wcd:celery", "advanced", 78, 3, False, ("Fon vazifalari", "Background jobs", "Фоновые задачи")),
        ("aiogram", "wcd:aiogram", "advanced", 85, 3, True, ("Telegram botlar", "Telegram bots", "Telegram-боты")),
    ]),
    (("Frontend", "Frontend Development", "Frontend-разработка"), "frontend", [
        ("HTML5", "html5", "advanced", 88, 5, False, ("Semantik belgilash", "Semantic markup", "Семантическая разметка")),
        ("CSS3", "css3", "advanced", 84, 5, False, ("Tailwind, animatsiya", "Tailwind, animation", "Tailwind, анимация")),
        ("React", "react", "intermediate", 70, 2, False, ("UI kutubxona", "UI library", "UI-библиотека")),
        ("Next.js", "wcd:nextjs", "intermediate", 64, 1, False, ("SSR va SEO", "SSR & SEO", "SSR и SEO")),
    ]),
    (("DevOps va infratuzilma", "DevOps & Infrastructure", "DevOps и инфраструктура"), "devops", [
        ("Docker", "docker", "advanced", 85, 3, True, ("Konteynerlar", "Containers", "Контейнеры")),
        ("Docker Compose", "docker-plain", "advanced", 85, 3, False, ("Ko'p servisli muhit", "Multi-service stacks", "Многосервисные стеки")),
        ("Nginx", "nginx", "advanced", 76, 3, False, ("Reverse proxy, SSL", "Reverse proxy, SSL", "Reverse proxy, SSL")),
        ("Linux / Ubuntu", "ubuntu", "advanced", 80, 4, False, ("Server boshqaruvi", "Server administration", "Администрирование")),
        ("Git", "git", "advanced", 88, 5, False, ("Versiya nazorati", "Version control", "Контроль версий")),
        ("GitHub", "wcd:github", "advanced", 88, 5, False, ("PR, Actions, code review", "PRs, Actions, code review", "PR, Actions, ревью")),
        ("VPS Deployment", "wcd:vps", "advanced", 80, 3, False, ("Production deploy", "Production deploys", "Деплой в продакшен")),
    ]),
    (("AI va samaradorlik", "AI & Productivity", "AI и продуктивность"), "ai", [
        ("AI-Assisted Development", "wcd:ai", "advanced", 86, 2, True, ("Claude, Copilot bilan tez ishlash", "Shipping faster with AI", "Разработка с AI")),
        ("Prompt Engineering", "wcd:prompt", "advanced", 82, 2, False, ("Aniq natija beruvchi promptlar", "Prompts that deliver", "Эффективные промпты")),
    ]),
]

CATEGORIES = {
    "university": ("Universitet loyihalari", "University projects", "Университетские проекты"),
    "commercial": ("Tijorat loyihalari", "Commercial projects", "Коммерческие проекты"),
    "startup": ("Startap", "Startup", "Стартап"),
}

# slug, kategoriya, nom, shior uz/en/ru, tavsif uz/en/ru, texnologiyalar, teglar, yil, rol, seed, live
PROJECTS = [
    ("nutrizone", "startup", "NutriZone", ("Aqlli ovqatlanish ekotizimi", "Smart nutrition ecosystem", "Умная экосистема питания"),
     ("Sport ovqatlanishi va sog'lom turmush tarzi uchun marketplace, kaloriya hisoblagich va Telegram bot. Men asoschi va CEO sifatida mahsulot, jamoa va texnik arxitekturani boshqaraman.",
      "A marketplace, calorie tracker and Telegram bot for sports nutrition and healthy living. As founder & CEO I lead the product, team and architecture.",
      "Маркетплейс, счётчик калорий и Telegram-бот для спортивного питания. Как основатель и CEO руковожу продуктом, командой и архитектурой."),
     ["Django", "Django REST Framework", "PostgreSQL", "Redis", "Celery", "aiogram", "Docker", "Next.js"], ["Web", "Mobile", "API", "Startup"], 2025, "Founder & CEO", 0, "https://nutrizone.uz"),
    ("tift-referral", "commercial", "TIFT Referral", ("Referal tizimi tift.uz uchun", "Referral system for tift.uz", "Реферальная система tift.uz"),
     ("Universitet uchun referal platformasi: abituriyent taklif qilganlarga bonuslar, shaxsiy kabinet, statistika va to'lovlar hisobi.",
      "A referral platform for tift.uz: rewards for applicant referrals, personal cabinet, analytics and payouts.",
      "Реферальная платформа tift.uz: бонусы за приглашённых абитуриентов, кабинет, аналитика и выплаты."),
     ["Django", "Django REST Framework", "PostgreSQL", "Celery", "Docker"], ["Web", "Analytics"], 2025, "Backend Developer", 3, "https://tift.uz"),
    ("clamo", "commercial", "Clamo", ("Xizmatlar uchun buyurtma platformasi", "Service ordering platform", "Платформа заказа услуг"),
     ("UIC Group'dagi loyiha: mijozlar va ijrochilarni bog'lovchi platforma uchun REST API, rollar va to'lov integratsiyasi.",
      "A UIC Group project: REST API, roles and payment integration for a platform connecting clients and providers.",
      "Проект UIC Group: REST API, роли и интеграция оплаты для платформы клиентов и исполнителей."),
     ["Django", "Django REST Framework", "PostgreSQL", "Redis"], ["API", "Web"], 2025, "Backend Developer", 1, ""),
    ("iwatt", "commercial", "Iwatt", ("Elektromobil quvvatlash tarmog'i", "EV charging network", "Сеть зарядки электромобилей"),
     ("Quvvatlash stansiyalarini bron qilish, sessiyalarni kuzatish va to'lov uchun mobil ilova backend'i.",
      "Backend for a mobile app to book charging stations, track sessions and pay.",
      "Бэкенд мобильного приложения для бронирования зарядных станций, сессий и оплаты."),
     ["Django", "Django REST Framework", "PostgreSQL", "Celery", "Docker"], ["Mobile", "API"], 2025, "Backend Developer", 2, ""),
    ("ixlos-nuri", "commercial", "Ixlos Nuri", ("Ta'lim va xayriya platformasi", "Education & charity platform", "Образовательная платформа"),
     ("Kurslar, video darslar va xayriya loyihalari uchun platforma: kontent boshqaruvi, foydalanuvchilar va bildirishnomalar.",
      "A platform for courses, video lessons and charity projects: content management, users and notifications.",
      "Платформа курсов, видеоуроков и благотворительности: контент, пользователи, уведомления."),
     ["Django", "PostgreSQL", "Redis", "aiogram"], ["Web", "Education"], 2025, "Backend Developer", 4, ""),
    ("goinvest", "commercial", "Goinvest", ("Investitsiya loyihalari platformasi", "Investment projects platform", "Платформа инвестпроектов"),
     ("Investorlar va startaplarni bog'lovchi platforma: loyiha kartalari, arizalar, admin panel va hisobotlar.",
      "A platform connecting investors and startups: project listings, applications, admin panel and reports.",
      "Платформа для инвесторов и стартапов: карточки проектов, заявки, админка и отчёты."),
     ["Django", "Django REST Framework", "PostgreSQL"], ["Web", "Fintech"], 2025, "Backend Developer", 5, ""),
    ("marjon", "commercial", "Marjon", ("Onlayn do'kon va CRM", "E-commerce & CRM", "Интернет-магазин и CRM"),
     ("Do'kon uchun katalog, buyurtmalar, yetkazib berish va CRM. Telegram bot orqali buyurtma holati.",
      "Catalog, orders, delivery and CRM for a retail business, with order status via Telegram bot.",
      "Каталог, заказы, доставка и CRM; статус заказа через Telegram-бота."),
     ["Django", "PostgreSQL", "aiogram", "Docker"], ["Web", "E-commerce"], 2025, "Backend Developer", 6, ""),
    ("sharebooks", "university", "ShareBooks", ("Kitob almashish platformasi", "Book sharing platform", "Платформа обмена книгами"),
     ("Talabalar kitob almashishi va ijaraga berishi uchun platforma: qidiruv, so'rovlar va reyting.",
      "A platform for students to swap and lend books: search, requests and ratings.",
      "Платформа обмена книгами для студентов: поиск, заявки и рейтинг."),
     ["Django", "PostgreSQL", "JavaScript"], ["Web", "Community"], 2023, "Full-stack Developer", 7, ""),
    ("myzoomapp", "university", "MyZoomApp", ("Videokonferensiya ilovasi", "Video conferencing app", "Видеоконференции"),
     ("WebRTC asosidagi videokonferensiya: xonalar, ekranni ulashish va chat.",
      "WebRTC-based video conferencing: rooms, screen sharing and chat.",
      "Видеоконференции на WebRTC: комнаты, демонстрация экрана и чат."),
     ["Python", "Django", "JavaScript"], ["Web", "Realtime"], 2023, "Full-stack Developer", 8, ""),
    ("myframework", "university", "MyFramework", ("O'z veb-freymvorkim", "My own web framework", "Собственный веб-фреймворк"),
     ("WSGI ustida noldan yozilgan mini-freymvork: routing, middleware va shablonlar — freymvorklar ichini tushunish uchun.",
      "A mini framework built from scratch on WSGI: routing, middleware and templates — to understand how frameworks work.",
      "Мини-фреймворк на WSGI с нуля: роутинг, middleware и шаблоны."),
     ["Python"], ["Open Source"], 2023, "Author", 9, ""),
    ("instagram-clone", "university", "Instagram Clone", ("Ijtimoiy tarmoq kloni", "Social network clone", "Клон соцсети"),
     ("Postlar, obunalar, layklar, izohlar va lenta. REST API va JWT autentifikatsiya.",
      "Posts, follows, likes, comments and a feed. REST API with JWT auth.",
      "Посты, подписки, лайки, комментарии и лента. REST API и JWT."),
     ["Django", "Django REST Framework", "PostgreSQL"], ["API", "Social"], 2023, "Backend Developer", 10, ""),
    ("metsenat", "university", "Metsenat App", ("Homiylik platformasi", "Sponsorship platform", "Платформа меценатов"),
     ("Talabalarga homiylik qilish tizimi: homiylar, talabalar, ajratilgan mablag'lar va admin dashboard.",
      "A student sponsorship system: sponsors, students, allocations and an admin dashboard.",
      "Система спонсорства студентов: спонсоры, студенты, распределение средств."),
     ["Django", "Django REST Framework", "PostgreSQL"], ["API", "Dashboard"], 2024, "Backend Developer", 11, ""),
    ("opencv-vision", "university", "OpenCV Vision", ("Kompyuter ko'rish loyihasi", "Computer vision project", "Компьютерное зрение"),
     ("OpenCV bilan yuzni aniqlash va obyektlarni kuzatish: kamera oqimi, filtrlash va natijalarni saqlash.",
      "Face detection and object tracking with OpenCV: camera stream, filtering and result logging.",
      "Распознавание лиц и трекинг объектов на OpenCV."),
     ["Python", "C++"], ["AI", "Vision"], 2023, "Developer", 12, ""),
    ("game", "university", "Arcade Game", ("2D o'yin", "2D game", "2D-игра"),
     ("C++ va Python'da yozilgan 2D arkada o'yini: fizika, darajalar va rekordlar jadvali.",
      "A 2D arcade game: physics, levels and a leaderboard.",
      "2D аркада: физика, уровни и таблица рекордов."),
     ["C++", "Python"], ["Game"], 2022, "Developer", 13, ""),
    ("uztest", "university", "UzTest App", ("Onlayn test tizimi", "Online testing system", "Система онлайн-тестов"),
     ("Abituriyentlar uchun test platformasi: fanlar bo'yicha testlar, taymer, natijalar tahlili.",
      "A test platform for applicants: subject tests, timer and result analytics.",
      "Тестовая платформа для абитуриентов: тесты, таймер и аналитика."),
     ["Django", "PostgreSQL", "JavaScript"], ["Web", "Education"], 2022, "Full-stack Developer", 14, ""),
    ("delivery-app", "university", "Delivery App", ("Yetkazib berish xizmati", "Delivery service", "Сервис доставки"),
     ("Buyurtma, kuryer va restoran rollari, xaritada kuzatish va Telegram bildirishnomalari.",
      "Orders, courier and restaurant roles, live map tracking and Telegram notifications.",
      "Заказы, роли курьера и ресторана, карта и уведомления в Telegram."),
     ["Django", "Django REST Framework", "PostgreSQL", "aiogram"], ["API", "Mobile"], 2024, "Backend Developer", 15, ""),
    ("translator-bot", "university", "Translator Bot", ("Tarjimon Telegram bot", "Translator Telegram bot", "Бот-переводчик"),
     ("Matn va ovozli xabarlarni o'zbek, rus va ingliz tillariga tarjima qiluvchi Telegram bot.",
      "A Telegram bot that translates text and voice messages between Uzbek, Russian and English.",
      "Telegram-бот для перевода текста и голосовых между узбекским, русским и английским."),
     ["Python", "aiogram", "Redis"], ["Bot"], 2022, "Developer", 16, ""),
]


def d(y, m, day=1):
    return date(y, m, day)


# (slug, kind, kompaniya, rol uz/en/ru, start, end, current, joy uz/en/ru, qisqa uz/en/ru, vazifalar, texnologiyalar, loyihalar, sayt, soha)
EXPERIENCES = [
    ("life-nutrition", "work", "LIFE Nutrition", ("Sales Manager va Marketplace Manager", "Sales Manager & Marketplace Manager", "Sales-менеджер и менеджер маркетплейсов"),
     d(2026, 7), None, True, ("Toshkent", "Tashkent", "Ташкент"),
     ("Sport ovqatlanishi brendida savdo va marketplace yo'nalishini boshqaraman: Uzum, Wildberries va boshqa platformalarda do'konlar, narx siyosati va o'sish.",
      "I lead sales and marketplace operations for a sports nutrition brand: Uzum, Wildberries and other stores, pricing and growth.",
      "Руковожу продажами и маркетплейсами бренда спортивного питания: Uzum, Wildberries, ценообразование и рост."),
     ["Marketplace do'konlarini boshqarish va kartochkalarni optimizatsiya qilish", "Savdo rejasi, narx va aksiyalar", "Analitika va hisobotlar"],
     ["AI-Assisted Development", "Prompt Engineering"], [], "", ("Sport ovqatlanishi", "Sports nutrition", "Спортивное питание")),
    ("openshop", "work", "OpenShop", ("Marketplace Manager", "Marketplace Manager", "Менеджер маркетплейсов"),
     d(2026, 6), d(2026, 7, 15), False, ("Toshkent", "Tashkent", "Ташкент"),
     ("Onlayn savdo jamoasida marketplace'lardagi do'konlarni yuritish va mahsulot kartochkalarini tayyorlash.",
      "Ran marketplace stores and prepared product listings in an e-commerce team.",
      "Вёл магазины на маркетплейсах и готовил карточки товаров."),
     ["Mahsulot kartochkalari va kontent", "Buyurtmalar va qoldiqlar nazorati"], [], [], "", ("E-commerce", "E-commerce", "E-commerce")),
    ("life-sport", "work", "LIFE Sport", ("Sales Manager", "Sales Manager", "Sales-менеджер"),
     d(2025, 10), d(2026, 5, 31), False, ("Toshkent", "Tashkent", "Ташкент"),
     ("Sport mahsulotlari savdosi, mijozlar bilan ishlash va savdo jarayonlarini avtomatlashtirish.",
      "Sports products sales, client relations and automating sales workflows.",
      "Продажи спортивных товаров, работа с клиентами и автоматизация продаж."),
     ["B2B va B2C savdo", "CRM va Telegram orqali avtomatlashtirish"], ["Python", "aiogram"], [], "", ("Sport", "Sports", "Спорт")),
    ("nutrizone-startup", "startup", "NutriZone", ("Asoschi va CEO", "Founder & CEO", "Основатель и CEO"),
     d(2025, 3), None, True, ("Toshkent", "Tashkent", "Ташкент"),
     ("nutrizone.uz — sport ovqatlanishi ekotizimi. Mahsulot g'oyasidan MVP va jamoagacha: arxitektura, backend, bot va o'sish strategiyasi.",
      "nutrizone.uz — a sports nutrition ecosystem. From idea to MVP and team: architecture, backend, bot and growth strategy.",
      "nutrizone.uz — экосистема спортивного питания: от идеи до MVP и команды."),
     ["Mahsulot strategiyasi va roadmap", "Backend arxitektura va infratuzilma", "Jamoa va hamkorlar bilan ishlash"],
     ["Django", "Django REST Framework", "PostgreSQL", "Redis", "Celery", "aiogram", "Docker", "Next.js"], ["nutrizone"], "https://nutrizone.uz",
     ("Startap · HealthTech", "Startup · HealthTech", "Стартап · HealthTech")),
    ("uic-group", "work", "UIC Group", ("Python Backend Developer", "Python Backend Developer", "Python Backend-разработчик"),
     d(2025, 2), d(2025, 10, 15), False, ("Toshkent", "Tashkent", "Ташкент"),
     ("IT kompaniyada mijozlar uchun loyihalar: Clamo, Iwatt, Ixlos Nuri, Goinvest, Marjon va tift.uz referal tizimi.",
      "Client projects at an IT company: Clamo, Iwatt, Ixlos Nuri, Goinvest, Marjon and the tift.uz referral system.",
      "Клиентские проекты в IT-компании: Clamo, Iwatt, Ixlos Nuri, Goinvest, Marjon и реферальная система tift.uz."),
     ["REST API va biznes logika", "PostgreSQL sxemalari va optimizatsiya", "Celery bilan fon vazifalari", "Docker bilan deploy", "Code review va jamoaviy ishlash"],
     ["Django", "Django REST Framework", "PostgreSQL", "Redis", "Celery", "Docker", "Git"],
     ["clamo", "iwatt", "ixlos-nuri", "goinvest", "marjon", "tift-referral"], "https://uic.group", ("IT xizmatlar", "IT services", "IT-услуги")),
]

EDUCATION = [
    dict(slug="tatu", company="Toshkent axborot texnologiyalari universiteti (TATU)", start=d(2021, 9), end=d(2025, 6, 30), order=10,
         website="https://tuit.uz", grade="4.0 / 5",
         role=("Talaba", "Student", "Студент"), degree=("Bakalavr", "Bachelor's degree", "Бакалавр"),
         field=("Dasturiy injiniring fakulteti", "Faculty of Software Engineering", "Факультет программной инженерии"),
         location=("Toshkent", "Tashkent", "Ташкент"),
         summary=("Dasturiy injiniring bo'yicha bakalavr (o'rtacha baho 4). C++, Python, JavaScript, algoritmlar, tizimlar, dizayn, matematika va fizika; Flutter bilan mobil dasturlash asoslari.",
                  "Bachelor's in Software Engineering (average grade 4). C++, Python, JavaScript, algorithms, systems, design, mathematics and physics; Flutter mobile basics.",
                  "Бакалавр программной инженерии (средний балл 4). C++, Python, JavaScript, алгоритмы, системы, дизайн, математика и физика; основы Flutter."),
         achievements="<ul><li>ShareBooks, MyZoomApp, MyFramework, Instagram Clone</li><li>Metsenat App, OpenCV Vision, Arcade Game</li><li>UzTest App, Delivery App, Translator Bot</li></ul>",
         tech=["C++", "Python", "JavaScript", "SQL", "Git"], logo=("TATU", 6)),
    dict(slug="pdp-academy", company="PDP Academy", start=d(2022, 2), end=d(2022, 8, 31), order=15, website="https://pdp.uz", grade="",
         role=("Tinglovchi", "Student", "Слушатель"), degree=("Kurs", "Course", "Курс"),
         field=("Backend dasturlash (Python)", "Backend development (Python)", "Backend-разработка (Python)"),
         location=("Toshkent", "Tashkent", "Ташкент"),
         summary=("Professional dasturlash yo'lim shu yerda boshlandi: Python, OOP, ma'lumotlar bazasi, Git va jamoada loyiha qilish.",
                  "Where my professional path started: Python, OOP, databases, Git and team projects.",
                  "Здесь начался мой профессиональный путь: Python, ООП, базы данных, Git и командные проекты."),
         achievements="", tech=["Python", "SQL", "Git"], logo=("PDP", 2)),
    dict(slug="termiz-maktab-internati", company="Termiz shahridagi Al-Hakim at-Termiziy nomidagi 1-sonli ixtisoslashtirilgan maktab-internati",
         start=d(2014, 9), end=d(2021, 6, 30), order=20, website="", grade="",
         role=("O'quvchi", "Student", "Ученик"),
         degree=("Umumiy o'rta ta'lim", "Secondary education", "Общее среднее образование"),
         field=("Matematika, fizika, informatika va ingliz tili", "Mathematics, physics, computer science and English", "Математика, физика, информатика и английский"),
         location=("Termiz, Surxondaryo", "Termez, Surkhandarya", "Термез, Сурхандарья"),
         summary=("Matematika va fizikaga ixtisoslashtirilgan maktab-internat: chuqurlashtirilgan matematika, fizika, informatika va ingliz tili. Mantiqiy fikrlash poydevori shu yerda qo'yildi.",
                  "A boarding school specialising in mathematics and physics, with advanced maths, physics, computer science and English — the foundation of my logical thinking.",
                  "Специализированная школа-интернат: углублённые математика, физика, информатика и английский язык."),
         achievements="", tech=["C++"], logo=("AT", 4)),
]

JOURNEY = [
    (2014, ("Al-Hakim at-Termiziy maktab-internati", "Al-Hakim at-Termiziy boarding school", "Школа-интернат им. ат-Термизи")),
    (2021, ("Dasturlashni boshladim · TATU", "Started programming · TUIT", "Начал программировать · ТУИТ")),
    (2022, ("PDP Academy", "PDP Academy", "PDP Academy")),
    (2025, ("UIC Group va NutriZone startapi", "UIC Group & the NutriZone startup", "UIC Group и стартап NutriZone")),
    (2026, ("LIFE Nutrition: Sales va Marketplace", "LIFE Nutrition: sales & marketplaces", "LIFE Nutrition: продажи и маркетплейсы")),
]

# Yangi kurslar: (slug, tartib, daraja, bepul, narx, eski narx, yopiq, seed, nom, shior, ko'nikmalar, modullar)
NEW_COURSES = [
    ("cpp-va-algoritmlar", 3, "beginner", True, 0, None, False, 7,
     ("C++ va algoritmlar", "C++ and algorithms", "C++ и алгоритмы"),
     ("Olimpiada va intervyu uchun: murakkablik, saralash, graflar va dinamik dasturlash.", "For contests and interviews: complexity, sorting, graphs and DP.", "Для олимпиад и собеседований: сложность, сортировки, графы и ДП."),
     ["C++"], [("Asoslar", ["C++ sintaksisi va STL", "Murakkablik: Big-O"]), ("Algoritmlar", ["Saralash va qidiruv", "Graflar: BFS va DFS", "Dinamik dasturlash"])]),
    ("javascript-typescript", 8, "beginner", True, 0, None, False, 9,
     ("JavaScript va TypeScript", "JavaScript and TypeScript", "JavaScript и TypeScript"),
     ("Zamonaviy JS: DOM, async/await, modullar va TypeScript bilan xavfsiz kod.", "Modern JS: DOM, async/await, modules and safe code with TypeScript.", "Современный JS: DOM, async/await, модули и TypeScript."),
     ["JavaScript", "TypeScript"], [("JavaScript", ["O'zgaruvchilar va funksiyalar", "DOM va hodisalar", "Async/await va fetch"]), ("TypeScript", ["Tiplar va interfeyslar", "Loyihani TypeScript'ga o'tkazish"])]),
    ("react-va-nextjs", 9, "intermediate", False, 349000, 499000, False, 10,
     ("React va Next.js: zamonaviy frontend", "React and Next.js: modern frontend", "React и Next.js: современный фронтенд"),
     ("Komponentlar, hooklar, SSR, SEO va Django API bilan to'liq loyiha.", "Components, hooks, SSR, SEO and a full project with a Django API.", "Компоненты, хуки, SSR, SEO и полный проект с Django API."),
     ["React", "Next.js", "TypeScript"], [("React", ["Komponentlar va props", "Hooklar: useState, useEffect", "Formalar va state"]), ("Next.js", ["Routing va layoutlar", "SSR, SSG va SEO", "Django REST API bilan ulash", "Vercel va VPS'ga deploy"])]),
    ("linux-nginx-vps-deploy", 10, "intermediate", False, 299000, 399000, False, 11,
     ("Linux, Nginx va VPS deploy", "Linux, Nginx and VPS deployment", "Linux, Nginx и деплой на VPS"),
     ("Django loyihani serverga chiqarish: Ubuntu, Docker Compose, Nginx, SSL, backup va monitoring.", "Ship Django to a server: Ubuntu, Docker Compose, Nginx, SSL, backups and monitoring.", "Деплой Django: Ubuntu, Docker Compose, Nginx, SSL, бэкапы и мониторинг."),
     ["Linux / Ubuntu", "Nginx", "Docker", "Docker Compose", "VPS Deployment"], [("Server", ["VPS tanlash va SSH", "Ubuntu: foydalanuvchi, firewall", "Docker Compose bilan stek"]), ("Production", ["Nginx va SSL (Let's Encrypt)", "CI/CD: GitHub Actions", "Backup va monitoring"])]),
    ("ai-bilan-dasturlash", 11, "intermediate", False, 249000, None, False, 12,
     ("AI bilan dasturlash: Prompt Engineering", "AI-assisted development & prompt engineering", "Разработка с AI и промпт-инжиниринг"),
     ("Claude va boshqa AI vositalari bilan 3x tez ishlash: promptlar, kod review, test va hujjatlar.", "Ship 3x faster with Claude and other AI tools: prompts, code review, tests and docs.", "Работайте в 3 раза быстрее с Claude: промпты, ревью, тесты и документация."),
     ["AI-Assisted Development", "Prompt Engineering"], [("Asoslar", ["AI vositalari xaritasi", "Yaxshi prompt anatomiyasi"]), ("Amaliyot", ["AI bilan kod yozish va review", "Test va hujjatlarni avtomatlashtirish", "AI agentlar bilan ishlash"])]),
    ("marketplace-savdo", 12, "beginner", False, 199000, 290000, False, 13,
     ("Marketplace'da savdo: Uzum va Wildberries", "Selling on marketplaces: Uzum & Wildberries", "Продажи на маркетплейсах: Uzum и Wildberries"),
     ("Do'kon ochish, kartochka, narx, reklama va analitika — LIFE Nutrition tajribasi asosida.", "Opening a store, listings, pricing, ads and analytics — from LIFE Nutrition experience.", "Магазин, карточки, цены, реклама и аналитика — на опыте LIFE Nutrition."),
     [], [("Start", ["Marketplace'lar va biznes modeli", "Do'kon ochish va hujjatlar"]), ("O'sish", ["Sotadigan kartochka", "Narx va aksiyalar", "Reklama va analitika"])]),
    ("startup-goyadan-mvpgacha", 13, "advanced", False, 590000, None, True, 0,
     ("StartUp: g'oyadan MVP'gacha", "Startup: from idea to MVP", "Стартап: от идеи до MVP"),
     ("Yopiq kurs: NutriZone misolida g'oyani tekshirish, MVP qurish, jamoa va investitsiya.", "Private course: validating ideas, building an MVP, team and fundraising — the NutriZone case.", "Закрытый курс: проверка идеи, MVP, команда и инвестиции на примере NutriZone."),
     ["Django", "AI-Assisted Development"], [("G'oya", ["Muammo va mijozni topish", "G'oyani tekshirish"]), ("MVP", ["MVP arxitekturasi", "Birinchi 100 foydalanuvchi", "Investorlar bilan ishlash"])]),
]

# Mavjud kurslar: tarjimalarni to'g'rilash, nashr qilish va narx
EXISTING_COURSES = {
    "python-asoslari": dict(status="published", is_free=True),
    "django-noldan-productiongacha": dict(status="published", is_free=False, price=349000, old_price=490000),
    "postgresql-va-sql-amaliyoti": dict(status="published", is_free=True),
    "telegram-bot-aiogram-3": dict(status="published", is_free=False, price=249000, old_price=None),
    "git-va-github": dict(status="published", is_free=True),
    "system-design-asoslari": dict(status="published", is_free=False, price=299000, old_price=399000),
}


class Command(BaseCommand):
    help = "Haqiqiy profil ma'lumotlari: ko'nikmalar, ta'lim, tajriba, loyihalar va kurslar"

    @transaction.atomic
    def handle(self, *args, **opts):
        self.site()
        self.skills()
        self.projects()
        self.experience()
        self.education()
        self.journey()
        self.courses()
        self.stdout.write(self.style.SUCCESS("Profil ma'lumotlari yangilandi"))

    # ------------------------------------------------------------------ Sayt
    def site(self):
        s = SiteSettings.load()
        s.owner_name = s.owner_name or "Otabek"
        tr(s, "owner_role", "Python Backend Developer · StartUp CEO", "Python Backend Developer · Startup CEO", "Python Backend-разработчик · CEO стартапа")
        tr(s, "hero_badges", "Developer, StartUp CEO, Sales Manager, Creator", "Developer, Startup CEO, Sales Manager, Creator",
           "Разработчик, CEO стартапа, Sales Manager, Креатор")
        tr(s, "owner_bio",
           "2021-yildan beri dasturlash bilan shug'ullanaman. Django va Telegram botlar bo'yicha backend dasturchi, NutriZone startapi asoschisi, "
           "hozir LIFE Nutrition'da Sales va Marketplace Manager. Bilganlarimni WeliCoDev'da kurs va maqolalar orqali ulashaman.",
           "Programming since 2021. Backend developer (Django, Telegram bots), founder of the NutriZone startup and currently Sales & Marketplace "
           "Manager at LIFE Nutrition. I share what I learn through WeliCoDev courses and articles.",
           "Программирую с 2021 года. Backend-разработчик (Django, Telegram-боты), основатель стартапа NutriZone, сейчас Sales и Marketplace "
           "Manager в LIFE Nutrition. Делюсь знаниями через курсы и статьи WeliCoDev.")
        s.years_experience = 5
        s.latitude, s.longitude, s.map_zoom, s.timezone_name = 41.311081, 69.240562, 12, "Asia/Tashkent"
        tr(s, "location", "Toshkent, O'zbekiston", "Tashkent, Uzbekistan", "Ташкент, Узбекистан")
        if not s.payment_note_uz:
            tr(s, "payment_note",
               "To'lov Click, Payme yoki bank kartasi orqali qabul qilinadi. To'lovdan so'ng chekni Telegram'da yuboring — kurs 1–2 soat ichida ochiladi.",
               "Payment via Click, Payme or bank card. Send the receipt on Telegram after paying — the course opens within 1–2 hours.",
               "Оплата через Click, Payme или банковскую карту. Отправьте чек в Telegram — курс откроется в течение 1–2 часов.")
        # Shaxsiy rasm: designs/ dagi fotodan (faqat hali yuklanmagan bo'lsa)
        for field, name in (("portrait", "portrait.jpg"), ("avatar", "avatar.jpg")):
            src = settings.BASE_DIR / "designs" / name
            if not getattr(s, field) and src.exists():
                getattr(s, field).save(f"otabek-{name}", File(src.open("rb")), save=False)
        s.save()
        hero = PageHero.objects.filter(page="home").first()
        if hero:
            tr(hero, "subtitle",
               "Backend tizimlar quraman, startap yurityapman va savdoni o'stiryapman. Bilganlarimni WeliCoDev'da o'zbek tilida ulashaman.",
               "I build backend systems, run a startup and grow sales. I share what I learn on WeliCoDev.",
               "Строю backend-системы, развиваю стартап и продажи. Делюсь знаниями на WeliCoDev.")
            hero.save()
        if not Role.objects.exists():
            roles = [
                ("code-xml", "blue", "/projects/",
                 ("Developer", "Developer", "Разработчик"),
                 ("Python · Django · Telegram botlar", "Python · Django · Telegram bots", "Python · Django · Telegram-боты"),
                 ("Backend tizimlar, REST API va botlar: g'oyadan production'gacha.", "Backend systems, REST APIs and bots — from idea to production.",
                  "Backend-системы, REST API и боты — от идеи до продакшена.")),
                ("rocket", "violet", "https://nutrizone.uz",
                 ("StartUp CEO", "Startup CEO", "CEO стартапа"),
                 ("NutriZone asoschisi", "Founder of NutriZone", "Основатель NutriZone"),
                 ("Mahsulot, jamoa va o'sish strategiyasini boshqaraman.", "I lead the product, the team and the growth strategy.",
                  "Руковожу продуктом, командой и стратегией роста.")),
                ("trending-up", "green", "/experience/",
                 ("Sales Manager", "Sales Manager", "Sales Manager"),
                 ("LIFE Nutrition · Marketplace", "LIFE Nutrition · Marketplaces", "LIFE Nutrition · маркетплейсы"),
                 ("Savdo va marketplace'larda brendni o'stiraman: Uzum, Wildberries.", "Growing the brand across sales channels and marketplaces.",
                  "Развиваю бренд в продажах и на маркетплейсах.")),
                ("clapperboard", "orange", "/education/",
                 ("Creator", "Creator", "Креатор"),
                 ("Kurslar · Blog · Telegram", "Courses · Blog · Telegram", "Курсы · Блог · Telegram"),
                 ("Bilganlarimni o'zbek tilida kurs va maqolalar orqali ulashaman.", "Sharing what I know through courses and articles.",
                  "Делюсь знаниями через курсы и статьи.")),
            ]
            for i, (icon, color, link, title, sub, desc) in enumerate(roles):
                r = Role(icon=icon, color=color, link=link, order=i)
                tr(r, "title", *title)
                tr(r, "subtitle", *sub)
                tr(r, "description", *desc)
                r.save()
        # Ijtimoiy tarmoqlar: mavjud bo'lmaganlarini qo'shadi (havolalarni dashboard → Sozlamalar'da almashtiring)
        defaults = [
            ("telegram", "https://t.me/welicodev", "@welicodev"), ("github", "https://github.com/welicodev", "welicodev"),
            ("linkedin", "https://www.linkedin.com/in/welicodev", "welicodev"), ("instagram", "https://instagram.com/welicodev", "@welicodev"),
            ("youtube", "https://youtube.com/@welicodev", "@welicodev"), ("facebook", "https://facebook.com/welicodev", "welicodev"),
        ]
        for i, (platform, url, username) in enumerate(defaults):
            if not SocialLink.objects.filter(platform=platform).exists():
                SocialLink.objects.create(platform=platform, url=url, username=username, order=i, show_in_header=i < 4)

    # ------------------------------------------------------------------ Ko'nikmalar
    def skills(self):
        keep = set()
        for ci, (cname, cslug, items) in enumerate(SKILLS):
            cat = SkillCategory.objects.filter(slug=cslug).first() or SkillCategory(slug=cslug)
            tr(cat, "name", *cname)
            cat.order = ci
            cat.save()
            for si, (name, icon, level, pct, years, featured, sub) in enumerate(items):
                sk = Skill.objects.filter(name__iexact=name).first() or Skill(name=name)
                if name == "Linux / Ubuntu" and not sk.pk:
                    sk = Skill.objects.filter(name="Linux").first() or sk
                sk.name, sk.category, sk.devicon, sk.level = name, cat, icon, level
                sk.proficiency, sk.years, sk.is_featured, sk.order = pct, years, featured, ci * 20 + si
                sk.started_year = 2026 - years
                sk.is_learning = name in ("Next.js", "TypeScript", "React")
                sk.learning_progress = {"Next.js": 60, "TypeScript": 70, "React": 72}.get(name, 0)
                tr(sk, "subtitle", *sub)
                sk.save()
                keep.add(sk.pk)
        Skill.objects.exclude(pk__in=keep).delete()
        SkillCategory.objects.filter(skills__isnull=True).delete()

    # ------------------------------------------------------------------ Loyihalar
    def projects(self):
        skills = {s.name: s for s in Skill.objects.all()}
        cats = {}
        for i, (slug, names) in enumerate(CATEGORIES.items()):
            c = ProjectCategory.objects.filter(slug=slug).first() or ProjectCategory(slug=slug)
            tr(c, "name", *names)
            c.order = i
            c.save()
            cats[slug] = c
        legacy = {"tift-referral": "referral-platform", "translator-bot": "translation-system"}
        keep = set()
        for order, (slug, cat, title, sub, desc, tech, tag_names, year, role, seed, live) in enumerate(PROJECTS):
            p = Project.objects.filter(slug=slug).first() or Project.objects.filter(slug=legacy.get(slug, "-")).first() or Project(slug=slug)
            p.slug, p.title, p.category, p.completed_year, p.order = slug, title, cats[cat], year, order
            p.status, p.is_featured = "published", slug in ("nutrizone", "tift-referral", "sharebooks", "clamo")
            p.live_url = live or p.live_url
            tr(p, "project_type", "Startup" if cat == "startup" else ("Web & Mobile" if "Mobile" in tag_names else "Web"))
            tr(p, "role", role)
            if cat == "startup":
                tr(p, "duration", "2025 — hozir", "2025 — present", "2025 — сейчас")
            else:
                tr(p, "duration", str(year))
            tr(p, "team_size", {"startup": "6", "commercial": "4–8", "university": "1–3"}[cat])
            tr(p, "title", title)
            tr(p, "subtitle", *sub)
            tr(p, "short_description", *desc)
            tr(p, "description", f"<p>{desc[0]}</p>", f"<p>{desc[1]}</p>", f"<p>{desc[2]}</p>")
            if not p.cover:
                p.cover.save(f"{slug}.jpg", ph.app_screenshot(seed, title, sub[1]), save=False)
            p.save()
            p.tech_stack.set([skills[n] for n in tech if n in skills])
            p.tags.set(tags(*tag_names))
            if not p.features.exists():
                for fi, (ft, ic) in enumerate([("REST API", "plug"), ("Admin panel", "layout-dashboard"), ("Telegram", "send")][: 2 + (seed % 2)]):
                    f = ProjectFeature(project=p, icon=ic, order=fi)
                    tr(f, "title", ft)
                    f.save()
            keep.add(p.pk)
        Project.objects.exclude(pk__in=keep).delete()
        ProjectCategory.objects.exclude(pk__in=[c.pk for c in cats.values()]).filter(projects__isnull=True).delete()

    # ------------------------------------------------------------------ Ish tajribasi
    def experience(self):
        skills = {s.name: s for s in Skill.objects.all()}
        keep = set()
        for order, (slug, kind, company, role, start, end, current, loc, summary, resp, tech, projects, site, industry) in enumerate(EXPERIENCES):
            e = Experience.objects.filter(slug=slug).first() or Experience(slug=slug)
            e.company, e.kind, e.start_date, e.end_date, e.is_current, e.order = company, kind, start, end, current, order
            e.website, e.is_published = site, True
            tr(e, "role", *role)
            tr(e, "location", *loc)
            tr(e, "summary", *summary)
            tr(e, "description", f"<p>{summary[0]}</p>", f"<p>{summary[1]}</p>", f"<p>{summary[2]}</p>")
            tr(e, "company_industry", *industry)
            if not e.logo:
                e.logo.save(f"{slug}.jpg", ph.logo_tile(order + 1, "".join(w[0] for w in company.replace("-", " ").split()[:2]).upper()), save=False)
            e.save()
            e.technologies.set([skills[n] for n in tech if n in skills])
            e.projects.set(Project.objects.filter(slug__in=projects))
            e.responsibilities.all().delete()
            for ri, text in enumerate(resp):
                r = Responsibility(experience=e, order=ri)
                tr(r, "text", text)
                r.save()
            if slug == "uic-group" and not e.milestones.exists():
                for mi, (label, title) in enumerate([("Feb 2025", "Jamoaga qo'shildim"), ("Iyun 2025", "tift.uz referal tizimi"), ("Okt 2025", "Loyihalarni topshirdim")]):
                    m = Milestone(experience=e, date_label=label, order=mi)
                    tr(m, "title", title)
                    m.save()
            keep.add(e.pk)
        Experience.objects.exclude(kind="education").exclude(pk__in=keep).delete()

    def education(self):
        skills = {s.name: s for s in Skill.objects.all()}
        keep = set()
        for e in EDUCATION:
            obj = Experience.objects.filter(slug=e["slug"]).first() or Experience(slug=e["slug"])
            obj.company, obj.kind, obj.start_date, obj.end_date, obj.order = e["company"], "education", e["start"], e["end"], e["order"]
            obj.website, obj.grade, obj.is_current, obj.is_published = e["website"], e["grade"], False, True
            tr(obj, "role", *e["role"])
            tr(obj, "degree", *e["degree"])
            tr(obj, "field_of_study", *e["field"])
            tr(obj, "location", *e["location"])
            tr(obj, "summary", *e["summary"])
            tr(obj, "description", f"<p>{e['summary'][0]}</p>", f"<p>{e['summary'][1]}</p>", f"<p>{e['summary'][2]}</p>")
            tr(obj, "achievements", e["achievements"])
            text, seed = e["logo"]
            obj.logo.save(f"{e['slug']}.jpg", ph.logo_tile(seed, text), save=False)
            obj.save()
            obj.technologies.set([skills[n] for n in e["tech"] if n in skills])
            if e["slug"] == "tatu":
                obj.projects.set(Project.objects.filter(category__slug="university"))
            keep.add(obj.pk)
        Experience.objects.filter(kind="education").exclude(pk__in=keep).delete()

    def journey(self):
        JourneyStep.objects.all().delete()
        for i, (year, title) in enumerate(JOURNEY):
            j = JourneyStep(year=year, order=i)
            tr(j, "title", *title)
            j.save()

    # ------------------------------------------------------------------ Kurslar
    def courses(self):
        from .seed_extra import COURSES

        # seed_extra'dagi tarjimalar (uz, ru, en) tartibida edi: to'g'rilaymiz
        for spec in COURSES:
            c = Course.objects.filter(slug=spec["slug"]).first()
            if not c:
                continue
            uz, ru, en = spec["title"]
            tr(c, "title", uz, en, ru)
            uz, ru, en = spec["subtitle"]
            tr(c, "subtitle", uz, en, ru)
            for k, v in EXISTING_COURSES.get(spec["slug"], {}).items():
                setattr(c, k, v)
            c.save()
        skills = {s.name: s for s in Skill.objects.all()}
        for slug, order, level, free, price, old, private, seed, title, sub, tech, modules in NEW_COURSES:
            c = Course.objects.filter(slug=slug).first()
            created = c is None
            c = c or Course(slug=slug)
            c.order, c.level, c.is_free, c.price, c.old_price, c.is_private = order, level, free, price, old, private
            c.status, c.sequential = "published", True
            tr(c, "title", *title)
            tr(c, "subtitle", *sub)
            tr(c, "description", f"<p>{sub[0]}</p><p>Har bir dars: video, konspekt, kod misollari va uyga vazifa.</p>",
               f"<p>{sub[1]}</p><p>Every lesson: video, notes, code samples and homework.</p>",
               f"<p>{sub[2]}</p><p>Каждый урок: видео, конспект, примеры кода и домашнее задание.</p>")
            tr(c, "what_you_learn", "<ul>" + "".join(f"<li>{t}</li>" for _m, ls in modules for t in ls) + "</ul>")
            tr(c, "requirements", "<ul><li>Kompyuter va internet</li><li>O'rganishga ishtiyoq</li></ul>",
               "<ul><li>A computer and internet</li><li>Willingness to learn</li></ul>",
               "<ul><li>Компьютер и интернет</li><li>Желание учиться</li></ul>")
            if not c.cover:
                c.cover.save(f"{slug}.jpg", ph.app_screenshot(seed, title[1].split(":")[0], sub[1][:42]), save=False)
            c.save()
            c.technologies.set([skills[n] for n in tech if n in skills])
            if not created:
                continue
            n = 0
            for mi, (mtitle, lessons) in enumerate(modules, start=1):
                m = Module(course=c, order=mi)
                tr(m, "title", mtitle)
                m.save()
                for lt in lessons:
                    n += 1
                    les = Lesson(course=c, module=m, order=n, status="published", is_preview=n == 1, video_url=YT,
                                 duration_seconds=420 + (n * 173) % 900, homework_mode="none" if n == 1 else "submit")
                    tr(les, "title", lt)
                    tr(les, "summary", f"{n}-dars: {lt}")
                    tr(les, "content", f"<h2>Dars rejasi</h2><p>Bu darsda «{lt}» mavzusini amaliy misollar bilan ko'rib chiqamiz.</p>")
                    if n > 1:
                        tr(les, "homework", "<p>Darsdagi misolni o'zingiz takrorlang va natijani yuboring.</p>")
                    les.save()
                    r = LessonResource(lesson=les, kind="docs", url="https://roadmap.sh", order=0)
                    tr(r, "title", "Qo'shimcha manba")
                    r.save()
