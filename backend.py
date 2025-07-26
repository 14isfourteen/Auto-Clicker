# backend.py - v1.0

import time
import threading
from pynput import keyboard, mouse

class ClickerBackend:
    def __init__(self, update_gui_callback):
        self.program_running_event = threading.Event()
        self.program_running_event.set()
        self.action_active_event = threading.Event()
        self.master_switch_on = False
        
        self.is_listening_for_action_key = False
        self.is_listening_for_trigger_key = False
        
        self.action_key = None # 这里可以存放键盘键，也可以存放鼠标键
        self.trigger_key = None
        self.click_interval = 0.02

        # 新增：鼠标控制器
        self.mouse_controller = mouse.Controller()
        self.keyboard_controller = keyboard.Controller()
        
        self.action_thread = None
        self.update_gui = update_gui_callback

        self.keyboard_listener = keyboard.Listener(on_press=self._on_press, daemon=True)
        self.mouse_listener = mouse.Listener(on_click=self._on_click, daemon=True)
        self.keyboard_listener.start()
        self.mouse_listener.start()

    def _format_key_for_display(self, key):
        if key is None: return "[尚未设置]"
        if hasattr(key, 'char') and key.char: return f"'{key.char}'"
        if hasattr(key, 'name'):
            # 区分是鼠标键还是键盘特殊键
            if isinstance(key, mouse.Button):
                return f"鼠标-{key.name.capitalize()}"
            return key.name.capitalize()
        return str(key)

    def _action_loop(self):
        """核心改进：增加对鼠标连点的判断"""
        try:
            while self.action_active_event.is_set() and self.program_running_event.is_set():
                
                # 判断要连点的是键盘还是鼠标
                if isinstance(self.action_key, keyboard.Key) or isinstance(self.action_key, keyboard.KeyCode):
                    self.keyboard_controller.press(self.action_key)
                    self.keyboard_controller.release(self.action_key)
                elif isinstance(self.action_key, mouse.Button):
                    self.mouse_controller.click(self.action_key, 1) # 模拟鼠标点击
                
                total_wait_time = 0; step = 0.01
                while total_wait_time < self.click_interval:
                    if not self.action_active_event.is_set() or not self.program_running_event.is_set():
                        return
                    time.sleep(step)
                    total_wait_time += step
        except Exception as e:
            self.update_gui("status", f"连点线程错误: {e}", "red")

    def _toggle_action(self):
        if self.action_active_event.is_set():
            self.action_active_event.clear()
            self.update_gui("status", "连点已停止", "blue")
        else:
            if self.action_key is None:
                self.update_gui("status", "错误: 未设置动作按键!", "red")
                return
            self.action_active_event.set()
            if self.action_thread is None or not self.action_thread.is_alive():
                 self.action_thread = threading.Thread(target=self._action_loop, daemon=True)
                 self.action_thread.start()
            self.update_gui("status", "连点运行中...", "green")

    def _on_press(self, key):
        """键盘监听回调，现在只在需要时处理动作键"""
        try:
            if self.is_listening_for_action_key:
                self.action_key = key; self.is_listening_for_action_key = False
                self.update_gui("action_key", self._format_key_for_display(self.action_key))
                self.update_gui("status", "动作按键(键盘)已记录!"); return
                
            if self.is_listening_for_trigger_key:
                self.trigger_key = key; self.is_listening_for_trigger_key = False
                self.update_gui("trigger_key", self._format_key_for_display(self.trigger_key))
                self.update_gui("status", "触发按键已记录!"); return
                
            if self.master_switch_on and key == self.trigger_key:
                self._toggle_action()
        except Exception as e:
            self.update_gui("status", f"键盘监听错误: {e}", "red")

    def _on_click(self, x, y, button, pressed):
        """鼠标监听回调，现在也可以录制动作键"""
        try:
            if not pressed: return
            
            # 录制动作键（鼠标）
            if self.is_listening_for_action_key:
                self.action_key = button; self.is_listening_for_action_key = False
                self.update_gui("action_key", self._format_key_for_display(self.action_key))
                self.update_gui("status", "动作按键(鼠标)已记录!"); return
                
            # 录制触发键（鼠标）
            if self.is_listening_for_trigger_key:
                self.trigger_key = button; self.is_listening_for_trigger_key = False
                self.update_gui("trigger_key", self._format_key_for_display(self.trigger_key))
                self.update_gui("status", "触发按键 (鼠标) 已记录!"); return
                
            # 响应触发
            if self.master_switch_on and button == self.trigger_key:
                self._toggle_action()
        except Exception as e:
             self.update_gui("status", f"鼠标监听错误: {e}", "red")

    def set_interval(self, interval_str):
        try:
            interval = float(interval_str)
            if interval >= 0.01:
                self.click_interval = interval
                self.update_gui("status", f"连点间隔已设为 {interval:.2f} 秒")
            else:
                self.update_gui("status", "错误: 间隔不能小于0.01秒!", "red")
        except (ValueError, TypeError):
             self.update_gui("status", "错误: 请输入有效的数字间隔!", "red")

    def toggle_master_switch(self, is_on):
        self.master_switch_on = is_on
        if self.master_switch_on:
            self.update_gui("status", "总开关已开启，等待触发...", "blue")
        else:
            if self.action_active_event.is_set():
                self.action_active_event.clear()
            self.update_gui("status", "总开关已关闭", "gray")

    def start_listening_for_action_key(self):
        self.is_listening_for_trigger_key = False
        self.is_listening_for_action_key = True
        # 改进：提示用户可以按键盘或鼠标
        self.update_gui("status", "请按下您想连点的【键盘或鼠标按键】...", "orange")

    def start_listening_for_trigger_key(self):
        self.is_listening_for_action_key = False
        self.is_listening_for_trigger_key = True
        self.update_gui("status", "请按下您想用来触发的【键盘或鼠标宏按键】...", "orange")

    def stop_all(self):
        self.program_running_event.clear()
        self.action_active_event.clear()