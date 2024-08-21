import asyncio
import datetime
from difflib import SequenceMatcher

from google.cloud import speech
from google.cloud.speech_v1 import SpeechRecognitionAlternative


async def transcribe_audio_to_text(content: bytes,
                                   encoding: speech.RecognitionConfig.AudioEncoding) -> SpeechRecognitionAlternative:
    """Этап 1: Преобразование аудио в текст"""
    client = speech.SpeechClient()

    # noinspection PyTypeChecker
    audio = speech.RecognitionAudio(content=content)

    # noinspection PyTypeChecker
    config = speech.RecognitionConfig(
        encoding=encoding,
        audio_channel_count=2,
        language_code="ru-RU",
        enable_word_time_offsets=True,
        enable_automatic_punctuation=True,
    )
    try:

        operation = client.long_running_recognize(config=config, audio=audio)

        while not operation.done():
            print("Waiting for operation to complete...")
            await asyncio.sleep(5)

        response = operation.result()

        if not response.results:
            raise RuntimeError("Empty result")

        result = response.results[0].alternatives[0]
        print(f"Transcript: {result.transcript}")
        print(f"Confidence: {result.confidence}")

    except Exception as e:
        raise RuntimeError(f'Ошибка распознавания: {e}')

    return result


def find_missing_sentences(speech_recognition_alternative: SpeechRecognitionAlternative,
                           script_text: str) -> list[tuple[str, datetime.timedelta, str]]:
    """Этап 2: Проверка потярешек"""
    transcribed_text = speech_recognition_alternative.transcript
    words_timestamps = speech_recognition_alternative.words

    transcribed_text_words = transcribed_text.split(' ')
    script_text_words = script_text.split(' ')

    matcher = SequenceMatcher(None, transcribed_text_words, script_text_words)
    mistakes: list[tuple[str, datetime.timedelta, str]] = []

    for tag, start1, end1, start2, end2 in matcher.get_opcodes():
        if tag == 'insert':  # строка в сценарии, отсутствующая в транскрибированном тексте
            timecode = words_timestamps[start1].start_time
            mistakes.append(('потеряшка', timecode, ' '.join(script_text_words[start2:end2])))

    return mistakes


async def main():
    audio_file_path = "input_examples/test.wav"  # local file

    script_text = """Опрошенные называли и некоторые распространенные страхи, которые возникают в преклонном возрасте (а в случае старческой деменции могут превращаться в навязчивый бред): это боязнь нищеты, краж, потери памяти и другие тревожные ощущения. А главным проявлением старости почти все назвали потерю независимости — как в физическом, так и в ментальном смысле.
    """.strip()

    try:
        with open(audio_file_path, "rb") as audio_file:
            content = audio_file.read()

        if audio_file_path.endswith('.wav'):
            encoding = speech.RecognitionConfig.AudioEncoding.LINEAR16
        elif audio_file_path.endswith('.flac'):
            encoding = speech.RecognitionConfig.AudioEncoding.FLAC
        else:
            raise RuntimeError('Не поддерживаемый тип файла. Используйте WAV/FLAC')

        result = await transcribe_audio_to_text(content, encoding)
        mistakes = find_missing_sentences(result, script_text)
    except RuntimeError as e:
        print(f"Возникла ошибка: {str(e)}")
    else:
        for mistake in mistakes:
            print(f"{mistake[0]} | {str(mistake[1])} | {mistake[2]}")


if __name__ == '__main__':
    asyncio.run(main())
