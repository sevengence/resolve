from aiogram import Router, Bot, types
from aiogram.filters import Command
from datetime import datetime
from pytz import timezone
from config import AUTHORIZED_USERS

router = Router()

# Устанавливаем часовой пояс Киева
KIEV_TIMEZONE = timezone('Europe/Kiev')

# ID группы, в которой бот должен работать
ALLOWED_CHAT_ID = -1001509336046  # Укажите ваш chat_id


async def check_chat_access(message: types.Message, bot: Bot) -> bool:
    """
    Проверяет доступ к чату:
    - Работает в разрешённой группе.
    - Работает с авторизованными пользователями в личных сообщениях.
    """
    if message.chat.type == "private":
        # Разрешить только авторизованным пользователям в личных чатах
        if message.from_user.id not in AUTHORIZED_USERS:
            await message.answer("Пожалуйста, для получения прав обратитесь к администратору.")
            return False
        return True

    # Проверяем доступ в группе
    if message.chat.id != ALLOWED_CHAT_ID:
        await bot.leave_chat(message.chat.id)
        return False

    return True


@router.message(Command("list"))
async def list_invoices_handler(message: types.Message, db, bot: Bot):
    if not await check_chat_access(message, bot):
        return

    invoices = db.get_all_invoices()
    now = datetime.now(tz=KIEV_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
    await message.delete()  # Удаляем команду

    if not invoices:
        quotes = [
            "🎯 Все накладные решены. Клиенты довольны, а вы — как всегда на высоте. Слабость не в вашем стиле.",
            "🔥 Проблемы приходят и уходят, а вы остаётесь мастером своего дела. Все накладные — под вашим контролем.",
            "🚀 Решить все накладные? Легко. Для профессионалов вашей команды это просто ещё один день на вершине.",
        ]
        await message.answer(quotes[datetime.now().second % len(quotes)])
        return

    response = [f"📋 Текущее количество накладных на {now}: {len(invoices)}"]
    for idx, invoice in enumerate(invoices, start=1):
        link = f"https://t.me/c/{str(invoice['chat_id'])[4:]}/{invoice['message_id']}"
        response.append(f"{idx}. {invoice['client_name']} — [Ссылка]({link})")

    await message.answer("\n".join(response), parse_mode="Markdown")


@router.message(Command("add"))
async def add_invoice_handler(message: types.Message, db, bot: Bot):
    if not await check_chat_access(message, bot):
        return

    reply = message.reply_to_message
    client_name = None

    if reply:
        if reply.caption:
            client_name = reply.caption.strip()
        elif reply.text:
            client_name = reply.text.strip()

    if not client_name:
        args = message.text.split(maxsplit=1)
        if len(args) == 2:
            client_name = args[1].strip()

    if client_name:
        db.add_invoice(
            chat_id=reply.chat.id if reply else message.chat.id,
            message_id=reply.message_id if reply else message.message_id,
            client_name=client_name,
            user_id=message.from_user.id,
            full_name=message.from_user.full_name
        )
    await message.delete()


@router.message(Command("report"))
async def detailed_report_handler(message: types.Message, db, bot: Bot):
    if not await check_chat_access(message, bot):
        return

    today_invoices = db.get_today_invoices()
    resolved_invoices = db.get_today_resolved_invoices()
    deleted_invoices = db.get_today_deleted_invoices()

    total_added = len(today_invoices)
    total_resolved = len(resolved_invoices)
    total_deleted = len(deleted_invoices)

    now = datetime.now(tz=KIEV_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
    report = [
        f"📊 Данные по накладным на {now}:",
        f"➖ Всего добавлено: {total_added}",
        f"✅ Решено: {total_resolved}",
        f"❌ Удалено: {total_deleted}",
    ]

    employees = {}
    for invoice in today_invoices:
        user_id = invoice["added_by"]["user_id"]
        full_name = invoice["added_by"]["full_name"]
        if user_id not in employees:
            employees[user_id] = {"name": full_name, "added": 0, "resolved": 0, "deleted": 0}
        employees[user_id]["added"] += 1

    for invoice in resolved_invoices:
        user_id = invoice["added_by"]["user_id"]
        if user_id in employees:
            employees[user_id]["resolved"] += 1

    for invoice in deleted_invoices:
        user_id = invoice["added_by"]["user_id"]
        if user_id in employees:
            employees[user_id]["deleted"] += 1

    report.append("\n📋 Статистика по сотрудникам:")
    for employee in employees.values():
        report.append(
            f"👤 {employee['name']}:\n"
            f"   ➕ Добавлено: {employee['added']}\n"
            f"   ✅ Решено: {employee['resolved']}\n"
            f"   ❌ Удалено: {employee['deleted']}\n"
        )

    await message.delete()
    await message.answer("\n".join(report))


@router.message(Command("del"))
async def delete_invoice_handler(message: types.Message, db, bot: Bot):
    if not await check_chat_access(message, bot):
        return

    reply = message.reply_to_message
    if reply:
        invoice = db.find_invoice_by_message_id(reply.message_id)
        if not invoice:
            await message.delete()
            return
        db.delete_invoice(reply.message_id)
        await message.delete()
        return

    try:
        index = int(message.text.split()[1]) - 1
        invoices = db.get_all_invoices()
        if index < 0 or index >= len(invoices):
            raise IndexError
        invoice = invoices[index]
        db.delete_invoice(invoice["message_id"])
    except (IndexError, ValueError):
        pass
    finally:
        await message.delete()


@router.message(lambda message: message.reply_to_message and "++" in message.text)
async def resolve_invoice_handler(message: types.Message, db, bot: Bot):
    if not await check_chat_access(message, bot):
        return

    reply = message.reply_to_message
    invoice = db.find_invoice_by_message_id(reply.message_id)
    if not invoice:
        return

    db.resolve_invoice(reply.message_id)


@router.message()
async def auto_add_invoice_handler(message: types.Message, db, bot: Bot):
    if not await check_chat_access(message, bot):
        return

    if message.photo and message.caption:
        client_name = message.caption.strip()
        db.add_invoice(
            chat_id=message.chat.id,
            message_id=message.message_id,
            client_name=client_name,
            user_id=message.from_user.id,
            full_name=message.from_user.full_name
        )
