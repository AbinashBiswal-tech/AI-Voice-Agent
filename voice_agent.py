import os
import sys
import math
import time
import threading
import queue
import tkinter as tk
from tkinter import ttk, messagebox
import win32com.client
import pythoncom
import webbrowser 
from urllib.parse import quote_plus
import chat_storage
from view_chats import open_history_window
# Safe import of Google GenAI SDK
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

# Gemini client with automatic retry
def create_gemini_client(api_key):
    retry_options = types.HttpRetryOptions(
        attempts=5,
        initial_delay=1.0,
        max_delay=16.0,
        exp_base=2.0,
        jitter=1.0,
        http_status_codes=[408, 429, 500, 502, 503, 504]
    )

    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            retry_options=retry_options
        )
    )
    
# Safe import of pyttsx3 (Text to speech)
try:
    import pyttsx3
    tts_engine = pyttsx3.init()
    tts_engine.setProperty('rate', 165)
    tts_engine.setProperty('volume', 1.0)
except Exception as e:
    tts_engine = None

# Safe import of SpeechRecognition and PyAudio
try:
    import speech_recognition as sr
    recognizer = sr.Recognizer()
except Exception:
    sr = None
    recognizer = None

# ==========================================
# GEMINI CLIENT & KEY PERSISTENCE
# ==========================================
KEY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".gemini_key")

def load_saved_key():
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key and os.path.exists(KEY_FILE):
        try:
            with open(KEY_FILE, "r", encoding="utf-8") as f:
                key = f.read().strip()
        except Exception:
            pass
    return key

def save_key_to_file(key):
    try:
        with open(KEY_FILE, "w", encoding="utf-8") as f:
            f.write(key.strip())
    except Exception as e:
        print(f"Key save error: {e}")

GEMINI_API_KEY = load_saved_key()
print("GEMINI KEY LOADED: ",bool(GEMINI_API_KEY))

client = None
if GEMINI_API_KEY and genai:
    try:
        client = create_gemini_client(GEMINI_API_KEY)
    except Exception as e:
        print(f"Note: Gemini client initialization: {e}")

# ==========================================
# MODERN DARK MODE GUI WITH FLUID GRADIENTS
# ==========================================
class ModernVoiceAgentApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Python AI Voice Agent • Fluid Dark Mode")
        self.root.geometry("480x640")
        self.root.configure(bg="#080B11")
        self.root.resizable(True, True)

        self.phase = 0.0
        self.is_listening = False
        self.is_speaking = False
        self.audio_level = 0.1
        
        self.speech_queue = queue.Queue()

        # Dedicated TTS worker
        self.tts_thread = threading.Thread(
            target=self.tts_worker,
            daemon=True
        )
        self.tts_thread.start()

        self.setup_ui()
        self.animate_fluid_gradients()
        
    def tts_worker(self):
        """Dedicated TTS worker for continuous speech."""
        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", 165)
            engine.setProperty("volume", 1.0)

            while True:
                text = self.speech_queue.get()

                if text is None:
                    break

                try:
                    self.is_speaking = True

                    engine.say(str(text))
                    engine.runAndWait()

                    print("TTS: Speech completed.")

                except Exception as e:
                    print(f"TTS Error: {e}")

                finally:
                    self.is_speaking = False
                    self.speech_queue.task_done()

            engine.stop()

        except Exception as e:
            print(f"TTS Engine Error: {e}")

    def setup_ui(self):
        # 1. Input & Control Bar (Pack to BOTTOM FIRST so it is always visible!)
        control_frame = tk.Frame(self.root, bg="#080B11")
        control_frame.pack(side="bottom", fill="x", padx=16, pady=(6, 16))

        self.text_input = tk.Entry(control_frame, bg="#1A2234", fg="#F8FAFC", insertbackground="#06B6D4", font=("Segoe UI", 11), relief="flat")
        self.text_input.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 8))
        self.text_input.bind("<Return>", lambda event: self.handle_text_submit())
        self.text_input.focus_set()

        self.send_btn = tk.Button(control_frame, text="Send", font=("Segoe UI", 10, "bold"), bg="#8B5CF6", fg="white", activebackground="#7C3AED", relief="flat", padx=14, command=self.handle_text_submit)
        self.send_btn.pack(side="left", padx=(0, 6))

        self.mic_btn = tk.Button(control_frame, text="🎙 Speak", font=("Segoe UI", 10, "bold"), bg="#D946EF", fg="white", activebackground="#C026D3", relief="flat", padx=12, command=self.toggle_mic)
        self.mic_btn.pack(side="right")

        # 2. Header Badge (Pack to top)
        header_frame = tk.Frame(self.root, bg="#080B11")
        header_frame.pack(side="top", fill="x", pady=(10, 4), padx=16)

        title_sub_frame = tk.Frame(header_frame, bg="#080B11")
        title_sub_frame.pack(side="left", fill="x", expand=True)

        title = tk.Label(title_sub_frame, text="⚡ VOICE AI AGENT", font=("Segoe UI", 15, "bold"), fg="#A855F7", bg="#080B11")
        title.pack(anchor="w")

        key_status = "● Gemini Connected" if (client or os.environ.get("GEMINI_API_KEY")) else "○ Set Gemini Key"
        key_color = "#10B981" if (client or os.environ.get("GEMINI_API_KEY")) else "#F59E0B"
        self.key_btn = tk.Button(header_frame, text=key_status, font=("Segoe UI", 8, "bold"), fg=key_color, bg="#1E293B", activebackground="#334155", relief="flat", padx=8, pady=2, command=self.open_key_config_dialog)
        self.key_btn.pack(side="right")
        
        self.history_btn = tk.Button(
            header_frame,
            text="☰ History",
            font=("Segoe UI", 9, "bold"),
            fg="#FFFFFF",
            bg="#252B3A",
            activebackground="#334155",
            relief="flat",
            padx=10,
            pady=5,
            command=self.open_chat_history
        )
        self.history_btn.pack(side="right", padx=5)

        subtitle = tk.Label(title_sub_frame, text="Powered by Gemini AI • Dark Mode Aesthetic", font=("Segoe UI", 9), fg="#94A3B8", bg="#080B11")
        subtitle.pack(anchor="w")

        # 3. Fluid Gradient Visualizer Canvas
        self.canvas = tk.Canvas(self.root, width=440, height=180, bg="#080B11", highlightthickness=0)
        self.canvas.pack(side="top", pady=4)

        # 4. Status & Transcript Label
        self.status_label = tk.Label(self.root, text="● READY • Speak or Type Command", font=("Segoe UI", 10, "bold"), fg="#06B6D4", bg="#080B11")
        self.status_label.pack(side="top", pady=2)

        self.transcript_label = tk.Label(self.root, text="Click '🎙 Speak' or type your prompt in the box below", font=("Segoe UI", 9), fg="#94A3B8", bg="#080B11", wraplength=420)
        self.transcript_label.pack(side="top", pady=2)

        # 5. Chat / Code Response Area (Fills remaining middle space)
        chat_frame = tk.Frame(self.root, bg="#111726", highlightbackground="#2D3748", highlightthickness=1)
        chat_frame.pack(side="top", fill="both", expand=True, padx=16, pady=(4, 6))

        self.response_text = tk.Text(chat_frame, bg="#0F172A", fg="#E2E8F0", font=("Consolas", 10), insertbackground="#06B6D4", wrap="word", relief="flat")
        self.response_text.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        self.response_text.insert("1.0", "AI Agent: Hello! I am your Voice AI Assistant. You can speak to me or type your request below!\n\n")
        
    
    def open_chat_history(self):
        open_history_window(self.root)
        
    def load_conversation(self, conversation_id):
        messages = chat_storage.get_messages(conversation_id)

        self.current_conversation_id = conversation_id
        self.response_text.delete("1.0", tk.END)

        for role, content, created_at in messages:
            label = "You" if role == "user" else "Agent"
            self.response_text.insert(
                tk.END,
                f"{label}: {content}\n\n"
            )

        self.response_text.see(tk.END)

    def new_chat(self):
        self.current_conversation_id = None
        self.response_text.delete("1.0", tk.END)
        self.response_text.insert(
            tk.END,
            "AI Agent: Hello! How can I help you?\n\n"
        )

        
    def handle_special_command(self, prompt):
        text = prompt.lower().strip()

        # YouTube play/search command
        if "youtube" in text or "play" in text:
            search_text = text

            for word in [
                "hey gemini",
                "gemini",
                "please",
                "play",
                "song",
                "music",
                "on youtube",
                "in youtube",
                "youtube",
                "for me",
                "the"
            ]:
                search_text = search_text.replace(word, " ")

            search_text = " ".join(search_text.split()).strip()

            if not search_text:
                search_text = "trending songs"

            url = "https://www.youtube.com/results?search_query=" + quote_plus(search_text)

            # ACTUALLY OPEN YOUTUBE
            webbrowser.open(url)

            return f"Sure! Playing '{search_text}' on YouTube. Enjoy!"

        return None

    def animate_fluid_gradients(self):
        """Draw animated fluid glowing orbs with color blending"""
        self.phase += 0.05
        self.canvas.delete("all")

        center_x, center_y = 230, 115
        pulse = math.sin(self.phase) * 10

        # 1. Background fluid glow circles
        glow_radius = 85 + pulse + (self.audio_level * 40)
        c1_x = center_x + math.sin(self.phase * 0.7) * 20
        c1_y = center_y + math.cos(self.phase * 0.8) * 15
        self.canvas.create_oval(c1_x - glow_radius, c1_y - glow_radius, c1_x + glow_radius, c1_y + glow_radius, fill="#2E1065", outline="")

        c2_x = center_x - math.cos(self.phase * 0.6) * 18
        c2_y = center_y + math.sin(self.phase * 0.9) * 16
        self.canvas.create_oval(c2_x - glow_radius*0.85, c2_y - glow_radius*0.85, c2_x + glow_radius*0.85, c2_y + glow_radius*0.85, fill="#3B0764", outline="")

        # 2. Main Central Orb
        orb_r = 50 + (self.audio_level * 22)
        orb_color = "#D946EF" if self.is_listening else ("#06B6D4" if self.is_speaking else "#8B5CF6")
        self.canvas.create_oval(center_x - orb_r, center_y - orb_r, center_x + orb_r, center_y + orb_r, fill=orb_color, outline="#C084FC", width=2)

        # 3. Inner Core Glow
        inner_r = orb_r * 0.55
        self.canvas.create_oval(center_x - inner_r, center_y - inner_r, center_x + inner_r, center_y + inner_r, fill="#FFFFFF", outline="")

        self.root.after(35, self.animate_fluid_gradients)

    def toggle_mic(self):
        if self.is_listening:
            return
        
        # Check if PyAudio / microphone is available
        has_mic = False
        try:
            import pyaudiowpatch as pyaudio
            has_mic = True
        except ImportError:
            has_mic = False

        if not has_mic or sr is None:
            # On Windows without PyAudio, show a voice dialog prompt so user can speak using Windows Dictation (Win + H)
            self.show_windows_voice_dialog()
            return

        threading.Thread(target=self.listen_for_voice, daemon=True).start()

    def show_windows_voice_dialog(self):
        """Windows Voice fallback using Windows built-in Speech Recognizer or Windows Dictation (Win + H)"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Voice Input (Windows)")
        dialog.geometry("400x230")
        dialog.configure(bg="#0F172A")
        dialog.resizable(False, False)

        lbl = tk.Label(dialog, text="🎙️ Windows Voice Input", font=("Segoe UI", 12, "bold"), fg="#D946EF", bg="#0F172A")
        lbl.pack(pady=(15, 6))

        info = tk.Label(
            dialog,
            text="Tip: Windows has built-in Speech-to-Text!\nPress [Windows Key + H] to speak anywhere on your PC.\nOr type your command below:",
            font=("Segoe UI", 9),
            fg="#94A3B8",
            bg="#0F172A",
            justify="center"
        )
        info.pack(pady=4)

        entry = tk.Entry(dialog, bg="#1E293B", fg="#F8FAFC", insertbackground="#06B6D4", font=("Segoe UI", 11), relief="flat")
        entry.pack(fill="x", padx=24, pady=10, ipady=6)
        entry.focus_set()

        def submit_dialog():
            val = entry.get().strip()
            if val:
                dialog.destroy()
                self.transcript_label.config(text=f"You said: \"{val}\"")
                threading.Thread(target=self.process_agent_query, args=(val,), daemon=True).start()

        entry.bind("<Return>", lambda e: submit_dialog())

        btn = tk.Button(dialog, text="Submit Voice/Text", font=("Segoe UI", 9, "bold"), bg="#8B5CF6", fg="white", relief="flat", padx=12, pady=4, command=submit_dialog)
        btn.pack(pady=6)

    def open_key_config_dialog(self):
        """Allows user to paste or update their Gemini API key directly in the GUI"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Configure Gemini API Key")
        dialog.geometry("440x220")
        dialog.configure(bg="#0F172A")
        dialog.resizable(False, False)

        lbl = tk.Label(dialog, text="🔑 Enter Gemini API Key", font=("Segoe UI", 12, "bold"), fg="#A855F7", bg="#0F172A")
        lbl.pack(pady=(16, 4))

        info = tk.Label(
            dialog,
            text="Paste your Google Gemini API key below (from Google AI Studio).\nIt will be saved and used immediately for all queries.",
            font=("Segoe UI", 9),
            fg="#94A3B8",
            bg="#0F172A",
            justify="center"
        )
        info.pack(pady=4)

        current_val = load_saved_key()
        entry = tk.Entry(dialog, bg="#1E293B", fg="#F8FAFC", insertbackground="#06B6D4", font=("Segoe UI", 10), relief="flat")
        entry.pack(fill="x", padx=20, pady=10, ipady=6)
        if current_val:
            entry.insert(0, current_val)
        entry.focus_set()

        def save_key():
            new_key = entry.get().strip()
            if new_key:
                os.environ["GEMINI_API_KEY"] = new_key
                save_key_to_file(new_key)
                global client
                if genai:
                    try:
                        client = create_gemini_client(new_key)
                    except Exception as e:
                        print(f"Error updating client: {e}")
                self.key_btn.config(text="● Gemini Connected", fg="#10B981")
                messagebox.showinfo("Success", "Gemini API key saved! You are now connected to Gemini AI.")
                dialog.destroy()

        btn = tk.Button(dialog, text="Save & Connect", font=("Segoe UI", 9, "bold"), bg="#10B981", fg="white", relief="flat", padx=16, pady=4, command=save_key)
        btn.pack(pady=8)

    def listen_for_voice(self):
        self.is_listening = True
        self.status_label.config(text="● LISTENING • Speak now...", fg="#D946EF")
        self.mic_btn.config(bg="#EF4444", text="Listening...")

        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.8)
                self.audio_level = 0.5
                audio = recognizer.listen(source, timeout=6, phrase_time_limit=12)

            self.status_label.config(text="● THINKING • Transcribing...", fg="#F59E0B")
            self.audio_level = 0.2
            user_text = recognizer.recognize_google(audio)
            self.transcript_label.config(text=f"You said: \"{user_text}\"")
            self.process_agent_query(user_text)

        except Exception as e:
            self.status_label.config(text=f"● Status: Ready", fg="#06B6D4")
            self.transcript_label.config(text="Microphone timeout or speech not heard. Type below.")
        finally:
            self.is_listening = False
            self.audio_level = 0.1
            self.mic_btn.config(bg="#D946EF", text="🎙 Speak")

    def handle_text_submit(self):
        query = self.text_input.get().strip()
        if not query:
            return
        self.text_input.delete(0, tk.END)
        self.transcript_label.config(text=f"Prompt: \"{query}\"")
        threading.Thread(target=self.process_agent_query, args=(query,), daemon=True).start()
        
        def tts_worker(self):
            """Dedicated thread for continuous text-to-speech."""
            try:
                engine = pyttsx3.init()
                engine.setProperty("rate", 165)
                engine.setProperty("volume", 1.0)

                while True:
                    text = self.speech_queue.get()

                    if text is None:
                        break

                try:
                    self.is_speaking = True

                    engine.say(str(text))
                    engine.runAndWait()

                    print("TTS: Speech completed.")

                except Exception as e:
                    print(f"TTS Error: {e}")

                finally:
                    self.is_speaking = False
                    self.speech_queue.task_done()

                engine.stop()

            except Exception as e:
                print(f"TTS Engine Error: {e}")

    def process_agent_query(self, prompt):

        # Create one conversation for this application session
        if not hasattr(self, "current_conversation_id"):
            self.current_conversation_id = chat_storage.create_conversation(
                title=prompt[:50] if prompt else "New Chat"
        )

        # Save user message
        try:
            chat_storage.save_message(
                self.current_conversation_id,
                "user",
                prompt
            )
        except Exception as e:
            print(f"Chat save error: {e}")

        special_response = self.handle_special_command(prompt)

        if special_response:
            self.response_text.insert(
                tk.END,
                f"User: {prompt}\n\n"
            )
            self.response_text.insert(
                tk.END,
                f"Agent: {special_response}\n\n"
            )
            self.response_text.see(tk.END)
            
            try:
                chat_storage.save_message(
                self.current_conversation_id,
                "assistant",
                special_response
                )
            except Exception as e:
                print(f"Chat save error: {e}")

            if tts_engine:
                try:
                    tts_engine.say(special_response)
                    tts_engine.runAndWait()
                except:
                    pass
                self.status_label.config(text="● READY • Speak or Type Command",fg="#06B6D4")
            return
        
        self.status_label.config(text="● SYNTHESIZING • Thinking...", fg="#06B6D4")
        
        self.response_text.insert(tk.END, f"User: {prompt}\n")
        self.response_text.see(tk.END)
   

        response_content = ""
        # Dynamically check/initialize client if key is in env
        current_key = os.environ.get("GEMINI_API_KEY", "").strip()
        active_client = client
        if not active_client and current_key and genai:
            try:
                active_client = create_gemini_client(current_key)
            except Exception as e:
                print(f"Client init error: {e}")

        if active_client:
            models_to_try = ["gemini-3.5-flash"]
            last_err = None
            for model_name in models_to_try:
                try:
                    ai_response = active_client.models.generate_content(
                        model=model_name,
                        contents=f"You are a helpful Voice AI Agent. Answer concisely and conversationally. User asks: {prompt}"
                    )
                    response_content = ai_response.text
                    last_err = None
                    break
                except Exception as e:
                    last_err = e
                    continue

            if last_err and not response_content:
                err_msg = str(last_err)
                print(f"Gemini API Error: {err_msg}")
                if "API_KEY_INVALID" in err_msg or "400" in err_msg:
                    response_content = (
                        "Your Gemini API key appears invalid.\n"
                        "Please get a free API key starting with 'AIzaSy...' from https://aistudio.google.com/app/apikey"
                    )
                else:
                    response_content = f"Gemini Error ({err_msg[:90]}).\n\n" + self.generate_offline_smart_response(prompt)
        else:
            response_content = self.generate_offline_smart_response(prompt)

        self.response_text.insert(tk.END, f"Agent: {response_content}\n\n")
        self.response_text.see(tk.END)
        
        try:
            chat_storage.save_message(
                self.current_conversation_id,
                "assistant",
                response_content
            )
        except Exception as e:
            print(f"Chat save error: {e}")
            
        if response_content:
            threading.Thread(
                target=self.speak_response,
                args=(response_content,),
                daemon=True
            ).start()

        # Send response to dedicated TTS worker
        if response_content:
            self.speech_queue.put(response_content)

        self.status_label.config(text="● READY • Speak or Type Command", fg="#06B6D4")

    def generate_offline_smart_response(self, prompt: str) -> str:
        """Intelligent conversational responses that work completely offline without an API key."""
        lower = prompt.lower().strip()
        
        if any(w in lower for w in ["hello", "hi", "hey", "greetings"]):
            return "Hello Abinash I am your AI Voice Agent. I can chat with you, help with Python code, explain concepts, and speak responses aloud."
        elif "time" in lower:
            import datetime
            return f"The current system time is {datetime.datetime.now().strftime('%I:%M %p')}."
        elif "date" in lower or "today" in lower:
            import datetime
            return f"Today's date is {datetime.datetime.now().strftime('%A, %B %d, %Y')}."
        elif "who are you" in lower or "what are you" in lower:
            return "I am an intelligent AI Voice Agent with dark mode aesthetics, fluid animated gradients, and text-to-speech capabilities."
        elif "python" in lower:
            return "Python is a high-level, interpreted programming language known for readability and strong support for AI, data science, and web applications."
        elif "weather" in lower:
            return "I can't check live satellites without an internet connection, but it's always a great day for coding!"
        elif "joke" in lower:
            return "Why do programmers prefer dark mode? Because light attracts bugs!"
        elif "code" in lower or "help" in lower:
            return "You can ask me programming questions, request Python functions, or test voice speech queries directly."
        else:
            return f"I received your query: \"{prompt}\". I'm running in offline intelligent mode with animated fluid gradients and text-to-speech audio feedback. Add a GEMINI_API_KEY to unlock full generative AI capabilities!"
    
    def speak_response(self, text):
        """Speak AI response using Windows SAPI."""
        try:
            print("TTS START:", text)

            pythoncom.CoInitialize()

            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            speaker.Volume = 100
            speaker.Rate = 0

            self.is_speaking = True

            speaker.Speak(str(text))

            self.is_speaking = False
            pythoncom.CoUninitialize()

            print("TTS FINISHED")

        except Exception as e:
            self.is_speaking = False
            print("TTS ERROR:", repr(e))

            try:
                pythoncom.CoUninitialize()
            except:
                pass


# ==========================================
# MAIN ENTRY POINT
# ==========================================
if __name__ == "__main__":
    print("Starting Voice AI Agent GUI...")
    root = tk.Tk()
    app = ModernVoiceAgentApp(root)
    root.mainloop()
