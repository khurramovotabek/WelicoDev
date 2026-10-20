"""To'liq Docker kursi: 6 modul, 27 dars (konspekt, kod, uyga vazifa, havolalar).

Videolar keyin dashboard orqali qo'shiladi; video bo'lmagan darsda faqat uyga vazifa talab qilinadi.

    python manage.py seed_docker_course            # kurs bo'lmasa yaratadi
    python manage.py seed_docker_course --replace  # mavjud darslarni qayta yozadi (progress o'chadi!)
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.html import escape

from apps.core.management.commands.seed_demo import tr
from apps.education.models import Course, Lesson, LessonResource, Module
from apps.portfolio.models import Skill

D = "https://docs.docker.com"


def code(lang, text):
    return f'<pre><code class="language-{lang}">{escape(text.strip())}</code></pre>'


# (modul nomi, [ (sarlavha uz, sarlavha en, daqiqa, qisqa, matn html, uyga vazifa html | None, [(havola nomi, url)]) ])
MODULES = [
    ("Kirish va asoslar", [
        ("Docker nima va qanday muammoni hal qiladi", "What Docker is and why it matters", 9,
         "\"Mening kompyuterimda ishlayapti\" muammosi va konteynerlash g'oyasi.",
         "<h2>Muammo</h2><p>Dastur sizning kompyuteringizda ishlaydi, serverda esa yo'q: Python versiyasi boshqa, kutubxona yetishmaydi, sozlama farq qiladi. Docker ilovani <strong>barcha bog'liqliklari bilan birga</strong> bitta paketga — <em>image</em>ga joylaydi va u istalgan joyda bir xil ishlaydi.</p>"
         "<h2>Asosiy g'oya</h2><ul><li><strong>Image</strong> — ilova va uning muhitining \"surati\" (faqat o'qish uchun).</li><li><strong>Container</strong> — image'dan ishga tushirilgan jonli jarayon.</li><li><strong>Registry</strong> — image'lar saqlanadigan joy (Docker Hub).</li></ul>"
         "<blockquote><p>Docker ilovani emas, ilovaning <strong>muhitini</strong> ham yetkazib beradi.</p></blockquote>",
         None, [("Docker overview", f"{D}/get-started/docker-overview/")]),
        ("Konteyner va virtual mashina farqi", "Containers vs virtual machines", 8,
         "Nega konteynerlar sekundlarda ishga tushadi va kam resurs talab qiladi.",
         "<h2>Virtual mashina</h2><p>Har bir VM o'zining to'liq operatsion tizimiga ega — gigabaytlar va daqiqalar.</p><h2>Konteyner</h2><p>Konteynerlar xost tizimning yadrosini (kernel) bo'lishib ishlatadi va faqat ilova uchun kerakli fayllarni o'z ichiga oladi — megabaytlar va sekundlar.</p>"
         "<table><thead><tr><th></th><th>VM</th><th>Konteyner</th></tr></thead><tbody><tr><td>Ishga tushish</td><td>daqiqalar</td><td>sekundlar</td></tr><tr><td>Hajm</td><td>GB</td><td>MB</td></tr><tr><td>Izolyatsiya</td><td>to'liq OS</td><td>jarayon darajasida</td></tr></tbody></table>",
         "<p>VM va konteyner farqini o'zingizning so'zlaringiz bilan 5-6 gapda yozing va qaysi holatda VM afzalroq ekanini misol bilan tushuntiring.</p>",
         [("Containers vs VMs", "https://www.docker.com/resources/what-container/")]),
        ("Docker'ni o'rnatish", "Installing Docker", 12,
         "Linux, Windows (WSL2) va macOS'da Docker Engine va Docker Desktop.",
         "<h2>Ubuntu</h2>" + code("bash", "curl -fsSL https://get.docker.com | sh\nsudo usermod -aG docker $USER\nnewgrp docker\ndocker --version") +
         "<h2>Windows va macOS</h2><p>Docker Desktop'ni o'rnating. Windows'da WSL2 yoqilgan bo'lishi kerak.</p><h2>Tekshirish</h2>" + code("bash", "docker info\ndocker compose version"),
         "<p>Docker'ni o'rnating va <code>docker --version</code> hamda <code>docker info</code> natijasining skrinshotini yuboring.</p>",
         [("Install Docker Engine", f"{D}/engine/install/"), ("Docker Desktop", f"{D}/desktop/")]),
        ("Birinchi konteyner", "Your first container", 7,
         "docker run hello-world: buyruq ortida nima sodir bo'ladi.",
         "<p>Birinchi buyruq:</p>" + code("bash", "docker run hello-world") +
         "<h2>Nima bo'ldi?</h2><ol><li>Docker lokal <code>hello-world</code> image'ini qidirdi.</li><li>Topmadi va Docker Hub'dan yuklab oldi (pull).</li><li>Image'dan konteyner yaratib, ishga tushirdi.</li><li>Konteyner matnni chiqardi va to'xtadi.</li></ol>" + code("bash", "docker ps -a      # barcha konteynerlar\ndocker images     # lokal image'lar"),
         "<p><code>nginx</code> image'ini ishga tushiring: <code>docker run -d -p 8080:80 nginx</code>, brauzerda <code>localhost:8080</code> ni oching va skrinshot yuboring.</p>",
         [("docker run", f"{D}/reference/cli/docker/container/run/")]),
        ("Image, container, registry", "Images, containers and registries", 10,
         "Uchta asosiy tushuncha va ular orasidagi bog'liqlik.",
         "<h2>Image</h2><p>Qatlamlardan iborat, o'zgarmaydigan shablon. Nomi: <code>repo:tag</code> (masalan <code>python:3.12-slim</code>).</p><h2>Container</h2><p>Image ustiga yoziladigan yupqa qatlam qo'shilgan jonli nusxa. Bitta image'dan istalgancha konteyner.</p><h2>Registry</h2><p>Docker Hub, GitHub Container Registry yoki o'zingizning registry.</p>" + code("bash", "docker pull python:3.12-slim\ndocker image inspect python:3.12-slim\ndocker run -it --rm python:3.12-slim python"),
         "<p>Modul yakuni: <code>python:3.12-slim</code> va <code>python:3.12</code> image'lari hajmini solishtiring (<code>docker images</code>) va farq sababini yozing.</p>",
         [("Docker Hub", "https://hub.docker.com/")]),
    ]),
    ("Konteynerlar bilan ishlash", [
        ("docker run parametrlari", "docker run options", 11,
         "-d, -p, --name, --rm, -it: kundalik ishda eng ko'p kerak bo'ladiganlari.",
         code("bash", "docker run -d --name web -p 8080:80 nginx   # fonda, port bilan\ndocker run -it --rm ubuntu bash             # interaktiv, tugagach o'chadi\ndocker run -d --restart unless-stopped redis # avtomatik qayta ishga tushish") +
         "<ul><li><code>-p HOST:CONTAINER</code> — portni ochish.</li><li><code>--rm</code> — to'xtaganda konteynerni o'chirish.</li><li><code>--restart</code> — server qayta yuklanganda ham ishlashi uchun.</li></ul>",
         "<p><code>redis</code> konteynerini <code>my-redis</code> nomi va 6380 porti bilan fonda ishga tushiring, <code>docker ps</code> natijasini yuboring.</p>",
         [("Running containers", f"{D}/engine/containers/run/")]),
        ("Konteyner hayot sikli", "Container lifecycle", 8,
         "create → start → stop → rm: holatlar va buyruqlar.",
         code("bash", "docker stop web\ndocker start web\ndocker restart web\ndocker rm -f web\ndocker container prune   # to'xtagan konteynerlarni tozalash") +
         "<p><code>stop</code> jarayonga SIGTERM yuboradi va 10 soniya kutadi, <code>kill</code> esa darhol to'xtatadi.</p>",
         "<p>Bitta konteynerni yarating, to'xtating, qayta ishga tushiring va o'chiring. Har bir qadamdagi <code>docker ps -a</code> holatini yozib yuboring.</p>",
         [("docker container", f"{D}/reference/cli/docker/container/")]),
        ("Loglar va konteyner ichiga kirish", "Logs and exec", 9,
         "docker logs, docker exec va docker inspect bilan muammolarni topish.",
         code("bash", "docker logs -f --tail 100 web\ndocker exec -it web sh\ndocker inspect web --format '{{.NetworkSettings.IPAddress}}'\ndocker stats") +
         "<blockquote><p>Productionda konteyner ichida qo'lda o'zgartirish qilmang — o'zgarish konteyner o'chganda yo'qoladi.</p></blockquote>",
         "<p>nginx konteyneri ichiga kiring, <code>/usr/share/nginx/html/index.html</code> faylini o'zgartiring va natijani brauzerda ko'rsating.</p>",
         [("docker logs", f"{D}/reference/cli/docker/container/logs/")]),
        ("Environment o'zgaruvchilar", "Environment variables", 8,
         "-e va --env-file: sozlamalarni koddan ajratish.",
         code("bash", "docker run -e POSTGRES_PASSWORD=secret -d postgres:16\ndocker run --env-file .env myapp") +
         "<p>Parol va kalitlarni hech qachon image ichiga yozmang — ular <code>.env</code> faylda yoki secret sifatida beriladi.</p>",
         "<p><code>.env</code> fayl yarating va <code>postgres:16</code> konteynerini shu fayl orqali ishga tushiring.</p>",
         [("Environment variables", f"{D}/compose/how-tos/environment-variables/")]),
        ("Resurslarni cheklash", "Limiting resources", 7,
         "--memory va --cpus: bitta konteyner butun serverni egallab olmasin.",
         code("bash", "docker run -d --memory 256m --cpus 0.5 --name limited nginx\ndocker stats limited"),
         "<p>Modul yakuni: CPU va xotirasi cheklangan konteyner ishga tushiring, <code>docker stats</code> skrinshoti va nega bu productionda muhimligini yozing.</p>",
         [("Resource constraints", f"{D}/engine/containers/resource_constraints/")]),
    ]),
    ("Image yaratish: Dockerfile", [
        ("Dockerfile asoslari", "Dockerfile basics", 12,
         "FROM, WORKDIR, COPY, RUN, CMD — birinchi Dockerfile.",
         code("dockerfile", 'FROM python:3.12-slim\nWORKDIR /app\nCOPY app.py .\nCMD ["python", "app.py"]') + code("bash", "docker build -t hello-py .\ndocker run --rm hello-py") +
         "<p><code>RUN</code> build paytida, <code>CMD</code> esa konteyner ishga tushganda bajariladi.</p>",
         "<p>\"Salom, Docker!\" chiqaradigan Python dasturi uchun Dockerfile yozing va GitHub'ga joylang.</p>",
         [("Dockerfile reference", f"{D}/reference/dockerfile/")]),
        ("Qatlamlar va build kesh", "Layers and build cache", 10,
         "Nega buyruqlar tartibi build tezligini 10 barobar o'zgartiradi.",
         "<p>Har bir instruksiya yangi qatlam. O'zgarmagan qatlamlar keshdan olinadi. Shuning uchun avval bog'liqliklarni, keyin kodni nusxalang:</p>" + code("dockerfile", "COPY requirements.txt .\nRUN pip install --no-cache-dir -r requirements.txt\nCOPY . .") ,
         "<p>Buyruqlar tartibini almashtirib ikki marta build qiling va vaqt farqini yozing.</p>",
         [("Build cache", f"{D}/build/cache/")]),
        (".dockerignore va image hajmi", ".dockerignore and image size", 8,
         "Keraksiz fayllarni chiqarish va kichik base image tanlash.",
         code("text", ".git\n__pycache__/\n*.pyc\n.venv/\nnode_modules/\n.env\nmedia/") +
         "<p><code>slim</code> va <code>alpine</code> image'lar ancha kichik, lekin alpine'da ba'zi Python paketlari qiyin o'rnatiladi.</p>",
         "<p>O'z loyihangiz uchun <code>.dockerignore</code> yozing va image hajmi oldin va keyin qancha bo'lganini yuboring.</p>",
         [(".dockerignore", f"{D}/build/concepts/context/#dockerignore-files")]),
        ("Multi-stage build", "Multi-stage builds", 11,
         "Build vositalarini yakuniy image'ga olib kirmaslik.",
         code("dockerfile", "FROM node:20 AS assets\nWORKDIR /src\nCOPY package*.json .\nRUN npm ci\nCOPY . .\nRUN npm run build\n\nFROM python:3.12-slim\nWORKDIR /app\nCOPY --from=assets /src/static/dist ./static/dist\nCOPY . .") ,
         "<p>Frontend assetlari bor loyiha uchun multi-stage Dockerfile yozing.</p>",
         [("Multi-stage builds", f"{D}/build/building/multi-stage/")]),
        ("Django ilovasi uchun Dockerfile", "A Dockerfile for Django", 14,
         "Production darajasidagi Django Dockerfile qadam-baqadam.",
         code("dockerfile", 'FROM python:3.12-slim\nENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1\nWORKDIR /app\nRUN apt-get update && apt-get install -y --no-install-recommends libpq5 && rm -rf /var/lib/apt/lists/*\nCOPY requirements.txt .\nRUN pip install --no-cache-dir -r requirements.txt\nCOPY . .\nRUN python manage.py collectstatic --noinput\nCMD ["gunicorn", "config.wsgi", "-b", "0.0.0.0:8000", "-w", "3"]'),
         "<p>O'zingizning Django loyihangizni konteynerga joylang va <code>localhost:8000</code> da ishlayotganini ko'rsating.</p>",
         [("Containerize a Python app", f"{D}/guides/python/containerize/")]),
        ("Image'ni registry'ga yuklash", "Pushing images to a registry", 8,
         "docker tag, docker login, docker push.",
         code("bash", "docker login\ndocker tag myapp:latest username/myapp:1.0\ndocker push username/myapp:1.0"),
         "<p>Modul yakuni: image'ingizni Docker Hub'ga yuklang va havolasini yuboring.</p>",
         [("docker push", f"{D}/reference/cli/docker/image/push/")]),
    ]),
    ("Ma'lumotlar va tarmoq", [
        ("Volumes: ma'lumotlarni saqlash", "Volumes: persisting data", 10,
         "Konteyner o'chsa ham ma'lumotlar saqlanishi uchun.",
         code("bash", "docker volume create pgdata\ndocker run -d --name db -v pgdata:/var/lib/postgresql/data -e POSTGRES_PASSWORD=secret postgres:16\ndocker volume ls"),
         "<p>PostgreSQL'da jadval yarating, konteynerni o'chiring va volume bilan qayta yarating — ma'lumot saqlanganini isbotlang.</p>",
         [("Volumes", f"{D}/engine/storage/volumes/")]),
        ("Bind mount: lokal ishlab chiqish", "Bind mounts for development", 8,
         "Kodni o'zgartirsangiz konteynerda darhol ko'rinadi.",
         code("bash", "docker run -d -p 8000:8000 -v \"$(pwd)\":/app myapp python manage.py runserver 0.0.0.0:8000"),
         "<p>Bind mount bilan Django dev serverini ishga tushiring va kod o'zgarishi darhol ko'rinishini ko'rsating.</p>",
         [("Bind mounts", f"{D}/engine/storage/bind-mounts/")]),
        ("Docker tarmoqlari", "Docker networking", 10,
         "bridge, host va o'zingiz yaratgan tarmoqlar; DNS nom bilan murojaat.",
         code("bash", "docker network create appnet\ndocker run -d --name db --network appnet postgres:16\ndocker run --rm --network appnet alpine ping -c 2 db"),
         "<p>Ikki konteynerni bitta tarmoqqa ulang va biri ikkinchisiga nom orqali murojaat qila olishini ko'rsating.</p>",
         [("Networking overview", f"{D}/engine/network/")]),
        ("Django + PostgreSQL konteynerlarda", "Django and PostgreSQL in containers", 12,
         "Ikki konteynerni qo'lda bog'lash: compose'dan oldin nima bo'layotganini tushunish.",
         code("bash", "docker network create web\ndocker run -d --name db --network web -e POSTGRES_PASSWORD=secret -v pgdata:/var/lib/postgresql/data postgres:16\ndocker run -d --name app --network web -p 8000:8000 -e DATABASE_HOST=db myapp"),
         "<p>Modul yakuni: Django va PostgreSQL'ni alohida konteynerlarda ishga tushiring, migratsiya qiling va admin panel skrinshotini yuboring.</p>",
         [("Use containers for Python development", f"{D}/guides/python/develop/")]),
    ]),
    ("Docker Compose", [
        ("Docker Compose asoslari", "Docker Compose basics", 11,
         "Bir nechta konteynerni bitta YAML fayl bilan boshqarish.",
         code("yaml", "services:\n  web:\n    image: nginx\n    ports:\n      - \"8080:80\"") + code("bash", "docker compose up -d\ndocker compose ps\ndocker compose logs -f\ndocker compose down"),
         "<p>nginx va redis'dan iborat compose fayl yozing va ishga tushiring.</p>",
         [("Compose overview", f"{D}/compose/")]),
        ("Django + PostgreSQL + Redis", "Django, PostgreSQL and Redis with Compose", 14,
         "To'liq ishlab chiqish muhiti bitta buyruq bilan.",
         code("yaml", "services:\n  db:\n    image: postgres:16-alpine\n    environment:\n      POSTGRES_PASSWORD: secret\n    volumes:\n      - pgdata:/var/lib/postgresql/data\n  redis:\n    image: redis:7-alpine\n  web:\n    build: .\n    command: python manage.py runserver 0.0.0.0:8000\n    ports:\n      - \"8000:8000\"\n    env_file: .env\n    depends_on:\n      - db\n      - redis\nvolumes:\n  pgdata:"),
         "<p>O'z loyihangiz uchun shunday compose fayl yozing va GitHub'ga joylang.</p>",
         [("Compose file reference", f"{D}/reference/compose-file/")]),
        ("Healthcheck va depends_on", "Healthchecks and startup order", 9,
         "Baza tayyor bo'lmasdan ilova ishga tushib ketmasligi uchun.",
         code("yaml", "  db:\n    image: postgres:16-alpine\n    healthcheck:\n      test: [\"CMD-SHELL\", \"pg_isready -U postgres\"]\n      interval: 5s\n      retries: 10\n  web:\n    depends_on:\n      db:\n        condition: service_healthy"),
         "<p>Compose faylingizga healthcheck qo'shing va <code>docker compose ps</code> da <em>healthy</em> holatini ko'rsating.</p>",
         [("Startup order", f"{D}/compose/how-tos/startup-order/")]),
        ("Celery worker va beat", "Celery worker and beat", 10,
         "Fon vazifalari uchun alohida servislar.",
         code("yaml", "  worker:\n    build: .\n    command: celery -A config worker -l info\n    env_file: .env\n    depends_on: [redis, db]\n  beat:\n    build: .\n    command: celery -A config beat -l info\n    env_file: .env\n    depends_on: [redis]"),
         "<p>Modul yakuni: Django + PostgreSQL + Redis + Celery worker'dan iborat to'liq stack'ni ishga tushiring va bitta fon vazifasi bajarilganini ko'rsating.</p>",
         [("Celery: Using Redis", "https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/redis.html")]),
    ]),
    ("Production", [
        ("Production uchun Docker", "Docker in production", 13,
         "gunicorn, Nginx reverse proxy, static fayllar va SSL.",
         code("nginx", "server {\n    listen 80;\n    server_name example.uz;\n    location /static/ { alias /app/staticfiles/; }\n    location / {\n        proxy_pass http://web:8000;\n        proxy_set_header Host $host;\n        proxy_set_header X-Forwarded-Proto $scheme;\n    }\n}"),
         "<p>Compose'ga Nginx servisini qo'shing va static fayllar Nginx orqali berilayotganini ko'rsating.</p>",
         [("Nginx reverse proxy", "https://nginx.org/en/docs/http/ngx_http_proxy_module.html")]),
        ("Xavfsizlik", "Security best practices", 10,
         "Non-root foydalanuvchi, secrets, minimal image va skanerlash.",
         code("dockerfile", "RUN useradd -m appuser\nUSER appuser") + code("bash", "docker scout cves myapp:latest") +
         "<ul><li>Konteynerni root sifatida ishlatmang.</li><li>Parollarni image'ga yozmang.</li><li>Base image'larni muntazam yangilang.</li></ul>",
         "<p>Dockerfile'ingizni non-root foydalanuvchiga o'tkazing va <code>docker scout</code> natijasini yuboring.</p>",
         [("Security", f"{D}/engine/security/"), ("Docker Scout", f"{D}/scout/")]),
        ("Yakuniy loyiha: serverga deploy", "Final project: deploying to a server", 18,
         "Django ilovasini VPS'ga Docker Compose bilan chiqarish: domen, SSL, backup.",
         "<h2>Reja</h2><ol><li>VPS'ga Docker o'rnatish.</li><li>Kodni serverga olish (git clone).</li><li><code>.env</code> production sozlamalari.</li><li><code>docker compose -f compose.prod.yml up -d --build</code></li><li>Let's Encrypt bilan SSL.</li><li>PostgreSQL backup cron bilan.</li></ol>" + code("bash", "docker compose -f compose.prod.yml up -d --build\ndocker compose exec web python manage.py migrate\ndocker compose exec db pg_dump -U postgres app > backup.sql"),
         "<p>Yakuniy loyiha: Django ilovangizni serverga deploy qiling. Sayt havolasi va GitHub repo'ni yuboring — tekshirilgach sertifikat beriladi.</p>",
         [("Deploy with Compose", f"{D}/compose/how-tos/production/")]),
    ]),
]

# Har modulning oxirgi darsi admin tekshiruvi bilan (modul yakuni), qolganlari topshirish bilan
APPROVAL_LAST_IN_MODULE = True


class Command(BaseCommand):
    help = "To'liq Docker kursi (27 dars) yaratadi va boshqa demo kurslarni qoralamaga o'tkazadi"

    def add_arguments(self, parser):
        parser.add_argument("--replace", action="store_true", help="Mavjud darslarni qayta yozish (o'quvchilar progressi o'chadi)")
        parser.add_argument("--keep-others", action="store_true", help="Boshqa kurslarni qoralamaga o'tkazmaslik")

    @transaction.atomic
    def handle(self, *args, replace=False, keep_others=False, **opts):
        course = Course.objects.filter(slug="docker-from-zero-to-production").first()
        if course is None:
            self.stderr.write("Docker kursi topilmadi: avval seed_demo ishga tushiring")
            return
        if course.lessons.count() >= 27 and not replace:
            self.stdout.write("Docker kursi allaqachon to'liq (--replace bilan qayta yozish mumkin)")
        else:
            course.lessons.all().delete()
            course.modules.all().delete()
            self._build(course)
        if not keep_others:
            n = Course.objects.exclude(pk=course.pk).filter(status="published").update(status="draft")
            self.stdout.write(f"{n} ta demo kurs qoralamaga o'tkazildi (dashboard'dan qaytarish mumkin)")
        self.stdout.write(self.style.SUCCESS(f"Docker kursi: {course.lessons.count()} dars, {course.modules.count()} modul"))

    def _build(self, course):
        tr(course, "subtitle", "Konteynerlar, Dockerfile, Compose va production deploy — 27 ta amaliy dars.",
           "Containers, Dockerfiles, Compose and production deployment — 27 hands-on lessons.",
           "Контейнеры, Dockerfile, Compose и продакшен-деплой — 27 практических уроков.")
        tr(course, "description",
           "<p>Docker'ni noldan o'rganib, kurs oxirida o'zingizning Django ilovangizni serverga Docker Compose bilan chiqarasiz. "
           "Har bir dars: konspekt, ishlaydigan kod, uyga vazifa va rasmiy hujjat havolalari.</p>"
           "<p>Darslar ketma-ket ochiladi. Har modul oxirida amaliy topshiriq tekshiriladi, yakuniy loyiha uchun sertifikat beriladi.</p>")
        tr(course, "what_you_learn",
           "<ul><li>Konteyner, image va registry qanday ishlashini</li><li>Production darajasidagi Dockerfile yozishni</li>"
           "<li>Volume va tarmoqlar bilan ishlashni</li><li>Docker Compose bilan Django + PostgreSQL + Redis + Celery stack'ini</li>"
           "<li>Nginx, SSL va xavfsizlik bilan serverga deploy qilishni</li></ul>")
        tr(course, "for_whom",
           "<ul><li>Backend dasturchilar (Python/Django)</li><li>DevOps'ni boshlamoqchi bo'lganlar</li><li>Loyihasini serverga chiqarmoqchi bo'lgan har kim</li></ul>")
        tr(course, "requirements",
           "<ul><li>Terminal bilan ishlash asoslari</li><li>Python yoki boshqa tilda oddiy dastur yozish tajribasi</li><li>Docker o'rnatiladigan kompyuter (8 GB RAM tavsiya etiladi)</li></ul>")
        course.status, course.is_featured, course.sequential, course.has_certificate = "published", True, True, True
        course.save()
        skills = {s.name: s for s in Skill.objects.filter(name__in=["Docker", "Linux", "Django", "PostgreSQL", "Redis", "Nginx"])}
        course.technologies.set(skills.values())

        order = 0
        for mi, (mtitle, lessons) in enumerate(MODULES, start=1):
            m = Module(course=course, order=mi)
            tr(m, "title", f"{mi}. {mtitle}")
            m.save()
            for li, (uz, en, minutes, summary, body, homework, resources) in enumerate(lessons):
                order += 1
                last = li == len(lessons) - 1
                mode = "none" if not homework else ("approval" if last and APPROVAL_LAST_IN_MODULE else "submit")
                les = Lesson(course=course, module=m, order=order, status="published", is_preview=order <= 2,
                             duration_seconds=minutes * 60, homework_mode=mode)
                tr(les, "title", uz, en)
                tr(les, "summary", summary)
                tr(les, "content", body)
                if homework:
                    tr(les, "homework", homework + "<p>Javobni GitHub havolasi, matn yoki fayl ko'rinishida topshiring.</p>")
                les.save()
                for ri, (title, url) in enumerate(resources):
                    r = LessonResource(lesson=les, kind="docs", url=url, order=ri)
                    tr(r, "title", title)
                    r.save()
