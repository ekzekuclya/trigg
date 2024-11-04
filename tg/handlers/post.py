from aiogram import Router, Bot, F
from aiogram.filters import Command, CommandObject, BaseFilter
from aiogram.types import Message, InlineKeyboardButton, ReplyKeyboardMarkup, ChatMemberOwner, ChatMemberAdministrator, \
    KeyboardButton, ReplyKeyboardRemove, CallbackQuery
from django.db.models import Q

from ..models import TelegramUser, Post, Button
from aiogram.filters import Command, CommandObject, BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from asgiref.sync import sync_to_async
from aiogram.fsm.state import StatesGroup, State
router = Router()


main_chat = "-1002297957772"


class AddButton(StatesGroup):
    wait_buttons = State()

class TriggerState(StatesGroup):
    wait_name = State()
    wait_buttons = State()
    wait_photo = State()


@router.message(Command("add_post"))
async def create_post(msg: Message, bot: Bot, state: FSMContext):
    user = await sync_to_async(TelegramUser.objects.get_or_create)(user_id=msg.from_user.id)
    # if user.is_admin:
    await msg.answer("->Введите название триггера:")
    await state.set_state(TriggerState.wait_name)


@router.message(Command("manage_posts"))
async def manage_posts(msg: Message, state: FSMContext):
    user = await sync_to_async(TelegramUser.objects.get_or_create)(user_id=msg.from_user.id)
    # if user.is_admin:
    posts = await sync_to_async(Post.objects.all)()
    builder = InlineKeyboardBuilder()
    for i in posts:
        builder.add(InlineKeyboardButton(text=f"{i.trigger_name}", callback_data=f"manage_post_{i.id}"))
        builder.add(InlineKeyboardButton(text=f"Удалить", callback_data=f"delete_post_{i.id}"))
    builder.adjust(2)
    await msg.answer("Редактирование кнопок поста:", reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("delete_post_"))
async def delete_post(callback: CallbackQuery):
    await callback.message.delete()
    data = callback.data.split("_")
    post_id = data[2]
    post = await sync_to_async(Post.objects.filter)(id=post_id)
    post.first().delete()
    posts = await sync_to_async(Post.objects.all)()
    builder = InlineKeyboardBuilder()
    for i in posts:
        builder.add(InlineKeyboardButton(text=f"{i.trigger_name}", callback_data=f"manage_post_{i.id}"))
        builder.add(InlineKeyboardButton(text=f"Удалить", callback_data=f"delete_post_{i.id}"))
    builder.adjust(2)
    await callback.message.answer("Редактирование кнопок поста:", reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("manage_post_"))
async def in_manage_post(callback: CallbackQuery, bot: Bot):
    data = callback.data.split("_")
    post_id = data[2]
    post = await sync_to_async(Post.objects.get)(id=post_id)
    buttons = await sync_to_async(Button.objects.filter)(post=post)
    builder = InlineKeyboardBuilder()
    for i in buttons:
        builder.add(InlineKeyboardButton(text=f"❌ {i.button_name}", callback_data=f"delete_button_{i.id}"))
    builder.add(InlineKeyboardButton(text="Добавить кнопки к посту", callback_data=f"add_buttons_{post.id}"))
    builder.adjust(1)
    if post.photo:
        await bot.send_photo(chat_id=callback.message.chat.id, caption=f"{post.trigger_name}", photo=f"{post.photo}",
                             reply_markup=builder.as_markup())
    else:
        await callback.message.answer(f"{post.trigger_name}", reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("delete_button_"))
async def delete_button(callback: CallbackQuery, state: FSMContext, bot: Bot):
    button_id = callback.data.split("_")[2]
    button = await sync_to_async(Button.objects.get)(id=button_id)
    button.delete()
    await callback.message.delete()
    post = await sync_to_async(Post.objects.get)(id=button.post.id)
    buttons = await sync_to_async(Button.objects.filter)(post=post)
    builder = InlineKeyboardBuilder()
    for i in buttons:
        builder.add(InlineKeyboardButton(text=f"❌ {i.button_name}", callback_data=f"delete_button_{i.id}"))
    builder.adjust(1)
    if post.photo:
        a = await bot.edit_message_reply_markup(chat_id=main_chat, message_id=post.message_id, reply_markup=builder.as_markup())
        post.message_id = a.message_id
        post.save()
        builder.add(InlineKeyboardButton(text="Добавить кнопки к посту", callback_data=f"add_buttons_{post.id}"))
        await bot.send_photo(chat_id=callback.message.chat.id, caption=f"{post.trigger_name}", photo=f"{post.photo}",
                             reply_markup=builder.as_markup())
    else:
        builder.add(InlineKeyboardButton(text="Добавить кнопки к посту", callback_data=f"add_buttons_{post.id}"))
        a = await bot.edit_message_reply_markup(chat_id=main_chat, message_id=post.message_id, reply_markup=builder.as_markup())
        post.message_id = a.message_id
        post.save()
        await callback.message.answer(f"{post.trigger_name}", reply_markup=builder.as_markup())


@router.message(TriggerState.wait_name)
async def awaiting_name(msg: Message, bot: Bot, state: FSMContext):
    name = msg.text
    post = await sync_to_async(Post.objects.create)(trigger_name=name)
    await state.update_data(post_id=post.id)
    await state.set_state(TriggerState.wait_buttons)
    keyboard_builder = ReplyKeyboardBuilder()
    keyboard_builder.row(KeyboardButton(text="Отменить"))
    keyboard_builder.row(KeyboardButton(text="Завершить"))
    keyboard_builder.row(KeyboardButton(text="Добавить фото и завершить"))
    keyboard = keyboard_builder.as_markup(resize_keyboard=True)
    await msg.answer("Добавьте кнопки в посту в формате:\nНАЗВАНИЕ КНОПКИ - ССЫЛКА", reply_markup=keyboard)


@router.message(TriggerState.wait_buttons)
async def add_buttons_to_post(msg: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    post_id = data.get("post_id")
    post = await sync_to_async(Post.objects.get)(id=post_id)
    if msg.text == "Отменить":
        post.delete()
        buttons = await sync_to_async(Button.objects.filter)(post=post)
        if buttons:
            for i in buttons:
                i.delete()
        await msg.answer("Пост отменен", reply_markup=ReplyKeyboardRemove())
        await state.clear()
    elif msg.text == "Завершить":
        buttons = await sync_to_async(Button.objects.filter)(post=post)
        builder = InlineKeyboardBuilder()
        print("IN ЗАВЕРШ")
        if buttons:
            for i in buttons:
                builder.add(InlineKeyboardButton(text=f"{i.button_name}", url=f"{i.button_click}"))
            builder.adjust(1)
        posted = await bot.send_message(main_chat, text=".", reply_markup=builder.as_markup())
        post.message_id = posted.message_id
        post.save()
        await state.clear()
        await msg.answer("Пост добавлен", reply_markup=ReplyKeyboardRemove())
    elif msg.text == "Добавить фото и завершить":
        await state.set_state(TriggerState.wait_photo)
        await state.update_data(post_id=post.id)
        await msg.answer("Отправьте фото для поста")
    else:
        button_data = msg.text.split("-")
        button_name = button_data[0].strip()
        button_click = button_data[1].strip()
        button = await sync_to_async(Button.objects.create)(post=post, button_name=button_name, button_click=button_click)
        buttons = await sync_to_async(Button.objects.filter)(post=post)
        builder = InlineKeyboardBuilder()
        if buttons:
            for i in buttons:
                builder.add(InlineKeyboardButton(text=f"{i.button_name}", url=f"{i.button_click}"))
            builder.adjust(1)
        await msg.answer("Кнопка добавлена в пост, продолжайте добавлять, или пройдите в следующий этап", reply_markup=builder.as_markup())


@router.message(TriggerState.wait_photo)
async def wait_photo(msg: Message, state: FSMContext, bot: Bot):
    if msg.photo:
        data = await state.get_data()
        post_id = data.get("post_id")
        post = await sync_to_async(Post.objects.get)(id=post_id)
        photo_id = msg.photo[-1].file_id
        post.photo = photo_id
        buttons = await sync_to_async(Button.objects.filter)(post=post)
        builder = InlineKeyboardBuilder()
        for i in buttons:
            builder.add(InlineKeyboardButton(text=f"{i.button_name}", url=f"{i.button_click}"))
        builder.adjust(1)
        post_msg = await bot.send_photo(main_chat, photo=photo_id, caption=".", reply_markup=builder.as_markup())
        post.message_id = post_msg.message_id
        post.save()
        post_link = f"https://t.me/{main_chat}/{post_msg.message_id}"
        await msg.answer(f"Пост выложен - {post_link}", reply_markup=ReplyKeyboardRemove())


class TriggerFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        if message.text:
            trigger_name = message.text.strip().lower()
            return Post.objects.filter(trigger_name=trigger_name).exists()


@router.message(TriggerFilter())
async def check_trigger(msg: Message, bot: Bot):
    chat_id = msg.chat.id
    trigger_name = msg.text.strip().lower()
    post = Post.objects.filter(Q(trigger_name=trigger_name)).first()

    if post:
        await bot.forward_message(chat_id=chat_id, from_chat_id=main_chat, message_id=post.message_id)
