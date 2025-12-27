import os
import random
from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.properties import NumericProperty, ListProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.screenmanager import Screen, ScreenManager
from pygame import mixer
from mutagen import File
import tkinter as tk
from tkinter import filedialog
from kivy.core.text import LabelBase

mixer.init()

LabelBase.register(
    name="FA",
    fn_regular="assets/fa-solid-900.ttf"
)

def format_time(seconds):
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02d}:{seconds:02d}"


class MainScreen(Screen):

    path = ''
    paused = False
    is_dragging_progress_bar = False

    # Skipping logic
    skip_time = 5
    current_time_offset = 0

    # Volume variable, max value at 1
    volume = NumericProperty(0.5)
    # Pygame does not provide any real time, manual clock to update slider
    current_time = 0

    # Gradient
    grad_color_1 = ListProperty([0.1, 0.1, 0.1, 1])
    grad_color_2 = ListProperty([0.2, 0.2, 0.2, 1])

    # Whenever we use self.playlist, these functions get triggered
    @property
    def app(self):
        return App.get_running_app()

    @property
    def playlist(self):
        return self.app.playlist

    @playlist.setter
    def playlist(self, value):
        self.app.playlist = value

    @property
    def current_song_index(self):
        return self.app.current_song_index

    @current_song_index.setter
    def current_song_index(self, value):
        # This sends the new value back to the App class
        self.app.current_song_index = value

    @property
    def music_started(self):
        return self.app.music_started

    @music_started.setter
    def music_started(self, value):
        self.app.music_started = value

    def on_enter(self):
        # Refresh the UI whenever we return to this screen
        Clock.schedule_once(self.deferred_refreshed, 0)

    def deferred_refreshed(self, dt):
        if self.playlist:
            if not self.music_started:
                # Reloads metadata for the current index
                mixer.music.stop()
                self.music_started = False
                Clock.unschedule(self.update_slider)
                self.import_audio()
                self.play_music()
            else:
                pass
        else:
            self.stop_and_reset()

            # 2. Add these "Deep Clean" steps:
            mixer.music.unload()  # Critical: Releases the file lock on the current MP3

            # Reset internal logic flags not covered in stop_and_reset
            self.current_time_offset = 0
            self.path = ''

            # 3. Reset UI elements that only exist on the MainScreen
            song_title = self.ids.get("song_title")
            if song_title:
                song_title.text = "Select a Song"
            self.stop_pulse()  # Ensure the animation isn't running in the background

            # 4. Handle the "Smart Button" position
            # If the list is empty, snap the button back to the center

            main_action_btn = self.ids.get("main_action_btn")
            if main_action_btn:
                main_action_btn.pos_hint = {'center_x': 0.5, 'center_y': 0.5}
                main_action_btn.size_hint = (0.6, 0.1)


    def start_pulse(self):
        Animation.cancel_all(self.ids.center_icon)

        # Use raw numbers instead of strings like "130sp"
        # 130 and 100 are the pixel equivalents
        anim = Animation(font_size=130, opacity=1.0, duration=1.2, t='in_out_sine') + \
               Animation(font_size=100, opacity=0.4, duration=1.2, t='in_out_sine')

        anim.repeat = True
        anim.start(self.ids.center_icon)

    def stop_pulse(self):
        Animation.cancel_all(self.ids.center_icon)
        # Return to base state using numbers
        Animation(font_size=100, opacity=0.5, duration=0.5).start(self.ids.center_icon)

    def handle_action(self):
        # Access the shared app state
        if not self.app.playlist:
            # First time: Open explorer
            self.open_windows_explorer()
        else:
            # Subsequent times: Go to the editing screen
            self.manager.current = 'list'
            self.manager.transition.direction = 'left'

    def open_windows_explorer(self):
        # 1. Create a hidden Tkinter root window
        root = tk.Tk()

        # We only need to access file dialog of tkinter.
        # When filedialog opens, a blank window also pops up (root) instance
        # root.withdraw hides that window
        root.withdraw()

        # 2. Make the dialog appear on top of our Kivy app
        root.attributes('-topmost', True)

        # 3. Open the actual Windows File Explorer
        file_paths = filedialog.askopenfilenames(
            title="Select Audio File",
            filetypes=[("Audio Files", "*.mp3 *.wav *.flac *.ogg"), ("All Files", "*.*")]
        )

        # 4. Close the hidden window
        root.destroy()

        # 5. Send the path to your existing import_audio function
        if file_paths:
            # Destroy previous session
            anim = Animation(pos_hint={'right': 0.98, 'top': 0.98},
                             size_hint=(0.3, 0.07),
                             duration=0.5, t='out_cubic')
            anim.start(self.ids.main_action_btn)
            for file_path in file_paths:
                # Standardize path slashes for Python
                file_path = file_path.replace('\\', '/')
                self.playlist.append(file_path)

            print(self.playlist, self.current_song_index)
            self.import_audio()

    def import_audio(self):
        # 1. Get Metadata using Mutagen
        audio = File(self.playlist[self.current_song_index])
        self.path = self.playlist[self.current_song_index]

        # Check for next and back buttons
        if len(self.playlist) > 1 and self.current_song_index < len(self.playlist) - 1:
            self.ids["next_song"].disabled = False
        else:
            self.ids["next_song"].disabled = True

        if len(self.playlist) > 1 and self.current_song_index > 0:
            self.ids["prev_song"].disabled = False
        else:
            self.ids["prev_song"].disabled = True

        # 2. Update Slider Max and Labels
        self.current_time = 0
        self.current_time_offset = 0
        length = audio.info.length
        self.ids["progress_slider"].max = length
        self.ids["progress_slider"].value = 0
        self.ids["song_title"].text = os.path.basename(self.path)
        self.ids["total_time_label"].text = format_time(length)
        self.ids["play_button"].disabled = False
        self.update_procedural_bg()

    def update_procedural_bg(self):
        random.seed(os.path.basename(self.path))
        self.grad_color_1 = [random.uniform(0, 0.2), random.uniform(0, 0.2), random.uniform(0, 0.2), 1]
        self.grad_color_2 = [random.uniform(0.1, 0.4), random.uniform(0.1, 0.4), random.uniform(0.1, 0.4), 1]

    def play_music(self):
        #1. First time starting music
        if not self.music_started:
            self.ids["play_button"].text = "\uf04c"
            self.music_started = True
            mixer.music.load(self.path)
            self.ids["skip_forward"].disabled = False
            self.ids["skip_backward"].disabled = False

            self.start_pulse()

            # What if we already moved the slider even before music was played
            mixer.music.play(start = self.current_time)

            # This object calls that function after every 1/60 second
            Clock.schedule_interval(self.update_slider, 1/60)
            return

        #2. If music is currently playing, pause it
        if self.music_started and not self.paused:
            self.ids["play_button"].text = "\uf04b"
            self.paused = True
            mixer.music.pause()
            self.stop_pulse()

            # Stop the UI timer
            # Clock object stops this calling
            Clock.unschedule(self.update_slider)

        #3. If music is paused, unpause it
        else:
            self.ids["play_button"].text = "\uf04c"
            self.paused = False
            self.start_pulse()
            mixer.music.unpause()
            Clock.schedule_interval(self.update_slider, 1/60)

    def update_slider(self, dt):
        # we just add the 'dt' (delta time) to our variable
        # dt is provided by Clock object, that dt is timeout variable
        self.current_time += dt

        # Check if we have reached the end of song
        if self.current_time >= self.ids["progress_slider"].max:
            # Separate function, cleaner
            self.stop_and_reset()
            return

        if self.is_dragging_progress_bar:
            return

        self.ids["progress_slider"].value = self.current_time
        self.ids["current_time_label"].text = format_time(self.current_time)

    def stop_and_reset(self):
        mixer.music.stop()
        Clock.unschedule(self.update_slider)
        self.music_started = False
        self.paused = False
        self.current_time = 0
        self.stop_pulse()

        # Use .get() to safely check if the widget exists yet
        play_btn = self.ids.get("play_button")
        if play_btn:
            play_btn.text = "\uf04b"

        slider = self.ids.get("progress_slider")
        if slider:
            slider.value = 0

        time_label = self.ids.get("current_time_label")
        if time_label:
            time_label.text = "00:00"

    def progress_bar_drag(self, value):
        self.ids["current_time_label"].value = value

    """
    1.In Kivy's on_touch_up or on_touch_down events, two arguments are passed automatically passed:
        args[0]: The widget itself (the Slider).
        args[1]: The Touch Object, args[1], I wrote touch, which contains the $(x, y)$ coordinates of where your mouse is.
        
    2. .pos => This is simply the $(x, y)$ position of the click. So *args[1].pos or touch.pos "unpacks" those coordinates into the function.
    
    3. self.collide_point(...) => This is a built-in Kivy function. It asks: "Does this $(x, y)$ coordinate fall within the rectangular boundaries of the Slider?
        True: You clicked the slider. Jump the music!
        False: You clicked a button nearby. Do nothing.
    
    In Kivy, when we click the screen, the "Touch Event" is sent to every single widget on the screen simultaneously.

    If we have a Play button and a Slider, and we click the Play button, the Slider also hears that click.
    
    Without collide_point, the Slider would think, "Oh, someone clicked the screen! I better move the music to where that click happened!" even though we were just trying to hit Play.
    """

    def seek_music(self, value):
        # Update our tracker to current time
        self.current_time = float(value)

        if self.music_started:
            # 2. Tell Pygame to jump to the new second
            # Note: start=value works for MP3 and OGG; WAV may require restarting

            """
            alright so here, we first use play function to jump to our desired position. Say, for a brief, let it be in nanosecond, my music will play, 
            but immediately that self.paused will be executed, and it will pause it
            
            Because mixer.music.play(start=value) is the only reliable way in Pygame to move the playhead to a specific timestamp, 
            you have to "kickstart" the engine for a split second before freezing it again.

            Why this works (and why it's necessary)
            Pygame's mixer behaves like an old-school tape deck. You can't just "move the tape" while the power is off; the engine has to be "Engaged" (play) 
            for the playhead to find the correct byte in the file.
            
            The "Jump": mixer.music.play(start=value) resets the internal buffer and starts streaming from the new location.
            
            The "Freeze": mixer.music.pause() happens so fast (in microseconds) that the user's ears won't even process a sound. To them, it looks like the player 
            just "skipped" while paused.
            
            """

            mixer.music.play(start=value)

            Clock.unschedule(self.update_slider)

            # 3. If we were paused, pause immediately after jumping
            if self.paused:

                """
                The "Volume Sandwich" is a defensive programming technique used to hide audio artifacts (like pops, clicks, or "ghost" notes) that occur during rapid state changes in an audio engine.

                Why does this happen on fast/low-latency devices?
                It boils down to the way modern computers handle Audio Buffers.
                
                The Buffer Delay: When you call mixer.music.play(), Python tells the hardware to start pushing data. On a slower device, there is a tiny "warm-up" period where the hardware prepares the stream.
                
                The Execution Speed: On a high-end PC with low-latency drivers, your CPU executes the Python code so fast that the play() command and the pause() command are sent to the audio hardware almost simultaneously.
                
                The "Glitch": Because the hardware is so responsive, it manages to play a few "frames" of audio (literally microseconds of sound) before the pause command hits the circuit. This results in a tiny chirp or pop sound.
                """
                mixer.music.pause()
            else:
                # 4. Restart the clock if we are playing, now why?
                """
                In a perfect world, yes, it would work. But in a real-world app, "letting it run" leads to a subtle but annoying visual jitter known as the Phase Offset.

                Here is the technical reason why we restart it:
                
                The "Sub-Second" Offset Problem
                The Kivy Clock doesn't care where we moved the slider; it only cares about the exact moment it was first started.
                
                => Imagine this timeline:
                
                1) The clock is ticking at: 1.0s, 2.0s, 3.0s, 4.0s.
                
                2) At 2.9s, we quickly scrub the slider to 50.0s and release.
                
                3) If we let it run: The next tick happens at 3.0s (because that’s the next 1-second interval).
                
                3) The Result: Our current_time immediately jumps from 50.0 to 51.0 after only 0.1 seconds of listening.
                
                To the user, it looks like the slider "hiccups" or jumps forward too fast the moment they let go.
                
                The "Drift" cumulative error
                Because Kivy's Clock is influenced by the frame rate (FPS) of our app, small delays in processing can build up. By restarting the clock upon a seek, 
                we resynchronize the UI's heartbeat with the user's manual action. It ensures the first "tick" after the seek happens exactly 1.0 seconds later.
                """
                Clock.schedule_interval(self.update_slider, 1/60)

    def update_volume(self, value):
        self.volume = value
        mixer.music.set_volume(self.volume)

    # Skipping, current_time keeps track of this

    def skip_forward(self):
        # 1. Update our master variable
        self.current_time += self.skip_time

        # 2. Safety check: Don't skip past the end of the song
        max_len = self.ids["progress_slider"].max
        if self.current_time > max_len:
            self.stop_and_reset()
            return

        # 3. Update the UI thumb immediately so it doesn't wait for the next Clock tick
        self.ids["progress_slider"].value = self.current_time
        self.ids["current_time_label"].text = format_time(self.current_time)

        # 4. Tell the mixer to jump
        # We use the same 'kickstart' logic as your seek function
        mixer.music.play(start=self.current_time)
        if self.paused:
            mixer.music.pause()

    def skip_backward(self):
        # 1. Update variable
        self.current_time -= self.skip_time

        # 2. Safety check: Don't go below 0
        if self.current_time < 0:
            self.current_time = 0

        # 3. Update UI
        self.ids["progress_slider"].value = self.current_time
        self.ids["current_time_label"].text = format_time(self.current_time)

        # 4. Jump
        mixer.music.play(start=self.current_time)
        if self.paused:
            mixer.music.pause()

    def next_song(self):
        app = App.get_running_app()
        if self.current_song_index < len(self.playlist) - 1:
            app.current_song_index += 1
            self.prepare_and_play()

    def prev_song(self):
        if self.current_song_index > 0:
            self.current_song_index -= 1
            self.prepare_and_play()


    def prepare_and_play(self):
        # Stop Current playing music
        mixer.music.stop()
        self.music_started = False
        # Unschedule clocks
        Clock.unschedule(self.update_slider)

        if not self.paused:
            self.paused = self.paused

        # Import next song data, change and update UI
        self.import_audio()

        # Play the song
        self.play_music()

class ListScreen(Screen):
    def refresh_list(self):
        container = self.ids["list_container"]
        container.clear_widgets()
        app = App.get_running_app()

        for index, song_path in enumerate(app.playlist):
            row = BoxLayout(size_hint_y=None, height="50dp")

            # Song Label (Click to play this song)
            btn = Button(
                text=os.path.basename(song_path),
                background_color=(0, 0, 0, 0) if index != app.current_song_index else (0, 0.5, 1, 0.3)
            )
            btn.bind(on_release=lambda x, i=index: self.select_song(i))

            # Delete Button
            del_btn = Button(text="\uf2ed", font_name="FA", size_hint_x=None, width="50dp")
            del_btn.bind(on_release=lambda x, i=index: self.remove_song(i))

            row.add_widget(btn)
            row.add_widget(del_btn)
            container.add_widget(row)

    def select_song(self, index):
        App.get_running_app().current_song_index = index
        # You stop the music
        App.get_running_app().music_started = False
        self.manager.current = "main"

    def remove_song(self, index):
        app = App.get_running_app()

        # If we delete the song that is currently playing
        if index == app.current_song_index:
            mixer.music.stop()
            app.playlist.pop(index)
            # Reset index to 0 or keep it within bounds
            app.current_song_index = max(0, min(index, len(app.playlist) - 1))
            # You have stopped the music too
            app.music_started = False
        else:
            app.playlist.pop(index)
            # If we deleted a song BEFORE the current one, shift index down
            if index < app.current_song_index:
                app.current_song_index -= 1

        self.refresh_list()

    def open_windows_explorer(self):
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)

        file_paths = filedialog.askopenfilenames(
            title="Add to Playlist",
            filetypes=[("Audio Files", "*.mp3 *.wav *.flac *.ogg")]
        )
        root.destroy()

        if file_paths:
            app = App.get_running_app()
            for path in file_paths:
                clean_path = path.replace('\\', '/')
                # Add to the existing list instead of replacing it
                app.playlist.append(clean_path)

            self.refresh_list()  # Re-draw the scrollable list

    # This is your ScrollView list of paths
    def on_enter(self):
        # Refresh the list view whenever we switch to this screen
        self.refresh_list()

class MusicPlayerAppScreenManager(ScreenManager):
    pass

class MusicPlayerApp(App):
    # SHARED DATA LIVES HERE
    playlist = ListProperty([])
    current_song_index = NumericProperty(0)
    music_started = False


    def build(self):
        return MusicPlayerAppScreenManager()

MusicPlayerApp().run()
