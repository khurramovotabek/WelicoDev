"""@welicodev_educationbot matnlari: uz / ru / en. Kalit topilmasa o'zbekcha matn qaytadi."""

TEXTS = {
    "welcome": {
        "uz": "🎓 <b>WeliCoDev Academy</b>ga xush kelibsiz, {name}!\n\nBu yerda kurslarga yozilasiz, o'qishni davom ettirasiz va uyga vazifalaringiz natijasini olasiz.\n\nPastdagi menyudan tanlang 👇",
        "ru": "🎓 Добро пожаловать в <b>WeliCoDev Academy</b>, {name}!\n\nЗдесь можно записаться на курсы, продолжить обучение и получать результаты домашних заданий.\n\nВыберите в меню ниже 👇",
        "en": "🎓 Welcome to <b>WeliCoDev Academy</b>, {name}!\n\nEnroll in courses, pick up where you left off and get your homework results here.\n\nChoose from the menu below 👇",
    },
    "need_register": {
        "uz": "👋 Avval asosiy botimizda ro'yxatdan o'ting — bir daqiqa vaqt oladi. Keyin shu yerga qayting va /start bosing.",
        "ru": "👋 Сначала зарегистрируйтесь в нашем основном боте — это займёт минуту. Затем вернитесь сюда и нажмите /start.",
        "en": "👋 Please register in our main bot first — it takes a minute. Then come back and tap /start.",
    },
    "btn_register": {"uz": "📝 Ro'yxatdan o'tish", "ru": "📝 Регистрация", "en": "📝 Register"},
    "btn_courses": {"uz": "📚 Kurslar", "ru": "📚 Курсы", "en": "📚 Courses"},
    "btn_my": {"uz": "🎓 Mening kurslarim", "ru": "🎓 Мои курсы", "en": "🎓 My courses"},
    "btn_homework": {"uz": "📝 Vazifalarim", "ru": "📝 Мои задания", "en": "📝 My homework"},
    "btn_lang": {"uz": "🌐 Til", "ru": "🌐 Язык", "en": "🌐 Language"},
    "btn_admin": {"uz": "🛠 Boshqaruv", "ru": "🛠 Управление", "en": "🛠 Admin"},
    "courses_header": {"uz": "📚 <b>Kurslar</b>\n\nBatafsil ko'rish uchun kursni tanlang:", "ru": "📚 <b>Курсы</b>\n\nВыберите курс:", "en": "📚 <b>Courses</b>\n\nPick a course:"},
    "courses_empty": {"uz": "Hozircha kurslar yo'q.", "ru": "Пока курсов нет.", "en": "No courses yet."},
    "course_card": {
        "uz": "🎓 <b>{title}</b>\n\n{subtitle}\n\n📊 {level} · 📚 {lessons} dars · ⏱ {duration}\n💰 {price}",
        "ru": "🎓 <b>{title}</b>\n\n{subtitle}\n\n📊 {level} · 📚 {lessons} уроков · ⏱ {duration}\n💰 {price}",
        "en": "🎓 <b>{title}</b>\n\n{subtitle}\n\n📊 {level} · 📚 {lessons} lessons · ⏱ {duration}\n💰 {price}",
    },
    "progress_line": {"uz": "\n\n✅ Progress: <b>{p}%</b>", "ru": "\n\n✅ Прогресс: <b>{p}%</b>", "en": "\n\n✅ Progress: <b>{p}%</b>"},
    "free": {"uz": "Bepul", "ru": "Бесплатно", "en": "Free"},
    "som": {"uz": "{price} so'm", "ru": "{price} сум", "en": "{price} UZS"},
    "btn_enroll": {"uz": "✅ Kursga yozilish", "ru": "✅ Записаться", "en": "✅ Enroll"},
    "btn_continue": {"uz": "▶️ Davom ettirish", "ru": "▶️ Продолжить", "en": "▶️ Continue"},
    "btn_request": {"uz": "💳 Ruxsat so'rash", "ru": "💳 Запросить доступ", "en": "💳 Request access"},
    "btn_requested": {"uz": "⏳ So'rov ko'rib chiqilmoqda", "ru": "⏳ Запрос на рассмотрении", "en": "⏳ Request pending"},
    "btn_site": {"uz": "🌐 Saytda ochish", "ru": "🌐 Открыть на сайте", "en": "🌐 Open on website"},
    "btn_back": {"uz": "⬅️ Orqaga", "ru": "⬅️ Назад", "en": "⬅️ Back"},
    "enrolled": {
        "uz": "🎉 <b>{title}</b> kursiga yozildingiz!\n\nBirinchi darsdan boshlang — saytga Telegram orqali kirasiz.",
        "ru": "🎉 Вы записались на курс <b>{title}</b>!\n\nНачните с первого урока — вход на сайт через Telegram.",
        "en": "🎉 You're enrolled in <b>{title}</b>!\n\nStart with the first lesson — you sign in to the site with Telegram.",
    },
    "requested": {
        "uz": "✅ So'rovingiz qabul qilindi · <code>{ref}</code>\n\nAdmin to'lov tafsilotlari bo'yicha siz bilan bog'lanadi. Ruxsat berilishi bilan shu botga xabar keladi.",
        "ru": "✅ Запрос принят · <code>{ref}</code>\n\nАдминистратор свяжется с вами по оплате. Как только доступ откроют — придёт сообщение в этот бот.",
        "en": "✅ Request received · <code>{ref}</code>\n\nAn admin will contact you about payment. You'll get a message here as soon as access is granted.",
    },
    "my_empty": {
        "uz": "Siz hali hech qaysi kursga yozilmagansiz. 📚 Kurslar bo'limidan boshlang!",
        "ru": "Вы ещё не записаны ни на один курс. Начните с раздела 📚 Курсы!",
        "en": "You're not enrolled in any course yet. Start with 📚 Courses!",
    },
    "my_header": {"uz": "🎓 <b>Mening kurslarim</b>", "ru": "🎓 <b>Мои курсы</b>", "en": "🎓 <b>My courses</b>"},
    "my_row": {"uz": "\n\n<b>{title}</b>\n{bar} {p}%{done}", "ru": "\n\n<b>{title}</b>\n{bar} {p}%{done}", "en": "\n\n<b>{title}</b>\n{bar} {p}%{done}"},
    "done_mark": {"uz": " · 🏆 tugatilgan", "ru": " · 🏆 завершён", "en": " · 🏆 completed"},
    "hw_empty": {"uz": "Hali uyga vazifa topshirmagansiz.", "ru": "Вы ещё не сдавали домашних заданий.", "en": "You haven't submitted any homework yet."},
    "hw_header": {"uz": "📝 <b>Uyga vazifalarim</b>", "ru": "📝 <b>Мои домашние задания</b>", "en": "📝 <b>My homework</b>"},
    "hw_status": {
        "uz": {"pending": "⏳ tekshirilmoqda", "approved": "✅ qabul qilindi", "rejected": "🔁 qayta ishlash kerak"},
        "ru": {"pending": "⏳ на проверке", "approved": "✅ принято", "rejected": "🔁 нужно доработать"},
        "en": {"pending": "⏳ under review", "approved": "✅ accepted", "rejected": "🔁 needs rework"},
    },
    "help": {
        "uz": "🎓 <b>WeliCoDev Academy boti</b>\n\n/courses — kurslar katalogi\n/my — mening kurslarim va progress\n/homework — uyga vazifalar holati\n/lang — tilni o'zgartirish\n\nSaytga kirish va boshqa savollar uchun — @{main}",
        "ru": "🎓 <b>Бот WeliCoDev Academy</b>\n\n/courses — каталог курсов\n/my — мои курсы и прогресс\n/homework — статус заданий\n/lang — язык\n\nВход на сайт и другие вопросы — @{main}",
        "en": "🎓 <b>WeliCoDev Academy bot</b>\n\n/courses — course catalog\n/my — my courses and progress\n/homework — homework status\n/lang — change language\n\nSite sign-in and other questions — @{main}",
    },
    "unknown": {
        "uz": "Menyudan tanlang 👇 Savol bo'lsa — @{main} ga yozing.",
        "ru": "Выберите в меню 👇 Вопросы — пишите в @{main}.",
        "en": "Pick from the menu 👇 Questions — write to @{main}.",
    },
    "choose_lang": {"uz": "🌐 Tilni tanlang", "ru": "🌐 Выберите язык", "en": "🌐 Choose your language"},
    "lang_saved": {"uz": "✅ Til saqlandi", "ru": "✅ Язык сохранён", "en": "✅ Language saved"},
    "not_found": {"uz": "Kurs topilmadi.", "ru": "Курс не найден.", "en": "Course not found."},
    "no_access": {"uz": "Bu amal faqat adminlar uchun.", "ru": "Только для администраторов.", "en": "Admins only."},
    "blocked": {"uz": "⛔️ Hisobingiz bloklangan.", "ru": "⛔️ Ваш аккаунт заблокирован.", "en": "⛔️ Your account is blocked."},
    # --- Admin
    "admin_panel": {
        "uz": "🛠 <b>Ta'lim boshqaruvi</b>\n\n👥 O'quvchilar: <b>{students}</b>\n📚 Faol yozilishlar: <b>{enrollments}</b>\n🏆 Tugatganlar: <b>{completed}</b>\n💳 Kutilayotgan so'rovlar: <b>{requests}</b>\n📝 Tekshiriladigan vazifalar: <b>{homework}</b>\n💰 Jami tushum: <b>{revenue} so'm</b>",
        "ru": "🛠 <b>Управление обучением</b>\n\n👥 Учеников: <b>{students}</b>\n📚 Активных записей: <b>{enrollments}</b>\n🏆 Завершили: <b>{completed}</b>\n💳 Запросов ждут: <b>{requests}</b>\n📝 Заданий на проверку: <b>{homework}</b>\n💰 Выручка: <b>{revenue} сум</b>",
        "en": "🛠 <b>Education admin</b>\n\n👥 Students: <b>{students}</b>\n📚 Active enrollments: <b>{enrollments}</b>\n🏆 Completed: <b>{completed}</b>\n💳 Pending requests: <b>{requests}</b>\n📝 Homework to review: <b>{homework}</b>\n💰 Revenue: <b>{revenue} UZS</b>",
    },
    "btn_adm_requests": {"uz": "💳 So'rovlar ({n})", "ru": "💳 Запросы ({n})", "en": "💳 Requests ({n})"},
    "btn_adm_homework": {"uz": "📝 Vazifalar ({n})", "ru": "📝 Задания ({n})", "en": "📝 Homework ({n})"},
    "btn_dashboard": {"uz": "📊 Dashboard", "ru": "📊 Дашборд", "en": "📊 Dashboard"},
    "adm_nothing": {"uz": "Hammasi ko'rib chiqilgan ✨", "ru": "Всё рассмотрено ✨", "en": "All caught up ✨"},
    "btn_approve": {"uz": "✅ Ruxsat berish", "ru": "✅ Открыть доступ", "en": "✅ Grant access"},
    "btn_reject": {"uz": "❌ Rad etish", "ru": "❌ Отклонить", "en": "❌ Reject"},
    "btn_hw_ok": {"uz": "✅ Qabul", "ru": "✅ Принять", "en": "✅ Accept"},
    "btn_hw_redo": {"uz": "🔁 Qayta ishlash", "ru": "🔁 На доработку", "en": "🔁 Rework"},
    "btn_open": {"uz": "🔗 Ochish", "ru": "🔗 Открыть", "en": "🔗 Open"},
    "adm_done": {"uz": "\n\n<b>{verdict}</b> · {by}", "ru": "\n\n<b>{verdict}</b> · {by}", "en": "\n\n<b>{verdict}</b> · {by}"},
    "adm_already": {"uz": "Allaqachon ko'rib chiqilgan.", "ru": "Уже рассмотрено.", "en": "Already handled."},
    "v_granted": {"uz": "✅ Ruxsat berildi", "ru": "✅ Доступ открыт", "en": "✅ Access granted"},
    "v_rejected": {"uz": "❌ Rad etildi", "ru": "❌ Отклонено", "en": "❌ Rejected"},
    "v_hw_ok": {"uz": "✅ Vazifa qabul qilindi", "ru": "✅ Задание принято", "en": "✅ Homework accepted"},
    "v_hw_redo": {"uz": "🔁 Qayta ishlashga qaytarildi", "ru": "🔁 Отправлено на доработку", "en": "🔁 Sent back for rework"},
    # --- Kanal
    "btn_adm_post": {"uz": "📢 Kanalga post", "ru": "📢 Пост в канал", "en": "📢 Channel post"},
    "btn_adm_lessons": {"uz": "🎬 Darsni e'lon qilish", "ru": "🎬 Анонс урока", "en": "🎬 Announce a lesson"},
    "btn_adm_courses": {"uz": "🎓 Kursni e'lon qilish", "ru": "🎓 Анонс курса", "en": "🎓 Announce a course"},
    "no_channel": {
        "uz": "⚠️ Ta'lim kanali sozlanmagan: Dashboard → Bot sozlamalari → «Ta'lim kanali» (masalan @welicodev_education). Bot kanalda admin bo'lishi kerak.",
        "ru": "⚠️ Учебный канал не настроен: Дашборд → Настройки бота → «Учебный канал». Бот должен быть админом канала.",
        "en": "⚠️ Education channel isn't set: Dashboard → Bot settings → “Education channel”. The bot must be a channel admin.",
    },
    "post_prompt": {
        "uz": "📢 <b>{channel}</b> kanaliga joylanadigan xabarni yuboring: matn, rasm, video yoki fayl — formatlash va tugmalar saqlanadi.\n\nBekor qilish: /cancel",
        "ru": "📢 Отправьте сообщение для канала <b>{channel}</b>: текст, фото, видео или файл — форматирование сохранится.\n\nОтмена: /cancel",
        "en": "📢 Send the message for <b>{channel}</b>: text, photo, video or file — formatting is kept.\n\nCancel: /cancel",
    },
    "post_preview": {"uz": "👆 Kanalda shunday ko'rinadi. Joylaymizmi?", "ru": "👆 Так будет в канале. Публикуем?", "en": "👆 This is how it will look. Publish?"},
    "btn_publish": {"uz": "📢 Joylash", "ru": "📢 Опубликовать", "en": "📢 Publish"},
    "btn_publish_silent": {"uz": "🔕 Ovozsiz joylash", "ru": "🔕 Без звука", "en": "🔕 Publish silently"},
    "btn_cancel": {"uz": "❌ Bekor qilish", "ru": "❌ Отмена", "en": "❌ Cancel"},
    "post_done": {"uz": "✅ Kanalga joylandi: {link}", "ru": "✅ Опубликовано: {link}", "en": "✅ Published: {link}"},
    "post_failed": {"uz": "❌ Joylab bo'lmadi: {error}\n\nBot kanalda admin ekanini va «Xabar yuborish» huquqini tekshiring.", "ru": "❌ Не удалось: {error}\n\nПроверьте, что бот — админ канала.", "en": "❌ Failed: {error}\n\nMake sure the bot is a channel admin."},
    "cancelled": {"uz": "Bekor qilindi.", "ru": "Отменено.", "en": "Cancelled."},
    "nothing_to_announce": {"uz": "E'lon qilinmagan narsa yo'q ✨", "ru": "Нечего анонсировать ✨", "en": "Nothing left to announce ✨"},
    "pick_announce": {"uz": "Kanalga e'lon qilish uchun tanlang:", "ru": "Выберите, что анонсировать:", "en": "Pick what to announce:"},
}

LEVELS = {
    "beginner": {"uz": "Boshlang'ich", "ru": "Начальный", "en": "Beginner"},
    "intermediate": {"uz": "O'rta", "ru": "Средний", "en": "Intermediate"},
    "advanced": {"uz": "Yuqori", "ru": "Продвинутый", "en": "Advanced"},
}


def t(key, lang="uz", **kwargs):
    entry = TEXTS.get(key, {})
    text = entry.get(lang) or entry.get("uz") or key
    return text.format(**kwargs) if kwargs and isinstance(text, str) else text
