import asyncio
import json
import logging
import os
import re
from pyrogram import Client, filters
import httpx
from pyrogram.enums import ChatType

CONFIG_FILE = 'config.json'
SESSION_FILE = 'anon_session'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DEFAULT_CONFIG = {
    "api_id": "",
    "api_hash": "",
    "behavior": "Вы — собеседник, который должен отвечать как живой человек. Ваши ответы должны быть естественными, честными и живыми, как у реального человека.",
    "allow_swear": True
}

async def load_or_create_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)

    config = DEFAULT_CONFIG.copy()
    config["api_id"] = input("Введите api_id: ")
    config["api_hash"] = input("Введите api_hash: ")

    await save_config(config)
    return config

async def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

async def ask_gpt4(question: str, config: dict) -> str:
    try:
        logging.info(f"Отправка запроса к GPT-4: {question}")
        system_message = config['behavior']

        payload = {
            "model": "gpt-4o-mini",
            "request": {
                "messages": [
                    {"role": "assistant", "content": system_message},
                    {"role": "user", "content": question}
                ]
            }
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post('http://api.onlysq.ru/ai/v2', json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get('answer', "Ошибка: API не вернул корректный ответ.")
    except Exception as e:
        logging.error(f"Ошибка при запросе к GPT-4: {str(e)}")
        return "Произошла ошибка при запросе к AI. Попробуйте позже."

async def main():
    config = await load_or_create_config()
    app = Client(SESSION_FILE, api_id=config['api_id'], api_hash=config['api_hash'])

    @app.on_message(filters.private | filters.group)
    async def handler(client, message):
        text = message.text or ""
        logging.info(f"Получено сообщение: chat_id={message.chat.id}, text='{text}'")

        if message.chat.type == ChatType.PRIVATE:
            reply_text = await ask_gpt4(text, config)
            await message.reply_text(reply_text)
        else:
            bot_info = await client.get_me()
            if re.search(fr'@{bot_info.username}', text, re.IGNORECASE):
                reply_text = await ask_gpt4(text, config)
                await message.reply_text(reply_text)

    logging.info("Бот запущен. Ожидание сообщений...")
    await app.start()
    await idle()
    await app.stop()

if __name__ == "__main__":
    import nest_asyncio
    from pyrogram import idle
    nest_asyncio.apply()
    try:
        asyncio.run(main())
    except Exception as e:
        logging.error(f"Ошибка при запуске бота: {e}")
