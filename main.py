import os
import sqlite3
from functools import partial
from datetime import datetime
import shutil
import random

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.video import Video
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.clock import Clock
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import AsyncImage
from kivy.uix.carousel import Carousel
from kivy.core.window import Window
from kivy.properties import BooleanProperty, NumericProperty, StringProperty, ObjectProperty
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.behaviors import FocusBehavior

# Database Setup
db_path = os.path.join(os.path.dirname(__file__), "amazstreme.db")
conn = sqlite3.connect(db_path, check_same_thread=False)
cursor = conn.cursor()

# Create tables
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT,
        avatar_path TEXT,
        bio TEXT DEFAULT ''
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS videos (
        id INTEGER PRIMARY KEY,
        title TEXT,
        file_path TEXT,
        uploader_id INTEGER,
        likes INTEGER DEFAULT 0,
        category TEXT DEFAULT 'General',
        tags TEXT DEFAULT '',
        duration INTEGER DEFAULT 0,
        FOREIGN KEY (uploader_id) REFERENCES users (id)
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY,
        video_id INTEGER,
        user_id INTEGER,
        text TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (video_id) REFERENCES videos (id),
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS subscriptions (
        user_id INTEGER,
        channel_name TEXT,
        PRIMARY KEY (user_id, channel_name),
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS watch_history (
        user_id INTEGER,
        video_id INTEGER,
        progress INTEGER DEFAULT 0,
        last_watched DATETIME DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, video_id),
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (video_id) REFERENCES videos (id)
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS downloads (
        user_id INTEGER,
        video_id INTEGER,
        download_path TEXT,
        downloaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, video_id),
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (video_id) REFERENCES videos (id)
    )
''')

conn.commit()

class ChatMessage(BoxLayout):
    text = StringProperty("")
    sender = StringProperty("")
    timestamp = StringProperty("")
    is_user = BooleanProperty(False)

class ChatRecycleView(RecycleView):
    def __init__(self, **kwargs):
        super(ChatRecycleView, self).__init__(**kwargs)
        self.data = []

class RaikunAI:
    def __init__(self):
        self.name = "Raikun"
        self.responses = {
            "hello": "Hello! I'm Raikun, your AI assistant. How can I help you today?",
            "how are you": "I'm just a program, but thanks for asking! How can I assist you?",
            "recommend": "Based on your watch history, I recommend checking out the Tech category videos!",
            "help": "I can help with video recommendations, app navigation, and general questions about the app.",
            "settings": "You can change app settings like dark mode, playback speed, and ads in the Settings tab.",
            "subscribe": "To subscribe to a channel, go to the video and click the Subscribe button below it.",
            "download": "You can download videos by clicking the download button when watching a video.",
            "history": "Your watch history is available in your Profile tab under Watch History.",
            "default": "I'm not sure I understand. Could you rephrase that or ask something else?"
        }
    
    def respond(self, message):
        message = message.lower().strip()
        for key in self.responses:
            if key in message:
                return self.responses[key]
        return self.responses["default"]

class AmazonVideoApp(App):
    dark_mode = BooleanProperty(False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_user = None
        self.user_data = {
            "ads_enabled": True,
            "earnings": 0,
            "donations": 0,
            "memberships": 0,
            "play_speed": 1.0,
            "likes": {},
            "watch_history": [],
            "downloads": [],
            "notifications": []
        }
        
        self.channels = {
            "TechReviews": {
                "logo": "https://via.placeholder.com/100x100?text=Tech",
                "videos": ["Tech Review", "New Gadgets Unboxing", "Smartphone Comparison"]
            },
            "NatureChannel": {
                "logo": "https://via.placeholder.com/100x100?text=Nature",
                "videos": ["Nature Documentary", "Wildlife Adventures", "Ocean Exploration"]
            },
            "UserUploads": {
                "logo": "https://via.placeholder.com/100x100?text=User",
                "videos": []
            }
        }
        self.selected_video_path = None
        self.current_playing_video = None
        self.video_progress = 0
        self.downloads_dir = "downloads"
        
        # Create directories if they don't exist
        os.makedirs(self.downloads_dir, exist_ok=True)
        os.makedirs("videos", exist_ok=True)

    def build(self):
        Window.size = (800, 600)
        self.apply_theme()
        self.layout = BoxLayout(orientation='vertical')
        self.show_login_screen()
        return self.layout

    def apply_theme(self):
        if self.dark_mode:
            Window.clearcolor = (0.1, 0.1, 0.1, 1)
        else:
            Window.clearcolor = (1, 1, 1, 1)

    def show_login_screen(self):
        self.layout.clear_widgets()
        
        login_layout = BoxLayout(orientation='vertical', padding=50, spacing=20)
        
        title = Label(text="Amazstreme", font_size=32, color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1))
        login_layout.add_widget(title)
        
        self.login_username = TextInput(
            hint_text="Username", 
            size_hint=(1, None), 
            height=40,
            background_color=(1, 1, 1, 1) if not self.dark_mode else (0.2, 0.2, 0.2, 1),
            foreground_color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
        )
        login_layout.add_widget(self.login_username)
        
        self.login_password = TextInput(
            hint_text="Password", 
            password=True, 
            size_hint=(1, None), 
            height=40,
            background_color=(1, 1, 1, 1) if not self.dark_mode else (0.2, 0.2, 0.2, 1),
            foreground_color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
        )
        login_layout.add_widget(self.login_password)
        
        btn_layout = BoxLayout(spacing=10, size_hint=(1, None), height=40)
        login_btn = Button(text="Login")
        login_btn.bind(on_press=self.login)
        btn_layout.add_widget(login_btn)
        
        signup_btn = Button(text="Sign Up")
        signup_btn.bind(on_press=self.show_signup_screen)
        btn_layout.add_widget(signup_btn)
        
        login_layout.add_widget(btn_layout)
        self.layout.add_widget(login_layout)

    def show_signup_screen(self, instance):
        self.layout.clear_widgets()
        
        signup_layout = BoxLayout(orientation='vertical', padding=50, spacing=20)
        
        title = Label(text="Create Account", font_size=32, color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1))
        signup_layout.add_widget(title)
        
        self.signup_username = TextInput(
            hint_text="Username", 
            size_hint=(1, None), 
            height=40,
            background_color=(1, 1, 1, 1) if not self.dark_mode else (0.2, 0.2, 0.2, 1),
            foreground_color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
        )
        signup_layout.add_widget(self.signup_username)
        
        self.signup_password = TextInput(
            hint_text="Password", 
            password=True, 
            size_hint=(1, None), 
            height=40,
            background_color=(1, 1, 1, 1) if not self.dark_mode else (0.2, 0.2, 0.2, 1),
            foreground_color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
        )
        signup_layout.add_widget(self.signup_password)
        
        btn_layout = BoxLayout(spacing=10, size_hint=(1, None), height=40)
        create_btn = Button(text="Create Account")
        create_btn.bind(on_press=self.signup)
        btn_layout.add_widget(create_btn)
        
        back_btn = Button(text="Back")
        back_btn.bind(on_press=lambda x: self.show_login_screen())
        btn_layout.add_widget(back_btn)
        
        signup_layout.add_widget(btn_layout)
        self.layout.add_widget(signup_layout)

    def login(self, instance):
        username = self.login_username.text
        password = self.login_password.text
        
        try:
            cursor.execute("SELECT id, avatar_path, bio FROM users WHERE username=? AND password=?", (username, password))
            user = cursor.fetchone()
            
            if user:
                self.current_user = user[0]
                self.user_data["avatar_path"] = user[1]
                self.user_data["bio"] = user[2] if user[2] else ""
                self.load_user_data()
                self.create_main_screen()
            else:
                self.show_info_popup("Invalid username or password")
        except Exception as e:
            self.show_info_popup(f"Login error: {str(e)}")

    def load_user_data(self):
        """Load user-specific data from database"""
        try:
            # Load subscriptions
            cursor.execute("SELECT channel_name FROM subscriptions WHERE user_id=?", (self.current_user,))
            self.user_data["subscriptions"] = [row[0] for row in cursor.fetchall()]
            
            # Add default subscription if none exists
            if not self.user_data["subscriptions"]:
                self.user_data["subscriptions"] = ["TechReviews"]
                for channel in self.user_data["subscriptions"]:
                    cursor.execute(
                        "INSERT OR IGNORE INTO subscriptions (user_id, channel_name) VALUES (?, ?)",
                        (self.current_user, channel)
                    )
                conn.commit()

            # Load watch history
            cursor.execute('''
                SELECT v.id, v.title, wh.progress, v.duration 
                FROM watch_history wh
                JOIN videos v ON wh.video_id = v.id
                WHERE wh.user_id = ?
                ORDER BY wh.last_watched DESC
            ''', (self.current_user,))
            self.user_data["watch_history"] = [
                {"id": row[0], "title": row[1], "progress": row[2], "duration": row[3]}
                for row in cursor.fetchall()
            ]

            # Load downloads
            cursor.execute('''
                SELECT v.id, v.title, d.download_path
                FROM downloads d
                JOIN videos v ON d.video_id = v.id
                WHERE d.user_id = ?
            ''', (self.current_user,))
            self.user_data["downloads"] = [
                {"id": row[0], "title": row[1], "path": row[2]}
                for row in cursor.fetchall()
            ]
        except Exception as e:
            self.show_info_popup(f"Error loading user data: {str(e)}")

    def signup(self, instance):
        username = self.signup_username.text
        password = self.signup_password.text
        
        if not username or not password:
            self.show_info_popup("Please enter both username and password")
            return
        
        try:
            # Default avatar path
            avatar_path = "https://via.placeholder.com/100x100?text=User"
            
            cursor.execute(
                "INSERT INTO users (username, password, avatar_path) VALUES (?, ?, ?)", 
                (username, password, avatar_path)
            )
            user_id = cursor.lastrowid
            conn.commit()
            
            # Add default subscriptions
            for channel in ["TechReviews"]:
                cursor.execute(
                    "INSERT INTO subscriptions (user_id, channel_name) VALUES (?, ?)",
                    (user_id, channel)
                )
            conn.commit()
            
            self.show_info_popup("Account created successfully!")
            self.show_login_screen()
        except sqlite3.IntegrityError:
            self.show_info_popup("Username already exists")
        except Exception as e:
            self.show_info_popup(f"Signup error: {str(e)}")

    def create_main_screen(self):
        self.layout.clear_widgets()
        self.tab_panel = TabbedPanel(size_hint=(1, 1), do_default_tab=False)
        
        # Home Tab
        home_tab = TabbedPanelItem(text="🏠 Home")
        home_tab.add_widget(self.create_home_tab())
        self.tab_panel.add_widget(home_tab)

        # Shorts Tab
        shorts_tab = TabbedPanelItem(text="🎬 Shorts")
        shorts_tab.add_widget(self.create_shorts_tab())
        self.tab_panel.add_widget(shorts_tab)

        # Subscriptions Tab
        subs_tab = TabbedPanelItem(text="📌 Subscriptions")
        subs_tab.add_widget(self.create_subscriptions_tab())
        self.tab_panel.add_widget(subs_tab)

        # Upload Tab
        upload_tab = TabbedPanelItem(text="📤 Upload")
        upload_tab.add_widget(self.create_upload_tab())
        self.tab_panel.add_widget(upload_tab)

        # Chat Tab
        chat_tab = TabbedPanelItem(text="💬 Chat")
        chat_tab.add_widget(self.create_chat_tab())
        self.tab_panel.add_widget(chat_tab)

        # Profile Tab
        profile_tab = TabbedPanelItem(text="👤 Profile")
        profile_tab.add_widget(self.create_profile_tab())
        self.tab_panel.add_widget(profile_tab)

        self.layout.add_widget(self.tab_panel)

    def create_chat_tab(self):
        layout = BoxLayout(orientation='vertical')
        
        # Chat header
        header = BoxLayout(size_hint=(1, 0.1))
        ai_avatar = AsyncImage(
            source="https://via.placeholder.com/50x50?text=AI",
            size_hint=(0.2, 1)
        )
        ai_name = Label(
            text="Raikun AI",
            size_hint=(0.8, 1),
            halign="left",
            valign="middle",
            color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
        )
        header.add_widget(ai_avatar)
        header.add_widget(ai_name)
        layout.add_widget(header)
        
        # Chat history
        self.chat_view = ChatRecycleView()
        self.chat_view.viewclass = 'ChatMessage'
        self.chat_view.data = []
        layout.add_widget(self.chat_view)
        
        # Send message area
        send_layout = BoxLayout(size_hint=(1, 0.15), spacing=10, padding=10)
        self.chat_input = TextInput(
            hint_text="Type your message...",
            size_hint=(0.8, 1),
            multiline=False,
            background_color=(1, 1, 1, 1) if not self.dark_mode else (0.2, 0.2, 0.2, 1),
            foreground_color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
        )
        self.chat_input.bind(on_text_validate=self.send_chat_message)
        send_btn = Button(
            text="Send",
            size_hint=(0.2, 1),
            background_color=(0.2, 0.6, 1, 1),
            color=(1, 1, 1, 1)
        )
        send_btn.bind(on_press=self.send_chat_message)
        
        send_layout.add_widget(self.chat_input)
        send_layout.add_widget(send_btn)
        layout.add_widget(send_layout)
        
        # Initialize AI
        self.raikun = RaikunAI()
        
        # Add welcome message
        self.add_chat_message("Hello! I'm Raikun, your AI assistant. Ask me anything about the app!", "Raikun", False)
        
        return layout

    def send_chat_message(self, instance):
        message = self.chat_input.text.strip()
        if not message:
            return
            
        # Add user message
        self.add_chat_message(message, "You", True)
        self.chat_input.text = ""
        
        # Get AI response after a short delay
        Clock.schedule_once(lambda dt: self.get_ai_response(message), 0.5)

    def get_ai_response(self, message):
        response = self.raikun.respond(message)
        self.add_chat_message(response, "Raikun", False)

    def add_chat_message(self, text, sender, is_user):
        timestamp = datetime.now().strftime("%H:%M")
        self.chat_view.data.append({
            "text": text,
            "sender": sender,
            "timestamp": timestamp,
            "is_user": is_user
        })
        self.chat_view.refresh_from_data()
        # Scroll to bottom
        if len(self.chat_view.data) > 0:
            Clock.schedule_once(lambda dt: self.chat_view.scroll_to(len(self.chat_view.data) - 1))

    def create_home_tab(self):
        layout = BoxLayout(orientation='vertical', size_hint=(1, 1))

        # Search Section
        search_bar = BoxLayout(size_hint=(1, 0.1))
        self.search_input = TextInput(
            hint_text="Search videos...", 
            size_hint=(0.8, 1),
            background_color=(1, 1, 1, 1) if not self.dark_mode else (0.2, 0.2, 0.2, 1),
            foreground_color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
        )
        search_button = Button(text="Search", size_hint=(0.2, 1))
        search_button.bind(on_press=self.search_video)
        search_bar.add_widget(self.search_input)
        search_bar.add_widget(search_button)
        layout.add_widget(search_bar)

        # Categories filter
        categories = ["All", "Tech", "Nature", "Gaming", "Music", "Education"]
        categories_bar = ScrollView(size_hint=(1, 0.08))
        categories_layout = GridLayout(cols=len(categories), size_hint_x=None, spacing=5)
        categories_layout.bind(minimum_width=categories_layout.setter('width'))
        
        for category in categories:
            btn = ToggleButton(
                text=category, 
                group="categories",
                size_hint_x=None,
                width=100
            )
            btn.bind(on_press=partial(self.filter_by_category, category))
            categories_layout.add_widget(btn)
        
        categories_bar.add_widget(categories_layout)
        layout.add_widget(categories_bar)

        # Video Recommendations
        scroll = ScrollView(size_hint=(1, 0.82))
        self.grid = GridLayout(cols=1, spacing=10, size_hint_y=None)
        self.grid.bind(minimum_height=self.grid.setter('height'))

        self.load_recommended_videos()

        scroll.add_widget(self.grid)
        layout.add_widget(scroll)
        return layout

    def filter_by_category(self, category, instance):
        if category == "All":
            self.load_recommended_videos()
        else:
            self.load_recommended_videos(category_filter=category)

    def create_shorts_tab(self):
        layout = BoxLayout(orientation='vertical')
        
        # Shorts Carousel
        self.carousel = Carousel(direction='right')
        shorts_list = [
            {
                "title": "Funny Clip", 
                "thumbnail": "https://via.placeholder.com/300x500?text=Funny+Clip", 
                "source": "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4",
                "category": "Entertainment"
            },
            {
                "title": "Cooking Hack", 
                "thumbnail": "https://via.placeholder.com/300x500?text=Cooking+Hack", 
                "source": "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4",
                "category": "Food"
            },
            {
                "title": "Quick DIY", 
                "thumbnail": "https://via.placeholder.com/300x500?text=Quick+DIY", 
                "source": "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4",
                "category": "DIY"
            },
        ]

        for short in shorts_list:
            video_layout = BoxLayout(orientation='vertical')
            thumbnail = AsyncImage(source=short["thumbnail"], size_hint=(1, 0.8))
            title_label = Label(
                text=short["title"], 
                size_hint=(1, 0.1),
                color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
            )
            play_button = Button(text="▶ Play", size_hint=(1, 0.1))
            play_button.bind(on_press=partial(self.play_video, short))
            video_layout.add_widget(thumbnail)
            video_layout.add_widget(title_label)
            video_layout.add_widget(play_button)
            self.carousel.add_widget(video_layout)

        layout.add_widget(self.carousel)
        return layout

    def create_subscriptions_tab(self):
        layout = BoxLayout(orientation='vertical')
        
        # Title
        title = Label(
            text="Your Subscriptions", 
            size_hint=(1, 0.1),
            color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
        )
        layout.add_widget(title)
        
        # Subscribed channels list
        scroll = ScrollView()
        self.subs_grid = GridLayout(cols=1, size_hint_y=None)
        self.subs_grid.bind(minimum_height=self.subs_grid.setter('height'))
        
        # Load subscriptions
        self.load_subscriptions()
        
        scroll.add_widget(self.subs_grid)
        layout.add_widget(scroll)
        return layout

    def create_upload_tab(self):
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        self.upload_title = TextInput(
            hint_text="Video Title", 
            size_hint=(1, None), 
            height=40,
            background_color=(1, 1, 1, 1) if not self.dark_mode else (0.2, 0.2, 0.2, 1),
            foreground_color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
        )
        layout.add_widget(self.upload_title)
        
        self.upload_category = TextInput(
            hint_text="Category (e.g., Tech, Gaming)", 
            size_hint=(1, None), 
            height=40,
            background_color=(1, 1, 1, 1) if not self.dark_mode else (0.2, 0.2, 0.2, 1),
            foreground_color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
        )
        layout.add_widget(self.upload_category)
        
        self.upload_tags = TextInput(
            hint_text="Tags (comma separated)", 
            size_hint=(1, None), 
            height=40,
            background_color=(1, 1, 1, 1) if not self.dark_mode else (0.2, 0.2, 0.2, 1),
            foreground_color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
        )
        layout.add_widget(self.upload_tags)
        
        self.video_path_label = Label(
            text="No video selected", 
            size_hint=(1, None), 
            height=30,
            color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
        )
        layout.add_widget(self.video_path_label)
        
        select_btn = Button(text="Select Video", size_hint=(1, None), height=40)
        select_btn.bind(on_press=self.select_video)
        layout.add_widget(select_btn)
        
        upload_btn = Button(text="Upload Video", size_hint=(1, None), height=40)
        upload_btn.bind(on_press=self.upload_video)
        layout.add_widget(upload_btn)
        
        return layout

    def create_profile_tab(self):
        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        
        # Profile Header
        header = BoxLayout(size_hint=(1, 0.3), orientation='horizontal')
        
        # Avatar
        avatar = AsyncImage(
            source=self.user_data.get("avatar_path", "https://via.placeholder.com/100x100?text=User"),
            size_hint=(0.3, 1),
            keep_ratio=True
        )
        header.add_widget(avatar)
        
        # User Info
        info_layout = BoxLayout(orientation='vertical', size_hint=(0.7, 1))
        username = Label(
            text=self.login_username.text if hasattr(self, 'login_username') else "User",
            size_hint=(1, 0.5),
            font_size=20,
            color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
        )
        info_layout.add_widget(username)
        
        # Bio
        bio_text = self.user_data.get("bio", "No bio yet")
        bio = Label(
            text=bio_text,
            size_hint=(1, 0.5),
            text_size=(Window.width * 0.7 - 20, None),
            halign="left",
            valign="top",
            color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
        )
        info_layout.add_widget(bio)
        
        header.add_widget(info_layout)
        layout.add_widget(header)
        
        # Edit Profile Button
        edit_profile_btn = Button(text="✏ Edit Profile", size_hint=(1, 0.1))
        edit_profile_btn.bind(on_press=self.show_edit_profile)
        layout.add_widget(edit_profile_btn)
        
        # Watch History
        history_button = Button(text="📺 Watch History", size_hint=(1, 0.1))
        history_button.bind(on_press=self.show_watch_history)
        layout.add_widget(history_button)
        
        # Notifications
        notification_button = Button(text="🔔 Notifications", size_hint=(1, 0.1))
        notification_button.bind(on_press=self.show_notifications)
        layout.add_widget(notification_button)

        # Downloads
        download_button = Button(text="📥 Downloads", size_hint=(1, 0.1))
        download_button.bind(on_press=self.show_downloads)
        layout.add_widget(download_button)

        # Settings Button
        settings_button = Button(text="⚙ Settings", size_hint=(1, 0.1))
        settings_button.bind(on_press=self.show_settings)
        layout.add_widget(settings_button)

        # Logout Button
        logout_button = Button(text="Logout", size_hint=(1, 0.1))
        logout_button.bind(on_press=self.logout)
        layout.add_widget(logout_button)

        return layout

    def show_edit_profile(self, instance):
        popup = Popup(title="Edit Profile", size_hint=(0.8, 0.6))
        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        
        # Avatar URL
        avatar_url = TextInput(
            hint_text="Avatar URL", 
            text=self.user_data.get("avatar_path", ""),
            size_hint=(1, 0.2),
            background_color=(1, 1, 1, 1) if not self.dark_mode else (0.2, 0.2, 0.2, 1),
            foreground_color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
        )
        
        # Bio
        bio_input = TextInput(
            hint_text="Bio", 
            text=self.user_data.get("bio", ""),
            size_hint=(1, 0.5),
            background_color=(1, 1, 1, 1) if not self.dark_mode else (0.2, 0.2, 0.2, 1),
            foreground_color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
        )
        
        # Buttons
        btn_layout = BoxLayout(size_hint=(1, 0.2), spacing=10)
        save_btn = Button(text="Save")
        save_btn.bind(on_press=lambda x: self.save_profile(
            avatar_url.text, 
            bio_input.text, 
            popup
        ))
        
        cancel_btn = Button(text="Cancel")
        cancel_btn.bind(on_press=popup.dismiss)
        
        btn_layout.add_widget(save_btn)
        btn_layout.add_widget(cancel_btn)
        
        layout.add_widget(avatar_url)
        layout.add_widget(bio_input)
        layout.add_widget(btn_layout)
        
        popup.content = layout
        popup.open()

    def save_profile(self, avatar_url, bio, popup):
        try:
            self.user_data["avatar_path"] = avatar_url
            self.user_data["bio"] = bio
            
            cursor.execute(
                "UPDATE users SET avatar_path=?, bio=? WHERE id=?",
                (avatar_url, bio, self.current_user)
            )
            conn.commit()
            
            popup.dismiss()
            self.show_info_popup("Profile updated successfully!")
            self.tab_panel.switch_to(self.tab_panel.tab_list[-1])  # Switch to Profile tab
        except Exception as e:
            self.show_info_popup(f"Error updating profile: {str(e)}")

    def select_video(self, instance):
        try:
            from plyer import filechooser
            filechooser.open_file(
                title="Select video to upload",
                filters=[("Video Files", "*.mp4", "*.avi", "*.mov")],
                on_selection=self.handle_video_selection
            )
        except ImportError:
            self.show_info_popup("File selection requires plyer module. Please install with: pip install plyer")
        except Exception as e:
            self.show_info_popup(f"Error selecting file: {str(e)}")

    def handle_video_selection(self, selection):
        if selection:
            self.selected_video_path = selection[0]
            self.video_path_label.text = os.path.basename(self.selected_video_path)

    def upload_video(self, instance):
        if not hasattr(self, 'selected_video_path') or not self.selected_video_path:
            self.show_info_popup("Please select a video first")
            return
            
        title = self.upload_title.text.strip()
        if not title:
            self.show_info_popup("Please enter a title")
            return
            
        category = self.upload_category.text.strip() or "General"
        tags = self.upload_tags.text.strip()
        
        try:
            # Get video duration (simplified - in a real app you'd use a proper method)
            duration = 300  # Default 5 minutes
            
            cursor.execute(
                '''INSERT INTO videos 
                (title, file_path, uploader_id, category, tags, duration) 
                VALUES (?, ?, ?, ?, ?, ?)''',
                (title, self.selected_video_path, self.current_user, category, tags, duration)
            )
            video_id = cursor.lastrowid
            
            # Copy video to app directory
            os.makedirs("videos", exist_ok=True)
            dest_path = os.path.join("videos", f"{video_id}.mp4")
            shutil.copy(self.selected_video_path, dest_path)
            
            # Update the file path in DB to the copied location
            cursor.execute(
                "UPDATE videos SET file_path=? WHERE id=?",
                (dest_path, video_id)
            )
            
            conn.commit()
            
            # Add to UserUploads channel
            self.channels["UserUploads"]["videos"].append(title)
            
            self.show_info_popup("Video uploaded successfully!")
            self.load_recommended_videos()
            self.tab_panel.switch_to(self.tab_panel.tab_list[0])  # Switch to Home tab
            
            # Reset form
            self.upload_title.text = ""
            self.upload_category.text = ""
            self.upload_tags.text = ""
            self.video_path_label.text = "No video selected"
            self.selected_video_path = None
            
        except Exception as e:
            self.show_info_popup(f"Error uploading video: {str(e)}")

    def play_video(self, video, instance=None):
        if not video.get("source"):
            self.show_info_popup("Video source not available")
            return
            
        popup = Popup(
            title=video["title"], 
            size_hint=(0.9, 0.8),
            background_color=(0.9, 0.9, 0.9, 1) if not self.dark_mode else (0.2, 0.2, 0.2, 1)
        )
        layout = BoxLayout(orientation='vertical')

        video_source = video.get("source", "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4")
        video_widget = Video(
            source=video_source, 
            size_hint=(1, 0.8),
            options={'eos': 'loop'}
        )
        video_widget.state = 'play'
        self.current_playing_video = video_widget
        
        # Store video progress when position changes
        video_widget.bind(position=self.update_video_progress)
        
        # Check if we have saved progress for this video
        if 'id' in video:
            cursor.execute(
                "SELECT progress FROM watch_history WHERE user_id=? AND video_id=?",
                (self.current_user, video["id"])
            )
            progress = cursor.fetchone()
            if progress:
                video_widget.seek(progress[0] / 100)  # Convert percentage to position

        # Add to watch history
        if 'id' in video:
            cursor.execute(
                '''INSERT OR REPLACE INTO watch_history 
                (user_id, video_id, progress, last_watched) 
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)''',
                (self.current_user, video["id"], self.video_progress)
            )
            conn.commit()
        elif video["title"] not in [vh["title"] for vh in self.user_data["watch_history"]]:
            self.user_data["watch_history"].append({
                "title": video["title"],
                "progress": 0,
                "duration": 300  # Default duration
            })

        # Video controls
        controls = BoxLayout(size_hint=(1, 0.1))
        
        # Progress bar
        self.progress_label = Label(
            text="0:00 / 5:00",
            size_hint_x=0.3,
            color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
        )
        
        # Fullscreen button
        full_screen_btn = Button(text="⛶", size_hint_x=0.1)
        full_screen_btn.bind(on_press=self.toggle_fullscreen)
        
        # Speed control
        speed_btn = Button(text=f"Speed: {self.user_data['play_speed']}x", size_hint_x=0.2)
        speed_btn.bind(on_press=self.change_play_speed)
        
        # Download button
        download_btn = Button(text="↓ Download", size_hint_x=0.2)
        download_btn.bind(on_press=partial(self.download_video, video))
        
        # Comments button
        comments_btn = Button(text="💬 Comments", size_hint_x=0.2)
        comments_btn.bind(on_press=partial(self.show_comments, video.get("id")))
        
        controls.add_widget(self.progress_label)
        controls.add_widget(full_screen_btn)
        controls.add_widget(speed_btn)
        controls.add_widget(download_btn)
        controls.add_widget(comments_btn)

        # Update progress periodically
        Clock.schedule_interval(partial(self.update_progress_label, video_widget), 1)

        close_button = Button(text="Close", size_hint=(1, 0.1))
        close_button.bind(on_press=popup.dismiss)

        layout.add_widget(video_widget)
        layout.add_widget(controls)
        layout.add_widget(close_button)

        popup.content = layout
        popup.open()
        
        # When popup closes, unschedule the progress updater
        popup.bind(on_dismiss=lambda x: Clock.unschedule(self.update_progress_label))

    def update_video_progress(self, instance, position):
        if hasattr(instance, 'duration') and instance.duration > 0:
            self.video_progress = (position / instance.duration) * 100
            
            # Update DB if this is a database video
            if hasattr(self, 'current_playing_video') and hasattr(instance, 'source'):
                cursor.execute('''
                    SELECT id FROM videos WHERE file_path=?
                ''', (instance.source,))
                video_id = cursor.fetchone()
                if video_id:
                    cursor.execute('''
                        INSERT OR REPLACE INTO watch_history 
                        (user_id, video_id, progress, last_watched) 
                        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (self.current_user, video_id[0], self.video_progress))
                    conn.commit()

    def update_progress_label(self, video_widget, dt):
        if hasattr(video_widget, 'position') and hasattr(video_widget, 'duration'):
            if video_widget.duration > 0:
                current = int(video_widget.position)
                total = int(video_widget.duration)
                self.progress_label.text = f"{current//60}:{current%60:02d} / {total//60}:{total%60:02d}"

    def download_video(self, video, instance):
        if 'id' not in video:
            self.show_info_popup("Cannot download this video")
            return
            
        try:
            cursor.execute("SELECT file_path FROM videos WHERE id=?", (video["id"],))
            video_path = cursor.fetchone()[0]
            
            if not os.path.exists(video_path):
                self.show_info_popup("Video file not found")
                return
                
            # Create downloads directory if it doesn't exist
            os.makedirs(self.downloads_dir, exist_ok=True)
                
            # Copy video to downloads directory
            dest_path = os.path.join(self.downloads_dir, f"{video['id']}_{os.path.basename(video_path)}")
            shutil.copy(video_path, dest_path)
            
            # Add to downloads in DB
            cursor.execute('''
                INSERT OR REPLACE INTO downloads 
                (user_id, video_id, download_path) 
                VALUES (?, ?, ?)
            ''', (self.current_user, video["id"], dest_path))
            conn.commit()
            
            # Update user data
            self.user_data["downloads"].append({
                "id": video["id"],
                "title": video["title"],
                "path": dest_path
            })
            
            self.show_info_popup("Video downloaded successfully!")
        except Exception as e:
            self.show_info_popup(f"Error downloading video: {str(e)}")

    def show_comments(self, video_id, instance):
        if not video_id:
            self.show_info_popup("No comments available for this video")
            return
            
        popup = Popup(
            title="Comments", 
            size_hint=(0.8, 0.7),
            background_color=(0.9, 0.9, 0.9, 1) if not self.dark_mode else (0.2, 0.2, 0.2, 1)
        )
        layout = BoxLayout(orientation='vertical')
        
        # Fetch comments from DB
        cursor.execute('''
            SELECT u.username, c.text, c.timestamp 
            FROM comments c
            JOIN users u ON c.user_id = u.id
            WHERE c.video_id = ?
            ORDER BY c.timestamp DESC
        ''', (video_id,))
        comments = cursor.fetchall()
        
        # Comments list
        scroll = ScrollView()
        comments_layout = GridLayout(cols=1, size_hint_y=None, spacing=10)
        comments_layout.bind(minimum_height=comments_layout.setter('height'))
        
        if not comments:
            no_comments = Label(
                text="No comments yet", 
                size_hint_y=None,
                height=40,
                color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
            )
            comments_layout.add_widget(no_comments)
        else:
            for username, text, timestamp in comments:
                comment_box = BoxLayout(orientation='vertical', size_hint_y=None, height=100)
                
                header = BoxLayout(size_hint=(1, 0.3))
                user_label = Label(
                    text=username,
                    size_hint=(0.7, 1),
                    halign="left",
                    color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
                )
                time_label = Label(
                    text=timestamp,
                    size_hint=(0.3, 1),
                    halign="right",
                    color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
                )
                header.add_widget(user_label)
                header.add_widget(time_label)
                
                comment_text = Label(
                    text=text,
                    size_hint=(1, 0.7),
                    text_size=(Window.width * 0.8 - 20, None),
                    halign="left",
                    valign="top",
                    color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
                )
                
                comment_box.add_widget(header)
                comment_box.add_widget(comment_text)
                comments_layout.add_widget(comment_box)
        
        scroll.add_widget(comments_layout)
        
        # Add comment section
        add_comment_layout = BoxLayout(size_hint=(1, 0.2), spacing=10)
        self.comment_input = TextInput(
            hint_text="Add a comment...",
            size_hint=(0.7, 1),
            background_color=(1, 1, 1, 1) if not self.dark_mode else (0.2, 0.2, 0.2, 1),
            foreground_color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
        )
        post_btn = Button(text="Post", size_hint=(0.3, 1))
        post_btn.bind(on_press=partial(self.post_comment, video_id, popup))
        
        add_comment_layout.add_widget(self.comment_input)
        add_comment_layout.add_widget(post_btn)
        
        # Close button
        close_btn = Button(text="Close", size_hint=(1, 0.1))
        close_btn.bind(on_press=popup.dismiss)
        
        layout.add_widget(scroll)
        layout.add_widget(add_comment_layout)
        layout.add_widget(close_btn)
        
        popup.content = layout
        popup.open()

    def post_comment(self, video_id, popup, instance):
        comment_text = self.comment_input.text.strip()
        if not comment_text:
            self.show_info_popup("Comment cannot be empty")
            return
            
        try:
            cursor.execute('''
                INSERT INTO comments (video_id, user_id, text)
                VALUES (?, ?, ?)
            ''', (video_id, self.current_user, comment_text))
            conn.commit()
            
            self.comment_input.text = ""
            popup.dismiss()
            self.show_comments(video_id, instance)  # Refresh comments
        except Exception as e:
            self.show_info_popup(f"Error posting comment: {str(e)}")

    def logout(self, instance):
        self.current_user = None
        self.show_login_screen()

    def toggle_fullscreen(self, instance):
        Window.fullscreen = 'auto' if not Window.fullscreen else False

    def change_play_speed(self, instance):
        speeds = [0.5, 1.0, 1.5, 2.0]
        current_index = speeds.index(self.user_data["play_speed"])
        new_speed = speeds[(current_index + 1) % len(speeds)]
        self.user_data["play_speed"] = new_speed
        
        if hasattr(self, 'current_playing_video') and self.current_playing_video:
            self.current_playing_video.volume = 0  # Mute during speed change
            self.current_playing_video.state = 'pause'
            Clock.schedule_once(partial(self.apply_speed_change, new_speed), 0.1)
        
        instance.text = f"Speed: {new_speed}x"
        self.show_info_popup(f"Playback speed changed to {new_speed}x")

    def apply_speed_change(self, new_speed, dt):
        if hasattr(self, 'current_playing_video') and self.current_playing_video:
            self.current_playing_video.rate = new_speed
            self.current_playing_video.volume = 1
            self.current_playing_video.state = 'play'

    def search_video(self, instance):
        query = self.search_input.text.strip()
        self.load_recommended_videos(search_query=query)

    def show_watch_history(self, instance):
        popup = Popup(
            title="Watch History", 
            size_hint=(0.9, 0.8),
            background_color=(0.9, 0.9, 0.9, 1) if not self.dark_mode else (0.2, 0.2, 0.2, 1)
        )
        scroll = ScrollView()
        layout = GridLayout(cols=1, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))
        
        if not self.user_data["watch_history"]:
            no_history = Label(
                text="No watch history yet", 
                size_hint_y=None, 
                height=40,
                color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
            )
            layout.add_widget(no_history)
        else:
            for video in reversed(self.user_data["watch_history"]):
                btn = Button(
                    text=f"{video['title']} - {video['progress']}% watched",
                    size_hint_y=None, 
                    height=60
                )
                btn.bind(on_press=partial(self.resume_video, video))
                layout.add_widget(btn)
            
        close_button = Button(text="Close", size_hint=(1, 0.1))
        close_button.bind(on_press=popup.dismiss)
        
        main_layout = BoxLayout(orientation='vertical')
        scroll.add_widget(layout)
        main_layout.add_widget(scroll)
        main_layout.add_widget(close_button)
        
        popup.content = main_layout
        popup.open()

    def resume_video(self, video, instance):
        # Create a video dict that matches what play_video expects
        video_dict = {
            "title": video["title"],
            "source": "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4"
        }
        
        if 'id' in video:
            video_dict["id"] = video["id"]
        
        self.play_video(video_dict)
        
        # Seek to saved position
        if hasattr(self, 'current_playing_video') and self.current_playing_video:
            if 'duration' in video and video["duration"] > 0:
                position = (video["progress"] / 100) * video["duration"]
                self.current_playing_video.seek(position / video["duration"])

    def show_notifications(self, instance):
        popup = Popup(
            title="Notifications", 
            size_hint=(0.9, 0.8),
            background_color=(0.9, 0.9, 0.9, 1) if not self.dark_mode else (0.2, 0.2, 0.2, 1)
        )
        scroll = ScrollView()
        layout = GridLayout(cols=1, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))
        
        if not self.user_data["notifications"]:
            self.user_data["notifications"] = [
                "Welcome to Amazon Video!",
                "New video uploaded by TechReviews",
                "Your subscription is active"
            ]
            
        for notification in self.user_data["notifications"]:
            label = Label(
                text=notification, 
                size_hint_y=None, 
                height=40,
                color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
            )
            layout.add_widget(label)
            
        close_button = Button(text="Close", size_hint=(1, 0.1))
        close_button.bind(on_press=popup.dismiss)
        
        main_layout = BoxLayout(orientation='vertical')
        scroll.add_widget(layout)
        main_layout.add_widget(scroll)
        main_layout.add_widget(close_button)
        
        popup.content = main_layout
        popup.open()

    def show_downloads(self, instance):
        popup = Popup(
            title="Downloads", 
            size_hint=(0.9, 0.8),
            background_color=(0.9, 0.9, 0.9, 1) if not self.dark_mode else (0.2, 0.2, 0.2, 1)
        )
        scroll = ScrollView()
        layout = GridLayout(cols=1, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))
        
        if not self.user_data["downloads"]:
            no_downloads = Label(
                text="No downloads yet", 
                size_hint_y=None, 
                height=40,
                color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
            )
            layout.add_widget(no_downloads)
        else:
            for download in self.user_data["downloads"]:
                btn = Button(
                    text=download["title"], 
                    size_hint_y=None, 
                    height=60
                )
                btn.bind(on_press=partial(self.play_downloaded_video, download))
                layout.add_widget(btn)
            
        close_button = Button(text="Close", size_hint=(1, 0.1))
        close_button.bind(on_press=popup.dismiss)
        
        main_layout = BoxLayout(orientation='vertical')
        scroll.add_widget(layout)
        main_layout.add_widget(scroll)
        main_layout.add_widget(close_button)
        
        popup.content = main_layout
        popup.open()

    def play_downloaded_video(self, download, instance):
        if not os.path.exists(download["path"]):
            self.show_info_popup("Downloaded file not found")
            return
            
        popup = Popup(
            title=download["title"], 
            size_hint=(0.9, 0.8),
            background_color=(0.9, 0.9, 0.9, 1) if not self.dark_mode else (0.2, 0.2, 0.2, 1)
        )
        layout = BoxLayout(orientation='vertical')

        video_widget = Video(source=download["path"], size_hint=(1, 0.9))
        video_widget.state = 'play'
        
        # Check for saved progress
        cursor.execute(
            "SELECT progress FROM watch_history WHERE user_id=? AND video_id=?",
            (self.current_user, download["id"])
        )
        progress = cursor.fetchone()
        if progress:
            video_widget.seek(progress[0] / 100)

        close_button = Button(text="Close", size_hint=(1, 0.1))
        close_button.bind(on_press=popup.dismiss)

        layout.add_widget(video_widget)
        layout.add_widget(close_button)

        popup.content = layout
        popup.open()

    def show_settings(self, instance):
        popup = Popup(
            title="Settings", 
            size_hint=(0.8, 0.6),
            background_color=(0.9, 0.9, 0.9, 1) if not self.dark_mode else (0.2, 0.2, 0.2, 1)
        )
        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        
        # Dark mode toggle
        dark_mode_btn = Button(
            text="Dark Mode: ON" if self.dark_mode else "Dark Mode: OFF",
            size_hint=(1, 0.2)
        )
        dark_mode_btn.bind(on_press=self.toggle_dark_mode)
        
        # Ads toggle
        ads_toggle = Button(
            text="Ads: ON" if self.user_data["ads_enabled"] else "Ads: OFF",
            size_hint=(1, 0.2)
        )
        ads_toggle.bind(on_press=self.toggle_ads_setting)
        
        # Playback speed
        speed_btn = Button(
            text=f"Playback Speed: {self.user_data['play_speed']}x",
            size_hint=(1, 0.2)
        )
        speed_btn.bind(on_press=self.change_play_speed)
        
        # Close button
        close_btn = Button(text="Close", size_hint=(1, 0.2))
        close_btn.bind(on_press=popup.dismiss)
        
        layout.add_widget(dark_mode_btn)
        layout.add_widget(ads_toggle)
        layout.add_widget(speed_btn)
        layout.add_widget(close_btn)
        popup.content = layout
        popup.open()

    def toggle_dark_mode(self, instance):
        self.dark_mode = not self.dark_mode
        instance.text = "Dark Mode: ON" if self.dark_mode else "Dark Mode: OFF"
        self.apply_theme()
        status = "enabled" if self.dark_mode else "disabled"
        self.show_info_popup(f"Dark mode {status}")

    def toggle_ads_setting(self, instance):
        self.user_data["ads_enabled"] = not self.user_data["ads_enabled"]
        instance.text = "Ads: ON" if self.user_data["ads_enabled"] else "Ads: OFF"
        status = "enabled" if self.user_data["ads_enabled"] else "disabled"
        self.show_info_popup(f"Ads have been {status}")

    def load_recommended_videos(self, search_query="", category_filter=None):
        self.grid.clear_widgets()
        query = '''
            SELECT id, title, likes, category, tags 
            FROM videos 
            WHERE 1=1
        '''
        params = []
        
        if search_query:
            query += " AND title LIKE ?"
            params.append(f"%{search_query}%")
            
        if category_filter:
            query += " AND category = ?"
            params.append(category_filter)
            
        cursor.execute(query, params)
        db_videos = cursor.fetchall()
        
        video_list = []
        for vid in db_videos:
            video_list.append({
                "id": vid[0],
                "title": vid[1],
                "thumbnail": "https://via.placeholder.com/300x200?text=" + vid[1].replace(" ", "+"),
                "source": "local_video.mp4",  # In a real app, use actual path
                "channel": "UserUploads",
                "likes": vid[2],
                "category": vid[3],
                "tags": vid[4]
            })
        
        # Add channel videos
        for channel in self.channels:
            if channel != "UserUploads":
                for video in self.channels[channel]["videos"]:
                    video_list.append({
                        "title": video,
                        "thumbnail": "https://via.placeholder.com/300x200?text=" + video.replace(" ", "+"),
                        "source": "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4",
                        "channel": channel,
                        "likes": 0,
                        "category": "General"
                    })
        
        # Add an ad if enabled
        if self.user_data["ads_enabled"]:
            video_list.append({
                "title": "Ad", 
                "thumbnail": "https://via.placeholder.com/300x200?text=Sponsored+Ad", 
                "source": None, 
                "channel": "",
                "category": "Ad"
            })

        for video in video_list:
            video_layout = BoxLayout(orientation="horizontal", size_hint_y=None, height=150)

            thumbnail = AsyncImage(source=video["thumbnail"], size_hint_x=0.3)

            if video["source"]:
                play_button = Button(
                    text=video["title"], 
                    size_hint_x=0.3,
                    background_color=(1, 1, 1, 1) if not self.dark_mode else (0.2, 0.2, 0.2, 1),
                    color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
                )
                play_button.bind(on_press=partial(self.play_video, video))

                like_count = video.get("likes", 0)
                like_button = Button(
                    text=f"👍 {like_count}", 
                    size_hint_x=0.15,
                    background_color=(1, 1, 1, 1) if not self.dark_mode else (0.2, 0.2, 0.2, 1),
                    color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
                )
                if 'id' in video:
                    like_button.bind(on_press=partial(self.like_video_db, video["id"]))
                else:
                    like_button.bind(on_press=partial(self.like_video_mem, video["title"]))
                
                channel_label = Label(
                    text=f"Channel: {video['channel']}", 
                    size_hint_x=0.15,
                    color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
                )
                sub_button = Button(
                    text="Subscribed ✓" if video['channel'] in self.user_data["subscriptions"] else "Subscribe",
                    size_hint_x=0.1,
                    background_color=(1, 1, 1, 1) if not self.dark_mode else (0.2, 0.2, 0.2, 1),
                    color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
                )
                sub_button.bind(on_press=partial(self.toggle_subscription, video['channel']))

                video_layout.add_widget(thumbnail)
                video_layout.add_widget(play_button)
                video_layout.add_widget(like_button)
                video_layout.add_widget(channel_label)
                video_layout.add_widget(sub_button)
            else:
                ad_label = Label(
                    text="Sponsored Ad", 
                    size_hint_x=0.7,
                    color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
                )
                ad_button = Button(
                    text="Learn More", 
                    size_hint_x=0.3,
                    background_color=(1, 1, 1, 1) if not self.dark_mode else (0.2, 0.2, 0.2, 1),
                    color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
                )
                ad_button.bind(on_press=self.show_ad)
                video_layout.add_widget(thumbnail)
                video_layout.add_widget(ad_label)
                video_layout.add_widget(ad_button)

            self.grid.add_widget(video_layout)

    def like_video_db(self, video_id, instance):
        cursor.execute("UPDATE videos SET likes = likes + 1 WHERE id = ?", (video_id,))
        conn.commit()
        cursor.execute("SELECT likes FROM videos WHERE id = ?", (video_id,))
        new_count = cursor.fetchone()[0]
        instance.text = f"👍 {new_count}"
        self.show_info_popup("Video liked!")

    def like_video_mem(self, video_title, instance):
        if video_title in self.user_data["likes"]:
            self.user_data["likes"][video_title] += 1
        else:
            self.user_data["likes"][video_title] = 1
        instance.text = f"👍 {self.user_data['likes'][video_title]}"
        self.show_info_popup(f"You liked {video_title}")

    def load_subscriptions(self):
        self.subs_grid.clear_widgets()
        if not self.user_data["subscriptions"]:
            no_subs = Label(
                text="No subscriptions yet", 
                size_hint_y=None, 
                height=40,
                color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
            )
            self.subs_grid.add_widget(no_subs)
        else:
            for channel in self.user_data["subscriptions"]:
                btn = Button(
                    text=channel, 
                    size_hint_y=None, 
                    height=40,
                    background_color=(1, 1, 1, 1) if not self.dark_mode else (0.2, 0.2, 0.2, 1),
                    color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
                )
                btn.bind(on_press=lambda x, c=channel: self.show_channel(c))
                self.subs_grid.add_widget(btn)

    def show_channel(self, channel_name):
        if channel_name not in self.channels:
            self.show_info_popup("Channel not found")
            return
            
        popup = Popup(
            title=channel_name, 
            size_hint=(0.9, 0.8),
            background_color=(0.9, 0.9, 0.9, 1) if not self.dark_mode else (0.2, 0.2, 0.2, 1)
        )
        layout = BoxLayout(orientation='vertical')
        
        # Channel header
        header = BoxLayout(size_hint=(1, 0.2))
        header.add_widget(AsyncImage(source=self.channels[channel_name]["logo"]))
        
        channel_info = BoxLayout(orientation='vertical')
        channel_label = Label(
            text=channel_name,
            color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
        )
        subs_count = Label(
            text=f"{len(self.user_data['subscriptions'])} subscribers",
            color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
        )
        channel_info.add_widget(channel_label)
        channel_info.add_widget(subs_count)
        header.add_widget(channel_info)
        
        # Subscribe button
        sub_text = "Subscribed ✓" if channel_name in self.user_data["subscriptions"] else "Subscribe"
        sub_button = Button(
            text=sub_text,
            background_color=(1, 1, 1, 1) if not self.dark_mode else (0.2, 0.2, 0.2, 1),
            color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
        )
        sub_button.bind(on_press=partial(self.toggle_subscription, channel_name))
        
        # Channel videos
        scroll = ScrollView()
        grid = GridLayout(cols=1, size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))
        
        if not self.channels[channel_name]["videos"]:
            no_videos = Label(
                text="No videos in this channel yet", 
                size_hint_y=None, 
                height=40,
                color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
            )
            grid.add_widget(no_videos)
        else:
            for video in self.channels[channel_name]["videos"]:
                btn = Button(
                    text=video, 
                    size_hint_y=None, 
                    height=40,
                    background_color=(1, 1, 1, 1) if not self.dark_mode else (0.2, 0.2, 0.2, 1),
                    color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
                )
                btn.bind(on_press=partial(self.play_video, {
                    "title": video, 
                    "source": "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4"
                }))
                grid.add_widget(btn)
        
        layout.add_widget(header)
        layout.add_widget(sub_button)
        layout.add_widget(scroll)
        scroll.add_widget(grid)
        popup.content = layout
        popup.open()

    def toggle_subscription(self, channel_name, instance):
        if channel_name not in self.channels:
            self.show_info_popup("Channel not found")
            return
            
        if channel_name in self.user_data["subscriptions"]:
            self.user_data["subscriptions"].remove(channel_name)
            cursor.execute(
                "DELETE FROM subscriptions WHERE user_id=? AND channel_name=?",
                (self.current_user, channel_name)
            )
            instance.text = "Subscribe"
        else:
            self.user_data["subscriptions"].append(channel_name)
            cursor.execute(
                "INSERT INTO subscriptions (user_id, channel_name) VALUES (?, ?)",
                (self.current_user, channel_name)
            )
            instance.text = "Subscribed ✓"
        conn.commit()
        self.load_subscriptions()

    def show_ad(self, instance):
        if self.user_data["ads_enabled"]:
            self.user_data["earnings"] += 0.05
            self.show_info_popup("Ad played! Earned $0.05")
        else:
            self.show_info_popup("Ads are disabled in your settings")

    def show_info_popup(self, message):
        popup = Popup(
            title="Info",
            content=Label(
                text=message,
                color=(0, 0, 0, 1) if not self.dark_mode else (1, 1, 1, 1)
            ),
            size_hint=(0.6, 0.3),
            background_color=(0.9, 0.9, 0.9, 1) if not self.dark_mode else (0.2, 0.2, 0.2, 1)
        )
        popup.open()

    def on_stop(self):
        """Called when the application is closing"""
        conn.close()

if __name__ == "__main__":
    AmazonVideoApp().run()