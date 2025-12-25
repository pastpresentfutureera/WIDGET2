#!/usr/bin/env python3
"""
Desktop Widgets Application
Calendar, To-do List, Day/Weekly/Monthly Planner, Pomodoro Timer
Sticks to desktop, colorful, expandable widgets
"""

import tkinter as tk
from tkinter import ttk, colorchooser, messagebox, simpledialog
import json
import os
from datetime import datetime, timedelta
import calendar
from pathlib import Path
import threading
import time
import sys
import subprocess

# Windows-specific imports
if sys.platform == 'win32':
    import ctypes
    from ctypes import wintypes
    import winreg

# ============== DATA MANAGEMENT ==============
class DataManager:
    def __init__(self):
        self.data_dir = Path.home() / '.desktop_widgets'
        self.data_dir.mkdir(exist_ok=True)
        self.data_file = self.data_dir / 'widget_data.json'
        self.load_data()
    
    def load_data(self):
        default_data = {
            'widget_positions': {},
            'widget_colors': {
                'calendar': '#E3F2FD',
                'todo': '#F3E5F5',
                'day_planner': '#E8F5E9',
                'weekly_planner': '#FFF3E0',
                'monthly_planner': '#FCE4EC',
                'pomodoro': '#E0F7FA'
            },
            'widget_sizes': {
                'calendar': 'compact',
                'todo': 'compact',
                'day_planner': 'compact',
                'weekly_planner': 'compact',
                'monthly_planner': 'compact',
                'pomodoro': 'compact'
            },
            'widget_visible': {
                'calendar': True,
                'todo': True,
                'day_planner': True,
                'weekly_planner': True,
                'monthly_planner': True,
                'pomodoro': True
            },
            'calendar_events': {},
            'todo_items': [],
            'day_plans': {},
            'weekly_plans': {},
            'monthly_plans': {},
            'pomodoro_settings': {
                'focus_time': 25,
                'break_time': 5,
                'long_break_time': 15,
                'sessions_before_long_break': 4
            },
            'pomodoro_history': {},
            'autostart': True
        }
        
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r') as f:
                    saved_data = json.load(f)
                    for key in default_data:
                        if key not in saved_data:
                            saved_data[key] = default_data[key]
                    self.data = saved_data
            except:
                self.data = default_data
        else:
            self.data = default_data
        self.save_data()
    
    def save_data(self):
        with open(self.data_file, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    def get(self, key, default=None):
        return self.data.get(key, default)
    
    def set(self, key, value):
        self.data[key] = value
        self.save_data()

# ============== WINDOWS DESKTOP INTEGRATION ==============
class WindowsDesktopIntegration:
    def __init__(self):
        self.user32 = ctypes.windll.user32
        self.HWND_BOTTOM = 1
        self.SWP_NOSIZE = 0x0001
        self.SWP_NOMOVE = 0x0002
        self.SWP_NOACTIVATE = 0x0010
        self.GWL_EXSTYLE = -20
        self.WS_EX_TOOLWINDOW = 0x00000080
        self.WS_EX_NOACTIVATE = 0x08000000
    
    def stick_to_desktop(self, hwnd):
        """Make window stay on desktop level"""
        try:
            # Set window to bottom (below other windows, above desktop)
            self.user32.SetWindowPos(
                hwnd, 
                self.HWND_BOTTOM, 
                0, 0, 0, 0,
                self.SWP_NOMOVE | self.SWP_NOSIZE | self.SWP_NOACTIVATE
            )
            
            # Hide from taskbar
            style = self.user32.GetWindowLongW(hwnd, self.GWL_EXSTYLE)
            style |= self.WS_EX_TOOLWINDOW
            self.user32.SetWindowLongW(hwnd, self.GWL_EXSTYLE, style)
            
            return True
        except Exception as e:
            print(f"Desktop integration error: {e}")
            return False
    
    def keep_at_bottom(self, hwnd):
        """Continuously keep window at bottom"""
        try:
            self.user32.SetWindowPos(
                hwnd, 
                self.HWND_BOTTOM, 
                0, 0, 0, 0,
                self.SWP_NOMOVE | self.SWP_NOSIZE | self.SWP_NOACTIVATE
            )
        except:
            pass

def setup_autostart(enable=True):
    """Setup application to start with Windows"""
    if sys.platform != 'win32':
        return
    
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "DesktopWidgets"
        
        if getattr(sys, 'frozen', False):
            app_path = sys.executable
        else:
            app_path = f'pythonw "{os.path.abspath(__file__)}"'
        
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
        
        if enable:
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, app_path)
        else:
            try:
                winreg.DeleteValue(key, app_name)
            except:
                pass
        
        winreg.CloseKey(key)
    except Exception as e:
        print(f"Autostart setup error: {e}")

# ============== BASE WIDGET CLASS ==============
class BaseWidget(tk.Toplevel):
    def __init__(self, master, name, title, data_manager, desktop_integration):
        super().__init__(master)
        self.name = name
        self.title_text = title
        self.data_manager = data_manager
        self.desktop_integration = desktop_integration
        self.is_expanded = False
        self.is_dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        
        # Window configuration
        self.title(title)
        self.overrideredirect(True)
        self.attributes('-topmost', False)
        
        # Get saved position and color
        positions = self.data_manager.get('widget_positions', {})
        colors = self.data_manager.get('widget_colors', {})
        sizes = self.data_manager.get('widget_sizes', {})
        
        self.bg_color = colors.get(name, '#E3F2FD')
        self.is_expanded = sizes.get(name, 'compact') == 'expanded'
        
        # Set position
        pos = positions.get(name, None)
        if pos:
            self.geometry(f"+{pos['x']}+{pos['y']}")
        else:
            self.geometry("+100+100")
        
        self.configure(bg=self.bg_color)
        
        # Create main frame with border
        self.main_frame = tk.Frame(self, bg=self.bg_color, relief='raised', bd=2)
        self.main_frame.pack(fill='both', expand=True, padx=2, pady=2)
        
        # Title bar
        self.create_title_bar()
        
        # Content area
        self.content_frame = tk.Frame(self.main_frame, bg=self.bg_color)
        self.content_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Build widget content
        self.build_content()
        
        # Bind events for dragging
        self.bind_drag_events()
        
        # Schedule desktop sticking
        self.after(100, self.stick_to_desktop_periodic)
    
    def create_title_bar(self):
        title_bar = tk.Frame(self.main_frame, bg=self.darken_color(self.bg_color), height=25)
        title_bar.pack(fill='x', padx=0, pady=0)
        title_bar.pack_propagate(False)
        
        # Title label
        title_label = tk.Label(
            title_bar, 
            text=self.title_text, 
            bg=self.darken_color(self.bg_color),
            fg='#333333',
            font=('Segoe UI', 9, 'bold')
        )
        title_label.pack(side='left', padx=5)
        
        # Buttons frame
        btn_frame = tk.Frame(title_bar, bg=self.darken_color(self.bg_color))
        btn_frame.pack(side='right', padx=2)
        
        # Color button
        color_btn = tk.Button(
            btn_frame, 
            text='🎨', 
            command=self.change_color,
            font=('Segoe UI', 8),
            bd=0,
            bg=self.darken_color(self.bg_color),
            activebackground=self.bg_color,
            cursor='hand2'
        )
        color_btn.pack(side='left', padx=1)
        
        # Expand/Collapse button
        self.expand_btn = tk.Button(
            btn_frame, 
            text='⬇' if not self.is_expanded else '⬆', 
            command=self.toggle_expand,
            font=('Segoe UI', 8),
            bd=0,
            bg=self.darken_color(self.bg_color),
            activebackground=self.bg_color,
            cursor='hand2'
        )
        self.expand_btn.pack(side='left', padx=1)
        
        # Close button
        close_btn = tk.Button(
            btn_frame, 
            text='✕', 
            command=self.hide_widget,
            font=('Segoe UI', 8),
            bd=0,
            bg=self.darken_color(self.bg_color),
            activebackground='#ff6b6b',
            cursor='hand2'
        )
        close_btn.pack(side='left', padx=1)
        
        # Bind drag to title bar
        title_bar.bind('<Button-1>', self.start_drag)
        title_bar.bind('<B1-Motion>', self.on_drag)
        title_bar.bind('<ButtonRelease-1>', self.stop_drag)
        title_label.bind('<Button-1>', self.start_drag)
        title_label.bind('<B1-Motion>', self.on_drag)
        title_label.bind('<ButtonRelease-1>', self.stop_drag)
    
    def darken_color(self, hex_color, factor=0.9):
        """Darken a hex color"""
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        darkened = tuple(int(c * factor) for c in rgb)
        return '#{:02x}{:02x}{:02x}'.format(*darkened)
    
    def bind_drag_events(self):
        self.bind('<Button-1>', self.start_drag)
        self.bind('<B1-Motion>', self.on_drag)
        self.bind('<ButtonRelease-1>', self.stop_drag)
    
    def start_drag(self, event):
        self.is_dragging = True
        self.drag_start_x = event.x_root - self.winfo_x()
        self.drag_start_y = event.y_root - self.winfo_y()
    
    def on_drag(self, event):
        if self.is_dragging:
            x = event.x_root - self.drag_start_x
            y = event.y_root - self.drag_start_y
            self.geometry(f"+{x}+{y}")
    
    def stop_drag(self, event):
        self.is_dragging = False
        self.save_position()
    
    def save_position(self):
        positions = self.data_manager.get('widget_positions', {})
        positions[self.name] = {'x': self.winfo_x(), 'y': self.winfo_y()}
        self.data_manager.set('widget_positions', positions)
    
    def change_color(self):
        color = colorchooser.askcolor(initialcolor=self.bg_color, title="Choose Widget Color")
        if color[1]:
            self.bg_color = color[1]
            self.update_colors()
            colors = self.data_manager.get('widget_colors', {})
            colors[self.name] = self.bg_color
            self.data_manager.set('widget_colors', colors)
    
    def update_colors(self):
        self.configure(bg=self.bg_color)
        self.main_frame.configure(bg=self.bg_color)
        self.content_frame.configure(bg=self.bg_color)
        for widget in self.main_frame.winfo_children():
            try:
                widget.configure(bg=self.darken_color(self.bg_color) if isinstance(widget, tk.Frame) else self.bg_color)
            except:
                pass
        self.update_widget_colors()
    
    def update_widget_colors(self):
        """Override in subclasses to update specific widget colors"""
        pass
    
    def toggle_expand(self):
        self.is_expanded = not self.is_expanded
        self.expand_btn.configure(text='⬆' if self.is_expanded else '⬇')
        sizes = self.data_manager.get('widget_sizes', {})
        sizes[self.name] = 'expanded' if self.is_expanded else 'compact'
        self.data_manager.set('widget_sizes', sizes)
        self.build_content()
    
    def hide_widget(self):
        visible = self.data_manager.get('widget_visible', {})
        visible[self.name] = False
        self.data_manager.set('widget_visible', visible)
        self.withdraw()
    
    def show_widget(self):
        visible = self.data_manager.get('widget_visible', {})
        visible[self.name] = True
        self.data_manager.set('widget_visible', visible)
        self.deiconify()
    
    def stick_to_desktop_periodic(self):
        """Periodically stick window to desktop"""
        if sys.platform == 'win32' and self.desktop_integration:
            try:
                hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
                self.desktop_integration.keep_at_bottom(hwnd)
            except:
                pass
        self.after(500, self.stick_to_desktop_periodic)
    
    def build_content(self):
        """Override in subclasses"""
        pass

# ============== CALENDAR WIDGET ==============
class CalendarWidget(BaseWidget):
    def __init__(self, master, data_manager, desktop_integration):
        super().__init__(master, 'calendar', '📅 Calendar', data_manager, desktop_integration)
    
    def build_content(self):
        # Clear existing content
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        self.current_date = datetime.now()
        self.selected_date = datetime.now()
        
        # Navigation frame
        nav_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        nav_frame.pack(fill='x', pady=(0, 5))
        
        prev_btn = tk.Button(
            nav_frame, text='◀', command=self.prev_month,
            font=('Segoe UI', 10), bd=0, bg=self.bg_color, cursor='hand2'
        )
        prev_btn.pack(side='left')
        
        self.month_label = tk.Label(
            nav_frame, 
            text=self.current_date.strftime('%B %Y'),
            font=('Segoe UI', 10, 'bold'),
            bg=self.bg_color
        )
        self.month_label.pack(side='left', expand=True)
        
        next_btn = tk.Button(
            nav_frame, text='▶', command=self.next_month,
            font=('Segoe UI', 10), bd=0, bg=self.bg_color, cursor='hand2'
        )
        next_btn.pack(side='right')
        
        # Days header
        days_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        days_frame.pack(fill='x')
        
        days = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su']
        for day in days:
            lbl = tk.Label(
                days_frame, text=day, font=('Segoe UI', 8, 'bold'),
                width=4, bg=self.bg_color, fg='#555'
            )
            lbl.pack(side='left', padx=1)
        
        # Calendar grid
        self.calendar_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        self.calendar_frame.pack(fill='both', expand=True)
        
        self.update_calendar()
        
        # Event section (expanded mode)
        if self.is_expanded:
            self.build_event_section()
    
    def build_event_section(self):
        event_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        event_frame.pack(fill='x', pady=(10, 0))
        
        tk.Label(
            event_frame, text="📝 Events:", 
            font=('Segoe UI', 9, 'bold'), bg=self.bg_color
        ).pack(anchor='w')
        
        # Event entry
        entry_frame = tk.Frame(event_frame, bg=self.bg_color)
        entry_frame.pack(fill='x', pady=2)
        
        self.event_entry = tk.Entry(entry_frame, font=('Segoe UI', 9), width=25)
        self.event_entry.pack(side='left', fill='x', expand=True)
        
        add_btn = tk.Button(
            entry_frame, text='+', command=self.add_event,
            font=('Segoe UI', 9, 'bold'), bd=1, cursor='hand2'
        )
        add_btn.pack(side='right', padx=(5, 0))
        
        # Events list
        self.events_list = tk.Listbox(
            event_frame, font=('Segoe UI', 8), height=4, 
            selectbackground='#bbdefb'
        )
        self.events_list.pack(fill='x', pady=2)
        self.events_list.bind('<Double-Button-1>', self.delete_event)
        
        self.update_events_list()
    
    def update_calendar(self):
        for widget in self.calendar_frame.winfo_children():
            widget.destroy()
        
        year = self.current_date.year
        month = self.current_date.month
        
        cal = calendar.monthcalendar(year, month)
        events = self.data_manager.get('calendar_events', {})
        
        for week in cal:
            week_frame = tk.Frame(self.calendar_frame, bg=self.bg_color)
            week_frame.pack(fill='x')
            
            for day in week:
                if day == 0:
                    lbl = tk.Label(week_frame, text='', width=4, bg=self.bg_color)
                else:
                    date_key = f"{year}-{month:02d}-{day:02d}"
                    has_event = date_key in events and len(events[date_key]) > 0
                    is_today = (day == datetime.now().day and 
                               month == datetime.now().month and 
                               year == datetime.now().year)
                    
                    bg = '#ff8a80' if is_today else ('#ffeb3b' if has_event else self.bg_color)
                    
                    lbl = tk.Label(
                        week_frame, text=str(day), width=4,
                        font=('Segoe UI', 9, 'bold' if is_today else 'normal'),
                        bg=bg, cursor='hand2', relief='flat'
                    )
                    lbl.bind('<Button-1>', lambda e, d=day: self.select_date(d))
                
                lbl.pack(side='left', padx=1, pady=1)
    
    def select_date(self, day):
        self.selected_date = self.current_date.replace(day=day)
        if self.is_expanded:
            self.update_events_list()
    
    def prev_month(self):
        if self.current_date.month == 1:
            self.current_date = self.current_date.replace(year=self.current_date.year - 1, month=12)
        else:
            self.current_date = self.current_date.replace(month=self.current_date.month - 1)
        self.month_label.config(text=self.current_date.strftime('%B %Y'))
        self.update_calendar()
    
    def next_month(self):
        if self.current_date.month == 12:
            self.current_date = self.current_date.replace(year=self.current_date.year + 1, month=1)
        else:
            self.current_date = self.current_date.replace(month=self.current_date.month + 1)
        self.month_label.config(text=self.current_date.strftime('%B %Y'))
        self.update_calendar()
    
    def add_event(self):
        event_text = self.event_entry.get().strip()
        if event_text:
            date_key = self.selected_date.strftime('%Y-%m-%d')
            events = self.data_manager.get('calendar_events', {})
            if date_key not in events:
                events[date_key] = []
            events[date_key].append(event_text)
            self.data_manager.set('calendar_events', events)
            self.event_entry.delete(0, tk.END)
            self.update_events_list()
            self.update_calendar()
    
    def delete_event(self, event):
        selection = self.events_list.curselection()
        if selection:
            date_key = self.selected_date.strftime('%Y-%m-%d')
            events = self.data_manager.get('calendar_events', {})
            if date_key in events:
                del events[date_key][selection[0]]
                if not events[date_key]:
                    del events[date_key]
                self.data_manager.set('calendar_events', events)
                self.update_events_list()
                self.update_calendar()
    
    def update_events_list(self):
        if hasattr(self, 'events_list'):
            self.events_list.delete(0, tk.END)
            date_key = self.selected_date.strftime('%Y-%m-%d')
            events = self.data_manager.get('calendar_events', {})
            if date_key in events:
                for event in events[date_key]:
                    self.events_list.insert(tk.END, f"• {event}")

# ============== TODO WIDGET ==============
class TodoWidget(BaseWidget):
    def __init__(self, master, data_manager, desktop_integration):
        super().__init__(master, 'todo', '✅ To-Do List', data_manager, desktop_integration)
    
    def build_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Add task entry
        entry_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        entry_frame.pack(fill='x', pady=(0, 5))
        
        self.task_entry = tk.Entry(entry_frame, font=('Segoe UI', 9), width=20)
        self.task_entry.pack(side='left', fill='x', expand=True)
        self.task_entry.bind('<Return>', lambda e: self.add_task())
        
        add_btn = tk.Button(
            entry_frame, text='+', command=self.add_task,
            font=('Segoe UI', 9, 'bold'), bd=1, cursor='hand2'
        )
        add_btn.pack(side='right', padx=(5, 0))
        
        # Tasks list
        list_height = 10 if self.is_expanded else 5
        
        list_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        list_frame.pack(fill='both', expand=True)
        
        self.tasks_canvas = tk.Canvas(list_frame, bg=self.bg_color, highlightthickness=0)
        scrollbar = tk.Scrollbar(list_frame, orient='vertical', command=self.tasks_canvas.yview)
        self.tasks_inner_frame = tk.Frame(self.tasks_canvas, bg=self.bg_color)
        
        self.tasks_canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side='right', fill='y')
        self.tasks_canvas.pack(side='left', fill='both', expand=True)
        
        self.canvas_window = self.tasks_canvas.create_window((0, 0), window=self.tasks_inner_frame, anchor='nw')
        
        self.tasks_inner_frame.bind('<Configure>', self.on_frame_configure)
        self.tasks_canvas.bind('<Configure>', self.on_canvas_configure)
        
        self.update_tasks()
        
        # Priority legend (expanded)
        if self.is_expanded:
            legend = tk.Frame(self.content_frame, bg=self.bg_color)
            legend.pack(fill='x', pady=(5, 0))
            tk.Label(legend, text="🔴 High  🟡 Medium  🟢 Low", 
                    font=('Segoe UI', 8), bg=self.bg_color).pack()
    
    def on_frame_configure(self, event):
        self.tasks_canvas.configure(scrollregion=self.tasks_canvas.bbox('all'))
    
    def on_canvas_configure(self, event):
        self.tasks_canvas.itemconfig(self.canvas_window, width=event.width)
    
    def add_task(self):
        task_text = self.task_entry.get().strip()
        if task_text:
            tasks = self.data_manager.get('todo_items', [])
            tasks.append({
                'text': task_text,
                'done': False,
                'priority': 'medium',
                'created': datetime.now().isoformat()
            })
            self.data_manager.set('todo_items', tasks)
            self.task_entry.delete(0, tk.END)
            self.update_tasks()
    
    def update_tasks(self):
        for widget in self.tasks_inner_frame.winfo_children():
            widget.destroy()
        
        tasks = self.data_manager.get('todo_items', [])
        
        for i, task in enumerate(tasks):
            task_frame = tk.Frame(self.tasks_inner_frame, bg=self.bg_color)
            task_frame.pack(fill='x', pady=1)
            
            # Checkbox
            var = tk.BooleanVar(value=task['done'])
            cb = tk.Checkbutton(
                task_frame, variable=var,
                command=lambda idx=i, v=var: self.toggle_task(idx, v),
                bg=self.bg_color, activebackground=self.bg_color
            )
            cb.pack(side='left')
            
            # Priority indicator
            priority_colors = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}
            priority_lbl = tk.Label(
                task_frame, text=priority_colors.get(task.get('priority', 'medium'), '🟡'),
                bg=self.bg_color, font=('Segoe UI', 8)
            )
            priority_lbl.pack(side='left')
            priority_lbl.bind('<Button-1>', lambda e, idx=i: self.cycle_priority(idx))
            
            # Task text
            text_style = 'overstrike' if task['done'] else 'normal'
            fg_color = '#888' if task['done'] else '#333'
            task_lbl = tk.Label(
                task_frame, text=task['text'],
                font=('Segoe UI', 9, text_style), bg=self.bg_color, fg=fg_color,
                anchor='w', wraplength=150
            )
            task_lbl.pack(side='left', fill='x', expand=True)
            
            # Delete button
            del_btn = tk.Button(
                task_frame, text='✕', command=lambda idx=i: self.delete_task(idx),
                font=('Segoe UI', 7), bd=0, bg=self.bg_color, fg='#999',
                activebackground='#ff6b6b', cursor='hand2'
            )
            del_btn.pack(side='right')
    
    def toggle_task(self, index, var):
        tasks = self.data_manager.get('todo_items', [])
        if 0 <= index < len(tasks):
            tasks[index]['done'] = var.get()
            self.data_manager.set('todo_items', tasks)
            self.update_tasks()
    
    def cycle_priority(self, index):
        tasks = self.data_manager.get('todo_items', [])
        if 0 <= index < len(tasks):
            priorities = ['low', 'medium', 'high']
            current = tasks[index].get('priority', 'medium')
            current_idx = priorities.index(current)
            tasks[index]['priority'] = priorities[(current_idx + 1) % 3]
            self.data_manager.set('todo_items', tasks)
            self.update_tasks()
    
    def delete_task(self, index):
        tasks = self.data_manager.get('todo_items', [])
        if 0 <= index < len(tasks):
            del tasks[index]
            self.data_manager.set('todo_items', tasks)
            self.update_tasks()

# ============== DAY PLANNER WIDGET ==============
class DayPlannerWidget(BaseWidget):
    def __init__(self, master, data_manager, desktop_integration):
        super().__init__(master, 'day_planner', '📋 Day Planner', data_manager, desktop_integration)
    
    def build_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        self.current_date = datetime.now()
        
        # Date header
        header = tk.Frame(self.content_frame, bg=self.bg_color)
        header.pack(fill='x', pady=(0, 5))
        
        prev_btn = tk.Button(
            header, text='◀', command=self.prev_day,
            font=('Segoe UI', 10), bd=0, bg=self.bg_color, cursor='hand2'
        )
        prev_btn.pack(side='left')
        
        self.date_label = tk.Label(
            header, text=self.current_date.strftime('%A, %B %d'),
            font=('Segoe UI', 10, 'bold'), bg=self.bg_color
        )
        self.date_label.pack(side='left', expand=True)
        
        next_btn = tk.Button(
            header, text='▶', command=self.next_day,
            font=('Segoe UI', 10), bd=0, bg=self.bg_color, cursor='hand2'
        )
        next_btn.pack(side='right')
        
        # Time slots
        if self.is_expanded:
            hours = range(6, 22)  # 6 AM to 10 PM
        else:
            hours = range(8, 18)  # 8 AM to 6 PM (compact)
        
        slots_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        slots_frame.pack(fill='both', expand=True)
        
        canvas = tk.Canvas(slots_frame, bg=self.bg_color, highlightthickness=0, width=200)
        scrollbar = tk.Scrollbar(slots_frame, orient='vertical', command=canvas.yview)
        inner_frame = tk.Frame(canvas, bg=self.bg_color)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        
        canvas_window = canvas.create_window((0, 0), window=inner_frame, anchor='nw')
        
        day_plans = self.data_manager.get('day_plans', {})
        date_key = self.current_date.strftime('%Y-%m-%d')
        current_plans = day_plans.get(date_key, {})
        
        self.time_entries = {}
        
        for hour in hours:
            row = tk.Frame(inner_frame, bg=self.bg_color)
            row.pack(fill='x', pady=1)
            
            time_lbl = tk.Label(
                row, text=f"{hour:02d}:00",
                font=('Segoe UI', 8), bg=self.bg_color, width=5
            )
            time_lbl.pack(side='left')
            
            entry = tk.Entry(row, font=('Segoe UI', 8), width=20)
            entry.pack(side='left', fill='x', expand=True, padx=2)
            entry.insert(0, current_plans.get(str(hour), ''))
            entry.bind('<FocusOut>', lambda e, h=hour: self.save_plan(h))
            entry.bind('<Return>', lambda e, h=hour: self.save_plan(h))
            
            self.time_entries[hour] = entry
        
        inner_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
    
    def prev_day(self):
        self.current_date -= timedelta(days=1)
        self.date_label.config(text=self.current_date.strftime('%A, %B %d'))
        self.build_content()
    
    def next_day(self):
        self.current_date += timedelta(days=1)
        self.date_label.config(text=self.current_date.strftime('%A, %B %d'))
        self.build_content()
    
    def save_plan(self, hour):
        day_plans = self.data_manager.get('day_plans', {})
        date_key = self.current_date.strftime('%Y-%m-%d')
        
        if date_key not in day_plans:
            day_plans[date_key] = {}
        
        if hour in self.time_entries:
            text = self.time_entries[hour].get().strip()
            if text:
                day_plans[date_key][str(hour)] = text
            elif str(hour) in day_plans[date_key]:
                del day_plans[date_key][str(hour)]
        
        self.data_manager.set('day_plans', day_plans)

# ============== WEEKLY PLANNER WIDGET ==============
class WeeklyPlannerWidget(BaseWidget):
    def __init__(self, master, data_manager, desktop_integration):
        super().__init__(master, 'weekly_planner', '📆 Weekly Planner', data_manager, desktop_integration)
    
    def build_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        today = datetime.now()
        self.week_start = today - timedelta(days=today.weekday())
        
        # Week navigation
        nav_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        nav_frame.pack(fill='x', pady=(0, 5))
        
        prev_btn = tk.Button(
            nav_frame, text='◀', command=self.prev_week,
            font=('Segoe UI', 10), bd=0, bg=self.bg_color, cursor='hand2'
        )
        prev_btn.pack(side='left')
        
        week_end = self.week_start + timedelta(days=6)
        self.week_label = tk.Label(
            nav_frame, 
            text=f"{self.week_start.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')}",
            font=('Segoe UI', 9, 'bold'), bg=self.bg_color
        )
        self.week_label.pack(side='left', expand=True)
        
        next_btn = tk.Button(
            nav_frame, text='▶', command=self.next_week,
            font=('Segoe UI', 10), bd=0, bg=self.bg_color, cursor='hand2'
        )
        next_btn.pack(side='right')
        
        # Days grid
        self.build_week_grid()
    
    def build_week_grid(self):
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        short_days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        
        weekly_plans = self.data_manager.get('weekly_plans', {})
        week_key = self.week_start.strftime('%Y-%W')
        current_plans = weekly_plans.get(week_key, {})
        
        self.day_entries = {}
        
        if self.is_expanded:
            # Full view with all days in grid
            grid_frame = tk.Frame(self.content_frame, bg=self.bg_color)
            grid_frame.pack(fill='both', expand=True)
            
            for i, (day, short) in enumerate(zip(days, short_days)):
                day_date = self.week_start + timedelta(days=i)
                is_today = day_date.date() == datetime.now().date()
                
                day_frame = tk.Frame(grid_frame, bg='#ffeb3b' if is_today else self.bg_color, 
                                    relief='groove', bd=1)
                day_frame.pack(fill='x', pady=1)
                
                header = tk.Label(
                    day_frame, text=f"{short} {day_date.day}",
                    font=('Segoe UI', 8, 'bold'), 
                    bg='#ffeb3b' if is_today else self.darken_color(self.bg_color)
                )
                header.pack(fill='x')
                
                entry = tk.Text(day_frame, font=('Segoe UI', 8), height=2, width=25, wrap='word')
                entry.pack(fill='x', padx=2, pady=2)
                entry.insert('1.0', current_plans.get(str(i), ''))
                entry.bind('<FocusOut>', lambda e, idx=i: self.save_week_plan(idx))
                
                self.day_entries[i] = entry
        else:
            # Compact view
            for i, short in enumerate(short_days):
                day_date = self.week_start + timedelta(days=i)
                is_today = day_date.date() == datetime.now().date()
                
                row = tk.Frame(self.content_frame, bg=self.bg_color)
                row.pack(fill='x', pady=1)
                
                day_lbl = tk.Label(
                    row, text=f"{short} {day_date.day}",
                    font=('Segoe UI', 8, 'bold' if is_today else 'normal'),
                    bg='#ffeb3b' if is_today else self.bg_color, width=8
                )
                day_lbl.pack(side='left')
                
                entry = tk.Entry(row, font=('Segoe UI', 8), width=20)
                entry.pack(side='left', fill='x', expand=True, padx=2)
                entry.insert(0, current_plans.get(str(i), ''))
                entry.bind('<FocusOut>', lambda e, idx=i: self.save_week_plan(idx))
                
                self.day_entries[i] = entry
    
    def prev_week(self):
        self.week_start -= timedelta(weeks=1)
        week_end = self.week_start + timedelta(days=6)
        self.week_label.config(text=f"{self.week_start.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')}")
        self.build_content()
    
    def next_week(self):
        self.week_start += timedelta(weeks=1)
        week_end = self.week_start + timedelta(days=6)
        self.week_label.config(text=f"{self.week_start.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')}")
        self.build_content()
    
    def save_week_plan(self, day_index):
        weekly_plans = self.data_manager.get('weekly_plans', {})
        week_key = self.week_start.strftime('%Y-%W')
        
        if week_key not in weekly_plans:
            weekly_plans[week_key] = {}
        
        if day_index in self.day_entries:
            entry = self.day_entries[day_index]
            if isinstance(entry, tk.Text):
                text = entry.get('1.0', 'end-1c').strip()
            else:
                text = entry.get().strip()
            
            if text:
                weekly_plans[week_key][str(day_index)] = text
            elif str(day_index) in weekly_plans[week_key]:
                del weekly_plans[week_key][str(day_index)]
        
        self.data_manager.set('weekly_plans', weekly_plans)

# ============== MONTHLY PLANNER WIDGET ==============
class MonthlyPlannerWidget(BaseWidget):
    def __init__(self, master, data_manager, desktop_integration):
        super().__init__(master, 'monthly_planner', '🗓️ Monthly Planner', data_manager, desktop_integration)
    
    def build_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        self.current_date = datetime.now()
        
        # Month navigation
        nav_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        nav_frame.pack(fill='x', pady=(0, 5))
        
        prev_btn = tk.Button(
            nav_frame, text='◀', command=self.prev_month,
            font=('Segoe UI', 10), bd=0, bg=self.bg_color, cursor='hand2'
        )
        prev_btn.pack(side='left')
        
        self.month_label = tk.Label(
            nav_frame, text=self.current_date.strftime('%B %Y'),
            font=('Segoe UI', 10, 'bold'), bg=self.bg_color
        )
        self.month_label.pack(side='left', expand=True)
        
        next_btn = tk.Button(
            nav_frame, text='▶', command=self.next_month,
            font=('Segoe UI', 10), bd=0, bg=self.bg_color, cursor='hand2'
        )
        next_btn.pack(side='right')
        
        # Goals sections
        self.build_goals_section()
    
    def build_goals_section(self):
        monthly_plans = self.data_manager.get('monthly_plans', {})
        month_key = self.current_date.strftime('%Y-%m')
        current_plans = monthly_plans.get(month_key, {})
        
        categories = ['🎯 Goals', '📝 Notes', '💡 Ideas'] if self.is_expanded else ['🎯 Goals']
        self.goal_entries = {}
        
        for category in categories:
            cat_frame = tk.Frame(self.content_frame, bg=self.bg_color)
            cat_frame.pack(fill='x', pady=2)
            
            tk.Label(
                cat_frame, text=category,
                font=('Segoe UI', 9, 'bold'), bg=self.bg_color
            ).pack(anchor='w')
            
            height = 4 if self.is_expanded else 2
            text_widget = tk.Text(cat_frame, font=('Segoe UI', 8), height=height, width=25, wrap='word')
            text_widget.pack(fill='x', pady=2)
            text_widget.insert('1.0', current_plans.get(category, ''))
            text_widget.bind('<FocusOut>', lambda e, cat=category: self.save_goals(cat))
            
            self.goal_entries[category] = text_widget
    
    def prev_month(self):
        if self.current_date.month == 1:
            self.current_date = self.current_date.replace(year=self.current_date.year - 1, month=12)
        else:
            self.current_date = self.current_date.replace(month=self.current_date.month - 1)
        self.month_label.config(text=self.current_date.strftime('%B %Y'))
        self.build_content()
    
    def next_month(self):
        if self.current_date.month == 12:
            self.current_date = self.current_date.replace(year=self.current_date.year + 1, month=1)
        else:
            self.current_date = self.current_date.replace(month=self.current_date.month + 1)
        self.month_label.config(text=self.current_date.strftime('%B %Y'))
        self.build_content()
    
    def save_goals(self, category):
        monthly_plans = self.data_manager.get('monthly_plans', {})
        month_key = self.current_date.strftime('%Y-%m')
        
        if month_key not in monthly_plans:
            monthly_plans[month_key] = {}
        
        if category in self.goal_entries:
            text = self.goal_entries[category].get('1.0', 'end-1c').strip()
            if text:
                monthly_plans[month_key][category] = text
            elif category in monthly_plans[month_key]:
                del monthly_plans[month_key][category]
        
        self.data_manager.set('monthly_plans', monthly_plans)

# ============== POMODORO WIDGET ==============
class PomodoroWidget(BaseWidget):
    def __init__(self, master, data_manager, desktop_integration):
        self.timer_running = False
        self.is_focus_time = True
        self.remaining_seconds = 0
        self.sessions_completed = 0
        super().__init__(master, 'pomodoro', '🍅 Pomodoro Timer', data_manager, desktop_integration)
    
    def build_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        settings = self.data_manager.get('pomodoro_settings', {
            'focus_time': 25,
            'break_time': 5,
            'long_break_time': 15,
            'sessions_before_long_break': 4
        })
        
        self.focus_time = settings['focus_time']
        self.break_time = settings['break_time']
        self.long_break_time = settings['long_break_time']
        self.sessions_before_long_break = settings['sessions_before_long_break']
        
        if self.remaining_seconds == 0:
            self.remaining_seconds = self.focus_time * 60
        
        # Timer display
        timer_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        timer_frame.pack(fill='x', pady=10)
        
        self.status_label = tk.Label(
            timer_frame, text='🎯 Focus Time' if self.is_focus_time else '☕ Break Time',
            font=('Segoe UI', 10, 'bold'), bg=self.bg_color,
            fg='#d32f2f' if self.is_focus_time else '#388e3c'
        )
        self.status_label.pack()
        
        self.timer_label = tk.Label(
            timer_frame, text=self.format_time(self.remaining_seconds),
            font=('Consolas', 28, 'bold'), bg=self.bg_color
        )
        self.timer_label.pack()
        
        # Session counter
        self.session_label = tk.Label(
            timer_frame, text=f"Sessions: {self.sessions_completed}/{self.sessions_before_long_break}",
            font=('Segoe UI', 9), bg=self.bg_color
        )
        self.session_label.pack()
        
        # Control buttons
        btn_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        btn_frame.pack(fill='x', pady=5)
        
        self.start_btn = tk.Button(
            btn_frame, text='▶ Start', command=self.toggle_timer,
            font=('Segoe UI', 9), cursor='hand2'
        )
        self.start_btn.pack(side='left', padx=2)
        
        reset_btn = tk.Button(
            btn_frame, text='↺ Reset', command=self.reset_timer,
            font=('Segoe UI', 9), cursor='hand2'
        )
        reset_btn.pack(side='left', padx=2)
        
        skip_btn = tk.Button(
            btn_frame, text='⏭ Skip', command=self.skip_session,
            font=('Segoe UI', 9), cursor='hand2'
        )
        skip_btn.pack(side='left', padx=2)
        
        # Expanded features
        if self.is_expanded:
            self.build_expanded_features()
    
    def build_expanded_features(self):
        # Settings
        settings_frame = tk.LabelFrame(
            self.content_frame, text="⚙️ Settings",
            font=('Segoe UI', 9, 'bold'), bg=self.bg_color
        )
        settings_frame.pack(fill='x', pady=5, padx=2)
        
        # Focus time setting
        focus_row = tk.Frame(settings_frame, bg=self.bg_color)
        focus_row.pack(fill='x', pady=2)
        tk.Label(focus_row, text="Focus (min):", font=('Segoe UI', 8), bg=self.bg_color).pack(side='left')
        self.focus_spinbox = tk.Spinbox(focus_row, from_=1, to=120, width=5, 
                                        font=('Segoe UI', 8))
        self.focus_spinbox.pack(side='right')
        self.focus_spinbox.delete(0, tk.END)
        self.focus_spinbox.insert(0, self.focus_time)
        
        # Break time setting
        break_row = tk.Frame(settings_frame, bg=self.bg_color)
        break_row.pack(fill='x', pady=2)
        tk.Label(break_row, text="Break (min):", font=('Segoe UI', 8), bg=self.bg_color).pack(side='left')
        self.break_spinbox = tk.Spinbox(break_row, from_=1, to=60, width=5,
                                        font=('Segoe UI', 8))
        self.break_spinbox.pack(side='right')
        self.break_spinbox.delete(0, tk.END)
        self.break_spinbox.insert(0, self.break_time)
        
        # Long break setting
        long_break_row = tk.Frame(settings_frame, bg=self.bg_color)
        long_break_row.pack(fill='x', pady=2)
        tk.Label(long_break_row, text="Long Break (min):", font=('Segoe UI', 8), bg=self.bg_color).pack(side='left')
        self.long_break_spinbox = tk.Spinbox(long_break_row, from_=1, to=60, width=5,
                                             font=('Segoe UI', 8))
        self.long_break_spinbox.pack(side='right')
        self.long_break_spinbox.delete(0, tk.END)
        self.long_break_spinbox.insert(0, self.long_break_time)
        
        # Save settings button
        save_btn = tk.Button(
            settings_frame, text="💾 Save Settings", command=self.save_settings,
            font=('Segoe UI', 8), cursor='hand2'
        )
        save_btn.pack(pady=5)
        
        # History
        history_frame = tk.LabelFrame(
            self.content_frame, text="📊 Today's Progress",
            font=('Segoe UI', 9, 'bold'), bg=self.bg_color
        )
        history_frame.pack(fill='x', pady=5, padx=2)
        
        today = datetime.now().strftime('%Y-%m-%d')
        history = self.data_manager.get('pomodoro_history', {})
        today_data = history.get(today, {'sessions': 0, 'focus_minutes': 0})
        
        tk.Label(
            history_frame, 
            text=f"✅ Sessions: {today_data['sessions']}\n⏱️ Focus: {today_data['focus_minutes']} min",
            font=('Segoe UI', 9), bg=self.bg_color, justify='left'
        ).pack(anchor='w', padx=5, pady=5)
        
        # Weekly summary
        week_frame = tk.LabelFrame(
            self.content_frame, text="📈 Week Summary",
            font=('Segoe UI', 9, 'bold'), bg=self.bg_color
        )
        week_frame.pack(fill='x', pady=5, padx=2)
        
        week_stats = self.get_week_stats()
        tk.Label(
            week_frame,
            text=f"Sessions: {week_stats['sessions']} | Focus: {week_stats['minutes']} min",
            font=('Segoe UI', 8), bg=self.bg_color
        ).pack(padx=5, pady=5)
    
    def format_time(self, seconds):
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes:02d}:{secs:02d}"
    
    def toggle_timer(self):
        self.timer_running = not self.timer_running
        self.start_btn.config(text='⏸ Pause' if self.timer_running else '▶ Start')
        if self.timer_running:
            self.run_timer()
    
    def run_timer(self):
        if self.timer_running and self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self.timer_label.config(text=self.format_time(self.remaining_seconds))
            self.after(1000, self.run_timer)
        elif self.remaining_seconds == 0:
            self.timer_complete()
    
    def timer_complete(self):
        self.timer_running = False
        self.start_btn.config(text='▶ Start')
        
        if self.is_focus_time:
            # Record focus session
            self.sessions_completed += 1
            self.record_session()
            
            # Switch to break
            self.is_focus_time = False
            if self.sessions_completed >= self.sessions_before_long_break:
                self.remaining_seconds = self.long_break_time * 60
                self.sessions_completed = 0
            else:
                self.remaining_seconds = self.break_time * 60
        else:
            # Switch to focus
            self.is_focus_time = True
            self.remaining_seconds = self.focus_time * 60
        
        self.status_label.config(
            text='🎯 Focus Time' if self.is_focus_time else '☕ Break Time',
            fg='#d32f2f' if self.is_focus_time else '#388e3c'
        )
        self.timer_label.config(text=self.format_time(self.remaining_seconds))
        self.session_label.config(text=f"Sessions: {self.sessions_completed}/{self.sessions_before_long_break}")
        
        # Play notification sound (system bell)
        self.bell()
        messagebox.showinfo(
            "Timer Complete!",
            "Focus session complete! Take a break." if not self.is_focus_time else "Break over! Time to focus."
        )
    
    def reset_timer(self):
        self.timer_running = False
        self.start_btn.config(text='▶ Start')
        self.is_focus_time = True
        self.remaining_seconds = self.focus_time * 60
        self.status_label.config(text='🎯 Focus Time', fg='#d32f2f')
        self.timer_label.config(text=self.format_time(self.remaining_seconds))
    
    def skip_session(self):
        self.timer_running = False
        self.start_btn.config(text='▶ Start')
        self.timer_complete()
    
    def save_settings(self):
        try:
            focus = int(self.focus_spinbox.get())
            break_time = int(self.break_spinbox.get())
            long_break = int(self.long_break_spinbox.get())
            
            settings = {
                'focus_time': focus,
                'break_time': break_time,
                'long_break_time': long_break,
                'sessions_before_long_break': self.sessions_before_long_break
            }
            
            self.data_manager.set('pomodoro_settings', settings)
            self.focus_time = focus
            self.break_time = break_time
            self.long_break_time = long_break
            
            if not self.timer_running:
                self.remaining_seconds = self.focus_time * 60
                self.timer_label.config(text=self.format_time(self.remaining_seconds))
            
            messagebox.showinfo("Settings Saved", "Pomodoro settings updated!")
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers")
    
    def record_session(self):
        today = datetime.now().strftime('%Y-%m-%d')
        history = self.data_manager.get('pomodoro_history', {})
        
        if today not in history:
            history[today] = {'sessions': 0, 'focus_minutes': 0}
        
        history[today]['sessions'] += 1
        history[today]['focus_minutes'] += self.focus_time
        
        self.data_manager.set('pomodoro_history', history)
    
    def get_week_stats(self):
        history = self.data_manager.get('pomodoro_history', {})
        today = datetime.now()
        week_start = today - timedelta(days=today.weekday())
        
        total_sessions = 0
        total_minutes = 0
        
        for i in range(7):
            day = week_start + timedelta(days=i)
            day_key = day.strftime('%Y-%m-%d')
            if day_key in history:
                total_sessions += history[day_key]['sessions']
                total_minutes += history[day_key]['focus_minutes']
        
        return {'sessions': total_sessions, 'minutes': total_minutes}

# ============== SYSTEM TRAY / CONTROL PANEL ==============
class ControlPanel(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("Desktop Widgets Control")
        self.geometry("300x400")
        self.resizable(False, False)
        
        # Initialize data manager
        self.data_manager = DataManager()
        
        # Initialize desktop integration
        self.desktop_integration = None
        if sys.platform == 'win32':
            self.desktop_integration = WindowsDesktopIntegration()
        
        # Setup autostart if enabled
        if self.data_manager.get('autostart', True):
            setup_autostart(True)
        
        # Create widgets
        self.widgets = {}
        self.create_control_panel()
        self.create_widgets()
        
        # Hide control panel on close, show in tray
        self.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        
        # Minimize to tray on start
        self.after(1000, self.hide_to_tray)
    
    def create_control_panel(self):
        # Header
        header = tk.Label(
            self, text="🖥️ Desktop Widgets",
            font=('Segoe UI', 14, 'bold')
        )
        header.pack(pady=10)
        
        # Widget toggles
        toggle_frame = tk.LabelFrame(self, text="Show/Hide Widgets", font=('Segoe UI', 10, 'bold'))
        toggle_frame.pack(fill='x', padx=10, pady=5)
        
        widget_names = [
            ('calendar', '📅 Calendar'),
            ('todo', '✅ To-Do List'),
            ('day_planner', '📋 Day Planner'),
            ('weekly_planner', '📆 Weekly Planner'),
            ('monthly_planner', '🗓️ Monthly Planner'),
            ('pomodoro', '🍅 Pomodoro Timer')
        ]
        
        self.toggle_vars = {}
        visible = self.data_manager.get('widget_visible', {})
        
        for widget_id, widget_label in widget_names:
            var = tk.BooleanVar(value=visible.get(widget_id, True))
            self.toggle_vars[widget_id] = var
            
            cb = tk.Checkbutton(
                toggle_frame, text=widget_label, variable=var,
                font=('Segoe UI', 10),
                command=lambda wid=widget_id: self.toggle_widget(wid)
            )
            cb.pack(anchor='w', padx=10, pady=2)
        
        # Settings
        settings_frame = tk.LabelFrame(self, text="Settings", font=('Segoe UI', 10, 'bold'))
        settings_frame.pack(fill='x', padx=10, pady=5)
        
        # Autostart toggle
        self.autostart_var = tk.BooleanVar(value=self.data_manager.get('autostart', True))
        autostart_cb = tk.Checkbutton(
            settings_frame, text="Start with Windows", variable=self.autostart_var,
            font=('Segoe UI', 10), command=self.toggle_autostart
        )
        autostart_cb.pack(anchor='w', padx=10, pady=2)
        
        # Buttons
        btn_frame = tk.Frame(self)
        btn_frame.pack(fill='x', padx=10, pady=10)
        
        show_all_btn = tk.Button(
            btn_frame, text="Show All Widgets",
            command=self.show_all_widgets, font=('Segoe UI', 10)
        )
        show_all_btn.pack(fill='x', pady=2)
        
        hide_all_btn = tk.Button(
            btn_frame, text="Hide All Widgets",
            command=self.hide_all_widgets, font=('Segoe UI', 10)
        )
        hide_all_btn.pack(fill='x', pady=2)
        
        reset_btn = tk.Button(
            btn_frame, text="Reset Positions",
            command=self.reset_positions, font=('Segoe UI', 10)
        )
        reset_btn.pack(fill='x', pady=2)
        
        # Exit button
        exit_btn = tk.Button(
            self, text="Exit Application",
            command=self.exit_app, font=('Segoe UI', 10), fg='red'
        )
        exit_btn.pack(pady=10)
        
        # Show control panel button (floating)
        self.show_panel_btn = tk.Toplevel(self)
        self.show_panel_btn.title("")
        self.show_panel_btn.geometry("40x40+10+10")
        self.show_panel_btn.overrideredirect(True)
        self.show_panel_btn.attributes('-topmost', True)
        
        panel_btn = tk.Button(
            self.show_panel_btn, text="⚙️",
            font=('Segoe UI', 16), command=self.show_control_panel,
            cursor='hand2'
        )
        panel_btn.pack(fill='both', expand=True)
        
        # Make the button draggable
        self.show_panel_btn.bind('<Button-1>', self.start_btn_drag)
        self.show_panel_btn.bind('<B1-Motion>', self.on_btn_drag)
    
    def start_btn_drag(self, event):
        self.btn_drag_x = event.x
        self.btn_drag_y = event.y
    
    def on_btn_drag(self, event):
        x = self.show_panel_btn.winfo_x() + event.x - self.btn_drag_x
        y = self.show_panel_btn.winfo_y() + event.y - self.btn_drag_y
        self.show_panel_btn.geometry(f"+{x}+{y}")
    
    def create_widgets(self):
        visible = self.data_manager.get('widget_visible', {})
        
        # Create all widgets
        self.widgets['calendar'] = CalendarWidget(self, self.data_manager, self.desktop_integration)
        self.widgets['todo'] = TodoWidget(self, self.data_manager, self.desktop_integration)
        self.widgets['day_planner'] = DayPlannerWidget(self, self.data_manager, self.desktop_integration)
        self.widgets['weekly_planner'] = WeeklyPlannerWidget(self, self.data_manager, self.desktop_integration)
        self.widgets['monthly_planner'] = MonthlyPlannerWidget(self, self.data_manager, self.desktop_integration)
        self.widgets['pomodoro'] = PomodoroWidget(self, self.data_manager, self.desktop_integration)
        
        # Set initial visibility
        for widget_id, widget in self.widgets.items():
            if not visible.get(widget_id, True):
                widget.withdraw()
    
    def toggle_widget(self, widget_id):
        visible = self.toggle_vars[widget_id].get()
        vis_data = self.data_manager.get('widget_visible', {})
        vis_data[widget_id] = visible
        self.data_manager.set('widget_visible', vis_data)
        
        if visible:
            self.widgets[widget_id].deiconify()
        else:
            self.widgets[widget_id].withdraw()
    
    def toggle_autostart(self):
        enabled = self.autostart_var.get()
        self.data_manager.set('autostart', enabled)
        setup_autostart(enabled)
    
    def show_all_widgets(self):
        for widget_id in self.widgets:
            self.toggle_vars[widget_id].set(True)
            self.toggle_widget(widget_id)
    
    def hide_all_widgets(self):
        for widget_id in self.widgets:
            self.toggle_vars[widget_id].set(False)
            self.toggle_widget(widget_id)
    
    def reset_positions(self):
        positions = {}
        x, y = 100, 100
        for widget_id, widget in self.widgets.items():
            positions[widget_id] = {'x': x, 'y': y}
            widget.geometry(f"+{x}+{y}")
            x += 50
            y += 50
        self.data_manager.set('widget_positions', positions)
    
    def hide_to_tray(self):
        self.withdraw()
    
    def show_control_panel(self):
        self.deiconify()
        self.lift()
    
    def exit_app(self):
        self.data_manager.save_data()
        self.destroy()

# ============== MAIN ENTRY POINT ==============
def main():
    app = ControlPanel()
    app.mainloop()

if __name__ == "__main__":
    main()
