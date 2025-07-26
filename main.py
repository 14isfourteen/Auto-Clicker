# main.py - v1.0 (Final - Tooltip Refined)

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import ctypes
import configparser
import os
import webbrowser

def set_dpi_awareness():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass

from backend import ClickerBackend

APP_NAME = "MyClicker"
CONFIG_DIR = os.path.join(os.getenv('APPDATA'), APP_NAME)
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.ini')

def load_config():
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        return config.getboolean('Settings', 'show_startup_info', fallback=True)
    return True

def save_config(show_info):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    config = configparser.ConfigParser()
    config['Settings'] = {'show_startup_info': 'yes' if show_info else 'no'}
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)

def center_window(window):
    window.update_idletasks()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    window_width = window.winfo_width()
    window_height = window.winfo_height()
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    window.geometry(f'+{x}+{y}')

# --- 核心改进：添加朋友提供的 Tooltip 类 ---
class Tooltip:
    def __init__(self, widget, text, delay=500):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tipwindow = None
        self.id = None
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.delay, self.showtip)

    def unschedule(self):
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None

    def showtip(self, event=None):
        if self.tipwindow or not self.text:
            return
        # 获取控件在屏幕上的精确位置
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 1
        
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True) # 移除窗口边框
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("DengXian", 9)) # 使用稍小号字体
        label.pack(ipadx=5, ipady=3)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("连点器 v1.0")
        self.root.minsize(440, 350)
        self.backend = ClickerBackend(update_gui_callback=self.handle_gui_update)
        self.font_main = ("DengXian", 10)
        self.font_link = ("DengXian", 10, "underline")
        style = ttk.Style(self.root)
        style.configure("TLabelFrame.Label", font=self.font_main)
        style.configure("TCheckbutton", font=self.font_main)
        self._is_ui_updating = False
        self._create_menu()
        self._create_widgets()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        if load_config():
            self.root.after(100, self.show_startup_info_dialog)
            
    def _create_menu(self):
        menu_bar = tk.Menu(self.root)
        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="显示提示", command=self.show_startup_info_dialog)
        help_menu.add_separator()
        help_menu.add_command(label="关于...", command=self.show_about_window)
        help_menu.add_separator()
        help_menu.add_command(label="恢复首次启动提示", command=self.restore_startup_info)
        menu_bar.add_cascade(label="帮助", menu=help_menu)
        self.root.config(menu=menu_bar)

    def _create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        action_frame = ttk.LabelFrame(main_frame, text="1. 设置连点内容 (键盘或鼠标)", padding=10)
        action_frame.pack(fill=tk.X, pady=(0, 5))
        self.action_key_label = ttk.Label(
            action_frame, text="[尚未设置]", font=self.font_main, 
            width=12, foreground="gray"
        )
        self.action_key_label.pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="点击设置", command=self.backend.start_listening_for_action_key).pack(side=tk.RIGHT)
        trigger_frame = ttk.LabelFrame(main_frame, text="2. 设置触发方式", padding=10)
        trigger_frame.pack(fill=tk.X, pady=5)
        self.trigger_key_label = ttk.Label(
            trigger_frame, text="[尚未设置]", font=self.font_main, 
            width=12, foreground="gray"
        )
        self.trigger_key_label.pack(side=tk.LEFT, padx=5)
        ttk.Button(trigger_frame, text="点击设置", command=self.backend.start_listening_for_trigger_key).pack(side=tk.RIGHT)
        settings_frame = ttk.LabelFrame(main_frame, text="3. 参数设置", padding=10)
        settings_frame.pack(fill=tk.X, pady=5)
        self.interval_var = tk.StringVar(value=f"{self.backend.click_interval:.2f}")
        self.interval_scale = ttk.Scale(
            settings_frame, from_=0.01, to=2.00, orient="horizontal",
            command=self.on_scale_move
        )
        self.interval_scale.set(self.backend.click_interval)
        self.interval_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,10))
        self.interval_entry = ttk.Entry(
            settings_frame, textvariable=self.interval_var, 
            width=6, font=self.font_main
        )
        self.interval_entry.pack(side=tk.LEFT)
        ttk.Label(settings_frame, text="秒", font=self.font_main).pack(side=tk.LEFT)
        self.interval_var.trace_add("write", self.on_entry_write)
        switch_frame = ttk.LabelFrame(main_frame, text="4. 启动/停止", padding=10)
        switch_frame.pack(fill=tk.X, pady=10)
        self.master_switch_var = tk.BooleanVar()
        ttk.Checkbutton(switch_frame, text="启用总开关", variable=self.master_switch_var, command=self.toggle_switch).pack()
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        permission_label = ttk.Label(
            bottom_frame, text="提示: 若无法后台触发, 请尝试以管理员权限运行本程序。",
            foreground="gray", wraplength=400, font=self.font_main
        )
        permission_label.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_label = ttk.Label(bottom_frame, text="状态: 总开关已关闭", anchor=tk.W, font=self.font_main)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

    def show_startup_info_dialog(self):
        info_window = tk.Toplevel(self.root)
        info_window.title("欢迎使用")
        info_window.transient(self.root)
        info_window.grab_set()
        info_window.withdraw()
        main_frame = ttk.Frame(info_window, padding=20)
        main_frame.pack()
        message = (
            "提示：\n"
            "1. 本软件仅适用于Windows10与Windows11系统。\n\n"
            "2. 在使用这个连点器之前，请先在桌面新建一个空白的文本文档，\n"
            "   试一下效果后再在需要的软件内使用。\n\n"
            "3. 这个连点器还在持续打磨中，如有bug请联系我，\n"
            "   联系方式在“帮助 -> 关于”界面。\n\n"
            "4. 如果不知道触发键该用哪个，那就设置成F8吧，\n"
            "   如果你的键盘没有F8，那就换另一个你用不上的键吧。"
        )
        ttk.Label(main_frame, text=message, font=self.font_main, justify=tk.LEFT).pack(pady=(0, 20))
        should_show_at_startup = load_config()
        dont_show_var = tk.BooleanVar(value=not should_show_at_startup)
        ttk.Checkbutton(main_frame, text="不再弹出", variable=dont_show_var).pack(side=tk.LEFT)
        def on_ok():
            save_config(not dont_show_var.get())
            info_window.destroy()
        ttk.Button(main_frame, text="好的", command=on_ok).pack(side=tk.RIGHT)
        center_window(info_window)
        info_window.deiconify()
        
    def copy_to_clipboard(self, text_to_copy):
        self.root.clipboard_clear()
        self.root.clipboard_append(text_to_copy)
        messagebox.showinfo("已复制", f"'{text_to_copy}' 已复制到剪贴板")

    def show_about_window(self):
        about_window = tk.Toplevel(self.root)
        about_window.title("关于本软件")
        about_window.transient(self.root)
        about_window.grab_set()
        about_window.withdraw()
        main_frame = ttk.Frame(about_window, padding=20)
        main_frame.pack()
        
        contact_frame = ttk.LabelFrame(main_frame, text="联系方式", padding=10)
        contact_frame.pack(fill=tk.X)
        
        info_items = {
            "QQ:": "2987783912",
            "邮箱:": "yuanwangnan@foxmail.com",
            "制作者:": "十四"
        }
        for label, value in info_items.items():
            item_frame = ttk.Frame(contact_frame)
            item_frame.pack(fill=tk.X, pady=1)
            ttk.Label(item_frame, text=label, font=self.font_main).pack(side=tk.LEFT, padx=(0, 5))
            value_label = ttk.Label(item_frame, text=value, font=self.font_main, 
                                    foreground="darkblue", cursor="hand2")
            value_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
            value_label.bind("<Button-3>", lambda event, v=value: self.copy_to_clipboard(v))
            
            # --- 核心改进：为每个联系方式标签添加悬停提示 ---
            Tooltip(value_label, "右键点击可复制")
            
        github_url = "https://github.com/14isfourteen"
        link_frame = ttk.Frame(contact_frame)
        link_frame.pack(anchor="w", pady=(5,0))
        ttk.Label(link_frame, text="GitHub:", font=self.font_main).pack(side=tk.LEFT)
        link_label = ttk.Label(
            link_frame, text=github_url, font=self.font_link, 
            foreground="blue", cursor="hand2"
        )
        link_label.pack(side=tk.LEFT)
        def open_link(event):
            webbrowser.open_new(github_url)
        link_label.bind("<Button-1>", open_link)
        Tooltip(link_label, "左键点击可跳转")
        
        story_frame = ttk.LabelFrame(main_frame, text="我想说的话", padding=10)
        story_frame.pack(fill=tk.X, pady=10)
        story_text = (
            "在上个学期，有一位同学想要一个连点器跳过游戏内剧情，\n"
            "我当时自己着急忙慌编译了一个，结果没法用，还是在百度上\n"
            "下载了一个连点器，但这些软件多少有点捆绑广告，\n"
            "今天我心血来潮，想着自己做一个纯净的连点器。\n\n"
            "在这途中，Google Gemini是我的得力助手，他帮了我许多，\n"
            "虽然中间很多bug过程坎坷，但还算做出来了个能用的东西。\n\n"
            "我知道，连点器这东西网络上肯定很多人做，但我还是想自己\n"
            "搓一个，这是我选择程序设计专业以来，第一个自己搓出来的\n"
            "软件，希望大家用得开心。\n\n"
            "有bug或者软件上的建议，欢迎联系我。"
        )
        ttk.Label(story_frame, text=story_text, font=self.font_main, justify=tk.LEFT).pack()
        ttk.Button(main_frame, text="关闭", command=about_window.destroy).pack(pady=(10,0))
        center_window(about_window)
        about_window.deiconify()

    def restore_startup_info(self):
        save_config(True)
        messagebox.showinfo("操作成功", "下次启动时将会再次显示提示窗口。")

    def on_scale_move(self, value_str):
        if self._is_ui_updating: return
        self._is_ui_updating = True
        value = float(value_str)
        self.interval_var.set(f"{value:.2f}")
        self.backend.set_interval(value_str)
        self._is_ui_updating = False

    def on_entry_write(self, *args):
        if self._is_ui_updating: return
        self._is_ui_updating = True
        try:
            value = float(self.interval_var.get())
            if 0.01 <= value <= 2.0:
                self.interval_scale.set(value)
            self.backend.set_interval(str(value))
        except (ValueError, TypeError):
            pass
        self._is_ui_updating = False

    def toggle_switch(self):
        self.backend.set_interval(self.interval_var.get())
        is_on = self.master_switch_var.get()
        self.backend.toggle_master_switch(is_on)

    def handle_gui_update(self, widget_name, value, color=None):
        def update():
            if widget_name == "status": self.status_label.config(text=f"状态: {value}", foreground=color or "black")
            elif widget_name == "action_key": self.action_key_label.config(text=value, foreground="black")
            elif widget_name == "trigger_key": self.trigger_key_label.config(text=value, foreground="black")
        self.root.after(0, update)

    def on_closing(self):
        self.backend.stop_all()
        self.root.destroy()

if __name__ == "__main__":
    set_dpi_awareness()
    main_root = tk.Tk()
    main_root.withdraw()
    app = App(main_root)
    center_window(main_root)
    main_root.deiconify()
    main_root.mainloop()