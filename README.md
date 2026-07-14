# Anime Terminal / Аниме Терминал

A modern, fast, and convenient Terminal UI (TUI) for searching, watching, and downloading anime. Works on Linux, Termux, and any terminal with Python support.

Современный, быстрый и удобный интерфейс для терминала (TUI) для поиска, просмотра и загрузки аниме. Работает на Linux, Termux и в любом терминале с поддержкой Python.

## Features / Особенности

- 🔍 **Fast Search**: Find your favorite anime in seconds. / **Быстрый поиск**: Найдите любимое аниме за считанные секунды.
- 🌍 **Bilingual**: Supports both Russian and English interfaces. / **Двуязычный**: Поддержка русского и английского интерфейсов.
- 🎬 **Smooth TUI**: Built with `Textual` for a smooth and adaptive experience. / **Плавный TUI**: Создан на базе `Textual` для плавности и адаптивности.
- 📱 **Cross-platform**: Works on Linux, macOS, and Termux (Android). / **Кроссплатформенность**: Работает на Linux, macOS и Termux (Android).
- 🔊 **Translation Choice**: Select your favorite voice acting or subtitles. / **Выбор озвучки**: Выбирайте любимую озвучку или субтитры.
- 💾 **Offline Mode**: Download episodes and watch them locally. / **Оффлайн-режим**: Скачивайте серии и смотрите их локально.

## Installation / Установка

### Prerequisites / Предварительные условия
- Python 3.10+
- `pip`
- `yt-dlp` (for downloading episodes) / `yt-dlp` (для загрузки серий)
- `mpv` or `vlc` (for local playback) / `mpv` или `vlc` (для локального воспроизведения)

### Steps / Шаги

1.  **Clone the repository / Клонируйте репозиторий**:
    ```bash
    git clone https://github.com/fightmeb1tch99-ux/anime-terminal.git
    cd anime-terminal
    ```

2.  **Install Python dependencies / Установите зависимости Python**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Install `yt-dlp` (if not already installed) / Установите `yt-dlp` (если еще не установлен)**:
    ```bash
    pip install yt-dlp
    # Or via package manager on Linux/Termux:
    # sudo apt install yt-dlp (Linux)
    # pkg install yt-dlp (Termux)
    ```

4.  **Install a local video player (e.g., `mpv` or `vlc`) / Установите локальный видеоплеер (например, `mpv` или `vlc`)**:
    ```bash
    # On Linux:
    # sudo apt install mpv
    # sudo apt install vlc
    # On Termux:
    # pkg install mpv
    # pkg install vlc
    ```

5.  **Run the app / Запустите приложение**:
    ```bash
    python anime_terminal.py
    ```

## Keybindings / Горячие клавиши

- `Q`: Exit / Выход
- `L`: Switch Language / Переключить язык
- `B`: Go Back / Назад
- `D`: Show Downloads / Показать Загрузки
- `Enter`: Select/Search / Выбрать/Поиск

## Requirements / Зависимости
- `textual`
- `anime-parsers-ru`
- `requests`
- `yt-dlp`

---
*Created with ❤️ for the Anime community.*
