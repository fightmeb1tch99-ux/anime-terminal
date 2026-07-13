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
    Button {
        width: 100%;
        margin-top: 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Exit", show=True),
        Binding("l", "toggle_language", "Switch Language", show=True),
        Binding("b", "back", "Back", show=True),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.lang = LANG_RU
        self.search_results = []
        self.selected_anime = None
        self.selected_translation = None
        self.kodik = KodikSearch()

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main-container"):
            yield Label(self.lang["title"], classes="title-label")
            with ContentSwitcher(initial="search_view"):
                with Vertical(id="search_view"):
                    yield Input(placeholder=self.lang["search_placeholder"], id="search_input")
                    yield ListView(id="results_list")
                with Vertical(id="detail_view"):
                    yield Static(id="anime_info", classes="info-panel")
                    yield ListView(id="translation_list")
                with Vertical(id="episode_view"):
                    yield Label(self.lang["select_episode"], id="episode_label")
                    yield ListView(id="episode_list")
        yield Footer()

    def action_toggle_language(self) -> None:
        self.lang = LANG_EN if self.lang["current_lang"] == "ru" else LANG_RU
        self.refresh_ui()

    def refresh_ui(self) -> None:
        self.query_one(".title-label").update(self.lang["title"])
        self.query_one("#search_input").placeholder = self.lang["search_placeholder"]
        self.query_one("#episode_label").update(self.lang["select_episode"])
        # Update bindings labels if needed (textual handles some automatically)
        
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
            search_data = self.kodik.title(query).with_material_data().execute()
            self.search_results = search_data.results
            
            results_list.clear()
            if not self.search_results:
                results_list.append(ListItem(Label(self.lang["no_results"])))
                return

            # Filter to show unique anime titles (Kodik returns multiple for different translations)
            seen_shikimori = set()
            for item in self.search_results:
                sid = getattr(item, 'shikimori_id', None)
                if sid and sid not in seen_shikimori:
                    seen_shikimori.add(sid)
                    title = getattr(item, 'title', 'Unknown')
                    year = getattr(item, 'year', '????')
                    results_list.append(ListItem(Label(f"{title} ({year})"), id=f"anime_{sid}"))
        except Exception as e:
            results_list.clear()
            results_list.append(ListItem(Label(f"Error: {str(e)}")))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        list_id = event.list_view.id
        if list_id == "results_list":
            item_id = event.item.id
            if item_id and item_id.startswith("anime_"):
                shikimori_id = item_id.split("_")[1]
                self.show_anime_details(shikimori_id)
        elif list_id == "translation_list":
            translation_id = event.item.id.split("_")[1]
            self.show_episodes(translation_id)
        elif list_id == "episode_list":
            episode_num = event.item.id.split("_")[1]
            self.watch_episode(episode_num)

    def show_anime_details(self, shikimori_id: str) -> None:
        # Find all results for this shikimori_id to get translations
        self.selected_anime_results = [r for r in self.search_results if getattr(r, 'shikimori_id', None) == shikimori_id]
        if not self.selected_anime_results:
            return
            
        anime = self.selected_anime_results[0]
        self.selected_anime = anime
        
        info_text = f"[bold]{anime.title}[/bold]\n"
        if hasattr(anime, 'material_data') and anime.material_data:
            md = anime.material_data
            info_text += f"Status: {getattr(md, 'anime_status', 'N/A')}\n"
            info_text += f"Rating: {getattr(md, 'shikimori_rating', 'N/A')}\n"
            info_text += f"Description: {getattr(md, 'description', 'No description available.')[:200]}..."

        self.query_one("#anime_info").update(info_text)
        
        trans_list = self.query_one("#translation_list", ListView)
        trans_list.clear()
        
        # Get unique translations
        translations = {}
        for r in self.selected_anime_results:
            if hasattr(r, 'translation'):
                t = r.translation
                translations[t.id] = t.title

        for tid, ttitle in translations.items():
            trans_list.append(ListItem(Label(ttitle), id=f"trans_{tid}"))
            
        self.query_one(ContentSwitcher).current = "detail_view"

    def show_episodes(self, translation_id: str) -> None:
        # Find the specific result for this translation
        res = next((r for r in self.selected_anime_results if str(getattr(r.translation, 'id', '')) == translation_id), None)
        if not res:
            return
            
        self.selected_result = res
        ep_list = self.query_one("#episode_list", ListView)
        ep_list.clear()
        
        # Get episode info
        try:
            # We use the link to determine episodes or use the result data
            # Kodik results for serials usually have last_episode
            last_ep = int(getattr(res, 'last_episode', 1))
            for i in range(1, last_ep + 1):
                ep_list.append(ListItem(Label(f"Episode {i}"), id=f"ep_{i}"))
        except:
            ep_list.append(ListItem(Label("Episode 1"), id="ep_1"))
            
        self.query_one(ContentSwitcher).current = "episode_view"

    def watch_episode(self, episode_num: str) -> None:
        # Construct the URL with episode
        base_url = self.selected_result.link
        if "episode=" not in base_url:
            if "?" in base_url:
                url = f"{base_url}&episode={episode_num}"
            else:
                url = f"{base_url}?episode={episode_num}"
        else:
            url = base_url # already has episode or handled by player
            
        # Ensure protocol
        if url.startswith("//"):
            url = "https:" + url
            
        webbrowser.open(url)

    def action_back(self) -> None:
        current = self.query_one(ContentSwitcher).current
        if current == "episode_view":
            self.query_one(ContentSwitcher).current = "detail_view"
        elif current == "detail_view":
            self.query_one(ContentSwitcher).current = "search_view"

if __name__ == "__main__":
    app = AnimeTerminal()
    app.run()
