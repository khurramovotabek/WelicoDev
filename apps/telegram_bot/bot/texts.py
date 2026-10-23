"""Bot matnlari: uz / ru / en. Kalit topilmasa o'zbekcha matn qaytadi."""

TEXTS = {
    "choose_lang": {
        "uz": "🌐 Tilni tanlang",
        "ru": "🌐 Выберите язык",
        "en": "🌐 Choose your language",
    },
    "ask_first_name": {
        "uz": "Keling, tanishamiz! 👋\n\n<b>Ismingizni</b> yozing:",
        "ru": "Давайте познакомимся! 👋\n\nНапишите ваше <b>имя</b>:",
        "en": "Let's get to know each other! 👋\n\nPlease type your <b>first name</b>:",
    },
    "ask_last_name": {
        "uz": "Rahmat, {name}! Endi <b>familiyangizni</b> yozing:",
        "ru": "Спасибо, {name}! Теперь напишите <b>фамилию</b>:",
        "en": "Thanks, {name}! Now type your <b>last name</b>:",
    },
    "ask_phone": {
        "uz": "📱 Telefon raqamingizni yuboring.\n\nPastdagi <b>«Raqamni yuborish»</b> tugmasini bosing — raqam Telegram orqali tasdiqlanadi.",
        "ru": "📱 Отправьте номер телефона.\n\nНажмите кнопку <b>«Отправить номер»</b> ниже — номер подтверждается через Telegram.",
        "en": "📱 Share your phone number.\n\nTap <b>“Share number”</b> below — the number is verified by Telegram.",
    },
    "btn_share_phone": {"uz": "📱 Raqamni yuborish", "ru": "📱 Отправить номер", "en": "📱 Share number"},
    "btn_use_tg_name": {"uz": "✅ {name}", "ru": "✅ {name}", "en": "✅ {name}"},
    "invalid_name": {
        "uz": "Iltimos, to'g'ri ism kiriting (2–40 harf).",
        "ru": "Пожалуйста, введите корректное имя (2–40 букв).",
        "en": "Please enter a valid name (2–40 letters).",
    },
    "phone_not_own": {
        "uz": "⚠️ Faqat o'zingizning raqamingizni yuboring — pastdagi tugmadan foydalaning.",
        "ru": "⚠️ Отправьте только свой номер — используйте кнопку ниже.",
        "en": "⚠️ Please share your own number using the button below.",
    },
    "phone_use_button": {
        "uz": "Raqamni qo'lda yozmang — pastdagi <b>«Raqamni yuborish»</b> tugmasini bosing.",
        "ru": "Не вводите номер вручную — нажмите кнопку <b>«Отправить номер»</b>.",
        "en": "Don't type the number — tap the <b>“Share number”</b> button.",
    },
    "registered": {
        "uz": "🎉 Ro'yxatdan o'tdingiz, <b>{name}</b>!",
        "ru": "🎉 Вы зарегистрированы, <b>{name}</b>!",
        "en": "🎉 You're registered, <b>{name}</b>!",
    },
    "login_confirm": {
        "uz": "🔐 <b>Saytga kirish so'rovi</b>\n\n🌐 {site}\n🖥 {device}\n📍 IP: <code>{ip}</code>\n🕐 {time}\n\nBu siz bo'lsangiz, tasdiqlang. Agar havolani o'zingiz ochmagan bo'lsangiz — <b>rad eting</b>.",
        "ru": "🔐 <b>Запрос на вход на сайт</b>\n\n🌐 {site}\n🖥 {device}\n📍 IP: <code>{ip}</code>\n🕐 {time}\n\nЕсли это вы — подтвердите. Если вы не открывали ссылку — <b>отклоните</b>.",
        "en": "🔐 <b>Website sign-in request</b>\n\n🌐 {site}\n🖥 {device}\n📍 IP: <code>{ip}</code>\n🕐 {time}\n\nIf this is you, confirm. If you didn't open the link — <b>reject</b>.",
    },
    "btn_confirm": {"uz": "✅ Tasdiqlash", "ru": "✅ Подтвердить", "en": "✅ Confirm"},
    "btn_reject": {"uz": "❌ Rad etish", "ru": "❌ Отклонить", "en": "❌ Reject"},
    "login_confirmed": {
        "uz": "✅ Kirish tasdiqlandi! Saytga qayting — sahifa avtomatik ochiladi.\n\nAgar ochilmasa, shu kodni kiriting:\n<code>{code}</code>\n\n<i>Kod {ttl} soniya amal qiladi.</i>",
        "ru": "✅ Вход подтверждён! Вернитесь на сайт — страница откроется автоматически.\n\nЕсли нет, введите код:\n<code>{code}</code>\n\n<i>Код действует {ttl} сек.</i>",
        "en": "✅ Sign-in confirmed! Go back to the website — it will open automatically.\n\nIf not, enter this code:\n<code>{code}</code>\n\n<i>The code is valid for {ttl} seconds.</i>",
    },
    "login_rejected": {
        "uz": "❌ Kirish rad etildi. Hisobingiz xavfsiz.",
        "ru": "❌ Вход отклонён. Ваш аккаунт в безопасности.",
        "en": "❌ Sign-in rejected. Your account is safe.",
    },
    "login_expired": {
        "uz": "⌛ Bu kirish so'rovi eskirgan. Saytdagi login sahifasini yangilang.",
        "ru": "⌛ Запрос устарел. Обновите страницу входа на сайте.",
        "en": "⌛ This request has expired. Refresh the login page on the website.",
    },
    "login_code": {
        "uz": "🔑 Saytga kirish kodi:\n\n<code>{code}</code>\n\n<i>Kod {ttl} soniya amal qiladi. Uni hech kimga bermang.</i>",
        "ru": "🔑 Код для входа на сайт:\n\n<code>{code}</code>\n\n<i>Код действует {ttl} сек. Никому его не сообщайте.</i>",
        "en": "🔑 Your sign-in code:\n\n<code>{code}</code>\n\n<i>Valid for {ttl} seconds. Never share it.</i>",
    },
    "btn_open_site": {"uz": "🌐 Saytni ochish", "ru": "🌐 Открыть сайт", "en": "🌐 Open website"},
    "btn_open_app": {"uz": "🚀 Ilovani ochish", "ru": "🚀 Открыть приложение", "en": "🚀 Open app"},
    "menu": {
        "uz": "Asosiy menyu 👇",
        "ru": "Главное меню 👇",
        "en": "Main menu 👇",
    },
    "btn_login": {"uz": "🔑 Kirish kodi", "ru": "🔑 Код входа", "en": "🔑 Sign-in code"},
    "btn_courses": {"uz": "🎓 Kurslar", "ru": "🎓 Курсы", "en": "🎓 Courses"},
    "btn_profile": {"uz": "👤 Profil", "ru": "👤 Профиль", "en": "👤 Profile"},
    "btn_lang": {"uz": "🌐 Til", "ru": "🌐 Язык", "en": "🌐 Language"},
    "btn_contact": {"uz": "✉️ Murojaat", "ru": "✉️ Написать", "en": "✉️ Contact"},
    "profile": {
        "uz": "👤 <b>{name}</b>\n📱 {phone}\n🗓 A'zo: {joined}\n\n🎓 Kurslar: {courses}\n💬 Izohlar: {comments}",
        "ru": "👤 <b>{name}</b>\n📱 {phone}\n🗓 С нами: {joined}\n\n🎓 Курсы: {courses}\n💬 Комментарии: {comments}",
        "en": "👤 <b>{name}</b>\n📱 {phone}\n🗓 Joined: {joined}\n\n🎓 Courses: {courses}\n💬 Comments: {comments}",
    },
    "courses_header": {"uz": "🎓 <b>Kurslar</b>", "ru": "🎓 <b>Курсы</b>", "en": "🎓 <b>Courses</b>"},
    "courses_empty": {"uz": "Hozircha kurslar yo'q.", "ru": "Пока курсов нет.", "en": "No courses yet."},
    "contact_prompt": {
        "uz": "✍️ Xabaringizni yozing — u to'g'ridan-to'g'ri adminga yetkaziladi.",
        "ru": "✍️ Напишите сообщение — оно будет передано админу.",
        "en": "✍️ Type your message — it will be delivered to the admin.",
    },
    "message_received": {
        "uz": "✅ Xabaringiz qabul qilindi. Tez orada javob beramiz.",
        "ru": "✅ Сообщение получено. Скоро ответим.",
        "en": "✅ Message received. We'll reply soon.",
    },
    "lang_saved": {"uz": "✅ Til saqlandi", "ru": "✅ Язык сохранён", "en": "✅ Language saved"},
    "blocked": {
        "uz": "⛔️ Hisobingiz bloklangan. Savollar bo'lsa, admin bilan bog'laning.",
        "ru": "⛔️ Ваш аккаунт заблокирован.",
        "en": "⛔️ Your account is blocked.",
    },
    "back_to_edu": {
        "uz": "✅ Tayyor! Endi ta'lim botiga qayting — kurslar o'sha yerda.",
        "ru": "✅ Готово! Возвращайтесь в учебный бот — курсы там.",
        "en": "✅ All set! Head back to the education bot — the courses are there.",
    },
    "btn_back_to_edu": {"uz": "🎓 Ta'lim botiga o'tish", "ru": "🎓 Перейти в учебный бот", "en": "🎓 Open the education bot"},
    "nudge_start_1": {
        "uz": "👋 {name}, WeliCoDev'ga xush kelibsiz!\n\nBirinchi qadamni bepul kursdan boshlang:\n<b>{course}</b>\n\n<i>{subtitle}</i>\n\n📚 {lessons} ta dars · o'zbek tilida · o'z tezligingizda.",
        "ru": "👋 {name}, добро пожаловать в WeliCoDev!\n\nНачните с бесплатного курса:\n<b>{course}</b>\n\n<i>{subtitle}</i>\n\n📚 {lessons} уроков · в своём темпе.",
        "en": "👋 {name}, welcome to WeliCoDev!\n\nTake your first step with a free course:\n<b>{course}</b>\n\n<i>{subtitle}</i>\n\n📚 {lessons} lessons · at your own pace.",
    },
    "nudge_start_2": {
        "uz": "🚀 {name}, kuniga 15 daqiqa — va bir oyda yangi ko'nikma.\n\n<b>{course}</b> kursining birinchi darsi sizni kutmoqda.",
        "ru": "🚀 {name}, 15 минут в день — и через месяц новый навык.\n\nПервый урок курса <b>{course}</b> ждёт вас.",
        "en": "🚀 {name}, 15 minutes a day — a new skill in a month.\n\nThe first lesson of <b>{course}</b> is waiting for you.",
    },
    "nudge_continue": {
        "uz": "📖 {name}, <b>{course}</b> kursini davom ettiramizmi?\n\nKeyingi dars: <b>{lesson}</b>",
        "ru": "📖 {name}, продолжим курс <b>{course}</b>?\n\nСледующий урок: <b>{lesson}</b>",
        "en": "📖 {name}, shall we continue <b>{course}</b>?\n\nNext lesson: <b>{lesson}</b>",
    },
    "btn_start_course": {"uz": "▶️ Kursni boshlash", "ru": "▶️ Начать курс", "en": "▶️ Start the course"},
    "btn_continue": {"uz": "▶️ Davom ettirish", "ru": "▶️ Продолжить", "en": "▶️ Continue"},
    "need_register": {
        "uz": "Avval ro'yxatdan o'ting: /start",
        "ru": "Сначала зарегистрируйтесь: /start",
        "en": "Please register first: /start",
    },
}

LANG_BUTTONS = [("uz", "🇺🇿 O'zbekcha"), ("ru", "🇷🇺 Русский"), ("en", "🇬🇧 English")]


def t(key, lang="uz", **kwargs):
    entry = TEXTS.get(key, {})
    text = entry.get(lang) or entry.get("uz") or key
    return text.format(**kwargs) if kwargs else text
