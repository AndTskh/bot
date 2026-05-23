import asyncio
import aiosqlite
from datetime import datetime
from aiogram import Bot, Dispatcher, Router, F
from aiogram.utils.markdown import hlink
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import os
from dotenv import load_dotenv

load_dotenv('BT.env')
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
OPERATOR_USERNAME = os.getenv("OPERATOR_USERNAME")
DB_PATH = os.getenv("DB_PATH")

router = Router()

class BroadcastState(StatesGroup):
    waiting_for_message = State()


# ================= БАЗА ДАННЫХ =================
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                full_name   TEXT,
                joined_at   TEXT
            )
        """)
        await db.commit()

async def add_user(user_id: int, username: str | None, full_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR IGNORE INTO users (user_id, username, full_name, joined_at)
            VALUES (?, ?, ?, ?)
        """, (user_id, username, full_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        await db.commit()

async def get_all_users() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM users")
        rows = await cursor.fetchall()
        return [row[0] for row in rows]

async def get_user_count() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        row = await cursor.fetchone()
        return row[0]

async def get_recent_users(limit: int = 5) -> list[tuple]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT full_name, username, joined_at FROM users ORDER BY joined_at DESC LIMIT ?",
            (limit,)
        )
        return await cursor.fetchall()


# ================= КЛАВИАТУРЫ =================
def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 База знаний (Статьи)", callback_data="topics")],
        [InlineKeyboardButton(text="ℹ️ О нас", callback_data="about")],
        [InlineKeyboardButton(text="🎯 Наша задача", callback_data="mission")],
        [InlineKeyboardButton(text="📞 Связаться с оператором", callback_data="contact")],
        [InlineKeyboardButton(text="🌐 Посетить сайт", callback_data="page")]
    ])

def topics_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Как оформить инвалидность?", callback_data="topic_invalid")],
        [InlineKeyboardButton(text="👨‍👩‍👧 Взыскание алиментов на детей", callback_data="topic_alimony")],
        [InlineKeyboardButton(text="🗺 Без документов в чужом городе", callback_data="topic_lost_docs")],
        [InlineKeyboardButton(text="📕 Восстановление паспорта РФ", callback_data="topic_passport")],
        [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back")],
    ])

# Клавиатура подраздела: Инвалидность
def invalid_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Кто может оформить?", callback_data="inv_who")],
        [InlineKeyboardButton(text="📋 Что даёт инвалидность?", callback_data="inv_what")],
        [InlineKeyboardButton(text="🛠 Как оформить (Шаги)", callback_data="inv_how")],
        [InlineKeyboardButton(text="⚖️ Если не согласны с решением", callback_data="inv_disagree")],
        [InlineKeyboardButton(text="⬅️ К списку тем", callback_data="topics")],
    ])

# Клавиатура подраздела: Алименты
def alimony_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Размер алиментов", callback_data="alim_size")],
        [InlineKeyboardButton(text="⚖️ Порядок взыскания", callback_data="alim_order")],
        [InlineKeyboardButton(text="🚨 Если должник не платит", callback_data="alim_penalty")],
        [InlineKeyboardButton(text="⬅️ К списку тем", callback_data="topics")],
    ])

# Клавиатура подраздела: Без документов в чужом городе
def lost_docs_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚨 Первые шаги — полиция", callback_data="lost_docs_police")],
        [InlineKeyboardButton(text="📄 Восстановление документов", callback_data="lost_docs_restore")],
        [InlineKeyboardButton(text="🏠 Где найти ночлег и еду", callback_data="lost_docs_food")],
        [InlineKeyboardButton(text="🚌 Как вернуться домой", callback_data="lost_docs_home")],
        [InlineKeyboardButton(text="⬅️ К списку тем", callback_data="topics")],
    ])

# Клавиатура подраздела: Восстановление паспорта
def passport_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❓ Кража или утеря?", callback_data="passport_loss")],
        [InlineKeyboardButton(text="📝 Какие документы нужны", callback_data="passport_docs")],
        [InlineKeyboardButton(text="🏢 Куда обращаться", callback_data="passport_where")],
        [InlineKeyboardButton(text="⏱ Сроки и временное удостоверение", callback_data="passport_time")],
        [InlineKeyboardButton(text="💸 Возможные штрафы", callback_data="passport_fines")],
        [InlineKeyboardButton(text="⬅️ К списку тем", callback_data="topics")],
    ])

# Кнопки возврата в подразделы
def back_to_invalid_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад к разделу", callback_data="topic_invalid")]
    ])

def back_to_alimony_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад к разделу", callback_data="topic_alimony")]
    ])

def back_to_lost_docs_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад к разделу", callback_data="topic_lost_docs")]
    ])

def back_to_passport_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад к разделу", callback_data="topic_passport")]
    ])

def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back")],
    ])

def admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Статистика пользователей", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Сделать рассылку", callback_data="admin_broadcast")],
    ])

def admin_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel")],
    ])


# ================= ТЕКСТЫ =================
WELCOME_TEXT = (
    "👋 Добро пожаловать!\n\n"
    "🏛 <b>Интернет-портал СОНКО МОО</b>\n"
    "для «Центра поддержки гражданских инициатив <i>Благо</i>»\n\n"
    "Мы рады видеть вас здесь. Выберите раздел, чтобы узнать больше о нашем проекте 👇"
)

ABOUT_TEXT = (
    "ℹ️ <b>О нас</b>\n\n"
    "🌐 <b>СОНКО МОО</b> — это интернет-портал, созданный в рамках поддержки\n"
    "социально ориентированных некоммерческих организаций.\n\n"
    "🤝 Мы объединяем гражданские инициативы, помогаем НКО развиваться\n"
    "и находить поддержку на всех уровнях.\n\n"
    "💡 Наш портал — пространство для диалога, сотрудничества\n"
    "и реализации добрых идей на благо общества."
)

MISSION_TEXT = (
    "🎯 <b>Наша задача</b>\n\n"
    "✅ Поддержка и развитие НКО и гражданских инициатив\n"
    "✅ Информирование о грантах, конкурсах и возможностях\n"
    "✅ Создание единой платформы для взаимодействия организаций\n"
    "✅ Содействие в реализации социальных проектов\n"
    "✅ Укрепление гражданского общества и местного самоуправления\n\n"
    "🌱 Мы верим, что каждая инициатива способна изменить мир к лучшему."
)

CONTACT_TEXT = (
    "📞 <b>Связаться с оператором</b>\n\n"
    "Наш оператор готов ответить на все ваши вопросы\n"
    "и помочь разобраться в работе портала.\n\n"
    "💬 Напишите нам напрямую в Telegram:\n"
    "👉 <a href='https://t.me/{username}'>@{username}</a>\n\n"
    "🕐 Мы стараемся отвечать как можно скорее."
)

PAGE_TEXT = (
    hlink("🔗 Нажмите, чтобы пройти по ссылке на сайт", "https://cblago.ru/")
)

ADMIN_PANEL_TEXT = (
    "🔐 <b>Панель администратора</b>\n\n"
    "Добро пожаловать, администратор!\n"
    "Выберите действие 👇"
)

# === Тексты: Инвалидность ===
INV_WHO_TEXT = (
    "✅ <b>Кто может оформить?</b>\n\n"
    "Люди со стойкими нарушениями функций, ограничивающими жизнедеятельность. "
    "Инвалидность устанавливает медико-социальная экспертиза (МСЭ).\n\n"
    "👶 Дети до 18 лет → статус «ребёнок-инвалид».\n"
    "🧑 Взрослым → 3 группы:\n"
    "<b>I</b> — самая тяжёлая (полная зависимость от помощи);\n"
    "<b>II</b> — значительные нарушения;\n"
    "<b>III</b> — умеренные нарушения (без постоянной помощи).\n\n"
    "⏳ Инвалидность может быть срочной (1–2 года) или бессрочной."
)

INV_WHAT_TEXT = (
    "📋 <b>Что даёт инвалидность?</b>\n\n"
    "Пенсия, ЕДВ, бесплатные лекарства, технические средства реабилитации, "
    "квоты на учёбу, льготы по ЖКХ, санатории, парковка и другое."
)

INV_HOW_TEXT = (
    "🛠 <b>Как оформить?</b>\n\n"
    "1. Получить <b>направление на МСЭ</b> (форма 088/у) у лечащего врача в поликлинике.\n"
    "2. Подать <b>согласие на МСЭ</b> через портал Госуслуг (выбрать очную или заочную форму).\n"
    "3. Собрать документы: паспорт, СНИЛС, направление, выписки, результаты анализов и др.\n"
    "4. Пройти экспертизу (срок — до 7 рабочих дней, бесплатно).\n"
    "5. Получить <b>справку об инвалидности и ИПРА</b> (индивидуальную программу реабилитации)."
)

INV_DISAGREE_TEXT = (
    "⚖️ <b>Если не согласны с решением</b>\n\n"
    "Решение можно обжаловать в течение 30 дней по цепочке:\n"
    "Главное бюро МСЭ → Федеральное бюро → Суд."
)

# === Тексты: Алименты ===
ALIM_SIZE_TEXT = (
    "💰 <b>Варианты размера алиментов:</b>\n\n"
    "• <b>Доля от дохода</b> — 1/4 на одного, 1/3 на двоих, 1/2 на троих и более детей. Суд может изменить доли.\n"
    "• <b>Твёрдая сумма</b> — если доход нерегулярный, в валюте или его нет.\n"
    "• <b>Смешанный вариант</b> — доли + твёрдая сумма."
)

ALIM_ORDER_TEXT = (
    "⚖️ <b>Два порядка взыскания через суд:</b>\n\n"
    "1. <b>Приказное производство</b> (мировой суд, без вызова сторон).\n"
    "Подходит, если не нужно устанавливать отцовство. Выдается судебный приказ (должник может отменить его в течение 10 дней).\n\n"
    "2. <b>Исковое производство</b> (районный суд, с вызовом сторон).\n"
    "Требуется для взыскания в твёрдой сумме или если есть спор. Выдается исполнительный лист.\n\n"
    "<i>Оба документа подлежат немедленному исполнению.</i>"
)

ALIM_PENALTY_TEXT = (
    "🚨 <b>Если должник всё равно не платит:</b>\n\n"
    "1. <b>Лишение родительских прав</b> — не освобождает от уплаты алиментов.\n"
    "2. <b>Неустойка</b> — 0,1% от долга за каждый день просрочки (через иск).\n"
    "3. <b>Административная ответственность</b> (если не платит 2+ месяцев):\n"
    "  - обязательные работы до 150 часов\n"
    "  - арест 10–15 суток\n"
    "  - штраф 20 000 ₽\n"
    "4. <b>Уголовная ответственность</b> (если уже был привлечён к «административке»):\n"
    "  - исправительные/принудительные работы или лишение свободы до 1 года."
)

# === Тексты: Без документов в чужом городе ===
LOST_DOCS_POLICE_TEXT = (
    "🚨 <b>Первые шаги — полиция</b>\n\n"
    "Обратитесь в любое отделение полиции (круглосуточно).\n\n"
    "📝 Напишите заявление:\n"
    "• <b>Кража</b> → возбуждают уголовное дело (это дольше).\n"
    "• <b>Утрата</b> → оформляют быстрее, выдадут талон-уведомление.\n\n"
    "📄 Получите <b>талон</b> — он подтвердит ваше положение перед другими службами."
)

LOST_DOCS_RESTORE_TEXT = (
    "📄 <b>Восстановление документов</b>\n\n"
    "Без паспорта нельзя купить билет. Вам нужно <b>временное удостоверение личности (форма №2П)</b>.\n\n"
    "🛠 Что делать:\n"
    "1. С талоном из полиции идите в подразделение по вопросам миграции МВД.\n"
    "2. Сделайте фото 3,5×4,5 см (попросите помощи у прохожих, в храме, у волонтёров).\n"
    "3. Напишите заявление на временное удостоверение.\n"
    "💡 Если есть копия паспорта (в облаке, почте, мессенджере) или СНИЛС — покажите, это ускорит процесс.\n\n"
    "⌛ <i>Временное удостоверение выдаётся до 2 месяцев. С ним можно покупать билеты на поезд/автобус, передвигаться по стране, совершать банковские операции.</i>"
)

LOST_DOCS_FOOD_TEXT = (
    "🏠 <b>Где найти ночлег и еду</b>\n\n"
    "• <b>Центры социальной адаптации (ЦСА)</b> — койко-место, душ, горячее питание. Талон из полиции поможет.\n"
    "• <b>Храмы, мечети, синагоги</b> — накормят, дадут временную работу за еду и ночлег, помогут с билетом.\n"
    "• <b>Благотворительные столовые и пункты обогрева</b> — адреса подскажут в ЦСА или у волонтёров."
)

LOST_DOCS_HOME_TEXT = (
    "🚌 <b>Как вернуться домой</b>\n\n"
    "💵 <b>Если есть родственники/друзья:</b> они могут перевести деньги через системы наличных переводов («Золотая Корона», «Юнистрим») — получить их можно по временному удостоверению.\n\n"
    "❌ <b>Если помощи ждать некого:</b>\n"
    "• Обратитесь в благотворительные фонды (у многих есть программы возвращения домой).\n"
    "• Программа «Возвращение» (РЖД + фонды) — соцработники могут купить билет.\n"
    "• В исключительных случаях местная соцзащита выделяет материальную помощь на билет.\n\n"
    "📞 <i>Телефоны помощи: 112, «Ночлежка», служба «Милосердие», Российский Красный Крест, «ЛизаАлерт».</i>"
)

# === Тексты: Восстановление паспорта ===
PASSPORT_LOSS_TEXT = (
    "❓ <b>Шаг первый: кража или утеря?</b>\n\n"
    "• <b>Если украли</b> → сразу в полицию. Пишете заявление о краже, получаете талон-уведомление. С этого момента украденный паспорт недействителен (это защитит вас от мошенников).\n"
    "• <b>Если потеряли</b> → в полицию идти НЕ надо. Сразу собираете документы и оплачиваете госпошлину.\n\n"
    "⚠️ <i>Важно: не заявляйте о краже, если просто потеряли. Полиция заведёт уголовное дело, и выдача паспорта затянется.</i>"
)

PASSPORT_DOCS_TEXT = (
    "📝 <b>Какие документы нужны:</b>\n\n"
    "1. Заявление о выдаче (замене) паспорта (форма №1-П).\n"
    "2. Заявление об утере/хищении (в свободной форме, подробно об обстоятельствах).\n"
    "3. Талон из полиции (только при краже).\n"
    "4. Две фотографии 3,5×4,5 см (цветные или Ч/Б, лицо 70–80% кадра).\n"
    "5. Квитанция об оплате госпошлины — <b>1500 ₽</b>.\n"
    "6. Дополнительно для отметок (по желанию): военный билет, свидетельства о браке/разводе, свидетельства о рождении детей до 14 лет."
)

PASSPORT_WHERE_TEXT = (
    "🏢 <b>Куда обращаться:</b>\n\n"
    "• <b>Подразделение по вопросам миграции МВД</b> — самый быстрый вариант. Можно записаться через Госуслуги.\n"
    "• <b>МФЦ «Мои документы»</b> — удобнее по графику, но дольше (добавляется 2–3 дня на пересылку).\n\n"
    "💡 <i>Полностью онлайн через Госуслуги восстановить паспорт нельзя — только записаться на личный приём.</i>"
)

PASSPORT_TIME_TEXT = (
    "⏱ <b>Сроки и временное удостоверение</b>\n\n"
    "• Новый паспорт делают не более <b>5 рабочих дней</b> (независимо от места подачи — по прописке или в другом городе).\n"
    "• <b>Временное удостоверение личности (ВУЛ, форма №2-П)</b> выдаётся бесплатно на срок оформления (нужна третья фотография).\n\n"
    "✈️ <i>С ВУЛ можно: летать по России, покупать ж/д билеты, подтверждать личность.</i>\n"
    "❌ <i>С ВУЛ нельзя: выехать за границу, оформить кредит, купить сим-карту.</i>"
)

PASSPORT_FINES_TEXT = (
    "💸 <b>Штрафы: за что могут оштрафовать</b>\n\n"
    "• <b>За небрежное хранение</b> (ст. 19.16 КоАП) — от 100 до 300 ₽ (при утере по вашей вине). При краже (с талоном из полиции) штрафа не будет.\n"
    "• <b>За проживание без паспорта</b> (ст. 19.15 КоАП) — если не обратились за новым паспортом в течение 30 дней с момента утраты:\n"
    "  - Для регионов: от 2 000 до 3 000 ₽\n"
    "  - Для Москвы и СПб: от 3 000 до 5 000 ₽"
)


# ================= ХЭНДЛЕРЫ МЕНЮ =================
@router.message(CommandStart())
async def cmd_start(message: Message):
    await add_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name
    )
    await message.answer(
        text=WELCOME_TEXT,
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "back")
async def handle_back(callback: CallbackQuery):
    await callback.message.edit_text(
        text=WELCOME_TEXT,
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "about")
async def handle_about(callback: CallbackQuery):
    await callback.message.edit_text(text=ABOUT_TEXT, reply_markup=back_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "mission")
async def handle_mission(callback: CallbackQuery):
    await callback.message.edit_text(text=MISSION_TEXT, reply_markup=back_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "page")
async def handle_page(callback: CallbackQuery):
    await callback.message.edit_text(text=PAGE_TEXT, reply_markup=back_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "contact")
async def handle_contact(callback: CallbackQuery):
    await callback.message.edit_text(
        text=CONTACT_TEXT.format(username=OPERATOR_USERNAME),
        reply_markup=back_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


# ================= ХЭНДЛЕРЫ БАЗЫ ЗНАНИЙ =================
@router.callback_query(F.data == "topics")
async def handle_topics(callback: CallbackQuery):
    await callback.message.edit_text(
        text="📚 <b>База знаний</b>\n\nВыберите интересующую вас тему ниже 👇",
        reply_markup=topics_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

# --- Ветка: Инвалидность ---
@router.callback_query(F.data == "topic_invalid")
async def handle_topic_invalid(callback: CallbackQuery):
    await callback.message.edit_text(
        text="📝 <b>Как оформляется инвалидность?</b>\n\nВыберите интересующий вас раздел:",
        reply_markup=invalid_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "inv_who")
async def handle_inv_who(callback: CallbackQuery):
    await callback.message.edit_text(text=INV_WHO_TEXT, reply_markup=back_to_invalid_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "inv_what")
async def handle_inv_what(callback: CallbackQuery):
    await callback.message.edit_text(text=INV_WHAT_TEXT, reply_markup=back_to_invalid_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "inv_how")
async def handle_inv_how(callback: CallbackQuery):
    await callback.message.edit_text(text=INV_HOW_TEXT, reply_markup=back_to_invalid_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "inv_disagree")
async def handle_inv_disagree(callback: CallbackQuery):
    await callback.message.edit_text(text=INV_DISAGREE_TEXT, reply_markup=back_to_invalid_keyboard(), parse_mode="HTML")
    await callback.answer()


# --- Ветка: Алименты ---
@router.callback_query(F.data == "topic_alimony")
async def handle_topic_alimony(callback: CallbackQuery):
    await callback.message.edit_text(
        text="👨‍👩‍👧 <b>Как заставить платить алименты на детей?</b>\n\nВыберите раздел для получения информации:",
        reply_markup=alimony_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "alim_size")
async def handle_alim_size(callback: CallbackQuery):
    await callback.message.edit_text(text=ALIM_SIZE_TEXT, reply_markup=back_to_alimony_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "alim_order")
async def handle_alim_order(callback: CallbackQuery):
    await callback.message.edit_text(text=ALIM_ORDER_TEXT, reply_markup=back_to_alimony_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "alim_penalty")
async def handle_alim_penalty(callback: CallbackQuery):
    await callback.message.edit_text(text=ALIM_PENALTY_TEXT, reply_markup=back_to_alimony_keyboard(), parse_mode="HTML")
    await callback.answer()


# --- Ветка: Без документов в другом городе ---
@router.callback_query(F.data == "topic_lost_docs")
async def handle_topic_lost_docs(callback: CallbackQuery):
    await callback.message.edit_text(
        text="🗺 <b>Что делать, если вы оказались в другом городе без документов и денег?</b>\n\nВыберите интересующий раздел:",
        reply_markup=lost_docs_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "lost_docs_police")
async def handle_lost_docs_police(callback: CallbackQuery):
    await callback.message.edit_text(text=LOST_DOCS_POLICE_TEXT, reply_markup=back_to_lost_docs_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "lost_docs_restore")
async def handle_lost_docs_restore(callback: CallbackQuery):
    await callback.message.edit_text(text=LOST_DOCS_RESTORE_TEXT, reply_markup=back_to_lost_docs_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "lost_docs_food")
async def handle_lost_docs_food(callback: CallbackQuery):
    await callback.message.edit_text(text=LOST_DOCS_FOOD_TEXT, reply_markup=back_to_lost_docs_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "lost_docs_home")
async def handle_lost_docs_home(callback: CallbackQuery):
    await callback.message.edit_text(text=LOST_DOCS_HOME_TEXT, reply_markup=back_to_lost_docs_keyboard(), parse_mode="HTML")
    await callback.answer()


# --- Ветка: Восстановление паспорта РФ ---
@router.callback_query(F.data == "topic_passport")
async def handle_topic_passport(callback: CallbackQuery):
    await callback.message.edit_text(
        text="📕 <b>Как восстановить паспорт при утере или краже?</b>\n\nВыберите интересующий раздел:",
        reply_markup=passport_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "passport_loss")
async def handle_passport_loss(callback: CallbackQuery):
    await callback.message.edit_text(text=PASSPORT_LOSS_TEXT, reply_markup=back_to_passport_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "passport_docs")
async def handle_passport_docs(callback: CallbackQuery):
    await callback.message.edit_text(text=PASSPORT_DOCS_TEXT, reply_markup=back_to_passport_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "passport_where")
async def handle_passport_where(callback: CallbackQuery):
    await callback.message.edit_text(text=PASSPORT_WHERE_TEXT, reply_markup=back_to_passport_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "passport_time")
async def handle_passport_time(callback: CallbackQuery):
    await callback.message.edit_text(text=PASSPORT_TIME_TEXT, reply_markup=back_to_passport_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "passport_fines")
async def handle_passport_fines(callback: CallbackQuery):
    await callback.message.edit_text(text=PASSPORT_FINES_TEXT, reply_markup=back_to_passport_keyboard(), parse_mode="HTML")
    await callback.answer()


# ================= АДМИН-ПАНЕЛЬ =================
@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer(text=ADMIN_PANEL_TEXT, reply_markup=admin_keyboard(), parse_mode="HTML")

@router.callback_query(F.data == "admin_stats")
async def handle_admin_stats(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    total = await get_user_count()
    recent = await get_recent_users(5)

    lines = ["👥 <b>Статистика пользователей</b>\n", f"📊 Всего зарегистрировано: <b>{total}</b>\n", "🕐 <b>Последние 5 пользователей:</b>"]
    for full_name, username, joined_at in recent:
        uname = f"@{username}" if username else "—"
        lines.append(f"\n• {full_name} ({uname})\n  📅 {joined_at}")

    await callback.message.edit_text(
        text="\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")]]),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "admin_broadcast")
async def handle_admin_broadcast(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    await callback.message.edit_text(
        text=(
            "📢 <b>Рассылка</b>\n\n"
            "Отправьте текст сообщения, которое будет разослано всем пользователям.\n\n"
            "Поддерживается HTML-разметка:\n"
            "<b>жирный</b>, <i>курсив</i>, <code>моноширинный</code>\n\n"
            "Для отмены нажмите кнопку ниже 👇"
        ),
        reply_markup=admin_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(BroadcastState.waiting_for_message)
    await callback.answer()

@router.callback_query(F.data == "admin_cancel")
async def handle_admin_cancel(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    await state.clear()
    await callback.message.edit_text(text=ADMIN_PANEL_TEXT, reply_markup=admin_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "admin_back")
async def handle_admin_back(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    await callback.message.edit_text(text=ADMIN_PANEL_TEXT, reply_markup=admin_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.message(BroadcastState.waiting_for_message)
async def process_broadcast(message: Message, state: FSMContext, bot: Bot):
    if message.from_user.id != ADMIN_ID:
        return

    await state.clear()

    users = await get_all_users()
    total = len(users)
    success = 0
    failed = 0

    status_msg = await message.answer(text=f"⏳ Начинаю рассылку для <b>{total}</b> пользователей...", parse_mode="HTML")

    for user_id in users:
        try:
            await bot.send_message(
                chat_id=user_id,
                text=message.text or message.caption or "",
                parse_mode="HTML"
            )
            success += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)

    await status_msg.edit_text(
        text=(
            f"✅ <b>Рассылка завершена!</b>\n\n"
            f"📨 Всего получателей: <b>{total}</b>\n"
            f"✔️ Успешно доставлено: <b>{success}</b>\n"
            f"❌ Не доставлено: <b>{failed}</b>"
        ),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ В панель", callback_data="admin_back")]]),
        parse_mode="HTML"
    )


async def main():
    await init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())