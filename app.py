import time
import json
import threading
import sys
from pynput import mouse, keyboard
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Controller as KeyboardController, Listener as KeyboardListener
from colorama import init, Fore, Back, Style


init(autoreset=True)

class ColorLogger:
    @staticmethod
    def info(message):
        print(Fore.CYAN + "ℹ " + Style.RESET_ALL + message)
    
    @staticmethod
    def success(message):
        print(Fore.GREEN + "✓ " + Style.RESET_ALL + message)
    
    @staticmethod
    def warning(message):
        print(Fore.YELLOW + "⚠ " + Style.RESET_ALL + message)
    
    @staticmethod
    def error(message):
        print(Fore.RED + "✗ " + Style.RESET_ALL + message)
    
    @staticmethod
    def recording(message):
        print(Fore.RED + "🔴 " + Style.RESET_ALL + message)
    
    @staticmethod
    def playback(message):
        print(Fore.BLUE + "▶ " + Style.RESET_ALL + message)
    
    @staticmethod
    def config(message):
        print(Fore.MAGENTA + "⚙ " + Style.RESET_ALL + message)

class MacroRecorder:
    def __init__(self):
        self.actions = []
        self.is_recording = False
        self.start_time = 0
        self.lock = threading.Lock()
        self.active_keys = set()
        self.active_buttons = set()
        self.control_keys = {
            Key.f8,  # Iniciar grabación
            Key.f9,  # Detener grabación
            Key.f10, # Reproducir
            Key.f11, # Configurar repeticiones
            Key.f12  # Salir
        }

    def record_action(self, action_type, **kwargs):
        with self.lock:
            if self.is_recording:
                self.actions.append({
                    'type': action_type,
                    'time': time.time() - self.start_time,
                    **kwargs
                })

    def start_recording(self):
        with self.lock:
            self.actions = []
            self.is_recording = True
            self.start_time = time.time()
            ColorLogger.recording("Grabación iniciada")

    def stop_recording(self):
        with self.lock:
            self.is_recording = False
            ColorLogger.success(f"Grabación detenida - {len(self.actions)} acciones capturadas")
            self._release_all()

    def _release_all(self):
        kb = KeyboardController()
        ms = MouseController()
        for key in list(self.active_keys):
            try: kb.release(key)
            except: pass
        for btn in list(self.active_buttons):
            try: ms.release(btn)
            except: pass

class MacroPlayer:
    def __init__(self, recorder):
        self.recorder = recorder
        self.mouse = MouseController()
        self.keyboard = KeyboardController()
        self.is_playing = False
        self.playback_speed = 1.0
        self.repeat_times = 1  # 1 = una vez, 0 = infinito
        self.stop_requested = False

    def play_actions(self):
        if self.is_playing or not self.recorder.actions:
            return
            
        def playback():
            self.is_playing = True
            self.stop_requested = False
            try:
                iteration = 0
                while True:
                    iteration += 1
                    if self.stop_requested or (self.repeat_times > 0 and iteration > self.repeat_times):
                        break
                        
                    repeat_text = f"{iteration}/{self.repeat_times}" if self.repeat_times > 0 else f"{iteration} (∞)"
                    ColorLogger.playback(f"Reproduciendo [{repeat_text}]...")
                    
                    start_time = time.time()
                    last_time = 0
                    
                    for action in self.recorder.actions:
                        if self.stop_requested:
                            break
                            
                        delay = (action['time'] - last_time) / self.playback_speed
                        if delay > 0: time.sleep(delay)
                        last_time = action['time']
                        self._execute_action(action)
                        
                    self.recorder._release_all()
                    
            finally:
                self.is_playing = False
                if not self.stop_requested:
                    ColorLogger.success("Reproducción completada")
                else:
                    ColorLogger.warning("Reproducción detenida")
                
        threading.Thread(target=playback, daemon=True).start()

    def _execute_action(self, action):
        try:
            if action['type'] == 'move':
                self.mouse.position = (action['x'], action['y'])
            elif action['type'] == 'click_press':
                self.mouse.position = (action['x'], action['y'])
                self.mouse.press(eval(action['button']))
            elif action['type'] == 'click_release':
                self.mouse.position = (action['x'], action['y'])
                self.mouse.release(eval(action['button']))
            elif action['type'] == 'scroll':
                self.mouse.position = (action['x'], action['y'])
                self.mouse.scroll(action['dx'], action['dy'])
            elif action['type'] == 'key_press':
                key = self._parse_key(action['key'])
                if key not in self.recorder.control_keys:
                    self.keyboard.press(key)
            elif action['type'] == 'key_release':
                key = self._parse_key(action['key'])
                if key not in self.recorder.control_keys:
                    self.keyboard.release(key)
        except Exception as e:
            ColorLogger.error(f"Error ejecutando acción: {e}")

    def _parse_key(self, key_str):
        try: return eval(key_str) if key_str.startswith('Key.') else key_str
        except: return key_str

    def stop_playback(self):
        self.stop_requested = True
        self.recorder._release_all()

class MacroManager:
    def __init__(self):
        self.recorder = MacroRecorder()
        self.player = MacroPlayer(self.recorder)
        self.setup_listeners()
        self.show_banner()
        self.show_help()

    def show_banner(self):
        print(Fore.YELLOW + """
  __  __           _                     _____           _             
 |  \/  |         | |                   / ____|         | |            
 | \  / | __ _ ___| |_ ___ _ __ ______ | |     ___ _ __ | |_ ___ _ __  
 | |\/| |/ _` / __| __/ _ \ '__|______| |    / _ \ '_ \| __/ _ \ '__| 
 | |  | | (_| \__ \ ||  __/ |         | |___|  __/ | | | ||  __/ |    
 |_|  |_|\__,_|___/\__\___|_|          \_____\___|_| |_|\__\___|_|    
        """ + Style.RESET_ALL)

    def show_help(self):
        print(Fore.CYAN + "\nCONTROLES PRINCIPALES:")
        print(Fore.WHITE + "┌─────────┬───────────────────────────────────────┐")
        print(Fore.WHITE + "│ " + Fore.YELLOW + "Tecla   " + Fore.WHITE + "│ " + Fore.CYAN + "Función                            " + Fore.WHITE + "│")
        print(Fore.WHITE + "├─────────┼───────────────────────────────────────┤")
        print(Fore.WHITE + "│ " + Fore.GREEN + "F8      " + Fore.WHITE + "│ " + Fore.WHITE + "Iniciar grabación                  " + Fore.WHITE + "│")
        print(Fore.WHITE + "│ " + Fore.GREEN + "F9      " + Fore.WHITE + "│ " + Fore.WHITE + "Detener grabación                  " + Fore.WHITE + "│")
        print(Fore.WHITE + "│ " + Fore.GREEN + "F10     " + Fore.WHITE + "│ " + Fore.WHITE + "Reproducir acciones                " + Fore.WHITE + "│")
        print(Fore.WHITE + "│ " + Fore.GREEN + "F11     " + Fore.WHITE + "│ " + Fore.WHITE + "Configurar repeticiones            " + Fore.WHITE + "│")
        print(Fore.WHITE + "│ " + Fore.GREEN + "F12     " + Fore.WHITE + "│ " + Fore.WHITE + "Salir del programa                 " + Fore.WHITE + "│")
        print(Fore.WHITE + "└─────────┴───────────────────────────────────────┘" + Style.RESET_ALL)

    def setup_listeners(self):
        self.mouse_listener = mouse.Listener(
            on_move=self._on_move,
            on_click=self._on_click,
            on_scroll=self._on_scroll)
        self.mouse_listener.start()
        
        self.keyboard_listener = KeyboardListener(
            on_press=self._on_key_press,
            on_release=self._on_key_release)
        self.keyboard_listener.start()

    def _on_move(self, x, y): self.recorder.record_action('move', x=x, y=y)
    def _on_click(self, x, y, button, pressed):
        if pressed:
            self.recorder.active_buttons.add(button)
            self.recorder.record_action('click_press', x=x, y=y, button=str(button))
        else:
            if button in self.recorder.active_buttons:
                self.recorder.active_buttons.remove(button)
            self.recorder.record_action('click_release', x=x, y=y, button=str(button))
    def _on_scroll(self, x, y, dx, dy): self.recorder.record_action('scroll', x=x, y=y, dx=dx, dy=dy)

    def _on_key_press(self, key):
        try:
            if key == Key.f8 and not self.recorder.is_recording:
                self.recorder.start_recording()
            elif key == Key.f9 and self.recorder.is_recording:
                self.recorder.stop_recording()
            elif key == Key.f10 and not self.player.is_playing:
                self.player.play_actions()
            elif key == Key.f11 and not self.recorder.is_recording:
                self._set_repetitions()
            elif key == Key.f12:
                self._clean_exit()
                return False
            
            if self.recorder.is_recording and key not in self.recorder.control_keys:
                char = key.char if hasattr(key, 'char') else str(key)
                self.recorder.active_keys.add(key)
                self.recorder.record_action('key_press', key=char)
                
        except Exception as e: ColorLogger.error(f"Error en key_press: {e}")

    def _on_key_release(self, key):
        try:
            if self.recorder.is_recording and key not in self.recorder.control_keys:
                char = key.char if hasattr(key, 'char') else str(key)
                if key in self.recorder.active_keys:
                    self.recorder.active_keys.remove(key)
                self.recorder.record_action('key_release', key=char)
        except Exception as e: ColorLogger.error(f"Error en key_release: {e}")

    def _set_repetitions(self):
        ColorLogger.config("\nCONFIGURAR REPETICIONES")
        print(Fore.WHITE + "┌──────────────┬──────────────────────────────┐")
        print(Fore.WHITE + "│ " + Fore.CYAN + "Opción      " + Fore.WHITE + "│ " + Fore.CYAN + "Descripción               " + Fore.WHITE + "│")
        print(Fore.WHITE + "├──────────────┼──────────────────────────────┤")
        print(Fore.WHITE + "│ " + Fore.YELLOW + "0           " + Fore.WHITE + "│ " + Fore.WHITE + "Repetición infinita        " + Fore.WHITE + "│")
        print(Fore.WHITE + "│ " + Fore.YELLOW + "1-9         " + Fore.WHITE + "│ " + Fore.WHITE + "Número de repeticiones     " + Fore.WHITE + "│")
        print(Fore.WHITE + "└──────────────┴──────────────────────────────┘" + Style.RESET_ALL)
        
        choice = input(Fore.CYAN + "\nSeleccione el número de repeticiones: " + Style.RESET_ALL)
        try:
            reps = int(choice)
            self.player.repeat_times = reps if reps > 0 else 0
            ColorLogger.success(f"Repeticiones configuradas: {Fore.YELLOW}{'∞' if reps == 0 else reps}")
        except:
            ColorLogger.warning("Entrada inválida. Usando 1 repetición")

    def _clean_exit(self):
        ColorLogger.info("\nSaliendo limpiamente...")
        self.player.stop_playback()
        self.recorder.stop_recording()
        self.mouse_listener.stop()
        self.keyboard_listener.stop()
        time.sleep(0.5)
        sys.exit(0)

    def run(self):
        try:
            while True: time.sleep(1)
        except KeyboardInterrupt:
            self._clean_exit()

if __name__ == "__main__":
    try:
        MacroManager().run()
    except Exception as e:
        ColorLogger.error(f"Error inesperado: {e}")
        sys.exit(1)