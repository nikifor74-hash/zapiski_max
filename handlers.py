import logging
from maxapi import Router, F
from maxapi.types import Command, MessageCreated, MessageCallback, BotStarted
from maxapi.context import MemoryContext, State, StatesGroup
from database import Database
from keyboards import get_main_menu, get_tasks_keyboard

logger = logging.getLogger(__name__)
router = Router()
db = Database()

class AddTask(StatesGroup):
    waiting_for_text = State()

@router.bot_started()
async def on_bot_started(event: BotStarted):
    await event.bot.send_message(
        chat_id=event.chat_id,
        text="Привет! Я бот для заметок. Нажми кнопку, чтобы добавить задачу.",
        attachments=[get_main_menu()]
    )

@router.message_created(Command("start"))
async def cmd_start(event: MessageCreated):
    await event.message.answer(
        "Выберите действие:",
        attachments=[get_main_menu()]
    )

# ------------------------------------------------------------------
# Добавление задачи через кнопку
# ------------------------------------------------------------------
@router.message_callback(F.callback.payload == "add_task")
async def callback_add_task(callback: MessageCallback, context: MemoryContext):
    await context.set_state(AddTask.waiting_for_text)
    await callback.message.answer("✏️ Отправьте текст новой задачи:")

@router.message_created(AddTask.waiting_for_text)
async def process_task_text(event: MessageCreated, context: MemoryContext):
    text = event.message.body.text.strip()
    if not text:
        await event.message.answer("❌ Текст не может быть пустым. Попробуйте снова.")
        return

    user_id = event.from_user.user_id
    logger.info(f"Добавление задачи: user_id={user_id}, text={text}")

    await db.add_task(user_id, text)
    await context.clear()
    await event.message.answer(f"✅ Задача добавлена: {text}", attachments=[get_main_menu()])

# ------------------------------------------------------------------
# Просмотр списка задач (с кнопками для выполнения)
# ------------------------------------------------------------------
@router.message_callback(F.callback.payload == "list_tasks")
async def callback_list_tasks(callback: MessageCallback):
    user_id = callback.from_user.user_id
    logger.info(f"Запрос списка задач: user_id={user_id}")

    tasks = await db.get_pending_tasks(user_id)

    if not tasks:
        await callback.message.answer("📭 У вас нет невыполненных задач.", attachments=[get_main_menu()])
        return

    task_lines = [f"{idx}. {t['task_text']} [❌]" for idx, t in enumerate(tasks, start=1)]
    text = "📋 Ваш список задач:\n" + "\n".join(task_lines)

    keyboard = get_tasks_keyboard(tasks)

    try:
        await callback.message.answer(text, attachments=[keyboard])
        logger.info("✅ Список с кнопками отправлен")
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке клавиатуры: {e}")
        await callback.message.answer(text, attachments=[get_main_menu()])

# ------------------------------------------------------------------
# Обработчик нажатий на кнопки задач (отметка выполнения)
# ------------------------------------------------------------------
@router.message_callback(lambda c: c.callback.payload.startswith("done_"))
async def callback_task_done(callback: MessageCallback):
    try:
        task_id = int(callback.callback.payload.split("_")[1])
    except (IndexError, ValueError):
        await callback.answer("❌ Ошибка: некорректные данные")
        return

    user_id = callback.from_user.user_id
    logger.info(f"Отметка задачи {task_id} как выполненной, user_id={user_id}")

    success = await db.mark_task_done(task_id, user_id)

    if success:
        await callback.answer("✅ Задача выполнена!")

        # Удаляем старое сообщение со списком
        await callback.message.delete()

        # Отправляем простое текстовое сообщение (БЕЗ ВЛОЖЕНИЙ)
        await callback.bot.send_message(
            chat_id=int(callback.chat.chat_id),  # преобразуем в int
            text="✅ Задача отмечена как выполненная. Введите /start для продолжения."
        )
    else:
        await callback.answer("❌ Не удалось отметить задачу. Возможно, она уже выполнена.", show_alert=True)

# ------------------------------------------------------------------
# Команда /done (оставлена для совместимости)
# ------------------------------------------------------------------
@router.message_created(Command("done"))
async def cmd_done(event: MessageCreated):
    parts = event.message.body.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await event.message.answer("Укажите номер задачи: /done <номер>")
        return

    task_number = int(parts[1])
    user_id = event.from_user.user_id
    tasks = await db.get_pending_tasks(user_id)

    if task_number < 1 or task_number > len(tasks):
        await event.message.answer(f"Задачи с номером {task_number} не существует.")
        return

    task_id = tasks[task_number - 1]["id"]
    success = await db.mark_task_done(task_id, user_id)
    if success:
        await event.message.answer(f"✅ Задача {task_number} выполнена!")
    else:
        await event.message.answer("❌ Ошибка. Возможно, задача уже выполнена.")