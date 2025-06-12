import os
import tempfile
import subprocess
import whisper
from tkinter import filedialog # Note: filedialogA was a typo, it's just filedialog
import time
import sys
import threading
import customtkinter as ctk
import shutil # For cleaning up temp directory
from googletrans import Translator # Import the Translator class
import googletrans # For checking version

# --- AnimatedLabel Class ---
class AnimatedLabel(ctk.CTkLabel):
    def fade_in(self, text, delay=50):
        self.configure(text="")
        def animate():
            for i in range(1, len(text) + 1):
                if self.master and hasattr(self.master, 'master') and self.master.master:
                    self.master.master.after(i * delay, lambda t=text[:i]: self.configure(text=t))
        animate()

# --- Main Application Class ---
class SubtitleApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("🎬 Subtitle Generator Pro")
        self.geometry("850x700")
        self.resizable(False, False)

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.base_font = ("Arial", 14)
        self.title_font = ("Arial", 28, "bold")
        self.button_font = ("Arial", 14, "bold")

        self.model = None
        self.translator = Translator()
        self.temp_dir = tempfile.mkdtemp()
        self.video_path = ""

        self.subtitle_settings = {
            "font": "Arial",
            "size": 24,
            "color": "white"
        }

        self.model_options = ["tiny", "base", "small", "medium"]
        self.selected_model_name = ctk.StringVar(value="base")
        self.load_whisper_model_initial()

        # Log googletrans version (useful for debugging translation issues)
        # Ensure this logging happens where it's visible early, e.g., in SubtitlePage log
        # For now, printing to console during init. SubtitlePage can log it too.
        try:
            print(f"INFO: Using googletrans version: {googletrans.__version__}")
        except Exception as e:
            print(f"INFO: Could not determine googletrans version: {e}")


        self.frames = {}
        container = ctk.CTkFrame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        for F in (SplashScreen, MainMenu, SubtitlePage):
            frame = F(container, self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(SplashScreen)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_whisper_model_initial(self):
        try:
            print(f"Initializing Whisper model: {self.selected_model_name.get()}...")
            self.model = whisper.load_model(self.selected_model_name.get())
            print(f"Whisper model '{self.selected_model_name.get()}' loaded successfully.")
        except Exception as e:
            print(f"FATAL ERROR: Could not load initial Whisper model '{self.selected_model_name.get()}': {e}")
            if self.selected_model_name.get() != "tiny":
                print("Attempting to load 'tiny' model as fallback...")
                try:
                    self.model = whisper.load_model("tiny")
                    self.selected_model_name.set("tiny")
                    print("Fallback 'tiny' model loaded.")
                except Exception as e_tiny:
                    print(f"FATAL ERROR: Could not load fallback 'tiny' model: {e_tiny}")
                    self.model = None
            else:
                self.model = None


    def load_whisper_model(self, model_name_str=None):
        model_to_load = model_name_str if model_name_str else self.selected_model_name.get()
        
        subtitle_page = self.frames.get(SubtitlePage)
        if not subtitle_page:
            print("Error: SubtitlePage not found for logging model load.")
            return

        if self.model and self.selected_model_name.get() == model_to_load and hasattr(self.model, 'name') and self.model.name == model_to_load : # check name attribute
            subtitle_page.log(f"ℹ️ Whisper model '{model_to_load}' is already loaded.")
            subtitle_page.enable_generate_button() 
            return

        def _load():
            try:
                subtitle_page.log(f"🔄 Loading Whisper model: {model_to_load}...")
                subtitle_page.update_progress(0.1, "Loading model...") 
                new_model = whisper.load_model(model_to_load)
                self.model = new_model 
                self.selected_model_name.set(model_to_load) 
                subtitle_page.log(f"✅ Whisper model '{model_to_load}' loaded successfully.")
                subtitle_page.update_progress(0, "") 
            except Exception as e:
                subtitle_page.log(f"❌ Error loading model '{model_to_load}': {e}")
                current_loaded_model_name = self.model.name if self.model and hasattr(self.model, 'name') else "None"
                subtitle_page.log(f"ℹ️ Keeping previously loaded model: '{current_loaded_model_name if self.model else self.selected_model_name.get()}' (if any).")

                if self.model and hasattr(self.model, 'name'):
                    self.selected_model_name.set(self.model.name)
                elif not self.model:
                     subtitle_page.log(f"❌ Critical: No Whisper model is currently loaded.")
                subtitle_page.update_progress(0, "Model load failed")
            finally:
                if subtitle_page and hasattr(subtitle_page, 'enable_generate_button'):
                    subtitle_page.enable_generate_button()

        if subtitle_page:
            subtitle_page.disable_generate_button()
        threading.Thread(target=_load, daemon=True).start()


    def show_frame(self, frame_class):
        frame = self.frames[frame_class]
        frame.tkraise()
        if hasattr(frame, 'on_show'): # Call on_show if it exists
            frame.on_show()

    def on_closing(self):
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                print(f"Cleaned up temp directory: {self.temp_dir}")
        except Exception as e:
            print(f"Error cleaning up temp directory: {e}")
        self.destroy()

# --- SplashScreen ---
class SplashScreen(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.label = AnimatedLabel(self, text="", font=controller.title_font, text_color=("gray10", "gray90"))
        self.label.pack(pady=(self.winfo_screenheight() // 3), padx=20) 

        self.continue_btn = ctk.CTkButton(self, text="Continue ✅",
                                          command=lambda: controller.show_frame(MainMenu),
                                          font=controller.button_font, width=200, height=50)
        self.continue_btn.pack(pady=20)
        # Defer animation until main window is ready
        self.after(100, self._deferred_animate_title)


    def _deferred_animate_title(self):
        # Check if the main CTk instance (app) is fully initialized
        if self.master and hasattr(self.master, 'master') and self.master.master:
            self.animate_title()
        else:
            # If not ready, try again shortly
            self.after(100, self._deferred_animate_title)

    def animate_title(self):
        # Ensure the controller (main app) context is valid for `after` calls
        if self.master and hasattr(self.master, 'master') and self.master.master:
             self.label.fade_in("✨ Subtitle Generator Pro ✨")
        else:
            print("Warning: SplashScreen controller not fully available for animation.")


    def on_show(self):
        """Called when the frame is shown."""
        self.after(100, self._deferred_animate_title) # Re-trigger animation if shown again


# --- MainMenu ---
class MainMenu(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        main_content_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_content_frame.pack(expand=True)

        ctk.CTkLabel(main_content_frame, text="Welcome to Subtitle Generator Pro!",
                     font=controller.title_font).pack(pady=(60,30))

        ctk.CTkLabel(main_content_frame, text="Ready to create and embed subtitles?",
                     font=("Arial", 18)).pack(pady=(0, 50))

        ctk.CTkButton(main_content_frame, text="🚀 Let's Go!",
                      command=lambda: controller.show_frame(SubtitlePage),
                      font=controller.button_font, width=220, height=55).pack(pady=20)

        ctk.CTkButton(main_content_frame, text="⚙️ Quick Settings (Global)",
                      command=self.open_global_settings_placeholder, 
                      font=controller.button_font, width=220, height=55).pack(pady=10)
        
        ctk.CTkButton(main_content_frame, text="🚪 Exit",
                      command=controller.on_closing,
                      font=controller.button_font, width=220, height=55,
                      fg_color="tomato").pack(pady=10)

    def on_show(self): # Optional: if MainMenu needs to do something when shown
        pass

    def open_global_settings_placeholder(self):
        # Create a Toplevel window that is transient to the main app window
        info_win = ctk.CTkToplevel(self.controller)
        info_win.geometry("300x150")
        info_win.title("Global Settings")
        info_win.transient(self.controller) # Makes it behave like a dialog for the main window
        info_win.grab_set() # Disables interaction with the main window until this is closed

        ctk.CTkLabel(info_win, text="Global application settings\n(e.g., theme, language)\nwould go here.",
                     font=self.controller.base_font).pack(padx=20, pady=20, expand=True)
        ctk.CTkButton(info_win, text="OK", command=info_win.destroy).pack(pady=10)
        info_win.lift() # Bring window to front
        info_win.focus_force() # Give focus


# --- SubtitlePage ---
class SubtitlePage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller 

        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Top section for video selection
        top_frame = ctk.CTkFrame(main_frame)
        top_frame.pack(fill="x", pady=(0, 15))

        self.video_label = ctk.CTkLabel(top_frame, text="No video selected", font=self.controller.base_font, wraplength=380)
        self.video_label.pack(side="left", padx=(0,10), expand=True, fill="x")

        self.select_video_btn = ctk.CTkButton(top_frame, text="📹 Select Video",
                                              command=self.select_video, font=self.controller.button_font)
        self.select_video_btn.pack(side="left", padx=5)

        # Controls section (Language, Model, Settings, Generate)
        controls_frame = ctk.CTkFrame(main_frame)
        controls_frame.pack(fill="x", pady=(0,15))
        controls_frame.grid_columnconfigure((0,1,2,3), weight=1) # Make columns responsive

        ctk.CTkLabel(controls_frame, text="Target Language:", font=self.controller.base_font).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.language_menu = ctk.CTkOptionMenu(controls_frame, values=["Original", "English (Translate)", "Urdu (Translate)"],
                                               font=self.controller.base_font, command=self.on_language_change)
        self.language_menu.set("Original") # Default
        self.language_menu.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        ctk.CTkLabel(controls_frame, text="AI Model:", font=self.controller.base_font).grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.model_menu = ctk.CTkOptionMenu(controls_frame, variable=self.controller.selected_model_name,
                                            values=self.controller.model_options,
                                            command=self.controller.load_whisper_model, 
                                            font=self.controller.base_font)
        self.model_menu.grid(row=0, column=3, padx=5, pady=5, sticky="ew")


        self.settings_btn = ctk.CTkButton(controls_frame, text="⚙️ Subtitle Style",
                                         command=self.open_settings, font=self.controller.button_font)
        self.settings_btn.grid(row=1, column=0, columnspan=2, padx=5, pady=10, sticky="ew")

        self.generate_btn = ctk.CTkButton(controls_frame, text="▶️ Generate Subtitles",
                                          command=self.run_subtitle_thread, font=self.controller.button_font, height=40)
        self.generate_btn.grid(row=1, column=2, columnspan=2, padx=5, pady=10, sticky="ew")

        # Progress Bar and Label
        self.progress_bar = ctk.CTkProgressBar(main_frame, orientation="horizontal", mode="determinate")
        self.progress_bar.set(0) 
        self.progress_bar.pack(fill="x", pady=(0,10))
        self.progress_label = ctk.CTkLabel(main_frame, text="", font=("Arial", 12))
        self.progress_label.pack(fill="x")

        # Log Box
        ctk.CTkLabel(main_frame, text="Process Log:", font=self.controller.base_font).pack(anchor="w", pady=(10,5))
        self.log_box = ctk.CTkTextbox(main_frame, height=200, font=("Consolas", 12) ) # Using a monospaced font for logs
        self.log_box.pack(fill="both", expand=True, pady=(0,10))

        # Back Button
        back_button = ctk.CTkButton(main_frame, text="⬅️ Back to Menu",
                                    command=lambda: controller.show_frame(MainMenu),
                                    font=self.controller.button_font)
        back_button.pack(pady=(5,0), anchor="sw") # Place at bottom-left

    def on_show(self):
        """Called when the SubtitlePage is shown."""
        # Log googletrans version here so it's visible in the GUI log
        try:
            self.log(f"ℹ️ Using googletrans version: {googletrans.__version__}")
        except Exception as e:
            self.log(f"ℹ️ Could not determine googletrans version: {e}")
        
        # Ensure the initial model (if loaded) state is reflected
        if self.controller.model:
            self.log(f"ℹ️ Current Whisper model: '{self.controller.selected_model_name.get()}' (loaded).")
        else:
            self.log(f"⚠️ No Whisper model loaded. Please select one or check console logs.")
            if not self.controller.selected_model_name.get() in self.controller.model_options:
                self.controller.selected_model_name.set("base") # Fallback if somehow var is invalid
            # Optionally trigger a load of the default if no model is present
            # self.controller.load_whisper_model(self.controller.selected_model_name.get())


    def on_language_change(self, choice):
        self.log(f"ℹ️ Subtitle language set to: {choice}")
        if choice == "Urdu (Translate)":
            self.log("💡 Note: Urdu translation quality depends on the source audio, model accuracy, and googletrans functionality.")

    def select_video(self):
        # Ensure the filedialog opens on top of the CTk window
        file_path = filedialog.askopenfilename(
            master=self.controller, # Parent this to the main app window
            title="Select Video File",
            filetypes=[("Video Files", "*.mp4 *.mkv *.mov *.avi"), ("All files", "*.*")]
        )
        if file_path:
            self.controller.video_path = file_path
            self.video_label.configure(text=f"📹: {os.path.basename(file_path)}")
            self.log(f"🎥 Video selected: {file_path}")
        else:
            self.log("🚫 Video selection cancelled.")

    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        # Ensure UI updates happen on the main thread
        def _log_update():
            self.log_box.insert("end", f"[{timestamp}] {message}\n")
            self.log_box.see("end") # Auto-scroll to the bottom
        self.controller.after(0, _log_update)


    def update_progress(self, value, text=""):
        def _progress_update():
            self.progress_bar.set(value)
            self.progress_label.configure(text=text)
        self.controller.after(0, _progress_update)


    def disable_generate_button(self):
        def _disable():
            self.generate_btn.configure(state="disabled", text="⏳ Processing...")
        self.controller.after(0, _disable)

    def enable_generate_button(self):
        def _enable():
            self.generate_btn.configure(state="normal", text="▶️ Generate Subtitles")
        self.controller.after(0, _enable)


    def run_subtitle_thread(self):
        if not self.controller.video_path:
            self.log("⚠️ Please select a video file first.")
            return
        if not self.controller.model:
            self.log("❌ Critical: Whisper AI model not loaded. Please select one from the menu.")
            self.log("🔄 Attempting to load default 'base' model if you haven't selected one...")
            # self.controller.selected_model_name.set("base") # Redundant if menu drives it
            self.controller.load_whisper_model("base") # Attempt to load
            self.log("ℹ️ Model loading initiated. Please click 'Generate Subtitles' again once loaded, or select a model manually.")
            return

        self.disable_generate_button()
        self.update_progress(0, "Starting...")
        thread = threading.Thread(target=self.generate_subtitles, daemon=True)
        thread.start()

    def generate_subtitles(self):
        self.log(f"🚀 Starting subtitle generation for: {os.path.basename(self.controller.video_path)}")
        self.log(f"🤖 Using Whisper model: {self.controller.selected_model_name.get()}")
        self.update_progress(0.05, "Preparing...")

        lang_choice = self.language_menu.get()
        task = "transcribe" # Default task for Whisper
        target_lang_code = None # For googletrans if needed

        if lang_choice == "English (Translate)":
            task = "translate" # Whisper handles direct translation to English
            self.log("🔊 Transcribing and translating to English (via Whisper)...")
        elif lang_choice == "Urdu (Translate)":
            task = "transcribe" # Transcribe in original language first
            target_lang_code = "ur" # Google Translate will translate to Urdu
            self.log("🔊 Transcribing audio (will translate to Urdu post-transcription)...")
        else: # "Original"
            self.log("🔊 Transcribing in original language...")

        try:
            self.update_progress(0.1, "Transcribing audio...")
            # Ensure fp16 is False for CPU, can be True if compatible GPU is available and desired
            transcription_result = self.controller.model.transcribe(
                self.controller.video_path,
                task=task,
                fp16=False # Safer for broader CPU compatibility
            )
            segments = transcription_result["segments"]
            detected_language = transcription_result.get("language", "unknown")
            self.log(f"🗣️ Detected audio language: {detected_language.upper()}")
            self.log(f"✅ Transcription complete. Segments found: {len(segments)}")
            self.update_progress(0.5, "Transcription complete.")

            # Post-transcription translation for Urdu
            if lang_choice == "Urdu (Translate)" and target_lang_code and segments:
                self.log(f"🌐 Translating {len(segments)} segments to Urdu using googletrans...")
                translated_segments = []
                total_segments = len(segments)
                for i, segment in enumerate(segments):
                    try:
                        # Add a small delay to avoid hitting rate limits too quickly
                        if i > 0 and i % 10 == 0: # After every 10 segments
                            time.sleep(0.5) # Wait for 0.5 seconds
                        
                        translated_text = self.controller.translator.translate(segment["text"], dest=target_lang_code).text
                        translated_segments.append({"start": segment["start"], "end": segment["end"], "text": translated_text})
                        current_progress = 0.5 + (0.2 * ((i + 1) / total_segments)) # Allocate 20% of progress to translation
                        self.update_progress(current_progress, f"Translating segment {i+1}/{total_segments}...")
                    except Exception as e:
                        self.log(f"⚠️ Translation error for a segment: {e}. Using original text.")
                        self.log(f"   Segment text: {segment['text'][:50]}...") # Log part of problematic segment
                        translated_segments.append(segment) # Fallback to original text
                segments = translated_segments # Update segments with translated text
                self.log("✅ Urdu translation complete.")
                self.update_progress(0.7, "Urdu translation complete.")
            elif not segments:
                 self.log("ℹ️ No audio segments found to translate or process.")


            # Create SRT file
            srt_temp_path = os.path.join(self.controller.temp_dir, "subtitles.srt")
            self.write_srt(segments, srt_temp_path)
            self.log(f"📄 Temporary SRT file created: {srt_temp_path}")
            self.update_progress(0.75, "SRT file created.")

            # Prompt user to save the SRT, then proceed to embed
            self.controller.after(0, lambda: self.save_srt_file_dialog(srt_temp_path))

        except Exception as e:
            self.log(f"❌ Critical Error during subtitle generation: {e}")
            import traceback
            self.log(f"Traceback: {traceback.format_exc()}")
            self.update_progress(0, "Error occurred.")
        finally:
            # Re-enable button only if not proceeding to embed or if an error stopped before embed
            # The embedding process will manage the button state itself.
            # This 'finally' might be too early if save_srt_file_dialog then calls embed_subtitles which disables it.
            # Consider enabling it at the very end of all operations or on failure.
            # For now, let save_srt_file_dialog and embed_subtitles manage it.
            # If an error happens *before* save_srt_file_dialog, this ensures button is re-enabled.
            if not (lang_choice and segments): # Simple check, might need refinement
                 self.enable_generate_button()

    def save_srt_file_dialog(self, temp_srt_path):
        """Prompts user to save SRT and then triggers embedding."""
        srt_user_path = filedialog.asksaveasfilename(
            master=self.controller, # Parent to main app
            title="Save SRT Subtitle File",
            defaultextension=".srt",
            filetypes=[("SRT files", "*.srt")],
            initialfile=f"{os.path.splitext(os.path.basename(self.controller.video_path))[0]}_subtitles.srt"
        )
        if srt_user_path:
            try:
                shutil.copyfile(temp_srt_path, srt_user_path)
                self.log(f"💾 Subtitle file saved by user: {srt_user_path}")
            except Exception as e:
                self.log(f"❌ Error saving SRT file: {e}")
        else:
            self.log("ℹ️ User cancelled saving SRT file. Temporary SRT still available for embedding.")
        
        # Proceed to embed subtitles regardless of whether user saved the SRT separately
        self.log("🎞️ Proceeding to embed subtitles...")
        self.disable_generate_button() # Disable again for embedding phase
        threading.Thread(target=self.embed_subtitles, args=(temp_srt_path,), daemon=True).start()


    def write_srt(self, segments, path):
        def format_time(seconds):
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            s = int(seconds % 60)
            # Ensure milliseconds are rounded correctly, not truncated
            ms = int(round((seconds - int(seconds)) * 1000))
            return f"{h:02}:{m:02}:{s:02},{ms:03}"

        with open(path, "w", encoding="utf-8") as f:
            if not segments: # Handle case with no speech or empty segments
                self.log("ℹ️ No segments to write to SRT file. Creating a placeholder SRT.")
                f.write("1\n00:00:00,000 --> 00:00:01,000\n(No speech detected or processed)\n\n") # Placeholder
                return

            for i, segment in enumerate(segments, 1):
                start_time = format_time(segment["start"])
                end_time = format_time(segment["end"])
                text = segment["text"].strip()
                if not text: text = "..." # Placeholder for empty text segments after potential processing
                f.write(f"{i}\n{start_time} --> {end_time}\n{text}\n\n")

    def embed_subtitles(self, srt_path):
        if not os.path.exists(srt_path) or os.path.getsize(srt_path) == 0:
            self.log(f"❌ Cannot embed: SRT file not found or empty at {srt_path}")
            self.update_progress(0, "SRT file missing or empty.")
            self.enable_generate_button()
            return

        output_dir = os.path.join(self.controller.temp_dir, "output_videos")
        os.makedirs(output_dir, exist_ok=True)
        
        base_video_name = os.path.splitext(os.path.basename(self.controller.video_path))[0]
        timestamp_str = time.strftime("%Y%m%d_%H%M%S")
        output_filename = f"{base_video_name}_subtitled_{timestamp_str}.mp4"
        output_path_temp = os.path.join(output_dir, output_filename) # Temporary path for ffmpeg output

        self.log("🔧 Embedding subtitles with FFmpeg...")
        self.update_progress(0.8, "Embedding subtitles...")

        font = self.controller.subtitle_settings["font"]
        size = self.controller.subtitle_settings["size"]
        color = self.controller.subtitle_settings["color"]
      
        color_hex_bgr = {
            "white": "FFFFFF", "yellow": "00FFFF", "green": "00FF00",
            "red": "0000FF", "blue": "FF0000", "black": "000000",
            "cyan": "FFFF00", "magenta": "FF00FF"
        }
        selected_bgr = color_hex_bgr.get(color.lower(), "FFFFFF") # Default to white
        style_primary_color = f"&H00{selected_bgr}" # ASS format: &H<Alpha><BB><GG><RR> (00 for opaque)


        srt_path_for_ffmpeg = srt_path.replace('\\', '/')

        if sys.platform == "win32" and len(srt_path_for_ffmpeg) > 1 and srt_path_for_ffmpeg[1] == ':':
            srt_path_for_ffmpeg = srt_path_for_ffmpeg[0] + '\\:' + srt_path_for_ffmpeg[2:]
        # 3. Escape single quotes within the path itself, as it will be enclosed in single quotes for 'filename='
        srt_path_for_ffmpeg = srt_path_for_ffmpeg.replace("'", "'\\''") # Escapes ' to '\''

        filter_string = f"subtitles=filename='{srt_path_for_ffmpeg}':force_style='FontName={font},FontSize={size},PrimaryColour={style_primary_color},BorderStyle=1,Outline=1,Shadow=0.5,Alignment=2'"

        cmd = [
            "ffmpeg", "-y", # Overwrite output files without asking
            "-i", self.controller.video_path,
            "-vf", filter_string,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23", # Decent quality and speed
            "-c:a", "aac", "-b:a", "192k", # Common audio codec
            output_path_temp
        ]
        self.log(f"🔩 FFmpeg command: {' '.join(cmd)}") # Log the command for debugging

        try:
            # Run FFmpeg
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                self.log(f"❌ FFmpeg Error (code {process.returncode}):")
                self.log(f"Stderr: {stderr}" if stderr else "No stderr output.")
                self.log(f"Stdout: {stdout}" if stdout else "No stdout output.") # Stdout might contain useful info too
                self.update_progress(0, "FFmpeg failed.")
                self.enable_generate_button() # Ensure button is re-enabled on FFmpeg failure
                return # Stop further processing

            # Check if output video was actually created and is not empty
            if not os.path.exists(output_path_temp) or os.path.getsize(output_path_temp) == 0:
                self.log("❌ FFmpeg created an empty or no output video, despite exit code 0.")
                self.log(f"Stderr: {stderr}" if stderr else "No stderr output.")
                self.log(f"Stdout: {stdout}" if stdout else "No stdout output.")
                self.update_progress(0, "Output video error.")
                self.enable_generate_button()
                return

            self.log("✅ Subtitles embedded successfully (temp file).")
            self.update_progress(0.95, "Embedding complete.")

            # Prompt user to save the final video (runs on main thread)
            self.controller.after(0, lambda: self.save_final_video_dialog(output_path_temp))

        except FileNotFoundError:
            self.log("❌ FFmpeg not found. Please ensure FFmpeg is installed and in your system's PATH.")
            self.update_progress(0, "FFmpeg not found.")
            self.enable_generate_button()
        except Exception as e:
            self.log(f"❌ FFmpeg execution error: {e}")
            import traceback
            self.log(f"Traceback: {traceback.format_exc()}")
            self.update_progress(0, "FFmpeg error.")
            self.enable_generate_button() # Re-enable button on other exceptions
        # 'finally' block removed from here as button re-enabling should be conditional

    def save_final_video_dialog(self, temp_video_path):
        """Prompts user to save the final subtitled video."""
        final_video_path = filedialog.asksaveasfilename(
            master=self.controller, # Parent to main app
            title="Save Subtitled Video As...",
            defaultextension=".mp4",
            filetypes=[("MP4 Video", "*.mp4")],
            initialfile=os.path.basename(temp_video_path) # Suggest the generated temp filename
        )
        if final_video_path:
            try:
                shutil.move(temp_video_path, final_video_path) # Move is more efficient than copy
                self.log(f"💾 Final subtitled video saved: {final_video_path}")
                self.update_progress(1, "Video saved!")
                self.play_video(final_video_path)
            except Exception as e:
                self.log(f"❌ Error saving final video: {e}. File might still be at {temp_video_path}")
                self.update_progress(1, "Error saving video.")
        else:
            self.log(f"ℹ️ User cancelled saving. Temp video at: {temp_video_path}")
            self.update_progress(1, "Video processed (not saved by user).")
            self.play_video(temp_video_path) # Offer to play even if not saved by user
        
        self.enable_generate_button() # Final step, re-enable the button

    def play_video(self, path):
        self.log(f"Attempting to play video: {path}")
        try:
            if sys.platform == 'win32':
                os.startfile(path)
            elif sys.platform == 'darwin': # macOS
                subprocess.Popen(['open', path])
            else: # Linux and other POSIX
                subprocess.Popen(['xdg-open', path])
            self.log("🎬 Video playback initiated.")
        except Exception as e:
            self.log(f"❌ Could not play video: {e}")
            self.log(f"💡 Please open manually: {path}")

    def open_settings(self):
        win = ctk.CTkToplevel(self.controller)
        win.title("🎨 Subtitle Style Settings")
        win.geometry("400x380") # Adjusted for better spacing
        win.transient(self.controller)
        win.grab_set()

        settings_frame = ctk.CTkFrame(win, fg_color="transparent")
        settings_frame.pack(expand=True, fill="both", padx=20, pady=20)

        # Font Family
        ctk.CTkLabel(settings_frame, text="Font:", font=self.controller.base_font).pack(anchor="w", pady=(0,2))
        self.font_menu_settings = ctk.CTkOptionMenu(settings_frame, 
                                      values=["Arial", "Helvetica", "Times New Roman", "Verdana", "Tahoma", "Calibri", "Segoe UI"], # Common fonts
                                      font=self.controller.base_font)
        self.font_menu_settings.set(self.controller.subtitle_settings["font"])
        self.font_menu_settings.pack(fill="x", pady=(0,10))

        # Font Size
        self.size_label_settings = ctk.CTkLabel(settings_frame, text=f"Font Size: {self.controller.subtitle_settings['size']}", font=self.controller.base_font)
        self.size_label_settings.pack(anchor="w", pady=(5,2))
        
        self.size_slider_var_settings = ctk.IntVar(value=self.controller.subtitle_settings["size"])
        
        def _update_size_label_settings(value_str): # Slider passes string value
            value = int(float(value_str)) # Convert string from slider to int
            self.size_label_settings.configure(text=f"Font Size: {value}") 
        
        size_slider_settings = ctk.CTkSlider(settings_frame, from_=10, to=48, number_of_steps=38, 
                                 variable=self.size_slider_var_settings, command=_update_size_label_settings)
        size_slider_settings.pack(fill="x", pady=(0,10))
        _update_size_label_settings(str(self.size_slider_var_settings.get())) # Initial label update

        # Text Color
        ctk.CTkLabel(settings_frame, text="Text Color:", font=self.controller.base_font).pack(anchor="w", pady=(5,2))
        self.color_menu_settings = ctk.CTkOptionMenu(settings_frame, values=["white", "yellow", "green", "red", "blue", "black", "cyan", "magenta"],
                                       font=self.controller.base_font)
        self.color_menu_settings.set(self.controller.subtitle_settings["color"])
        self.color_menu_settings.pack(fill="x", pady=(0,20)) # More padding before button

        # Apply Button
        def apply_settings():
            old_settings = dict(self.controller.subtitle_settings)
            self.controller.subtitle_settings["font"] = self.font_menu_settings.get()
            self.controller.subtitle_settings["size"] = int(self.size_slider_var_settings.get())
            self.controller.subtitle_settings["color"] = self.color_menu_settings.get()
            
            # Log changes to the SubtitlePage log if available
            subtitle_page = self.controller.frames.get(SubtitlePage)
            if subtitle_page:
                subtitle_page.log(f"🎨 Subtitle settings updated: Font: {self.font_menu_settings.get()}, Size: {int(self.size_slider_var_settings.get())}, Color: {self.color_menu_settings.get()}")
                if old_settings != self.controller.subtitle_settings:
                    subtitle_page.log("💡 Note: New style settings will apply to the NEXT subtitle generation.")
            win.destroy()

        apply_btn = ctk.CTkButton(settings_frame, text="Apply & Close", command=apply_settings, font=self.controller.button_font)
        apply_btn.pack(pady=10, side="bottom", fill="x")

        win.lift()
        win.focus_force()


if __name__ == "__main__":
    # Check for FFmpeg before starting the app
    if shutil.which("ffmpeg") is None:
        print("ERROR: FFmpeg not found in PATH. FFmpeg is required for embedding subtitles.")
        print("Please install FFmpeg and ensure it's added to your system's PATH.")

    app = SubtitleApp()
    try:
        app.mainloop()
    except Exception as e:
        print(f"An unhandled exception occurred in the main application loop: {e}")
        import traceback
        traceback.print_exc()
    finally: # Ensure temp directory cleanup on any exit
        if hasattr(app, 'temp_dir') and os.path.exists(app.temp_dir):
            try:
                shutil.rmtree(app.temp_dir)
                print(f"Cleaned up temp directory on exit: {app.temp_dir}")
            except Exception as cleanup_e:
                print(f"Error cleaning up temp directory during final exit: {cleanup_e}")