# DY SHOWS - Telegram Mini App Movie Library

## Overview

A full-stack Telegram Mini App (TMA) for a movie and series library called "DY SHOWS". Built with Python Flask backend, pyTelegramBotAPI for the bot, and HTML/CSS/JS for the Netflix-style dark-themed frontend.

## Stack

- **Backend**: Python Flask
- **Bot**: pyTelegramBotAPI (telebot) with webhooks
- **Database**: PostgreSQL (Replit built-in)
- **Frontend**: HTML/CSS/JS (served by Flask)
- **Font**: Inter (Google Fonts)

## Architecture

- `main.py` - Flask server + Telegram bot webhook handler + all bot commands
- `static/index.html` - Main HTML page
- `static/style.css` - Netflix-style dark theme CSS
- `static/app.js` - Frontend JavaScript (movie grid, modals, downloads)
- `static/placeholder.svg` - Placeholder for movies without posters

## Database Schema

- `movies` - Movie/series metadata (title, genre, poster_url, trailer_url, description, content_type)
- `movie_files` - Video file references (file_id, quality, part_number)
- `series_seasons` - Season records for series
- `series_episodes` - Episode records with file_ids
- `movie_requests` - User movie requests

## Bot Commands

### User Commands
- `/start` - Welcome message + Open DY SHOWS button
- `/request` - Request a movie or series
- `/about` - Learn about DY SHOWS

### Admin Commands
- `/upload` - Upload a single movie (guided prompts)
- `/uploadseries` - Upload a new series with seasons/episodes
- `/addseason` - Add a new season to existing series
- `/addepisode` - Add episode to existing season
- `/addquality` - Add quality variant (720p, 1080p, 4K)
- `/addpart` - Add part to multi-part movie
- `/listmovies` - List all movies with IDs
- `/deletemovie` - Delete a movie/series
- `/viewrequests` - View user requests

## Environment Variables

- `TELEGRAM_BOT_TOKEN` - Bot token from @BotFather
- `ADMIN_ID` - Admin's Telegram user ID
- `DATABASE_URL` - PostgreSQL connection string (auto-set)
- `PORT` - Server port (5000)

## Deployment

- Uses webhooks (not polling) for Autoscale compatibility
- Flask serves both the web UI and webhook endpoint
- Production command: `python main.py`
