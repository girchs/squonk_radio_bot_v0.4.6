import logging
import os
import json
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1

API_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

DATA_FILE = "songs.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.reply("👋 Welcome to Squonk Radio V0.4.6!
Use /setup to link your group.")

@dp.message_handler(commands=['setup'])
async def cmd_setup(message: types.Message):
    await message.reply("📩 Send me `GroupID: <your_group_id>` to register a group.")

@dp.message_handler(lambda message: message.text and message.text.startswith("GroupID:"))
async def set_group_id(message: types.Message):
    data = load_data()
    user_id = str(message.from_user.id)
    group_id = message.text.split(":", 1)[-1].strip()
    data[user_id] = group_id
    save_data(data)
    await message.reply(f"✅ Group ID `{group_id}` saved. Now send me .mp3 files!")

@dp.message_handler(content_types=['audio'])
async def handle_audio(message: types.Message):
    user_id = str(message.from_user.id)
    data = load_data()
    group_id = data.get(user_id)
    if not group_id:
        await message.reply("❗ Please first send `GroupID: <your_group_id>` in this private chat.")
        return

    file = await message.audio.download()
    audio = MP3(file.name, ID3=ID3)
    title = audio.tags.get("TIT2", "Unknown")
    artist = audio.tags.get("TPE1", "Unknown")
    text = f"🎵 {title.text[0]} by {artist.text[0]}" if hasattr(title, "text") and hasattr(artist, "text") else "🎵 Uploaded audio"
    
    song_data = {
        "file_id": message.audio.file_id,
        "title": title.text[0] if hasattr(title, "text") else "Unknown",
        "artist": artist.text[0] if hasattr(artist, "text") else "Unknown"
    }
    group_songs = data.get(group_id, [])
    group_songs.append(song_data)
    data[group_id] = group_songs
    save_data(data)

    await message.reply(f"✅ Saved `{song_data['title']}` by `{song_data['artist']}` for group {group_id}")

@dp.message_handler(commands=['play'])
async def cmd_play(message: types.Message):
    group_id = str(message.chat.id)
    data = load_data()
    songs = data.get(group_id)
    if not songs:
        await message.reply("❌ No songs found for this group.")
        return
    song = songs[0]
    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("▶️ Next", callback_data="next"),
        InlineKeyboardButton("📃 Playlist", callback_data="playlist")
    )
    await bot.send_audio(chat_id=group_id, audio=song["file_id"], caption="🎶 Squonking time!", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == "playlist")
async def show_playlist(callback_query: types.CallbackQuery):
    group_id = str(callback_query.message.chat.id)
    data = load_data()
    songs = data.get(group_id, [])
    if not songs:
        await bot.answer_callback_query(callback_query.id, "No songs in playlist.")
        return
    text = "🎵 Playlist:
"
    for idx, song in enumerate(songs, 1):
        text += f"{idx}. {song['title']} - {song['artist']}
"
    await bot.send_message(chat_id=group_id, text=text)

if __name__ == "__main__":
    from aiogram import executor
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp, skip_updates=True)
