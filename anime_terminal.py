import os
import sys
import json
import webbrowser
import requests
import re
import asyncio # Import asyncio
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Static, ListView, ListItem, Label, Button, ContentSwitcher
from textual.containers import Container, Vertical, Horizontal
from textual.binding import Binding
from anime_parsers_ru import KodikSearch, KodikParser, KodikParserAsync # Import KodikParserAsync

# Constants for Localization
LANG_RU = {
    "title": "Аниме Терминал",
    "search_placeholder": "Введите название аниме...",
    "searching": "Поиск...",
    "no_results": "Ничего не найдено.",
    "select_translation": "Выберите озвучку:",
    "select_episode": "Выберите серию:",
    "watch": "Смотреть в браузере",
    "back": "Назад",
    "exit": "Выход",
    "help": "Помощь",
    "switch_lang": "Switch to English",
    "current_lang": "ru"
}

LANG_EN = {
    "title": "Anime Terminal",
    "search_placeholder": "Enter anime title...",
    "searching": "Searching...",
    "no_results": "No results found.",
    "select_translation": "Select translation:",
    "select_episode": "Select episode:",
    "watch": "Watch in Browser",
    "back": "Back",
    "exit": "Exit",
    "help": "Help",
    "switch_lang": "Переключить на Русский",
    "current_lang": "en"
}

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
    """

    BINDINGS = [
        Binding("q", "quit", "Exit", show=False),
        Binding("l", "toggle_language", "Switch Language", show=False),
        Binding("b", "back", "Back", show=False),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.lang = LANG_RU
        self.search_results = []
        self.unique_anime_results = [] # Store unique anime for selection
        self.selected_anime = None
        self.selected_translation_id = None
        self.kodik = KodikSearch()
        self.current_episode_num = None
        self.selected_result_with_translation = None # Store the full result object for watching
        self.translations_for_selected_anime = [] # Store translations for the selected anime
        self.episodes_for_selected_translation = [] # Store episodes for the selected translation
        self.kodik_parser_async = KodikParserAsync() # Initialize async parser

    async def on_mount(self) -> None:
        self.query_one("#search_input").focus()
        # Attempt to get token asynchronously on mount
        try:
            token = await self.kodik_parser_async.get_token()
            self.kodik = KodikSearch(token=token)
        except Exception as e:
            self.notify(f"Failed to get Kodik token: {e}", title="Error")

    def action_toggle_language(self) -> None:
        self.lang = LANG_EN if self.lang["current_lang"] == "ru" else LANG_RU
        self.refresh_ui()

    def refresh_ui(self) -> None:
        self.query_one(".title-label").update(self.lang["title"])
        self.query_one("#search_input", Input).placeholder = self.lang["search_placeholder"]
        self.query_one("#episode_label", Label).update(self.lang["select_episode"])
        
        # Update button texts
        self.query_one("#btn_switch_lang", Button).label = self.lang["switch_lang"]
        self.query_one("#btn_exit", Button).label = self.lang["exit"]
        self.query_one("#btn_back_detail", Button).label = self.lang["back"]
        self.query_one("#btn_switch_lang_detail", Button).label = self.lang["switch_lang"]
        self.query_one("#btn_exit_detail", Button).label = self.lang["exit"]
        self.query_one("#btn_back_episode", Button).label = self.lang["back"]
        self.query_one("#btn_watch", Button).label = self.lang["watch"]

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

            # Use execute_async for non-blocking API call
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
                self.watch_episode(self.current_episode_num) # Automatically watch on selection

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

    def action_back(self) -> None:
        current = self.query_one("#main_switcher", ContentSwitcher).current
        if current == "episode_view":
            self.query_one("#main_switcher").current = "detail_view"
        elif current == "detail_view":
            self.query_one("#main_switcher").current = "search_view"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_exit" or event.button.id == "btn_exit_detail":
            self.exit()
        elif event.button.id == "btn_switch_lang" or event.button.id == "btn_switch_lang_detail":
            self.action_toggle_language()
        elif event.button.id == "btn_back_detail" or event.button.id == "btn_back_episode":
            self.action_back()
        elif event.button.id == "btn_watch":
            if self.current_episode_num:
                self.watch_episode(self.current_episode_num)
            else:
                # If no specific episode selected, try to watch the first one or default
                self.watch_episode("1")

    async def on_quit(self) -> None:
        await self.kodik_parser_async.close_async_session()

if __name__ == "__main__":
    app = AnimeTerminal()
    app.run()
