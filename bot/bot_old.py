import asyncio
import aiosqlite
from datetime import datetime
from aiogram import Bot, Dispatcher, Router, F
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


def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ℹ️ О нас", callback_data="about")],
        [InlineKeyboardButton(text="🎯 Наша задача", callback_data="mission")],
        [InlineKeyboardButton(text="📞 Связаться с оператором линии", callback_data="contact")],
    ])


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")],
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
    "✅ Поддержка и развитие НКО и гражданских инициатив\n\n"
    "✅ Информирование о грантах, конкурсах и возможностях\n\n"
    "✅ Создание единой платформы для взаимодействия организаций\n\n"
    "✅ Содействие в реализации социальных проектов\n\n"
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

ADMIN_PANEL_TEXT = (
    "🔐 <b>Панель администратора</b>\n\n"
    "Добро пожаловать, администратор!\n"
    "Выберите действие 👇"
)


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


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer(
        text=ADMIN_PANEL_TEXT,
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "about")
async def handle_about(callback: CallbackQuery):
    await callback.message.edit_text(
        text=ABOUT_TEXT,
        reply_markup=back_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "mission")
async def handle_mission(callback: CallbackQuery):
    await callback.message.edit_text(
        text=MISSION_TEXT,
        reply_markup=back_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "contact")
async def handle_contact(callback: CallbackQuery):
    await callback.message.edit_text(
        text=CONTACT_TEXT.format(username=OPERATOR_USERNAME),
        reply_markup=back_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "back")
async def handle_back(callback: CallbackQuery):
    await callback.message.edit_text(
        text=WELCOME_TEXT,
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


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
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")]
        ]),
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
    await callback.message.edit_text(
        text=ADMIN_PANEL_TEXT,
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_back")
async def handle_admin_back(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    await callback.message.edit_text(
        text=ADMIN_PANEL_TEXT,
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )
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

    status_msg = await message.answer(
        text=f"⏳ Начинаю рассылку для <b>{total}</b> пользователей...",
        parse_mode="HTML"
    )

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
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ В панель", callback_data="admin_back")]
        ]),
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
