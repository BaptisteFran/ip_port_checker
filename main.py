import tkinter as tk
from tkinter import messagebox
import socket
import threading
import time
import json
import os

SAVE_FILE = "monitor_settings.json"
CHECK_INTERVAL = 600 # 10 Minutes

class MonitorApp:
    def __init__(self, root):
        self.scrollbar = None
        self.canvas_window = None
        self.canvas = None
        self.main_targets_frame = None
        self.root = root
        self.root.title("Surveillance réseau")
        self.root.focus_force()
        self.targets = [] # Liste ip, ports
        self.status_labels = []

        self.bg_color = '#2b2b2b'
        self.fg_color = 'white'
        self.placeholder_color = 'grey'


        # Interface
        self.frame = tk.Frame(self.root)
        self.frame.pack(padx=10, pady=10)

        tk.Label(self.frame, text="Description:", fg="gray").grid(row=0, column=0, sticky='w')
        tk.Label(self.frame, text="Adresse IP:", fg="gray").grid(row=0, column=1, sticky='w')
        tk.Label(self.frame, text="Port:", fg="gray").grid(row=0, column=2, sticky='w')

        self.description = tk.Entry(self.frame, width=15, fg="gray")
        self.description.grid(row=1, column=0, padx=5)
        self.description.insert(0, "ex: Serveur web")
        self.description.bind("<FocusIn>", lambda e: self.clear_placeholder(self.description, "ex: Serveur web"))
        self.description.bind("<FocusOut>", lambda e: self.restore_placeholder(self.description, "ex: Serveur web"))

        self.ip_entry = tk.Entry(self.frame, width=15, fg="gray")
        self.ip_entry.grid(row=1, column=1, padx=5)
        self.ip_entry.insert(0, "192.168.1.1")
        self.ip_entry.bind("<FocusIn>", lambda e: self.clear_placeholder(self.ip_entry, "192.168.1.1"))
        self.ip_entry.bind("<FocusOut>", lambda e: self.restore_placeholder(self.ip_entry, "192.168.1.1"))

        self.port_entry = tk.Entry(self.frame, width=10, fg="gray")
        self.port_entry.grid(row=1, column=2, padx=5)
        self.port_entry.insert(0, "80")
        self.port_entry.bind("<FocusIn>", lambda e: self.clear_placeholder(self.port_entry, "80"))
        self.port_entry.bind("<FocusOut>", lambda e: self.restore_placeholder(self.port_entry, "80"))

        self.add_btn = tk.Button(self.frame, text="Ajouter", command=self.add_target)
        self.add_btn.grid(row=1, column=3, padx=5)

        self.check_btn = tk.Button(self.frame, text="Vérifier maintenant", command=self.manual_check)
        self.check_btn.grid(row=2, column=0, columnspan=4, pady=10)

        self.targets_frame = tk.Frame(self.root)
        self.targets_frame.pack()

        self.placeholders = {
            self.description: "ex: Serveur web",
            self.ip_entry: "192.168.1.1",
            self.port_entry: "80"
        }

        self.create_scrollable_targets_frame()

        self.load_targets()
        self.start_periodic_check()

    def clear_placeholder(self, entry, placeholder_text):
        if entry.get() == placeholder_text:
            entry.delete(0, tk.END)
            entry.config(fg='white')

    def restore_placeholder(self, entry, placeholder_text):
        if entry.get() == "":
            entry.insert(0, placeholder_text)
            entry.config(fg='grey')

    def add_target(self):
        description = self.description.get().strip()
        if description == self.placeholders[self.description]:
            description = ""

        ip = self.ip_entry.get().strip()
        if ip == self.placeholders[self.ip_entry]:
            ip = ""

        port = self.port_entry.get().strip()
        if port == self.placeholders[self.port_entry]:
            port = ""

        if not ip or not port:
            messagebox.showerror("Erreur", "IP et port requis.")
            return
        try:
            port = int(port)
            if (description, ip, port) in self.targets:
                messagebox.showwarning("Doublon", f"{ip}:{port} est déjà dans la liste.")
                return
            self.targets.append((description, ip, port))
            self.display_target(description, ip, port)

            self.description.delete(0, tk.END)
            self.description.insert(0, self.placeholders[self.description])
            self.description.config(fg='grey')

            self.ip_entry.delete(0, tk.END)
            self.ip_entry.insert(0, self.placeholders[self.ip_entry])
            self.ip_entry.config(fg='grey')

            self.port_entry.delete(0, tk.END)
            self.port_entry.insert(0, self.placeholders[self.port_entry])
            self.port_entry.config(fg='grey')

            self.save_targets()
        except ValueError:
            messagebox.showerror("Erreur", "Le port doit être un nombre.")


    def check_target(self, ip, port):
        try:
            with socket.create_connection((ip, port), timeout=3):
                return True
        except Exception:
            return False


    def periodic_check(self):
        while True:
            time.sleep(CHECK_INTERVAL)
            self.update_statuses()

    def start_periodic_check(self):
        threading.Thread(target=self.periodic_check, daemon=True).start()
        self.manual_check()

    def create_scrollable_targets_frame(self):
        self.main_targets_frame = tk.Frame(self.root, bg=self.bg_color)
        self.main_targets_frame.pack(fill='both', expand=True, padx=10, pady=5)

        self.canvas = tk.Canvas(
            self.main_targets_frame,
            bg=self.bg_color,
            highlightthickness=0,
            height=300
        )
        self.canvas.pack(side='left', fill='both', expand=True)

        self.scrollbar = tk.Scrollbar(
            self.main_targets_frame,
            orient='vertical',
            command=self.canvas.yview
        )
        self.scrollbar.pack(side='right', fill='y')

        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.targets_frame = tk.Frame(self.canvas, bg=self.bg_color)
        self.canvas_window = self.canvas.create_window(
            (0, 0),
            window=self.targets_frame,
            anchor='nw'
        )

        self.targets_frame.bind('<Configure>', self.on_frame_configure)
        self.canvas.bind('<Configure>', self.on_canvas_configure)

        self.canvas.bind('<MouseWheel>', self.on_mousewheel)
        self.canvas.bind('<Button-4>', self.on_mousewheel)
        self.canvas.bind('<Button-5>', self.on_mousewheel)

    def on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def on_canvas_configure(self, event):
        canvas_width = event.width
        self.canvas.itemconfig(self.canvas_window, width=canvas_width)

    def on_mousewheel(self, event):
        if event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, 'units')
        elif event.num == 5 or event.delta < 0:
            self.canvas.yview_scroll(1, 'units')

    def display_target(self, description, ip, port):
        row = len(self.status_labels)

        target_frame = tk.Frame(
            self.targets_frame,
            bg=self.bg_color,
            relief='raised',
            bd=0
        )
        target_frame.grid(row=row, column=0, sticky='ew', padx=5, pady=5)

        self.targets_frame.grid_columnconfigure(0, weight=1)
        target_frame.grid_columnconfigure(0, weight=1)

        label = tk.Label(
            target_frame,
            text=f"{description} - {ip}:{port}",
            bg=self.bg_color,
            fg=self.fg_color,
            anchor='w',
            padx=10,
            pady=8
        )
        label.grid(row=0, column=0, sticky='ew')

        btn = tk.Button(
            target_frame,
            text="x",
            command=lambda: self.remove_target(description, ip, port, target_frame),
            bg=self.bg_color,
            fg='black',
            width=3,
            relief='flat'
        )
        btn.grid(row=0, column=1, padx=5)

        self.status_labels.append((description, ip, port, label, btn, target_frame))

    def remove_target(self, description, ip, port, target_frame):
        if (description, ip, port) in self.targets:
            self.targets.remove((description, ip, port))

        target_frame.destroy()

        self.status_labels = [
            entry for entry in self.status_labels
            if not (entry[0] == description and entry[1] == ip and entry[2] == port)
        ]

        self.rebuild_targets_grid()
        self.save_targets()

    def rebuild_targets_grid(self):
        for i, (description, ip, port, label, btn, target_frame) in enumerate(self.status_labels):
            try:
                target_frame.grid(row=i, column=0, sticky='ew', padx=5, pady=5)
            except tk.TclError:
                pass

    def update_statuses(self):
        for description, ip, port, label, btn, target_frame in self.status_labels:
            status = "🟢 En ligne" if self.check_target(ip, port) else "🔴 Hors ligne"
            label.config(text=f"{description} - {ip}:{port} - {status}")

    def manual_check(self):
        for description, ip, port, label, btn, target_frame in self.status_labels:
            status = "⏳ En attente..."
            label.config(text=f"{description} - {ip}:{port} - {status}")
        threading.Thread(target=self.update_statuses).start()

    def load_targets(self):
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE, "r") as f:
                    data = json.load(f)
                    for entry in data:
                        description = entry.get("description", "")
                        ip = entry.get("ip", "")
                        port = entry.get("port", 0)
                        if ip and isinstance(port, int):
                            self.targets.append((description, ip, port))
                            self.display_target(description, ip, port)
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors du chargement : {e}")

    def save_targets(self):
        data = [{"description": description, "ip": ip, "port": port} for description, ip, port in self.targets]
        try:
            with open(SAVE_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la sauvegarde : {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = MonitorApp(root)
    root.mainloop()