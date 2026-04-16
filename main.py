import os
import json
import logging
import psycopg2
import psycopg2.extras
import telebot
from flask import Flask, request, jsonify, send_from_directory
from telebot import types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
DATABASE_URL = os.environ.get("DATABASE_URL")
PORT = int(os.environ.get("PORT", "5000"))

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__, static_folder="static", static_url_path="/static")

WEBAPP_URL = os.environ.get("RENDER_EXTERNAL_URL")

if not WEBAPP_URL:
    REPLIT_DOMAINS = os.environ.get("REPLIT_DOMAINS", "")
    if REPLIT_DOMAINS:
        WEBAPP_URL = f"https://{REPLIT_DOMAINS.split(',')[0]}"
    else:
        WEBAPP_URL = "http://localhost:5000"

logger.info(f"Using Webhook URL: {WEBAPP_URL}")
admin_state = {}


def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    return conn


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/movies")
def api_movies():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM movies ORDER BY created_at DESC")
    movies = cur.fetchall()
    for m in movies:
        m["created_at"] = str(m["created_at"])
    cur.close()
    conn.close()
    return jsonify(movies)


@app.route("/api/movies/<int:movie_id>")
def api_movie_detail(movie_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM movies WHERE id = %s", (movie_id,))
    movie = cur.fetchone()
    if not movie:
        cur.close()
        conn.close()
        return jsonify({"error": "Not found"}), 404
    movie["created_at"] = str(movie["created_at"])

    if movie["content_type"] == "movie":
        cur.execute("SELECT * FROM movie_files WHERE movie_id = %s ORDER BY part_number, quality", (movie_id,))
        files = cur.fetchall()
        for f in files:
            f["created_at"] = str(f["created_at"])
        movie["files"] = files
    else:
        cur.execute("SELECT * FROM series_seasons WHERE movie_id = %s ORDER BY season_number", (movie_id,))
        seasons = cur.fetchall()
        for s in seasons:
            s["created_at"] = str(s["created_at"])
            cur.execute("SELECT * FROM series_episodes WHERE season_id = %s ORDER BY episode_number", (s["id"],))
            episodes = cur.fetchall()
            for e in episodes:
                e["created_at"] = str(e["created_at"])
            s["episodes"] = episodes
        movie["seasons"] = seasons

    cur.close()
    conn.close()
    return jsonify(movie)


@app.route("/api/movies/<int:movie_id>", methods=["PUT"])
def api_update_movie(movie_id):
    data = request.json
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE movies SET title=%s, genre=%s, poster_url=%s, trailer_url=%s, description=%s WHERE id=%s",
        (data.get("title"), data.get("genre"), data.get("poster_url"), data.get("trailer_url"), data.get("description"), movie_id)
    )
    cur.close()
    conn.close()
    return jsonify({"success": True})


@app.route("/api/movies/<int:movie_id>", methods=["DELETE"])
def api_delete_movie(movie_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM movies WHERE id = %s", (movie_id,))
    cur.close()
    conn.close()
    return jsonify({"success": True})


@app.route("/api/movies/<int:movie_id>/files/<int:file_id>", methods=["DELETE"])
def api_delete_file(movie_id, file_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM movie_files WHERE id = %s AND movie_id = %s", (file_id, movie_id))
    cur.close()
    conn.close()
    return jsonify({"success": True})


@app.route("/api/movies/<int:movie_id>/seasons/<int:season_id>/episodes/<int:episode_id>", methods=["DELETE"])
def api_delete_episode(movie_id, season_id, episode_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM series_episodes WHERE id = %s AND season_id = %s", (episode_id, season_id))
    cur.close()
    conn.close()
    return jsonify({"success": True})


@app.route("/api/movies/<int:movie_id>/seasons/<int:season_id>", methods=["DELETE"])
def api_delete_season(movie_id, season_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM series_seasons WHERE id = %s AND movie_id = %s", (season_id, movie_id))
    cur.close()
    conn.close()
    return jsonify({"success": True})


@app.route("/api/download", methods=["POST"])
def api_download():
    data = request.json
    user_id = data.get("user_id")
    file_id = data.get("file_id")
    if not user_id or not file_id:
        return jsonify({"error": "Missing user_id or file_id"}), 400
    try:
        bot.send_video(chat_id=int(user_id), video=file_id, caption="Here's your movie from DY SHOWS")
    except Exception:
        try:
            bot.send_document(chat_id=int(user_id), document=file_id, caption="Here's your file from DY SHOWS")
        except Exception as e2:
            return jsonify({"error": str(e2)}), 500
    return jsonify({"success": True})


@app.route("/api/requests", methods=["GET"])
def api_get_requests():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM movie_requests ORDER BY created_at DESC")
    reqs = cur.fetchall()
    for r in reqs:
        r["created_at"] = str(r["created_at"])
    cur.close()
    conn.close()
    return jsonify(reqs)


@app.route("/api/requests", methods=["POST"])
def api_create_request():
    data = request.json
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO movie_requests (user_id, username, request_text) VALUES (%s, %s, %s)",
        (data.get("user_id"), data.get("username"), data.get("request_text"))
    )
    cur.close()
    conn.close()
    return jsonify({"success": True})


@app.route("/api/requests/<int:req_id>", methods=["PUT"])
def api_update_request(req_id):
    data = request.json
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE movie_requests SET status=%s WHERE id=%s", (data.get("status"), req_id))
    cur.close()
    conn.close()
    return jsonify({"success": True})


@app.route("/api/requests/<int:req_id>", methods=["DELETE"])
def api_delete_request(req_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM movie_requests WHERE id = %s", (req_id,))
    cur.close()
    conn.close()
    return jsonify({"success": True})


@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        json_string = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "", 200
    return "", 403


@bot.message_handler(commands=["start"])
def handle_start(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(
        text="Open DY SHOWS",
        web_app=types.WebAppInfo(url=WEBAPP_URL)
    ))

    welcome = (
        "*Welcome to DY SHOWS*\n\n"
        "Your ultimate movie & series library!\n\n"
        "*Available Commands:*\n"
        "/start - Show this welcome message\n"
        "/request - Request a movie or series\n"
        "/about - Learn about DY SHOWS\n"
    )

    if message.from_user.id == ADMIN_ID:
        welcome += (
            "\n*Admin Commands:*\n"
            "/upload - Upload a single movie\n"
            "/uploadseries - Upload a new series\n"
            "/addseason - Add season to existing series\n"
            "/addepisode - Add episode to existing season\n"
            "/addquality - Add quality variant to a movie\n"
            "/addpart - Add a part to a multi-part movie\n"
            "/listmovies - List all movies with IDs\n"
            "/deletemovie - Delete a movie\n"
            "/viewrequests - See user movie requests\n"
        )

    bot.send_message(message.chat.id, welcome, parse_mode="Markdown", reply_markup=markup)


@bot.message_handler(commands=["about"])
def handle_about(message):
    about_text = (
        "*DY SHOWS*\n\n"
        "DY SHOWS is your one-stop destination for movies and series.\n\n"
        "Browse our growing library of movies and series\n"
        "Download directly to your Telegram\n"
        "Request movies you'd love to see added\n"
        "Watch trailers before downloading\n"
        "Multiple quality options available\n\n"
        "Tap the button below to start browsing!"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(
        text="Open DY SHOWS",
        web_app=types.WebAppInfo(url=WEBAPP_URL)
    ))
    bot.send_message(message.chat.id, about_text, parse_mode="Markdown", reply_markup=markup)


@bot.message_handler(commands=["request"])
def handle_request(message):
    bot.send_message(message.chat.id, "What movie or series would you like to request?\n\nType the name below:")
    bot.register_next_step_handler(message, process_request)


def process_request(message):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO movie_requests (user_id, username, request_text) VALUES (%s, %s, %s)",
        (message.from_user.id, message.from_user.username or message.from_user.first_name, message.text)
    )
    cur.close()
    conn.close()
    bot.send_message(message.chat.id, "Your request has been submitted! We'll try to add it soon.")
    try:
        bot.send_message(ADMIN_ID, f"New movie request from @{message.from_user.username or message.from_user.first_name}:\n\n{message.text}")
    except:
        pass


@bot.message_handler(commands=["upload"])
def handle_upload(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "Admin only command.")
        return
    bot.send_message(message.chat.id, "Send the *movie title*:", parse_mode="Markdown")
    bot.register_next_step_handler(message, upload_get_title)


def upload_get_title(message):
    admin_state[message.from_user.id] = {"title": message.text, "content_type": "movie"}
    bot.send_message(message.chat.id, "Send the *genre* (e.g. Action, Drama):", parse_mode="Markdown")
    bot.register_next_step_handler(message, upload_get_genre)


def upload_get_genre(message):
    admin_state[message.from_user.id]["genre"] = message.text
    bot.send_message(message.chat.id, "Send the *poster image URL*:", parse_mode="Markdown")
    bot.register_next_step_handler(message, upload_get_poster)


def upload_get_poster(message):
    admin_state[message.from_user.id]["poster_url"] = message.text
    bot.send_message(message.chat.id, "Send a *YouTube trailer link* (or type 'skip'):", parse_mode="Markdown")
    bot.register_next_step_handler(message, upload_get_trailer)


def upload_get_trailer(message):
    trailer = message.text if message.text.lower() != "skip" else None
    admin_state[message.from_user.id]["trailer_url"] = trailer
    bot.send_message(message.chat.id, "Send a *description/about* for the movie (or type 'skip'):", parse_mode="Markdown")
    bot.register_next_step_handler(message, upload_get_description)


def upload_get_description(message):
    desc = message.text if message.text.lower() != "skip" else None
    admin_state[message.from_user.id]["description"] = desc
    bot.send_message(message.chat.id, "Send the *quality label* (e.g. 720p, 1080p, 4K) or type 'default':", parse_mode="Markdown")
    bot.register_next_step_handler(message, upload_get_quality)


def upload_get_quality(message):
    quality = message.text if message.text.lower() != "default" else "default"
    admin_state[message.from_user.id]["quality"] = quality
    bot.send_message(message.chat.id, "Now send the *video file*:", parse_mode="Markdown")
    bot.register_next_step_handler(message, upload_get_file)


def upload_get_file(message):
    state = admin_state.get(message.from_user.id)
    if not state:
        bot.send_message(message.chat.id, "Session expired. Use /upload again.")
        return

    file_id = None
    if message.video:
        file_id = message.video.file_id
    elif message.document:
        file_id = message.document.file_id
    else:
        bot.send_message(message.chat.id, "Please send a video file. Use /upload to start over.")
        return

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO movies (title, genre, poster_url, trailer_url, description, content_type) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
        (state["title"], state["genre"], state["poster_url"], state.get("trailer_url"), state.get("description"), "movie")
    )
    movie_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO movie_files (movie_id, file_id, quality) VALUES (%s,%s,%s)",
        (movie_id, file_id, state.get("quality", "default"))
    )
    cur.close()
    conn.close()
    del admin_state[message.from_user.id]
    bot.send_message(message.chat.id, f"Movie '{state['title']}' uploaded!\nMovie ID: {movie_id}")


@bot.message_handler(commands=["uploadseries"])
def handle_upload_series(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "Admin only command.")
        return
    bot.send_message(message.chat.id, "Send the *series title*:", parse_mode="Markdown")
    bot.register_next_step_handler(message, series_get_title)


def series_get_title(message):
    admin_state[message.from_user.id] = {"title": message.text, "content_type": "series"}
    bot.send_message(message.chat.id, "Send the *genre*:", parse_mode="Markdown")
    bot.register_next_step_handler(message, series_get_genre)


def series_get_genre(message):
    admin_state[message.from_user.id]["genre"] = message.text
    bot.send_message(message.chat.id, "Send the *poster image URL*:", parse_mode="Markdown")
    bot.register_next_step_handler(message, series_get_poster)


def series_get_poster(message):
    admin_state[message.from_user.id]["poster_url"] = message.text
    bot.send_message(message.chat.id, "Send a *YouTube trailer link* (or type 'skip'):", parse_mode="Markdown")
    bot.register_next_step_handler(message, series_get_trailer)


def series_get_trailer(message):
    trailer = message.text if message.text.lower() != "skip" else None
    admin_state[message.from_user.id]["trailer_url"] = trailer
    bot.send_message(message.chat.id, "Send a *description* (or type 'skip'):", parse_mode="Markdown")
    bot.register_next_step_handler(message, series_get_description)


def series_get_description(message):
    desc = message.text if message.text.lower() != "skip" else None
    admin_state[message.from_user.id]["description"] = desc
    bot.send_message(message.chat.id, "How many *seasons* to add now?", parse_mode="Markdown")
    bot.register_next_step_handler(message, series_get_season_count)


def series_get_season_count(message):
    try:
        count = int(message.text)
    except:
        bot.send_message(message.chat.id, "Please send a number.")
        bot.register_next_step_handler(message, series_get_season_count)
        return
    state = admin_state[message.from_user.id]
    state["season_count"] = count
    state["current_season"] = 1
    state["seasons_data"] = {}

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO movies (title, genre, poster_url, trailer_url, description, content_type) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
        (state["title"], state["genre"], state["poster_url"], state.get("trailer_url"), state.get("description"), "series")
    )
    state["movie_id"] = cur.fetchone()[0]
    cur.close()
    conn.close()

    bot.send_message(message.chat.id, f"Season {state['current_season']}: How many *episodes*?", parse_mode="Markdown")
    bot.register_next_step_handler(message, series_get_episode_count)


def series_get_episode_count(message):
    try:
        count = int(message.text)
    except:
        bot.send_message(message.chat.id, "Please send a number.")
        bot.register_next_step_handler(message, series_get_episode_count)
        return
    state = admin_state[message.from_user.id]
    season_num = state["current_season"]

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO series_seasons (movie_id, season_number) VALUES (%s,%s) RETURNING id",
        (state["movie_id"], season_num)
    )
    season_id = cur.fetchone()[0]
    cur.close()
    conn.close()

    state["current_season_id"] = season_id
    state["episode_count"] = count
    state["current_episode"] = 1

    bot.send_message(message.chat.id, f"Send *Episode {state['current_episode']}* file for Season {season_num}:", parse_mode="Markdown")
    bot.register_next_step_handler(message, series_get_episode_file)


def series_get_episode_file(message):
    state = admin_state.get(message.from_user.id)
    if not state:
        bot.send_message(message.chat.id, "Session expired.")
        return

    file_id = None
    if message.video:
        file_id = message.video.file_id
    elif message.document:
        file_id = message.document.file_id
    else:
        bot.send_message(message.chat.id, "Please send a video file.")
        bot.register_next_step_handler(message, series_get_episode_file)
        return

    caption = message.caption or f"S{state['current_season']}E{state['current_episode']}"

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO series_episodes (season_id, episode_number, file_id, caption) VALUES (%s,%s,%s,%s)",
        (state["current_season_id"], state["current_episode"], file_id, caption)
    )
    cur.close()
    conn.close()

    state["current_episode"] += 1

    if state["current_episode"] <= state["episode_count"]:
        bot.send_message(message.chat.id, f"Episode {state['current_episode']-1} saved!\nSend *Episode {state['current_episode']}* file:", parse_mode="Markdown")
        bot.register_next_step_handler(message, series_get_episode_file)
    else:
        state["current_season"] += 1
        if state["current_season"] <= state["season_count"]:
            bot.send_message(message.chat.id, f"Season {state['current_season']-1} complete!\nSeason {state['current_season']}: How many *episodes*?", parse_mode="Markdown")
            bot.register_next_step_handler(message, series_get_episode_count)
        else:
            movie_id = state["movie_id"]
            title = state["title"]
            del admin_state[message.from_user.id]
            bot.send_message(message.chat.id, f"Series '{title}' fully uploaded!\nSeries ID: {movie_id}")


@bot.message_handler(commands=["addseason"])
def handle_add_season(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "Admin only command.")
        return
    bot.send_message(message.chat.id, "Send the *series ID* to add a season to:", parse_mode="Markdown")
    bot.register_next_step_handler(message, addseason_get_id)


def addseason_get_id(message):
    try:
        movie_id = int(message.text)
    except:
        bot.send_message(message.chat.id, "Please send a valid ID number.")
        return
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM movies WHERE id = %s AND content_type = 'series'", (movie_id,))
    movie = cur.fetchone()
    if not movie:
        bot.send_message(message.chat.id, "Series not found.")
        cur.close()
        conn.close()
        return
    cur.execute("SELECT MAX(season_number) as max_s FROM series_seasons WHERE movie_id = %s", (movie_id,))
    result = cur.fetchone()
    next_season = (result["max_s"] or 0) + 1
    cur.close()
    conn.close()

    admin_state[message.from_user.id] = {
        "movie_id": movie_id,
        "title": movie["title"],
        "current_season": next_season,
        "season_count": next_season,
        "adding_season": True
    }
    bot.send_message(message.chat.id, f"Adding Season {next_season} to '{movie['title']}'\nHow many *episodes*?", parse_mode="Markdown")
    bot.register_next_step_handler(message, addseason_get_episode_count)


def addseason_get_episode_count(message):
    try:
        count = int(message.text)
    except:
        bot.send_message(message.chat.id, "Please send a number.")
        bot.register_next_step_handler(message, addseason_get_episode_count)
        return
    state = admin_state[message.from_user.id]

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO series_seasons (movie_id, season_number) VALUES (%s,%s) RETURNING id",
        (state["movie_id"], state["current_season"])
    )
    season_id = cur.fetchone()[0]
    cur.close()
    conn.close()

    state["current_season_id"] = season_id
    state["episode_count"] = count
    state["current_episode"] = 1

    bot.send_message(message.chat.id, "Send *Episode 1* file:", parse_mode="Markdown")
    bot.register_next_step_handler(message, addseason_get_episode_file)


def addseason_get_episode_file(message):
    state = admin_state.get(message.from_user.id)
    if not state:
        bot.send_message(message.chat.id, "Session expired.")
        return

    file_id = None
    if message.video:
        file_id = message.video.file_id
    elif message.document:
        file_id = message.document.file_id
    else:
        bot.send_message(message.chat.id, "Please send a video file.")
        bot.register_next_step_handler(message, addseason_get_episode_file)
        return

    caption = message.caption or f"S{state['current_season']}E{state['current_episode']}"

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO series_episodes (season_id, episode_number, file_id, caption) VALUES (%s,%s,%s,%s)",
        (state["current_season_id"], state["current_episode"], file_id, caption)
    )
    cur.close()
    conn.close()

    state["current_episode"] += 1
    if state["current_episode"] <= state["episode_count"]:
        bot.send_message(message.chat.id, f"Episode {state['current_episode']-1} saved!\nSend *Episode {state['current_episode']}* file:", parse_mode="Markdown")
        bot.register_next_step_handler(message, addseason_get_episode_file)
    else:
        title = state["title"]
        season = state["current_season"]
        del admin_state[message.from_user.id]
        bot.send_message(message.chat.id, f"Season {season} added to '{title}'!")


@bot.message_handler(commands=["addepisode"])
def handle_add_episode(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "Admin only command.")
        return
    bot.send_message(message.chat.id, "Send the *series ID*:", parse_mode="Markdown")
    bot.register_next_step_handler(message, addepisode_get_series_id)


def addepisode_get_series_id(message):
    try:
        movie_id = int(message.text)
    except:
        bot.send_message(message.chat.id, "Please send a valid ID.")
        return
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM series_seasons WHERE movie_id = %s ORDER BY season_number", (movie_id,))
    seasons = cur.fetchall()
    cur.close()
    conn.close()

    if not seasons:
        bot.send_message(message.chat.id, "No seasons found for this series.")
        return

    text = "Available seasons:\n"
    for s in seasons:
        text += f"  Season {s['season_number']} (ID: {s['id']})\n"
    text += "\nSend the *season number*:"

    admin_state[message.from_user.id] = {"movie_id": movie_id, "seasons": seasons}
    bot.send_message(message.chat.id, text, parse_mode="Markdown")
    bot.register_next_step_handler(message, addepisode_get_season)


def addepisode_get_season(message):
    try:
        season_num = int(message.text)
    except:
        bot.send_message(message.chat.id, "Please send a number.")
        return
    state = admin_state[message.from_user.id]
    season = None
    for s in state["seasons"]:
        if s["season_number"] == season_num:
            season = s
            break
    if not season:
        bot.send_message(message.chat.id, "Season not found.")
        return

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT MAX(episode_number) as max_e FROM series_episodes WHERE season_id = %s", (season["id"],))
    result = cur.fetchone()
    next_ep = (result["max_e"] or 0) + 1
    cur.close()
    conn.close()

    state["season_id"] = season["id"]
    state["season_number"] = season_num
    state["current_episode"] = next_ep

    bot.send_message(message.chat.id, f"Send the file for *Episode {next_ep}*:", parse_mode="Markdown")
    bot.register_next_step_handler(message, addepisode_get_file)


def addepisode_get_file(message):
    state = admin_state.get(message.from_user.id)
    if not state:
        bot.send_message(message.chat.id, "Session expired.")
        return
    file_id = None
    if message.video:
        file_id = message.video.file_id
    elif message.document:
        file_id = message.document.file_id
    else:
        bot.send_message(message.chat.id, "Please send a video file.")
        bot.register_next_step_handler(message, addepisode_get_file)
        return

    caption = message.caption or f"S{state['season_number']}E{state['current_episode']}"

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO series_episodes (season_id, episode_number, file_id, caption) VALUES (%s,%s,%s,%s)",
        (state["season_id"], state["current_episode"], file_id, caption)
    )
    cur.close()
    conn.close()

    ep = state["current_episode"]
    del admin_state[message.from_user.id]
    bot.send_message(message.chat.id, f"Episode {ep} added to Season {state['season_number']}!")


@bot.message_handler(commands=["addquality"])
def handle_add_quality(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "Admin only command.")
        return
    bot.send_message(message.chat.id, "Send the *movie ID*:", parse_mode="Markdown")
    bot.register_next_step_handler(message, addquality_get_id)


def addquality_get_id(message):
    try:
        movie_id = int(message.text)
    except:
        bot.send_message(message.chat.id, "Please send a valid ID.")
        return
    admin_state[message.from_user.id] = {"movie_id": movie_id}
    bot.send_message(message.chat.id, "Send the *quality label* (e.g. 720p, 1080p, 4K):", parse_mode="Markdown")
    bot.register_next_step_handler(message, addquality_get_label)


def addquality_get_label(message):
    admin_state[message.from_user.id]["quality"] = message.text
    bot.send_message(message.chat.id, "Send the *video file* for this quality:", parse_mode="Markdown")
    bot.register_next_step_handler(message, addquality_get_file)


def addquality_get_file(message):
    state = admin_state.get(message.from_user.id)
    if not state:
        bot.send_message(message.chat.id, "Session expired.")
        return
    file_id = None
    if message.video:
        file_id = message.video.file_id
    elif message.document:
        file_id = message.document.file_id
    else:
        bot.send_message(message.chat.id, "Please send a video file.")
        bot.register_next_step_handler(message, addquality_get_file)
        return

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO movie_files (movie_id, file_id, quality) VALUES (%s,%s,%s)",
        (state["movie_id"], file_id, state["quality"])
    )
    cur.close()
    conn.close()
    del admin_state[message.from_user.id]
    bot.send_message(message.chat.id, f"{state['quality']} quality added to movie ID {state['movie_id']}!")


@bot.message_handler(commands=["addpart"])
def handle_add_part(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "Admin only command.")
        return
    bot.send_message(message.chat.id, "Send the *movie ID*:", parse_mode="Markdown")
    bot.register_next_step_handler(message, addpart_get_id)


def addpart_get_id(message):
    try:
        movie_id = int(message.text)
    except:
        bot.send_message(message.chat.id, "Please send a valid ID.")
        return
    admin_state[message.from_user.id] = {"movie_id": movie_id}
    bot.send_message(message.chat.id, "Send the *part number* (e.g. 1, 2, 3):", parse_mode="Markdown")
    bot.register_next_step_handler(message, addpart_get_number)


def addpart_get_number(message):
    try:
        part = int(message.text)
    except:
        bot.send_message(message.chat.id, "Please send a number.")
        return
    admin_state[message.from_user.id]["part_number"] = part
    bot.send_message(message.chat.id, "Send the *quality label* (or type 'default'):", parse_mode="Markdown")
    bot.register_next_step_handler(message, addpart_get_quality)


def addpart_get_quality(message):
    quality = message.text if message.text.lower() != "default" else "default"
    admin_state[message.from_user.id]["quality"] = quality
    bot.send_message(message.chat.id, "Send the *video file*:", parse_mode="Markdown")
    bot.register_next_step_handler(message, addpart_get_file)


def addpart_get_file(message):
    state = admin_state.get(message.from_user.id)
    if not state:
        bot.send_message(message.chat.id, "Session expired.")
        return
    file_id = None
    if message.video:
        file_id = message.video.file_id
    elif message.document:
        file_id = message.document.file_id
    else:
        bot.send_message(message.chat.id, "Please send a video file.")
        bot.register_next_step_handler(message, addpart_get_file)
        return

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO movie_files (movie_id, file_id, quality, part_number) VALUES (%s,%s,%s,%s)",
        (state["movie_id"], file_id, state["quality"], state["part_number"])
    )
    cur.close()
    conn.close()
    del admin_state[message.from_user.id]
    bot.send_message(message.chat.id, f"Part {state['part_number']} added to movie ID {state['movie_id']}!")


@bot.message_handler(commands=["listmovies"])
def handle_list_movies(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "Admin only command.")
        return
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id, title, content_type, genre FROM movies ORDER BY id")
    movies = cur.fetchall()
    cur.close()
    conn.close()

    if not movies:
        bot.send_message(message.chat.id, "No movies registered yet.")
        return

    text = "*All Movies/Series:*\n\n"
    for m in movies:
        icon = "TV" if m["content_type"] == "series" else "Movie"
        text += f"[{icon}] ID: `{m['id']}` - {m['title']} ({m['genre']})\n"

    bot.send_message(message.chat.id, text, parse_mode="Markdown")


@bot.message_handler(commands=["deletemovie"])
def handle_delete_movie(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "Admin only command.")
        return
    bot.send_message(message.chat.id, "Send the *movie/series ID* to delete:", parse_mode="Markdown")
    bot.register_next_step_handler(message, deletemovie_confirm)


def deletemovie_confirm(message):
    try:
        movie_id = int(message.text)
    except:
        bot.send_message(message.chat.id, "Please send a valid ID.")
        return
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT title FROM movies WHERE id = %s", (movie_id,))
    movie = cur.fetchone()
    if not movie:
        bot.send_message(message.chat.id, "Movie not found.")
        cur.close()
        conn.close()
        return
    cur.execute("DELETE FROM movies WHERE id = %s", (movie_id,))
    cur.close()
    conn.close()
    bot.send_message(message.chat.id, f"'{movie['title']}' has been deleted.")


@bot.message_handler(commands=["viewrequests"])
def handle_view_requests(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "Admin only command.")
        return
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM movie_requests ORDER BY created_at DESC LIMIT 20")
    reqs = cur.fetchall()
    cur.close()
    conn.close()

    if not reqs:
        bot.send_message(message.chat.id, "No requests yet.")
        return

    text = "*Recent Movie Requests:*\n\n"
    for r in reqs:
        status_icon = "Pending" if r["status"] == "pending" else "Done"
        text += f"[{status_icon}] @{r['username']}: {r['request_text']}\n"

    bot.send_message(message.chat.id, text, parse_mode="Markdown")


def set_webhook():
    bot.remove_webhook()
    webhook_url = f"{WEBAPP_URL}/webhook/{BOT_TOKEN}"
    bot.set_webhook(url=webhook_url)
    logger.info(f"Webhook set to {webhook_url}")


if __name__ == "__main__":
    set_webhook()
    app.run(host="0.0.0.0", port=PORT, debug=False)
