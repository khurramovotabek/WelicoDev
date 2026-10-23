"""Demo kontent: dizayndagi matnlar asosida. Haqiqiy ma'lumotlar dashboard orqali almashtiriladi.

    python manage.py seed_demo          # bo'sh bazaga qo'shadi
    python manage.py seed_demo --reset  # avval demo kontentni o'chiradi
"""

from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.blog.models import Article, ArticleCategory
from apps.core import placeholders as ph
from apps.core.models import CurrentStatus, Faq, PageHero, SiteSettings, SocialLink, Tag
from apps.education.models import Course, Lesson, LessonResource, Module
from apps.gallery.models import Album, MediaCategory, Photo, Playlist, Track, Video
from apps.portfolio.models import (
    Experience, Interest, JourneyStep, Milestone, Project, ProjectCategory, ProjectChallenge,
    ProjectFeature, ProjectResult, Responsibility, Skill, SkillCategory,
)
from apps.telegram_bot.models import BotSettings


def tr(obj, field, uz, en=None, ru=None):
    setattr(obj, f"{field}_uz", uz)
    setattr(obj, f"{field}_en", en or uz)
    setattr(obj, f"{field}_ru", ru or en or uz)


def tags(*names):
    return [Tag.objects.get_or_create(name=n)[0] for n in names]


class Command(BaseCommand):
    help = "Dizayn asosida demo kontent yaratadi"

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true")

    @transaction.atomic
    def handle(self, *args, reset=False, **opts):
        if reset:
            for m in (Lesson, Course, Article, ArticleCategory, Project, ProjectCategory, Experience, Skill, SkillCategory,
                      Photo, Album, Video, Track, Playlist, MediaCategory, JourneyStep, Interest, CurrentStatus, PageHero, Faq, SocialLink):
                m.objects.all().delete()
        if Project.objects.exists():
            self.stdout.write(self.style.WARNING("Kontent allaqachon bor. --reset bilan qayta yarating."))
            return
        self.site()
        skills = self.skills()
        projects = self.projects(skills)
        self.experience(skills, projects)
        self.about()
        self.blog()
        self.media()
        self.education(skills)
        BotSettings.load()
        self.stdout.write(self.style.SUCCESS("Demo kontent yaratildi"))

    # ------------------------------------------------------------------ Sayt
    def site(self):
        s = SiteSettings.load()
        s.brand_name = "WeliCoDev"
        tr(s, "brand_tagline", "Build • Learn • Create • Live")
        s.owner_name = "Otabek"
        tr(s, "owner_role", "Python Backend Engineer")
        tr(
            s, "owner_bio",
            "Men Otabek, Python Backend Engineer. Kengaytiriladigan tizimlar quraman, murakkab muammolarni hal qilaman va g'oyalarni haqiqiy mahsulotlarga aylantiraman.",
            "I'm Otabek, a Python Backend Engineer who loves building scalable systems, solving complex problems, and turning ideas into real products.",
            "Я Отабек, Python Backend Engineer. Строю масштабируемые системы, решаю сложные задачи и превращаю идеи в реальные продукты.",
        )
        tr(s, "hero_badges", "Dasturchi, Inson, Kashfiyotchi", "Developer, Human, Explorer", "Разработчик, Человек, Исследователь")
        tr(s, "location", "Toshkent, Shayxontohur, Qoratosh 60B", "Tashkent, Shaykhantakhur, Qoratosh 60B", "Ташкент, Шайхантахур, Караташ 60Б")
        tr(s, "working_hours", "Du - Ju, 9:00 - 18:00", "Mon - Fri, 9:00 - 18:00", "Пн - Пт, 9:00 - 18:00")
        tr(s, "response_time", "24 soat", "24 hours", "24 часа")
        tr(s, "meta_description", "Otabek — Python Backend Engineer. Loyihalar, maqolalar va video kurslar.",
           "Otabek — Python Backend Engineer. Projects, articles and video courses.",
           "Отабек — Python Backend Engineer. Проекты, статьи и видеокурсы.")
        s.email = "xurramovotabek568@gmail.com"
        s.phone = "+998 94 275 56 38"
        s.latitude, s.longitude, s.map_zoom = 41.317029, 69.239155, 15
        s.map_url = "https://maps.google.com/?q=41.317029,69.239155"
        s.years_experience = 3
        s.save()

        for i, (platform, url) in enumerate([
            ("github", "https://github.com/khurramovotabek"),
            ("linkedin", "https://www.linkedin.com/"),
            ("telegram", "https://t.me/welicodevbot"),
            ("youtube", "https://www.youtube.com/"),
            ("instagram", "https://www.instagram.com/"),
        ]):
            SocialLink.objects.create(platform=platform, url=url, order=i, show_in_header=i < 3)

        for i, (label, value, color) in enumerate([
            (("Quryapman", "Building", "Строю"), ("Yangi loyihalar", "New Projects", "Новые проекты"), "green"),
            (("O'rganyapman", "Learning", "Изучаю"), ("AI va arxitektura", "AI & Architecture", "AI и архитектура"), "blue"),
            (("Tinglayapman", "Listening", "Слушаю"), ("Chill Vibes", "Chill Vibes", "Chill Vibes"), "purple"),
            (("Joylashuv", "In", "Где"), ("Toshkent, O'zbekiston", "Tashkent, Uzbekistan", "Ташкент, Узбекистан"), "orange"),
        ]):
            st = CurrentStatus(color=color, order=i)
            tr(st, "label", *label)
            tr(st, "value", *value)
            st.save()

        heroes = {
            "home": ("", ("Salom, men Otabek.", "Hi, I'm Otabek.", "Привет, я Отабек."),
                     ("Dasturlar yarataman, g'oyalarni o'rganaman va yo'limni hujjatlashtiraman.", "I build software, explore ideas, and document the journey.", "Создаю софт, исследую идеи и документирую свой путь."),
                     ("Bugungi intizom ertangi erkinlikni yaratadi.", "Discipline today creates the freedom tomorrow.", "Дисциплина сегодня создаёт свободу завтра.")),
            "about": (("Imkoniyatlarga ochiqman", "Available for opportunities", "Открыт к предложениям"), ("Men haqimda", "About Me", "Обо мне"), None,
                      ("Izchil rivojlanish, toza arxitektura va texnologiya orqali yaxshiroq ertaga ishonaman.", "I believe in consistent progress, clean architecture, and a better tomorrow through technology.", "Я верю в постоянный прогресс, чистую архитектуру и лучшее завтра через технологии.")),
            "projects": (("Ishlarim", "My work", "Мои работы"), ("Loyihalar", "Projects", "Проекты"),
                         ("Haqiqiy g'oyalar. Haqiqiy tizimlar. Haqiqiy natija.", "Real ideas. Real systems. Real impact.", "Реальные идеи. Реальные системы. Реальный результат."),
                         ("Yaxshi dastur haqiqiy muammolarni hal qiladi va hayotni yaxshilaydi.", "Good software solves real problems and makes life better.", "Хороший софт решает реальные задачи и делает жизнь лучше.")),
            "journal": (("Fikrlar • G'oyalar • O'sish", "Thoughts • Ideas • Progress", "Мысли • Идеи • Прогресс"), ("Blog", "Blog", "Блог"),
                        ("G'oyalar, tajribalar va ular orasidagi hamma narsa.", "Ideas, experiences, and everything in between.", "Идеи, опыт и всё, что между ними."),
                        ("O'zingning yaxshiroq versiyang har kuni qilgan ishingning natijasi.", "A better version of yourself is a result of what you do every day.", "Лучшая версия себя — результат того, что делаешь каждый день.")),
            "media": (("Suratga ol • Yarat • Saqla", "Capture • Create • Preserve", "Снимай • Создавай • Храни"), ("Media", "Media", "Медиа"),
                      ("Lahzalar, g'oyalar va ilhom.", "Moments, ideas, and inspiration.", "Моменты, идеи и вдохновение."),
                      ("Yaxshi lahzalar ajoyib hikoya yaratadi.", "Good moments make a great story.", "Хорошие моменты складываются в историю.")),
            "experience": (("Mening yo'lim", "My journey", "Мой путь"), ("Tajriba", "Experience", "Опыт"),
                           ("Uzluksiz o'rganish, qurish va natija yaratish yo'li.", "A journey of continuous learning, building, and creating impact.", "Путь непрерывного обучения, созидания и результата."),
                           ("Yaxshiroq tajriba yaxshiroq mahsulot quradi.", "Better experiences build better products.", "Лучший опыт создаёт лучшие продукты.")),
            "skills": (("Ko'nikmalar va texnologiyalar", "Skills & Technologies", "Навыки и технологии"), ("Ko'nikmalar", "Skills & Technologies", "Навыки и технологии"),
                       ("G'oyalarni haqiqatga aylantiradigan vositalar.", "Tools that turn ideas into reality.", "Инструменты, превращающие идеи в реальность."),
                       ("Yaxshi vositalar yaxshi g'oyalarni amalga oshiradi.", "Good tools make good ideas possible.", "Хорошие инструменты делают идеи возможными.")),
            "education": (("O'rgan • Amaliyot • O'sish", "Learn • Practice • Grow", "Учись • Практикуй • Расти"), ("Kurslar", "Courses", "Курсы"),
                          ("Amaliy video darslar: kod, topshiriq va uyga vazifa bilan.", "Hands-on video lessons with code, tasks and homework.", "Практические видеоуроки с кодом, заданиями и домашкой."),
                          ("Izchil o'rganish vaqt o'tib ko'payadi.", "Consistent learning compounds over time.", "Постоянное обучение со временем приумножается.")),
            "contact": (("Bog'lanamiz", "Let's connect", "На связи"), ("Aloqa", "Contact", "Контакты"),
                        ("Loyihangiz bormi yoki shunchaki salom demoqchimisiz?", "Have a project in mind or just want to say hi?", "Есть проект или просто хотите поздороваться?"),
                        ("Ajoyib g'oyalar oddiy suhbatdan boshlanadi.", "Great ideas start with a simple conversation.", "Великие идеи начинаются с простого разговора.")),
            "share": ("", ("Ulashish", "Share", "Поделиться"), ("G'oyalarni tarqating, boshqalarni ilhomlantiring.", "Spread ideas, inspire others.", "Делитесь идеями, вдохновляйте других."),
                      ("Yaxshi g'oyalar ulashilganda uzoqroqqa yetadi.", "Good ideas reach further when shared.", "Хорошие идеи идут дальше, когда ими делятся.")),
            "404": ("", ("Sahifa topilmadi", "Page Not Found", "Страница не найдена"), None, None),
        }
        for page, (eyebrow, title, subtitle, quote) in heroes.items():
            h = PageHero(page=page)
            if eyebrow:
                tr(h, "eyebrow", *eyebrow)
            tr(h, "title", *title)
            if subtitle:
                tr(h, "subtitle", *subtitle)
            if quote:
                tr(h, "quote", *quote)
            h.save()
        h = PageHero.objects.get(page="projects")
        tr(h, "description", "Kengaytiriladigan backend tizimlaridan to'liq platformalargacha. Har bir loyiha — muammo, yechim va saboq.",
           "From scalable backend systems to full platforms. Each project represents a problem, a solution, and a lesson learned.",
           "От масштабируемых backend-систем до полноценных платформ. Каждый проект — проблема, решение и урок.")
        h.save()

        for i, (q, a) in enumerate([
            (("Frilans ishga ochiqmisiz?", "Are you available for freelance work?", "Вы доступны для фриланса?"),
             ("Ha, qiziqarli loyihalar uchun vaqt ajrataman. Loyiha haqida qisqacha yozing.", "Yes, I take on interesting projects. Send a short description.", "Да, беру интересные проекты. Опишите задачу.")),
            (("Qanday loyihalar ustida ishlaysiz?", "What types of projects do you work on?", "С какими проектами вы работаете?"),
             ("Backend, API, integratsiyalar, Telegram botlar va yuqori yuklamali tizimlar.", "Backends, APIs, integrations, Telegram bots and high-load systems.", "Backend, API, интеграции, Telegram-боты и высоконагруженные системы.")),
            (("Javob qancha vaqtda keladi?", "How long does it take to get a response?", "Как быстро вы отвечаете?"),
             ("Odatda 24 soat ichida.", "Usually within 24 hours.", "Обычно в течение 24 часов.")),
            (("Qo'ng'iroq rejalashtirsak bo'ladimi?", "Can we schedule a call?", "Можно созвониться?"),
             ("Albatta. Telegram orqali yozing va qulay vaqtni kelishamiz.", "Sure. Message me on Telegram and we'll pick a time.", "Конечно. Напишите в Telegram, договоримся о времени.")),
        ]):
            f = Faq(order=i)
            tr(f, "question", *q)
            tr(f, "answer", *a)
            f.save()

    # ------------------------------------------------------------------ Skills
    def skills(self):
        cats = {}
        for i, (slug, names) in enumerate([
            ("backend", ("Backend", "Backend", "Backend")),
            ("database", ("Ma'lumotlar bazasi", "Database", "Базы данных")),
            ("devops", ("DevOps va vositalar", "DevOps & Tools", "DevOps и инструменты")),
            ("frontend", ("Frontend", "Frontend", "Frontend")),
        ]):
            c = SkillCategory(slug=slug, order=i)
            tr(c, "name", *names)
            c.save()
            cats[slug] = c
        data = [
            ("Python", "python", "backend", "expert", 92, 5, True, 2020, "Backend Development"),
            ("Django", "django-plain", "backend", "expert", 88, 4, True, 2021, "Web Framework"),
            ("FastAPI", "fastapi", "backend", "advanced", 72, 2, False, 2023, "API Framework"),
            ("Celery", "", "backend", "advanced", 75, 3, True, 2022, "Task Queue"),
            ("PostgreSQL", "postgresql", "database", "advanced", 80, 4, True, 2021, "Database"),
            ("Redis", "redis", "database", "advanced", 74, 3, True, 2022, "Caching & Queues"),
            ("Docker", "docker", "devops", "advanced", 78, 3, True, 2022, "Containerization"),
            ("Linux", "linux", "devops", "advanced", 76, 4, False, 2020, "Operating System"),
            ("Git", "git", "devops", "advanced", 82, 5, False, 2020, "Version Control"),
            ("Nginx", "nginx", "devops", "intermediate", 62, 2, False, 2023, "Web Server"),
            ("AWS", "amazonwebservices-original-wordmark", "devops", "intermediate", 55, 2, True, 2024, "Cloud Services"),
            ("JavaScript", "javascript", "frontend", "intermediate", 65, 3, False, 2021, "Language"),
            ("HTML5", "html5", "frontend", "advanced", 80, 5, False, 2020, "Markup"),
            ("CSS3", "css3", "frontend", "advanced", 75, 5, False, 2020, "Styles"),
        ]
        skills = {}
        for i, (name, dev, cat, lvl, prof, yrs, feat, start, sub) in enumerate(data):
            sk = Skill(name=name, devicon=dev, category=cats[cat], level=lvl, proficiency=prof, years=yrs,
                       is_featured=feat, started_year=start, order=i)
            tr(sk, "subtitle", sub)
            sk.save()
            skills[name] = sk
        for name, dev, cat, prog in [("React Native", "react", "frontend", 60), ("GraphQL", "graphql-plain", "backend", 40), ("Kubernetes", "kubernetes", "devops", 30)]:
            sk = Skill(name=name, devicon=dev, category=cats[cat], level="beginner", proficiency=30, years=0, is_learning=True, learning_progress=prog, started_year=2026)
            tr(sk, "subtitle", "Learning")
            sk.save()
            skills[name] = sk
        return skills

    # ------------------------------------------------------------------ Projects
    def projects(self, skills):
        cats = {}
        for i, (slug, name) in enumerate([("web", "Web"), ("mobile", "Mobile"), ("backend", "Backend"), ("api", "API"), ("platform", "Platform"), ("open-source", "Open Source")]):
            c = ProjectCategory(slug=slug, order=i)
            tr(c, "name", name)
            c.save()
            cats[slug] = c
        items = [
            ("NutriZone", "Smart nutrition ecosystem", "platform",
             "Sport ozuqasi uchun zamonaviy e-commerce platforma: ko'p do'kon, mahsulotlar, buyurtmalar va integratsiyalar.",
             "A modern e-commerce platform for sports nutrition with multi-store support, product management, orders, and integrations.",
             ["Django", "PostgreSQL", "Redis", "Celery", "Docker"], ["Django", "PostgreSQL", "Redis", "Celery", "API"], True, "https://nutrizone.uz"),
            ("ShareBooks", "Book sharing platform", "web", "Zamonaviy o'qish tajribasi va hamjamiyatga ega onlayn kutubxona.",
             "Online library platform with modern reading experience and community features.", ["Django", "PostgreSQL"], ["Django", "Web", "Community"], False, ""),
            ("Referral Platform", "Growth through people", "platform", "Tashqi CRM bilan integratsiyalangan referal ekotizim: webhooklar, statistika va mukofotlar.",
             "Referral ecosystem integrated with external CRM. Webhooks, statistics and rewards.", ["Django", "Celery", "Redis"], ["Django", "API", "Analytics"], False, ""),
            ("Admission System", "Education platform", "platform", "Integratsiya va bildirishnomalarga ega talabalar qabul tizimi.",
             "Student admission and application management system with integrations and notifications.", ["Django", "PostgreSQL"], ["Django", "API", "Webhooks"], False, ""),
            ("Taxi Service", "On-demand platform", "mobile", "Real vaqtda kuzatuv, haydovchilar va to'lovlarga ega taksi chaqirish tizimi.",
             "A complete taxi ordering system with real-time tracking, drivers and payments.", ["Django", "Redis", "Docker"], ["Django", "Mobile", "Maps"], False, ""),
            ("Marjon", "Discount & promotions", "web", "Moslashuvchan qoidalar va analitikaga ega chegirma kampaniyalari tizimi.",
             "Campaign and discount management system with flexible rules and analytics.", ["Django", "Celery"], ["Django", "Web", "Analytics"], False, ""),
            ("Translation System", "Multilingual platform", "backend", "JSON import va admin panelga ega dinamik tarjimalar tizimi.",
             "Dynamic translation management system with JSON import and admin panel.", ["Django", "PostgreSQL"], ["Django", "i18n", "Admin"], False, ""),
            ("Open Source", "Various contributions", "open-source", "Kichik vositalar, utilitalar va ochiq kodli hissalar.",
             "Small tools, utilities and open source contributions.", ["Python", "Git"], ["Python", "Tools", "Open Source"], False, "https://github.com/"),
        ]
        projects = {}
        for i, (title, sub, cat, d_uz, d_en, stack, tag_names, featured, live) in enumerate(items):
            p = Project(category=cats[cat], status="published", is_featured=featured or i < 3, order=i, completed_year=2025 - (i % 3),
                        live_url=live, source_url="https://github.com/" if i % 2 else "")
            tr(p, "title", title)
            tr(p, "subtitle", sub)
            tr(p, "short_description", d_uz, d_en)
            tr(p, "description", f"<p>{d_uz}</p><p>Platforma kengaytiriladigan arxitektura asosida qurilgan va o'sib borayotgan foydalanuvchilar bazasiga mo'ljallangan.</p>",
               f"<p>{d_en}</p><p>It is built on a scalable architecture to handle a growing user base and future expansion.</p>")
            tr(p, "project_type", "Web & Mobile" if cat in ("platform", "mobile") else "Web")
            tr(p, "role", "Backend Development")
            tr(p, "duration", f"{3 + i % 4} oy", f"{3 + i % 4} months", f"{3 + i % 4} мес.")
            tr(p, "team_size", f"{2 + i % 3} dasturchi", f"{2 + i % 3} developers", f"{2 + i % 3} разработчика")
            p.cover.save(f"{p.title_en.lower().replace(' ', '-')}.jpg", ph.app_screenshot(i, title, sub), save=False)
            p.save()
            p.tags.set(tags(*tag_names))
            p.tech_stack.set([skills[s] for s in stack if s in skills])
            if i == 0:
                for j, (ft, fd) in enumerate([("Multi-Store Support", "Separate stores with independent management"),
                                              ("Product Management", "Categories, brands, attributes, and variations"),
                                              ("Order & Payment System", "Secure payments and order tracking"),
                                              ("User Accounts", "Personal profiles, order history, and wishlist"),
                                              ("Admin Panel", "Powerful tools for store management"),
                                              ("Integrations", "SMS, delivery services, analytics, and more")]):
                    f = ProjectFeature(project=p, order=j, icon=["store", "package", "credit-card", "user-round", "layout-dashboard", "plug"][j])
                    tr(f, "title", ft)
                    tr(f, "description", fd)
                    f.save()
                for j, t in enumerate(["Designing a scalable multi-store architecture", "Optimizing performance for large product catalog",
                                       "Integrating multiple payment and delivery services", "Ensuring security and data integrity", "Building a flexible admin panel"]):
                    c = ProjectChallenge(project=p, order=j)
                    tr(c, "text", t)
                    c.save()
                for j, (v, lbl, ic) in enumerate([("10K+", "Active users", "users"), ("50K+", "Products", "package"), ("99.9%", "Uptime", "activity"), ("4.9/5", "User rating", "star")]):
                    r = ProjectResult(project=p, order=j, value=v, icon=ic)
                    tr(r, "label", lbl)
                    r.save()
                for j, name in enumerate(["Homepage", "Product List", "Product Detail", "Cart & Checkout", "User Profile", "Admin Panel"]):
                    img = p.images.model(project=p, order=j)
                    tr(img, "caption", name)
                    img.image.save(f"nutrizone-{j}.jpg", ph.app_screenshot(j + 2, "NutriZone", name), save=False)
                    img.save()
            projects[title] = p
        return projects

    # ------------------------------------------------------------------ Experience
    def experience(self, skills, projects):
        items = [
            ("UIC Group", "Python Backend Developer", "work", date(2024, 8, 1), None, True, "Tashkent, Uzbekistan",
             "Django, Celery va PostgreSQL yordamida kengaytiriladigan backend tizimlar ustida ishlayman. Haqiqiy mahsulotlar, integratsiyalar va yuqori yuklamali tizimlar.",
             "Working on scalable backend systems using Django, Celery, and PostgreSQL. Contributing to real-world products, integrations, and high-load systems.",
             ["Django", "Celery", "PostgreSQL", "Redis", "Docker"], ["NutriZone", "ShareBooks", "Marjon"]),
            ("Freelance", "Backend Developer", "freelance", date(2023, 1, 1), date(2024, 7, 31), False, "Remote",
             "Turli mamlakatlardagi mijozlar uchun veb-ilovalar, API va avtomatlashtirish vositalari.",
             "Worked on various freelance projects including web applications, APIs, and automation tools for clients from different countries.",
             ["Python", "Django", "PostgreSQL", "Linux", "Git"], ["Referral Platform", "Admission System"]),
            ("Personal Projects", "Indie Developer", "personal", date(2022, 1, 1), date(2023, 1, 1), False, "Remote",
             "ShareBooks va boshqa tajriba loyihalarini qurdim va ishga tushirdim.",
             "Built and launched several personal projects including ShareBooks and other experimental ideas.",
             ["Django", "JavaScript", "PostgreSQL"], ["ShareBooks"]),
            ("Self Learning", "Continuous Growth", "education", date(2020, 1, 1), date(2022, 1, 1), False, "Surxondaryo, Uzbekistan",
             "Dasturlash yo'limni boshladim: Python, veb asoslari va birinchi loyihalarim.",
             "Started my journey in programming. Learned Python, web development fundamentals, and built my first real projects.",
             ["Python", "HTML5", "CSS3", "JavaScript"], []),
        ]
        for i, (company, role, kind, start, end, current, loc, s_uz, s_en, tech, projs) in enumerate(items):
            e = Experience(company=company, kind=kind, start_date=start, end_date=end, is_current=current, order=i,
                           website="https://uic.group" if i == 0 else "", team_size=6 if i == 0 else None, products_count=3 if i == 0 else None)
            tr(e, "role", role)
            tr(e, "location", loc)
            tr(e, "summary", s_uz, s_en)
            tr(e, "description", f"<p>{s_uz}</p>", f"<p>{s_en}</p>")
            if i == 0:
                tr(e, "quote", "Great products are built by great people.")
                tr(e, "company_description", "UIC Group is a technology company focused on building innovative digital products and services that solve real-world problems.")
                tr(e, "company_industry", "IT Services & Software Development")
                e.logo.save("uic.jpg", ph.logo_tile(0, "UIC"), save=False)
            e.save()
            e.technologies.set([skills[t] for t in tech if t in skills])
            e.projects.set([projects[p] for p in projs])
            if i == 0:
                for j, t in enumerate(["Develop and maintain backend services using Django and Django REST Framework",
                                       "Design and optimize database structures with PostgreSQL",
                                       "Implement asynchronous tasks with Celery and Redis",
                                       "Integrate with third-party services (payment systems, SMS, external APIs)",
                                       "Write clean, maintainable, and well-documented code",
                                       "Participate in code reviews and technical discussions"]):
                    r = Responsibility(experience=e, order=j)
                    tr(r, "text", t)
                    r.save()
                for j, (dl, t, d) in enumerate([("Aug 2024", "Joined UIC Group", "Started as a Python Backend Developer"),
                                                ("Oct 2024", "First major feature delivered", "Implemented core API modules"),
                                                ("Jan 2025", "Worked on high-load system", "Optimized database and caching"),
                                                ("Jun 2025", "Led integration module", "Integrated external services (payment, SMS)"),
                                                ("Present", "Continuing to grow", "Building new features and improving the platform")]):
                    m = Milestone(experience=e, order=j)
                    tr(m, "date_label", dl)
                    tr(m, "title", t)
                    tr(m, "description", d)
                    m.save()
                for j in range(3):
                    img = e.images.model(experience=e, order=j)
                    img.image.save(f"uic-{j}.jpg", ph.landscape(30 + j, title=None), save=False)
                    img.save()

    # ------------------------------------------------------------------ About
    def about(self):
        for year, (uz, en, ru) in [(2020, ("Dasturlashni boshladim", "Started Programming", "Начал программировать")),
                                   (2022, ("Birinchi haqiqiy loyihalar", "First Real Projects", "Первые реальные проекты")),
                                   (2024, ("Professional tajriba", "Gained Professional Experience", "Профессиональный опыт")),
                                   (2025, ("UIC Group'ga qo'shildim", "Joined UIC Group", "Присоединился к UIC Group")),
                                   (2026, ("WeliCoDev'ni quryapman", "Building WeliCoDev", "Строю WeliCoDev"))]:
            j = JourneyStep(year=year)
            tr(j, "title", uz, en, ru)
            j.save()
        for i, (uz, en, ru) in enumerate([("Texnologiya", "Technology", "Технологии"), ("Kitoblar", "Books", "Книги"), ("Tarix", "History", "История"),
                                          ("Sayohat", "Travel", "Путешествия"), ("Musiqa", "Music", "Музыка"), ("Fotografiya", "Photography", "Фотография")]):
            it = Interest(order=i)
            tr(it, "title", uz, en, ru)
            it.image.save(f"interest-{i}.jpg", ph.landscape(40 + i, size=(600, 400)), save=False)
            it.save()

    # ------------------------------------------------------------------ Blog
    def blog(self):
        cats = {}
        for i, (slug, icon, names) in enumerate([("technology", "cpu", ("Texnologiya", "Technology", "Технологии")), ("career", "briefcase", ("Karyera", "Career", "Карьера")),
                                                 ("learning", "book-open", ("O'rganish", "Learning", "Обучение")), ("life", "leaf", ("Hayot", "Life", "Жизнь")),
                                                 ("personal", "user-round", ("Shaxsiy", "Personal", "Личное"))]):
            c = ArticleCategory(slug=slug, icon=icon, order=i)
            tr(c, "name", *names)
            c.save()
            cats[slug] = c
        code = (
            '<pre><code class="language-python">from django.shortcuts import render\n'
            'from django.http import JsonResponse\n\n'
            'def home(request):\n    return JsonResponse({"message": "Hello, Django!"})</code></pre>'
        )
        body_en = (
            "<h2>1. Introduction</h2><p>When I started my journey as a backend developer, I explored several frameworks. "
            "But Django quickly became the one I kept coming back to. It's not just a framework for me — it's a tool that lets me "
            "focus on solving real problems instead of reinventing the wheel.</p>"
            "<h2>2. The Developer Experience</h2><p>Django's batteries-included philosophy saves a lot of time. From authentication "
            "to admin panel, from ORM to migrations — everything works together out of the box.</p>" + code +
            "<h2>3. Real-World Applications</h2><p>I've used Django in multiple projects like NutriZone, ShareBooks, and internal platforms. "
            "Each project had different requirements, but Django's flexibility made it easy to adapt and scale.</p>"
            "<blockquote><p>Django gives you a solid foundation, so you can focus on what really matters — building value.</p></blockquote>"
            "<h2>4. Conclusion</h2><p>Django isn't perfect, but for me, it strikes the right balance between simplicity, power, and productivity.</p>"
        )
        body_uz = (
            "<h2>1. Kirish</h2><p>Backend dasturchi sifatida yo'limni boshlaganimda bir nechta freymvorklarni sinab ko'rdim. "
            "Lekin Django tezda men qaytib keladigan vositaga aylandi.</p>"
            "<h2>2. Dasturchi tajribasi</h2><p>Django'ning “batteries-included” falsafasi juda ko'p vaqt tejaydi: autentifikatsiya, admin panel, ORM, migratsiyalar.</p>"
            + code +
            "<h2>3. Amaliy qo'llanilishi</h2><p>Django'ni NutriZone, ShareBooks va ichki platformalarda ishlatganman.</p>"
            "<blockquote><p>Django mustahkam poydevor beradi, siz esa haqiqiy qiymat yaratishga e'tibor qaratasiz.</p></blockquote>"
            "<h2>4. Xulosa</h2><p>Django mukammal emas, lekin soddalik, kuch va unumdorlik o'rtasidagi to'g'ri muvozanatni topadi.</p>"
        )
        articles = [
            ("Why I Love Building with Django", "Nega Django bilan qurishni yaxshi ko'raman", "technology", True,
             "A deep dive into why Django remains my favorite framework.", "Django nega mening sevimli freymvorkim ekanligi haqida."),
            ("My Development Setup in 2026", "2026-yildagi ish muhitim", "personal", False, "Tools, extensions, and workflow that help me stay productive.", "Unumdor bo'lishimga yordam beradigan vositalar."),
            ("A Short Trip to the Mountains", "Tog'larga qisqa sayohat", "life", False, "Sometimes the best ideas come outside the screen.", "Ba'zan eng yaxshi g'oyalar ekrandan tashqarida tug'iladi."),
            ("Building Scalable APIs with Django & Celery", "Django va Celery bilan kengaytiriladigan API", "technology", False, "Architecture, task queues, and real-world lessons learned.", "Arxitektura, navbatlar va amaliy saboqlar."),
            ("Books That Changed My Thinking", "Fikrlashimni o'zgartirgan kitoblar", "learning", False, "A list of books that influenced my mindset.", "Dunyoqarashimga ta'sir qilgan kitoblar ro'yxati."),
            ("What I Learned Working on Real Projects", "Haqiqiy loyihalardan olgan saboqlarim", "career", False, "Key lessons, challenges, and mindset shifts.", "Asosiy saboqlar, qiyinchiliklar va fikrlash o'zgarishlari."),
        ]
        for i, (en, uz, cat, feat, ex_en, ex_uz) in enumerate(articles):
            a = Article(category=cats[cat], status="published", is_featured=feat, published_at=timezone.now() - timedelta(days=4 + i * 6))
            tr(a, "title", uz, en)
            tr(a, "excerpt", ex_uz, ex_en)
            tr(a, "content", body_uz if i == 0 else f"<p>{ex_uz}</p>", body_en if i == 0 else f"<p>{ex_en}</p>")
            a.cover.save(f"article-{i}.jpg", ph.landscape(10 + i, size=(1400, 800)), save=False)
            a.save()
            a.tags.set(tags("Django", "Python", "Backend") if i in (0, 3) else tags("Life"))

    # ------------------------------------------------------------------ Media
    def media(self):
        cats = {}
        for kind, names in [("photo", ["Life", "Travel", "Work", "Nature", "City"]), ("video", ["Vlogs", "Projects", "Education", "Events"]), ("music", ["Focus", "Chill", "Travel"])]:
            for i, n in enumerate(names):
                c = MediaCategory(kind=kind, order=i, slug=n.lower())
                tr(c, "name", n)
                c.save()
                cats[(kind, n)] = c
        album = Album(location="Kyrgyzstan")
        tr(album, "title", "Tog'lar", "Mountains", "Горы")
        album.cover.save("album.jpg", ph.landscape(50), save=False)
        album.save()
        photos = [("Tashkent at Night", "Toshkentdagi tun", "City", "Tashkent, Uzbekistan"), ("Mountains", "Tog'lar", "Nature", "Kyrgyzstan"),
                  ("My Workspace", "Ish joyim", "Work", "Tashkent, Uzbekistan"), ("Charvak Lake", "Chorvoq ko'li", "Travel", "Tashkent Region"),
                  ("Amirsoy", "Amirsoy", "Nature", "Greater Tashkent"), ("Sunset Hills", "Quyosh botishi", "Life", "Tashkent"),
                  ("City Lights", "Shahar chiroqlari", "City", "Tashkent, Uzbekistan"), ("Morning Fog", "Tonggi tuman", "Nature", "Kyrgyzstan"),
                  ("Road Trip", "Yo'lda", "Travel", "Samarkand")]
        for i, (en, uz, cat, loc) in enumerate(photos):
            p = Photo(album=album if cat in ("Nature",) else None, category=cats[("photo", cat)], camera="Sony A7 III", lens="FE 24-70mm f/2.8 GM",
                      exposure="f/2.8 • 1/50s • ISO 800", taken_at=timezone.now() - timedelta(days=i * 9), is_featured=i < 2)
            tr(p, "title", uz, en)
            tr(p, "location", loc)
            tr(p, "description", "Kechki tinch lahza. Shiddatli texnologiya hayoti va oddiy lahzalar osoyishtaligi o'rtasidagi muvozanat.",
               "A calm evening view. This photo represents the balance between a fast-paced tech life and the peace of simple moments.")
            p.image.save(f"photo-{i}.jpg", ph.landscape(60 + i), save=False)
            p.save()
            p.tags.set(tags(cat, "Uzbekistan"))
        for i, (en, cat, dur) in enumerate([("A Day at UIC Group", "Vlogs", "12:34"), ("Trip to Kyrgyzstan", "Vlogs", "08:21"),
                                            ("Building NutriZone", "Projects", "15:42"), ("Tech Conference 2026", "Events", "10:18")]):
            v = Video(category=cats[("video", cat)], duration=dur, youtube_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ", recorded_at=date.today() - timedelta(days=i * 20))
            tr(v, "title", en)
            v.thumbnail.save(f"video-{i}.jpg", ph.landscape(70 + i, size=(1280, 720)), save=False)
            v.save()
        tracks = []
        for i, (title, artist, cat) in enumerate([("Another Horizon", "WeliCoDev Ambient", "Chill"), ("Mountains", "WeliCoDev Ambient", "Focus"),
                                                  ("Experience", "WeliCoDev Ambient", "Focus"), ("Close To You", "WeliCoDev Ambient", "Travel")]):
            t = Track(title=title, artist=artist, category=cats[("music", cat)], duration="0:18", is_favorite=i == 0, order=i)
            t.audio.save(f"track-{i}.wav", ph.ambient_wav(i), save=False)
            t.cover.save(f"track-{i}.jpg", ph.landscape(80 + i, size=(400, 400)), save=False)
            t.save()
            tracks.append(t)
        for i, (en, uz) in enumerate([("Focus Mode", "Fokus"), ("Coding", "Kod yozish"), ("Chill Vibes", "Dam olish"), ("Workout", "Mashg'ulot")]):
            pl = Playlist(order=i)
            tr(pl, "title", uz, en)
            pl.cover.save(f"pl-{i}.jpg", ph.landscape(90 + i, size=(500, 400)), save=False)
            pl.save()
            pl.tracks.set(tracks[: 2 + i % 3])

    # ------------------------------------------------------------------ Education
    def education(self, skills):
        c = Course(level="beginner", is_free=True, status="published", is_featured=True, sequential=True)
        tr(c, "title", "Docker: noldan production'gacha", "Docker: from zero to production", "Docker: с нуля до продакшена")
        tr(c, "subtitle", "Konteynerlar, Dockerfile, Compose va deploy — amaliy loyihalar bilan.",
           "Containers, Dockerfiles, Compose and deployment — with hands-on projects.",
           "Контейнеры, Dockerfile, Compose и деплой — на практических проектах.")
        tr(c, "description", "<p>Bu kursda Docker'ni noldan o'rganib, haqiqiy Django loyihasini konteynerlarda ishga tushirasiz.</p>",
           "<p>Learn Docker from scratch and ship a real Django project in containers.</p>")
        tr(c, "what_you_learn", "<ul><li>Konteyner va image farqi</li><li>Dockerfile yozish</li><li>Docker Compose</li><li>Production deploy</li></ul>",
           "<ul><li>Containers vs images</li><li>Writing Dockerfiles</li><li>Docker Compose</li><li>Production deployment</li></ul>")
        c.cover.save("docker.jpg", ph.app_screenshot(2, "Docker", "From zero to production"), save=False)
        c.save()
        c.technologies.set([skills["Docker"], skills["Linux"], skills["Django"]])
        m1 = Module(course=c, order=1)
        tr(m1, "title", "Asoslar", "Fundamentals", "Основы")
        m1.save()
        m2 = Module(course=c, order=2)
        tr(m2, "title", "Amaliyot", "Practice", "Практика")
        m2.save()
        lessons = [
            ("Docker nima va nega kerak?", "What is Docker and why?", m1, "none", True),
            ("O'rnatish va birinchi konteyner", "Installation and first container", m1, "submit", False),
            ("Image va qatlamlar", "Images and layers", m1, "none", False),
            ("Dockerfile yozish", "Writing a Dockerfile", m2, "submit", False),
            ("Docker Compose", "Docker Compose", m2, "approval", False),
            ("Django loyihasini konteynerlash", "Containerizing a Django project", m2, "submit", False),
        ]
        dockerfile = (
            '<pre><code class="language-dockerfile">FROM python:3.12-slim\nWORKDIR /app\nCOPY requirements.txt .\n'
            'RUN pip install --no-cache-dir -r requirements.txt\nCOPY . .\nCMD ["gunicorn", "config.wsgi", "-b", "0.0.0.0:8000"]</code></pre>'
        )
        for i, (uz, en, mod, hw, preview) in enumerate(lessons, start=1):
            les = Lesson(course=c, module=mod, order=i, homework_mode=hw, is_preview=preview, status="published",
                         video_url="https://www.youtube.com/watch?v=pg19Z8LL06w", duration_seconds=420 + i * 95)
            tr(les, "title", uz, en)
            tr(les, "summary", f"{i}-dars: {uz}", f"Lesson {i}: {en}")
            tr(les, "content",
               f"<h2>Dars rejasi</h2><p>Bu darsda {uz.lower()} mavzusini ko'rib chiqamiz.</p><h2>Kod</h2>{dockerfile}<h2>Buyruqlar</h2>"
               '<pre><code class="language-bash">docker build -t myapp .\ndocker run -p 8000:8000 myapp</code></pre>',
               f"<h2>Lesson plan</h2><p>In this lesson we cover: {en.lower()}.</p><h2>Code</h2>{dockerfile}<h2>Commands</h2>"
               '<pre><code class="language-bash">docker build -t myapp .\ndocker run -p 8000:8000 myapp</code></pre>')
            if hw != "none":
                tr(les, "homework", "<p>O'z kompyuteringizda shu darsdagi buyruqlarni bajaring va natijani GitHub'ga joylang. Repo havolasini yuboring.</p>",
                   "<p>Run the commands from this lesson on your machine and push the result to GitHub. Submit the repo link.</p>")
            les.save()
            for j, (title, url) in enumerate([("Docker Docs", "https://docs.docker.com/"), ("Dockerfile reference", "https://docs.docker.com/reference/dockerfile/")]):
                r = LessonResource(lesson=les, kind="docs", url=url, order=j)
                tr(r, "title", title)
                r.save()
