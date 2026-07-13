import os
import sys
import json
import webbrowser
import requests
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Static, ListView, ListItem, Label, Button, ContentSwitcher
from textual.containers import Container, Vertical, Horizontal
from textual.binding import Binding
from anime_parsers_ru import KodikSearch, KodikParser

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
        self.selected_anime = None
        self.selected_translation = None
        self.kodik = KodikSearch()
        self.current_episode_num = None

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
                        yield Button(self.lang["watch"], id="btn_watch", classes="-last")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#search_input").focus()

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
            # Using KodikSearch to find anime
            # Ensure to get a fresh token if not already obtained or expired
            if not self.kodik.token:
                self.kodik = KodikSearch(token=KodikParser.get_token())

            search_data = self.kodik.title(query).with_material_data().execute()
            self.search_results = search_data.results
            
            results_list.clear()
            if not self.search_results:
                results_list.append(ListItem(Label(self.lang["no_results"])))
                return

            # Filter to show unique anime titles (Kodik returns multiple for different translations)
            seen_shikimori = set()
            unique_anime_results = []
            for item in self.search_results:
                sid = getattr(item, 'shikimori_id', None)
                if sid and sid not in seen_shikimori:
                    seen_shikimori.add(sid)
                    unique_anime_results.append(item)
            
            self.search_results = unique_anime_results # Update search_results to only unique ones

            for idx, item in enumerate(self.search_results):
                title = getattr(item, 'title', 'Unknown')
                year = getattr(item, 'year', '????')
                results_list.append(ListItem(Label(f"{title} ({year})"), id=f"anime_{idx}"))
        except Exception as e:
            results_list.clear()
            results_list.append(ListItem(Label(f"Error: {str(e)}")))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        list_id = event.list_view.id
        if list_id == "results_list":
            item_id = event.item.id
            if item_id and item_id.startswith("anime_"):
                idx = int(item_id.split("_")[1])
                self.show_anime_details(self.search_results[idx])
        elif list_id == "translation_list":
            item_id = event.item.id
            if item_id and item_id.startswith("trans_"):
                translation_id = item_id.split("_")[1]
                self.show_episodes(translation_id)
        elif list_id == "episode_list":
            item_id = event.item.id
            if item_id and item_id.startswith("ep_"):
                self.current_episode_num = item_id.split("_")[1]
                # No automatic watch, user clicks button

    def show_anime_details(self, anime_item) -> None:
        self.selected_anime = anime_item
        
        info_text = f"[bold]{anime_item.title}[/bold]\n"
        if hasattr(anime_item, 'material_data') and anime_item.material_data:
            md = anime_item.material_data
            info_text += f"Status: {getattr(md, 'anime_status', 'N/A')}\n"
            info_text += f"Rating: {getattr(md, 'shikimori_rating', 'N/A')}\n"
            description = getattr(md, 'description', 'No description available.')
            info_text += f"Description: {description[:200]}{'...' if len(description) > 200 else ''}\n"

        self.query_one("#anime_info", Static).update(info_text)
        
        trans_list = self.query_one("#translation_list", ListView)
        trans_list.clear()
        
        # Get all results for the selected anime's shikimori_id to find all translations
        all_translations_for_anime = [r for r in self.search_results if getattr(r, 'shikimori_id', None) == getattr(anime_item, 'shikimori_id', None)]
        
        unique_translations = {}
        for r in all_translations_for_anime:
            if hasattr(r, 'translation') and r.translation:
                unique_translations[r.translation.id] = r.translation.title

        for tid, ttitle in unique_translations.items():
            trans_list.append(ListItem(Label(ttitle), id=f"trans_{tid}"))
            
        self.query_one("#main_switcher").current = "detail_view"

    def show_episodes(self, translation_id: str) -> None:
        # Find the specific result for this translation
        self.selected_translation = translation_id
        res = next((r for r in self.search_results if 
                    getattr(r, 'shikimori_id', None) == getattr(self.selected_anime, 'shikimori_id', None) and 
                    str(getattr(r.translation, 'id', '')) == translation_id), None)
        if not res:
            return
            
        self.selected_result_with_translation = res
        ep_list = self.query_one("#episode_list", ListView)
        ep_list.clear()
        
        # Get episode info
        try:
            last_ep = int(getattr(res, 'last_episode', 1))
            for i in range(1, last_ep + 1):
                ep_list.append(ListItem(Label(f"Episode {i}"), id=f"ep_{i}"))
        except Exception:
            ep_list.append(ListItem(Label("Episode 1"), id="ep_1")) # Fallback if no episode info
            
        self.query_one("#main_switcher").current = "episode_view"

    def watch_episode(self, episode_num: str) -> None:
        if not self.selected_result_with_translation:
            return

        base_url = self.selected_result_with_translation.link
        if not base_url:
            return

        url = base_url
        # Kodik links often contain episode= parameter, update it or add it
        if "episode=" in url:
            url = requests.utils.url_replace(url, "episode", episode_num)
        else:
            separator = "?" if "?" not in url else "&"
            url = f"{url}{separator}episode={episode_num}"
            
        # Ensure protocol
        if url.startswith("//"):
            url = "https:" + url
            
        webbrowser.open(url)

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

if __name__ == "__main__":
    app = AnimeTerminal()
    app.run()
