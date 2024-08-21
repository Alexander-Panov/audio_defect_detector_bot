from aiohttp import web
import asyncio

from google.cloud import speech

from audio_defect_detector import transcribe_audio_to_text, find_missing_sentences


async def handle_upload(request):
    reader = await request.multipart()

    # Read audio file
    audio_part = await reader.next()
    audio_file = await audio_part.read()

    # Read text file
    text_part = await reader.next()
    text_file = await text_part.read(decode=True)

    result = {}
    try:
        audio_filename = audio_part.filename
        if audio_filename.endswith('.wav'):
            encoding = speech.RecognitionConfig.AudioEncoding.LINEAR16
        elif audio_filename.endswith('.flac'):
            encoding = speech.RecognitionConfig.AudioEncoding.FLAC
        else:
            raise RuntimeError('Не поддерживаемый тип файла. Используйте WAV/FLAC')

        script_text = text_file.decode()

        speech_recognition_result = await transcribe_audio_to_text(bytes(audio_file), encoding)
        mistakes = find_missing_sentences(speech_recognition_result, script_text)

        result["result"] = '\n'.join(f"{mistake[0]} | {str(mistake[1])} | {mistake[2]}" for mistake in mistakes)
    except Exception as err:
        result["error"] = str(err)

    return web.json_response(result)


async def init_app():
    app = web.Application()
    app.router.add_post('/process', handle_upload)
    return app


web.run_app(init_app(), host='0.0.0.0', port=8080)
