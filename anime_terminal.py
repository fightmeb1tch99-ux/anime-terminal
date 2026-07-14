import os
import sys
import json
import webbrowser
import requests
import re
import asyncio
import subprocess
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Static, ListView, ListItem, Label, Button, ContentSwitcher, ProgressBar
from textual.containers import Container, Vertical, Horizontal
from textual.binding import Binding
from anime_parsers_ru import KodikSearch, KodikParser, KodikParserAsync

# Constants for Localization
LANG_RU = {
    "title": "Аниме Терминал",
    "search_placeholder": "Введите название аниме...",
    "searching": "Поиск...",
    "no_results": "Ничего не найдено.",
    "select_translation": "Выберите озвучку:",
    "select_episode": "Выберите серию:",
    "watch": "Смотреть в браузере",
    "download": "Скачать серию",
    "downloads": "Загрузки",
    "play_local": "Воспроизвести локально",
    "back": "Назад",
    "exit": "Выход",
    "help": "Помощь",
    "switch_lang": "Switch to English",
    "current_lang": "ru",
    "downloading": "Загрузка...",
    "download_complete": "Загрузка завершена!",
    "download_failed": "Ошибка загрузки.",
    "no_downloads": "Нет загруженных серий."
}

LANG_EN = {
    "title": "Anime Terminal",
    "search_placeholder": "Enter anime title...",
    "searching": "Searching...",
    "no_results": "No results found.",
    "select_translation": "Select translation:",
    "select_episode": "Select episode:",
    "watch": "Watch in Browser",
    "download": "Download Episode",
    "downloads": "Downloads",
    "play_local": "Play Local",
    "back": "Back",
    "exit": "Exit",
    "help": "Help",
    "switch_lang": "Переключить на Русский",
    "current_lang": "en",
    "downloading": "Downloading...",
    "download_complete": "Download complete!",
    "download_failed": "Download failed.",
    "no_downloads": "No downloaded episodes."
}

DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "anime-terminal-downloads")

class AnimeTerminal(App):
    CSS = """
    Screen {
        background: #1a1b26;
        color: #c0caf5;
    }
    #main-container {
        padding: 1 2;
    }
    .title-label {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: #7aa2f7;
        margin-bottom: 1;
    }
    Input {
        border: tall #414868;
        background: #24283b;
        color: #c0caf5;
    }
    Input:focus {
        border: tall #7aa2f7;
    }
    ListView {
        background: #24283b;
        border: tall #414868;
        height: 1fr;
        margin-top: 1;
    }
    ListItem {
        padding: 0 1;
    }
    ListItem:hover {
        background: #414868;
    }
    ListItem.--highlight {
        background: #7aa2f7;
        color: #1a1b26;
    }
    .info-panel {
        background: #24283b;
        border: tall #414868;
        padding: 1;
        margin-top: 1;
    }
    .button-container {
        width: 100%;
        margin-top: 1;
        height: auto;
    }
    .button-container Button {
        width: 1fr;
        margin-left: 1;
        margin-right: 1;
    }
    .button-container Button.-first {
        margin-left: 0;
    }
    .button-container Button.-last {
        margin-right: 0;
    }
    #download_progress {
        width: 100%;
        height: 1;
        margin-top: 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Exit", show=False),
        Binding("l", "toggle_language", "Switch Language", show=False),
        Binding("b", "back", "Back", show=False),
        Binding("d", "show_downloads", "Downloads", show=False),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.lang = LANG_RU
        self.search_results = []
        self.unique_anime_results = []
        self.selected_anime = None
        self.selected_translation_id = None
        self.kodik = KodikSearch()
        self.current_episode_num = None
        self.selected_result_with_translation = None
        self.translations_for_selected_anime = []
        self.episodes_for_selected_translation = []
        self.kodik_parser_async = KodikParserAsync()
        self.downloaded_files = []

    async def on_mount(self) -> None:
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        self.query_one("#search_input").focus()
        try:
            token = await self.kodik_parser_async.get_token()
            self.kodik = KodikSearch(token=token)
        except Exception as e:
            self.notify(f"Failed to get Kodik token: {e}", title="Error")

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main-container"):
            yield Label(self.lang["title"], classes="title-label")
            with ContentSwitcher(initial="search_view", id="main_switcher"):
                with Vertical(id="search_view"):
                    yield Input(placeholder=self.lang["search_placeholder"], id="search_input")
                    yield ListView(id="results_list")
                    with Horizontal(classes="button-container"):
                        yield Button(self.lang["switch_lang"], id="btn_switch_lang", classes="-first")
                        yield Button(self.lang["downloads"], id="btn_show_downloads")
                        yield Button(self.lang["exit"], id="btn_exit", classes="-last")
                with Vertical(id="detail_view"):
                    yield Static(id="anime_info", classes="info-panel")
                    yield ListView(id="translation_list")
                    with Horizontal(classes="button-container"):
                        yield Button(self.lang["back"], id="btn_back_detail", classes="-first")
                        yield Button(self.lang["switch_lang"], id="btn_switch_lang_detail")
                        yield Button(self.lang["exit"], id="btn_exit_detail", classes="-last")
                with Vertical(id="episode_view"):
                    yield Label(self.lang["select_episode"], id="episode_label")
                    yield ListView(id="episode_list")
                    with Horizontal(classes="button-container"):
                        yield Button(self.lang["back"], id="btn_back_episode", classes="-first")
                        yield Button(self.lang["download"], id="btn_download_episode")
                        yield Button(self.lang["watch"], id="btn_watch", classes="-last")
                with Vertical(id="downloads_view"):
                    yield Label(self.lang["downloads"], classes="title-label")
                    yield ListView(id="downloaded_list")
                    with Horizontal(classes="button-container"):
                        yield Button(self.lang["back"], id="btn_back_downloads", classes="-first")
                        yield Button(self.lang["play_local"], id="btn_play_local", classes="-last")
        yield Footer()

    def action_toggle_language(self) -> None:
        self.lang = LANG_EN if self.lang["current_lang"] == "ru" else LANG_RU
        self.refresh_ui()

    def refresh_ui(self) -> None:
        self.query_one(".title-label").update(self.lang["title"])
        self.query_one("#search_input", Input).placeholder = self.lang["search_placeholder"]
        self.query_one("#episode_label", Label).update(self.lang["select_episode"])
        self.query_one("#downloads_view .title-label", Label).update(self.lang["downloads"])
        
        # Update button texts
        self.query_one("#btn_switch_lang", Button).label = self.lang["switch_lang"]
        self.query_one("#btn_show_downloads", Button).label = self.lang["downloads"]
        self.query_one("#btn_exit", Button).label = self.lang["exit"]
        
        self.query_one("#btn_back_detail", Button).label = self.lang["back"]
        self.query_one("#btn_switch_lang_detail", Button).label = self.lang["switch_lang"]
        self.query_one("#btn_exit_detail", Button).label = self.lang["exit"]
        
        self.query_one("#btn_back_episode", Button).label = self.lang["back"]
        self.query_one("#btn_download_episode", Button).label = self.lang["download"]
        self.query_one("#btn_watch", Button).label = self.lang["watch"]

        self.query_one("#btn_back_downloads", Button).label = self.lang["back"]
        self.query_one("#btn_play_local", Button).label = self.lang["play_local"]

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search_input":
            query = event.value.strip()
            if query:
                await self.perform_search(query)

    async def perform_search(self, query: str) -> None:
        results_list = self.query_one("#results_list", ListView)
        results_list.clear()
        results_list.append(ListItem(Label(self.lang["searching"])))
        
        try:
            if not self.kodik.token:
                try:
                    token = await self.kodik_parser_async.get_token()
                    self.kodik = KodikSearch(token=token)
                except Exception as token_e:
                    results_list.clear()
                    results_list.append(ListItem(Label(f"Error getting Kodik token: {str(token_e)}")))
                    return

            search_data = await self.kodik.title(query).with_material_data().execute_async()
            self.search_results = search_data.results
            
            results_list.clear()
            if not self.search_results:
                results_list.append(ListItem(Label(self.lang["no_results"])))
                return

            seen_shikimori = set()
            self.unique_anime_results = []
            for item in self.search_results:
                sid = getattr(item, 'shikimori_id', None)
                if sid and sid not in seen_shikimori:
                    seen_shikimori.add(sid)
                    self.unique_anime_results.append(item)
            
            for item in self.unique_anime_results:
                title = getattr(item, 'title', 'Unknown')
                year = getattr(item, 'year', '????')
                results_list.append(ListItem(Label(f"{title} ({year})")))
        except Exception as e:
            results_list.clear()
            results_list.append(ListItem(Label(f"Error during search: {str(e)}")))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        list_id = event.list_view.id
        if list_id == "results_list":
            selected_index = event.item.index
            if 0 <= selected_index < len(self.unique_anime_results):
                self.show_anime_details(self.unique_anime_results[selected_index])
        elif list_id == "translation_list":
            selected_index = event.item.index
            if 0 <= selected_index < len(self.translations_for_selected_anime):
                translation_id = self.translations_for_selected_anime[selected_index][0] # (id, title)
                self.show_episodes(translation_id)
        elif list_id == "episode_list":
            selected_index = event.item.index
            if 0 <= selected_index < len(self.episodes_for_selected_translation):
                self.current_episode_num = str(self.episodes_for_selected_translation[selected_index])
                # Do not auto-watch, wait for button press for download/watch
        elif list_id == "downloaded_list":
            selected_index = event.item.index
            if 0 <= selected_index < len(self.downloaded_files):
                self.play_local_file(self.downloaded_files[selected_index])

    def show_anime_details(self, anime_item) -> None:
        self.selected_anime = anime_item
        
        info_text = f"[bold]{anime_item.title}[/bold]\n"
        if hasattr(anime_item, 'material_data') and anime_item.material_data:
            md = anime_item.material_data
            info_text += f"Status: {getattr(md, 'anime_status', 'N/A')}\n"
            info_text += f"Rating: {getattr(md, 'shikimori_rating', 'N/A')}\n"
            description = getattr(md, 'description', 'No description available.')
            info_text += f"Description: {description[:200]}{\'...\' if len(description) > 200 else ''}\n"

        self.query_one("#anime_info", Static).update(info_text)
        
        trans_list = self.query_one("#translation_list", ListView)
        trans_list.clear()
        
        all_translations_for_anime = [r for r in self.search_results if getattr(r, 'shikimori_id', None) == getattr(anime_item, 'shikimori_id', None)]
        
        unique_translations = {}
        for r in all_translations_for_anime:
            if hasattr(r, 'translation') and r.translation:
                unique_translations[r.translation.id] = r.translation.title

        self.translations_for_selected_anime = sorted(unique_translations.items(), key=lambda item: item[1])

        for tid, ttitle in self.translations_for_selected_anime:
            trans_list.append(ListItem(Label(ttitle)))
            
        self.query_one("#main_switcher").current = "detail_view"

    def show_episodes(self, translation_id: str) -> None:
        self.selected_translation_id = translation_id
        res = next((r for r in self.search_results if 
                    getattr(r, 'shikimori_id', None) == getattr(self.selected_anime, 'shikimori_id', None) and 
                    str(getattr(r.translation, 'id', '')) == translation_id), None)
        if not res:
            return
            
        self.selected_result_with_translation = res
        ep_list = self.query_one("#episode_list", ListView)
        ep_list.clear()
        
        self.episodes_for_selected_translation = []
        try:
            last_ep = int(getattr(res, 'last_episode', 1))
            for i in range(1, last_ep + 1):
                self.episodes_for_selected_translation.append(i)
                ep_list.append(ListItem(Label(f"Episode {i}")))
        except Exception:
            self.episodes_for_selected_translation.append(1)
            ep_list.append(ListItem(Label("Episode 1"))) # Fallback if no episode info
            
        self.query_one("#main_switcher").current = "episode_view"

    def watch_episode(self, episode_num: str) -> None:
        if not self.selected_result_with_translation:
            self.notify("No anime selected to watch.", title="Error")
            return

        base_url = self.selected_result_with_translation.link
        if not base_url:
            self.notify("No streaming link available for this anime.", title="Error")
            return

        # Ensure protocol
        if base_url.startswith("//"):
            base_url = "https:" + base_url
        elif not base_url.startswith("http://") and not base_url.startswith("https://"):
            base_url = "https://" + base_url # Default to https if no protocol

        # Use urllib.parse for robust URL parameter manipulation
        parsed_url = urlparse(base_url)
        query_params = parse_qs(parsed_url.query)
        query_params['episode'] = [episode_num] # Set or update episode parameter
        new_query = urlencode(query_params, doseq=True)
        
        url = urlunparse(parsed_url._replace(query=new_query))
            
        try:
            webbrowser.open(url)
            self.notify(f"Opening episode {episode_num} in browser...", title="Watching Anime")
        except Exception as e:
            self.notify(f"Failed to open browser: {str(e)}", title="Error")

    async def download_episode(self, episode_num: str) -> None:
        if not self.selected_result_with_translation:
            self.notify("No anime selected to download.", title="Error")
            return

        base_url = self.selected_result_with_translation.link
        if not base_url:
            self.notify("No streaming link available for this anime.", title="Error")
            return

        if base_url.startswith("//"):
            base_url = "https:" + base_url
        elif not base_url.startswith("http://") and not base_url.startswith("https://"):
            base_url = "https://" + base_url

        parsed_url = urlparse(base_url)
        query_params = parse_qs(parsed_url.query)
        query_params['episode'] = [episode_num]
        new_query = urlencode(query_params, doseq=True)
        download_url = urlunparse(parsed_url._replace(query=new_query))

        anime_title = getattr(self.selected_anime, 'title', 'Unknown_Anime').replace(' ', '_').replace('/', '-')
        translation_title = next((t[1] for t in self.translations_for_selected_anime if t[0] == self.selected_translation_id), 'Unknown_Translation').replace(' ', '_').replace('/', '-')
        filename = f"{anime_title}_S01E{episode_num}_{translation_title}.mp4"
        output_path = os.path.join(DOWNLOAD_DIR, filename)

        self.notify(self.lang["downloading"], title="Download")
        try:
            # Using yt-dlp to download the video
            # -o for output template, --no-part to prevent .part files
            command = [sys.executable, '-m', 'yt_dlp', '-o', output_path, download_url]
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                self.notify(self.lang["download_complete"], title="Download")
                self.action_show_downloads() # Refresh downloads list
            else:
                self.notify(f"{self.lang['download_failed']}: {stderr.decode()}", title="Download Error")
        except FileNotFoundError:
            self.notify("yt-dlp not found. Please install it (pip install yt-dlp).", title="Error")
        except Exception as e:
            self.notify(f"{self.lang['download_failed']}: {str(e)}", title="Download Error")

    def action_show_downloads(self) -> None:
        self.downloaded_files = []
        downloaded_list = self.query_one("#downloaded_list", ListView)
        downloaded_list.clear()

        if not os.path.exists(DOWNLOAD_DIR):
            os.makedirs(DOWNLOAD_DIR)

        for filename in os.listdir(DOWNLOAD_DIR):
            if filename.endswith(('.mp4', '.mkv', '.avi', '.webm')):
                self.downloaded_files.append(os.path.join(DOWNLOAD_DIR, filename))
        
        if not self.downloaded_files:
            downloaded_list.append(ListItem(Label(self.lang["no_downloads"])))
        else:
            for f_path in self.downloaded_files:
                downloaded_list.append(ListItem(Label(os.path.basename(f_path))))
        
        self.query_one("#main_switcher").current = "downloads_view"

    def play_local_file(self, file_path: str) -> None:
        try:
            # Attempt to play with mpv, fallback to vlc or default opener
            if sys.platform == "win32":
                os.startfile(file_path)
            elif sys.platform == "darwin":
                subprocess.Popen(['open', file_path])
            else: # Linux, Termux
                # Check for mpv first
                try:
                    subprocess.Popen(['mpv', file_path])
                except FileNotFoundError:
                    # Fallback to vlc
                    try:
                        subprocess.Popen(['vlc', file_path])
                    except FileNotFoundError:
                        self.notify("No local player (mpv/vlc) found. Please install one.", title="Error")

            self.notify(f"Playing {os.path.basename(file_path)} locally.", title="Local Playback")
        except Exception as e:
            self.notify(f"Failed to play local file: {str(e)}", title="Error")

    def action_back(self) -> None:
        current = self.query_one("#main_switcher", ContentSwitcher).current
        if current == "episode_view":
            self.query_one("#main_switcher").current = "detail_view"
        elif current == "detail_view":
            self.query_one("#main_switcher").current = "search_view"
        elif current == "downloads_view":
            self.query_one("#main_switcher").current = "search_view"

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_exit" or event.button.id == "btn_exit_detail":
            self.exit()
        elif event.button.id == "btn_switch_lang" or event.button.id == "btn_switch_lang_detail":
            self.action_toggle_language()
        elif event.button.id == "btn_back_detail" or event.button.id == "btn_back_episode" or event.button.id == "btn_back_downloads":
            self.action_back()
        elif event.button.id == "btn_watch":
            if self.current_episode_num:
                self.watch_episode(self.current_episode_num)
            else:
                self.watch_episode("1")
        elif event.button.id == "btn_download_episode":
            if self.current_episode_num:
                await self.download_episode(self.current_episode_num)
            else:
                self.notify("Please select an episode to download.", title="Error")
        elif event.button.id == "btn_show_downloads":
            self.action_show_downloads()
        elif event.button.id == "btn_play_local":
            # Play selected downloaded file
            downloaded_list = self.query_one("#downloaded_list", ListView)
            if downloaded_list.highlighted is not None and 0 <= downloaded_list.highlighted < len(self.downloaded_files):
                self.play_local_file(self.downloaded_files[downloaded_list.highlighted])
            else:
                self.notify("Please select a downloaded episode to play.", title="Error")

    async def on_quit(self) -> None:
        await self.kodik_parser_async.close_async_session()

if __name__ == "__main__":
    app = AnimeTerminal()
    app.run()
