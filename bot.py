import asyncio

import aiohttp
from telegram import Update, Message
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, Application

from config import API_TOKEN, CHANNEL_ID, BACKEND_URL


async def start(application: Application):
    await application.bot.send_message(chat_id=CHANNEL_ID,
                                       text="Я бот-детектор аудио дефектов. Отправьте мне аудио и текст сценария к этому аудио. Я найду в нем ошибки.\n"
                                       )
    await application.bot.send_message(chat_id=CHANNEL_ID,
                                       text="1. Отправьте WAV/FLAC аудио файл длиной менее 60 секунд или размером меньше 10 MB.")


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    audio_file = update.channel_post.audio
    if audio_file is None:
        audio_file = update.channel_post.document

    if not audio_file.file_name.endswith(('.wav', '.flac')):
        await update.channel_post.reply_text(
            "Неизвестный формат. Отправьте WAV/FLAC аудио"
        )
        return
    if audio_file.file_size > 10 * 1024 * 1024:
        await update.channel_post.reply_text(
            "Слишком большой аудио-файл (больше 10 МБ)"
        )
        return

    context.chat_data['audio_received'] = audio_file
    await context.bot.send_message(chat_id=CHANNEL_ID,
                                   text="2. Отправьте текст сценария этого аудио в формате .txt"
                                   )


async def handle_txt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.chat_data.get("audio_received"):
        document = update.channel_post.document
        if document.mime_type == "text/plain":
            context.chat_data['text_received'] = document

            # text_file_path = os.path.join('/path/to/save', f'{document.file_id}.txt')
            # await document.get_file().download_to_drive(text_file_path)
            #
            message = await context.bot.send_message(CHANNEL_ID, "Отправка на сервер")
            await process_data(context, message)
        else:
            await update.channel_post.reply_text("Отправьте текст сценария в формате .txt")
    else:
        await update.channel_post.reply_text("Сначала отправьте аудио файл.")


async def process_data(context: ContextTypes.DEFAULT_TYPE, message: Message):
    # Fetch the audio and text files from context
    audio_file = context.chat_data['audio_received']
    audio_file_download = await context.bot.get_file(audio_file.file_id)
    text_file = context.chat_data['text_received']
    text_file_download = await context.bot.get_file(text_file.file_id)

    # Download the audio and text files into memory
    async with aiohttp.ClientSession() as session:
        async with session.get(audio_file_download.file_path) as audio_response:
            audio_data = await audio_response.read()

        async with session.get(text_file_download.file_path) as text_response:
            text_data = await text_response.read()

        # Prepare the payload for the backend
        data = aiohttp.FormData()
        data.add_field('audio', audio_data, filename=audio_file.file_name, content_type=audio_file.mime_type)
        data.add_field('text', text_data, filename=text_file.file_name, content_type=text_file.mime_type)

        # Task to update the loading indicator
        async def update_loading_message():
            states = ["Обработка аудио .", "Обработка аудио ..", "Обработка аудио ...", "Обработка аудио"]
            while not response_task.done():
                for state in states:
                    await message.edit_text(state)
                    await asyncio.sleep(1)

        # Send the files to the backend server and update the loading message in parallel
        response_task = asyncio.create_task(session.post(BACKEND_URL + "/process", data=data))
        loading_task = asyncio.create_task(update_loading_message())

        # Wait for the response and the loading message update tasks
        response = await response_task
        loading_task.cancel()

        if response.status == 200:
            result = await response.json()
            if "error" in result:
                message_result = f"Ошибка обработки: {result['error']}"
            else:
                message_result = result['result']
        else:
            message_result = f"Ошибка в соединении с сервером: статус код {response.status}"

    # Delete the previous message and send the result
    await message.delete()
    await context.bot.send_message(chat_id=CHANNEL_ID, text=message_result)

    context.chat_data["audio_received"] = None
    context.chat_data["text_received"] = None


def main():
    application = ApplicationBuilder().token(API_TOKEN).build()

    application.post_init = start

    application.add_handler(
        MessageHandler((filters.AUDIO | filters.Document.AUDIO) & ~filters.COMMAND, handle_audio))
    application.add_handler(MessageHandler(filters.Document.TXT & ~filters.COMMAND, handle_txt))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
