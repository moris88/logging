import customtkinter as ctk
import locale
import math
from datetime import datetime, timedelta
from tkcalendar import Calendar
from calendar_logger.zoho_api import get_projects, get_tasks, log_time_to_zoho
from calendar_logger import settings_manager

# --- WIDGET EVENTO DRAGGABILE ---
class DraggableEventButton(ctk.CTkButton):
    def __init__(self, master, event, app_controller, **kwargs):
        super().__init__(master, **kwargs)
        self.event_data = event
        self.app = app_controller

        # Variabili per distinguere click da drag
        self.press_time = None
        self.press_pos = None

        if self.event_data['is_logged'] == 0:
            self.bind("<ButtonPress-1>", self.on_press)
            self.bind("<B1-Motion>", self.on_drag)
            self.bind("<ButtonRelease-1>", self.on_release)

    def on_press(self, event):
        self.press_time = datetime.now()
        self.press_pos = (event.x_root, event.y_root)
        self.lift()

    def on_drag(self, event):
        # Usa place per far fluttuare il widget durante il drag
        x = self.winfo_x() - (self.press_pos[0] - event.x_root)
        y = self.winfo_y() - (self.press_pos[1] - event.y_root)
        self.place(x=x, y=y)

    def on_release(self, event):
        self.lower()
        # Annulla il place e rimetti il widget nella griglia (verrà distrutto e ricreato)
        self.place_forget()

        # Distingui click da drag
        is_drag = (datetime.now() - self.press_time) > timedelta(milliseconds=200) or \
                  abs(event.x_root - self.press_pos[0]) > 5 or \
                  abs(event.y_root - self.press_pos[1]) > 5

        if not is_drag:
            self.app.open_view_event_window(self.event_data)
            return

        # Logica di Drop (più robusta)
        self.place_forget() # Nasconde il widget per trovare cosa c'è sotto
        widget_under_cursor = self.winfo_containing(event.x_root, event.y_root)
        self.app.rebuild_calendar() # Mostra di nuovo tutto per evitare buchi visivi

        if widget_under_cursor in self.app.calendar_cells:
            try:
                # Trova la riga e colonna della cella di destinazione
                for r, row_list in enumerate(self.app.calendar_cells):
                    if widget_under_cursor in row_list:
                        new_row = r
                        new_col = row_list.index(widget_under_cursor)
                        break
                else:
                    raise ValueError("Cella non trovata")

                new_start_dt = self.app.current_week_start + timedelta(days=new_col)
                time_delta = timedelta(minutes=(new_row * 30) + self.app.calendar_start_hour * 60)
                new_start_dt = new_start_dt.replace(hour=0, minute=0, second=0, microsecond=0) + time_delta

                original_start = datetime.strptime(self.event_data['start_time'], '%Y-%m-%d %H:%M')
                original_end = datetime.strptime(self.event_data['end_time'], '%Y-%m-%d %H:%M')
                duration = original_end - original_start
                new_end_dt = new_start_dt + duration

                self.app.db.update_event(
                    self.event_data['id'], self.event_data['name'], self.event_data['description'],
                    new_start_dt.strftime('%Y-%m-%d %H:%M'), new_end_dt.strftime('%Y-%m-%d %H:%M')
                )
            except Exception as e:
                print(f"Errore durante il drop: {e}")
            finally:
                self.app.rebuild_calendar()

# --- CLASSE PRINCIPALE APP ---
class App(ctk.CTk):
    # ... [Il resto della classe App rimane invariato] ...
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.event_widgets = []
        self.calendar_cells = []
        self.calendar_start_hour = 8
        today = datetime.now()
        self.current_week_start = today - timedelta(days=today.weekday())

        try:
            locale.setlocale(locale.LC_TIME, 'it_IT.UTF-8')
        except locale.Error:
            try:
                locale.setlocale(locale.LC_TIME, 'Italian_Italy.1252')
            except locale.Error:
                print("Locale italiano non trovato")

        self.title("Calendario Eventi e Logging")
        self.geometry("1200x800")
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        top_frame = ctk.CTkFrame(self)
        top_frame.grid(row=0, column=0, columnspan=5, padx=10, pady=5, sticky="ew")
        top_frame.grid_columnconfigure(1, weight=1)

        prev_week_btn = ctk.CTkButton(top_frame, text="< Sett. Prec.", command=self.prev_week)
        prev_week_btn.grid(row=0, column=0, padx=5)

        self.week_label_var = ctk.StringVar()
        week_label = ctk.CTkLabel(top_frame, textvariable=self.week_label_var, font=ctk.CTkFont(size=16, weight="bold"))
        week_label.grid(row=0, column=1)

        next_week_btn = ctk.CTkButton(top_frame, text="Sett. Succ. >", command=self.next_week)
        next_week_btn.grid(row=0, column=2, padx=5)

        self.calendar_frame = ctk.CTkFrame(self)
        self.calendar_frame.grid(row=1, column=0, columnspan=5, sticky="nsew", padx=10, pady=10)
        self.calendar_frame.grid_columnconfigure(0, weight=1)
        self.calendar_frame.grid_rowconfigure(1, weight=1)

        self.action_frame = ctk.CTkFrame(self)
        self.action_frame.grid(row=2, column=0, columnspan=5, padx=10, pady=10, sticky="ew")
        self.action_frame.grid_columnconfigure((0, 1), weight=1)
        self.add_event_button = ctk.CTkButton(self.action_frame, text="Aggiungi Evento", command=self.open_add_event_window)
        self.add_event_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.settings_button = ctk.CTkButton(self.action_frame, text="Impostazioni", command=self.open_settings_window)
        self.settings_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.rebuild_calendar()

    def change_week(self, weeks_delta):
        self.current_week_start += timedelta(weeks=weeks_delta)
        self.rebuild_calendar()

    def prev_week(self):
        self.change_week(-1)

    def next_week(self):
        self.change_week(1)

    def open_datepicker(self, date_var, on_close_callback):
        top = ctk.CTkToplevel(self)
        top.title("Seleziona Data")
        top.transient(self)
        top.grab_set()
        try:
            current_date = datetime.strptime(date_var.get(), "%Y-%m-%d")
        except ValueError:
            current_date = datetime.now()
        cal = Calendar(top, selectmode='day', year=current_date.year, month=current_date.month, day=current_date.day, locale='it_IT')
        cal.pack(pady=20)
        def set_date_and_close():
            date_var.set(cal.strftime("%Y-%m-%d"))
            top.destroy()
            if on_close_callback:
                on_close_callback()
        confirm_button = ctk.CTkButton(top, text="Conferma", command=set_date_and_close)
        confirm_button.pack(pady=10)

    def rebuild_calendar(self):
        for widget in self.calendar_frame.winfo_children():
            widget.destroy()
        self.create_calendar_grid()
        self.refresh_events()

    def _create_datetime_picker(self, parent, frame_title, initial_datetime, form_state):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill='x', expand=True, padx=10, pady=5)
        ctk.CTkLabel(frame, text=frame_title, font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10)
        date_var = ctk.StringVar(value=initial_datetime.strftime("%Y-%m-%d"))
        hour_var = ctk.StringVar(value=initial_datetime.strftime("%H"))
        min_var = ctk.StringVar(value=initial_datetime.strftime("%M"))
        summary_var = ctk.StringVar()
        date_frame = ctk.CTkFrame(frame, fg_color="transparent")
        date_frame.pack(fill='x', expand=True, padx=10, pady=5)
        ctk.CTkLabel(date_frame, text="Data:", width=60).pack(side="left")
        date_entry = ctk.CTkEntry(date_frame, textvariable=date_var, state="readonly")
        date_entry.pack(side="left", expand=True, fill="x")
        datepicker_btn = ctk.CTkButton(date_frame, text="...", width=30, state=form_state,
                                       command=lambda: self.open_datepicker(date_var, lambda: self._update_summary(summary_var, date_var, hour_var, min_var)))
        datepicker_btn.pack(side="left", padx=5)
        time_frame = ctk.CTkFrame(frame, fg_color="transparent")
        time_frame.pack(fill='x', expand=True, padx=10, pady=5)
        ctk.CTkLabel(time_frame, text="Ora:", width=60).pack(side="left")
        hour_options = [f"{h:02d}" for h in range(24)]
        minute_options = ["00", "30"]
        hour_menu = ctk.CTkOptionMenu(time_frame, variable=hour_var, values=hour_options, state=form_state)
        hour_menu.pack(side="left", padx=(0,5))
        min_menu = ctk.CTkOptionMenu(time_frame, variable=min_var, values=minute_options, state=form_state)
        min_menu.pack(side="left")
        summary_frame = ctk.CTkFrame(frame, fg_color="transparent")
        summary_frame.pack(fill='x', expand=True, padx=10, pady=5)
        ctk.CTkLabel(summary_frame, text="Scelta:", width=60).pack(side="left")
        summary_label = ctk.CTkEntry(summary_frame, textvariable=summary_var, state="readonly", fg_color="transparent", border_width=0)
        summary_label.pack(side="left", fill="x", expand=True)
        hour_var.trace_add("write", lambda *args: self._update_summary(summary_var, date_var, hour_var, min_var))
        min_var.trace_add("write", lambda *args: self._update_summary(summary_var, date_var, hour_var, min_var))
        self._update_summary(summary_var, date_var, hour_var, min_var)
        return date_var, hour_var, min_var

    def _update_summary(self, summary_var, date_var, hour_var, min_var):
        days = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
        months = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
        try:
            dt = datetime.strptime(f"{date_var.get()} {hour_var.get()}:{min_var.get()}", "%Y-%m-%d %H:%M")
            day_name = days[dt.weekday()]
            month_name = months[dt.month - 1]
            summary_var.set(f"{day_name} {dt.day} {month_name} {dt.year}, {dt.strftime('%H:%M')}")
        except ValueError:
            summary_var.set("Data non valida")

    def create_calendar_grid(self):
        start_of_week = self.current_week_start
        end_of_week = start_of_week + timedelta(days=4)
        self.week_label_var.set(f"{start_of_week.strftime('%d %b')} - {end_of_week.strftime('%d %b %Y')}")
        days = [(start_of_week + timedelta(days=i)).strftime("%A %d") for i in range(5)]
        day_labels_frame = ctk.CTkFrame(self.calendar_frame)
        day_labels_frame.grid(row=0, column=0, columnspan=6, sticky="ew")
        ctk.CTkLabel(day_labels_frame, text="").pack(side="left", padx=25)
        for i, day_str in enumerate(days):
            label = ctk.CTkLabel(day_labels_frame, text=day_str, font=ctk.CTkFont(size=14, weight="bold"))
            label.pack(side="left", fill="x", expand=True)
        hours = settings_manager.get_calendar_hours()
        self.calendar_start_hour = int(hours["start_hour"])
        end_hour = int(hours["end_hour"])
        self.scrollable_frame = ctk.CTkScrollableFrame(self.calendar_frame)
        self.scrollable_frame.grid(row=1, column=0, columnspan=6, sticky="nsew")
        self.calendar_frame.grid_rowconfigure(1, weight=1)
        self.scrollable_frame.grid_columnconfigure((1, 2, 3, 4, 5), weight=1)
        self.calendar_cells = []
        for i in range((end_hour - self.calendar_start_hour) * 2):
            hour = self.calendar_start_hour + i // 2
            minute = (i % 2) * 30
            row_cells = []
            time_label = ctk.CTkLabel(self.scrollable_frame, text=f"{hour:02d}:{minute:02d}", font=ctk.CTkFont(size=10))
            time_label.grid(row=i, column=0, padx=5, pady=5, sticky="e")
            for day in range(5):
                cell_frame = ctk.CTkFrame(self.scrollable_frame, border_width=1, fg_color="transparent", corner_radius=0, height=30)
                cell_frame.grid(row=i, column=day+1, padx=0, pady=0, sticky="nsew")
                row_cells.append(cell_frame)
            self.calendar_cells.append(row_cells)

    def refresh_events(self):
        for widget in self.event_widgets:
            widget.destroy()
        self.event_widgets.clear()
        start_str = self.current_week_start.strftime("%Y-%m-%d 00:00:00")
        end_str = (self.current_week_start + timedelta(days=5)).strftime("%Y-%m-%d 23:59:59")
        events = self.db.get_events_for_week(start_str, end_str)
        for event in events:
            try:
                start_dt = datetime.strptime(event['start_time'], '%Y-%m-%d %H:%M')
                end_dt = datetime.strptime(event['end_time'], '%Y-%m-%d %H:%M')
            except ValueError:
                continue
            if start_dt.weekday() > 4: continue
            row = (start_dt.hour - self.calendar_start_hour) * 2 + (1 if start_dt.minute >= 30 else 0)
            col = start_dt.weekday()
            duration_minutes = (end_dt - start_dt).total_seconds() / 60
            num_slots = max(1, math.ceil(duration_minutes / 30))
            if not (0 <= row < len(self.calendar_cells)): continue
            event_text = f"{event['name']}"
            event_button = DraggableEventButton(self.scrollable_frame, event=event, app_controller=self, text=event_text, 
                                              fg_color="#c9514a" if event['is_logged'] else "#3b8ed0", 
                                              font=ctk.CTkFont(size=10))
            event_button.grid(row=row, column=col+1, rowspan=num_slots, padx=1, pady=1, sticky="nsew")
            self.event_widgets.append(event_button)

    def open_settings_window(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Impostazioni")
        dialog.geometry("500x500")
        dialog.grid_columnconfigure(1, weight=1)
        dialog.transient(self)
        dialog.grab_set()
        creds = settings_manager.get_credentials()
        hours = settings_manager.get_calendar_hours()
        ctk.CTkLabel(dialog, text="Impostazioni API Zoho", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, padx=10, pady=(10,5), sticky="w")
        ctk.CTkLabel(dialog, text="Client ID:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        client_id_entry = ctk.CTkEntry(dialog, width=300)
        client_id_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        if creds.get("client_id"): client_id_entry.insert(0, creds["client_id"])
        ctk.CTkLabel(dialog, text="Client Secret:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        client_secret_entry = ctk.CTkEntry(dialog, show="*", width=300)
        client_secret_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        if creds.get("client_secret"): client_secret_entry.insert(0, creds["client_secret"])
        ctk.CTkLabel(dialog, text="Refresh Token:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        refresh_token_entry = ctk.CTkEntry(dialog, show="*", width=300)
        refresh_token_entry.grid(row=3, column=1, padx=10, pady=5, sticky="ew")
        if creds.get("refresh_token"): refresh_token_entry.insert(0, creds["refresh_token"])
        ctk.CTkLabel(dialog, text="Dominio API:").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        api_domain_entry = ctk.CTkEntry(dialog, placeholder_text="es. https://www.zohoapis.eu", width=300)
        api_domain_entry.grid(row=4, column=1, padx=10, pady=5, sticky="ew")
        if creds.get("api_domain"): api_domain_entry.insert(0, creds["api_domain"])
        ctk.CTkLabel(dialog, text="Impostazioni Calendario", font=ctk.CTkFont(weight="bold")).grid(row=5, column=0, columnspan=2, padx=10, pady=(20,5), sticky="w")
        ctk.CTkLabel(dialog, text="Ora Inizio:").grid(row=6, column=0, padx=10, pady=5, sticky="w")
        start_hour_entry = ctk.CTkEntry(dialog, width=100)
        start_hour_entry.grid(row=6, column=1, padx=10, pady=5, sticky="w")
        start_hour_entry.insert(0, hours["start_hour"])
        ctk.CTkLabel(dialog, text="Ora Fine:").grid(row=7, column=0, padx=10, pady=5, sticky="w")
        end_hour_entry = ctk.CTkEntry(dialog, width=100)
        end_hour_entry.grid(row=7, column=1, padx=10, pady=5, sticky="w")
        end_hour_entry.insert(0, hours["end_hour"])
        def save_all_settings():
            self.save_settings_action(client_id_entry, client_secret_entry, refresh_token_entry, api_domain_entry, start_hour_entry, end_hour_entry)
            dialog.destroy()
            self.rebuild_calendar()
        save_button = ctk.CTkButton(dialog, text="Salva Impostazioni", command=save_all_settings)
        save_button.grid(row=8, column=0, columnspan=2, padx=10, pady=20, sticky="ew")

    def save_settings_action(self, client_id_entry, client_secret_entry, refresh_token_entry, api_domain_entry, start_hour_entry, end_hour_entry):
        settings_manager.save_credentials(client_id_entry.get(), client_secret_entry.get(), refresh_token_entry.get(), api_domain_entry.get())
        settings_manager.save_calendar_hours(start_hour_entry.get(), end_hour_entry.get())
        print("Impostazioni salvate.")

    def open_add_event_window(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Aggiungi Nuovo Evento")
        dialog.geometry("450x600")
        dialog.transient(self)
        dialog.grab_set()
        ctk.CTkLabel(dialog, text="Nome:").pack(anchor="w", padx=20, pady=(10,0))
        name_entry = ctk.CTkEntry(dialog)
        name_entry.pack(fill='x', padx=20, pady=5)
        ctk.CTkLabel(dialog, text="Descrizione:").pack(anchor="w", padx=20, pady=(10,0))
        desc_box = ctk.CTkTextbox(dialog, height=100)
        desc_box.pack(fill='x', padx=20, pady=5)
        start_dt = datetime.now().replace(second=0, microsecond=0)
        end_dt = start_dt + timedelta(hours=1)
        start_date_var, start_hour_var, start_min_var = self._create_datetime_picker(dialog, "Inizio", start_dt, 'normal')
        end_date_var, end_hour_var, end_min_var = self._create_datetime_picker(dialog, "Fine", end_dt, 'normal')
        def set_default_end_time(*args):
            try:
                start_datetime = datetime.strptime(f"{start_date_var.get()} {start_hour_var.get()}:{start_min_var.get()}", "%Y-%m-%d %H:%M")
                end_datetime = start_datetime + timedelta(hours=1)
                end_date_var.set(end_datetime.strftime("%Y-%m-%d"))
                end_hour_var.set(end_datetime.strftime("%H"))
                end_min_var.set(end_datetime.strftime("%M"))
            except (ValueError, TypeError): pass
        start_hour_var.trace_add("write", set_default_end_time)
        start_min_var.trace_add("write", set_default_end_time)
        def save_action():
            start_time_str = f"{start_date_var.get()} {start_hour_var.get()}:{start_min_var.get()}"
            end_time_str = f"{end_date_var.get()} {end_hour_var.get()}:{end_min_var.get()}"
            self.save_event(dialog, name_entry, desc_box, start_time_str, end_time_str)
        save_button = ctk.CTkButton(dialog, text="Salva Evento", command=save_action)
        save_button.pack(fill='x', padx=20, pady=20)

    def save_event(self, dialog, name_entry, desc_box, start_time_str, end_time_str):
        name = name_entry.get()
        description = desc_box.get("1.0", "end-1c")
        if not all([name, start_time_str, end_time_str]):
            print("Errore: Dati evento incompleti.")
            return
        self.db.add_event(name, description, start_time_str, end_time_str)
        dialog.destroy()
        self.refresh_events()

    def open_view_event_window(self, event):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Dettagli Evento")
        dialog.geometry("450x600")
        dialog.transient(self)
        dialog.grab_set()
        is_logged = event['is_logged'] == 1
        form_state = "disabled" if is_logged else "normal"
        ctk.CTkLabel(dialog, text="Nome:").pack(anchor="w", padx=20, pady=(10,0))
        name_entry = ctk.CTkEntry(dialog, state=form_state)
        name_entry.pack(fill='x', padx=20, pady=5)
        name_entry.insert(0, event['name'])
        ctk.CTkLabel(dialog, text="Descrizione:").pack(anchor="w", padx=20, pady=(10,0))
        desc_box = ctk.CTkTextbox(dialog, height=80)
        desc_box.pack(fill='x', padx=20, pady=5)
        desc_box.insert("1.0", event['description'])
        desc_box.configure(state=form_state)
        start_dt = datetime.strptime(event['start_time'], '%Y-%m-%d %H:%M')
        end_dt = datetime.strptime(event['end_time'], '%Y-%m-%d %H:%M')
        start_date_var, start_hour_var, start_min_var = self._create_datetime_picker(dialog, "Inizio", start_dt, form_state)
        end_date_var, end_hour_var, end_min_var = self._create_datetime_picker(dialog, "Fine", end_dt, form_state)
        event_end_dt = datetime.strptime(event['end_time'], '%Y-%m-%d %H:%M')
        is_past = event_end_dt < datetime.now()
        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(fill='x', expand=True, padx=10, pady=10)
        button_frame.grid_columnconfigure((0, 1), weight=1)
        if is_logged:
            logged_label = ctk.CTkLabel(dialog, text="Questo evento è stato loggato e non può essere modificato.", text_color="#c9514a")
            logged_label.pack(pady=20)
        else:
            delete_button = ctk.CTkButton(button_frame, text="Elimina", fg_color="transparent", border_width=2, text_color=("gray10", "#DCE4EE"), command=lambda: self.delete_event_action(dialog, event['id']))
            delete_button.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
            def update_action():
                start_time_str = f"{start_date_var.get()} {start_hour_var.get()}:{start_min_var.get()}"
                end_time_str = f"{end_date_var.get()} {end_hour_var.get()}:{end_min_var.get()}"
                self.update_event_action(dialog, event['id'], name_entry.get(), desc_box.get("1.0", "end-1c"), start_time_str, end_time_str)
            save_button = ctk.CTkButton(button_frame, text="Salva Modifiche", command=update_action)
            save_button.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
            if is_past:
                save_button.grid_forget()
                log_button = ctk.CTkButton(button_frame, text="Logga su Zoho", fg_color="#4CAF50", hover_color="#388E3C", command=lambda: self.open_zoho_log_window(dialog, event))
                log_button.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

    def update_event_action(self, dialog, event_id, name, description, start_time, end_time):
        self.db.update_event(event_id, name, description, start_time, end_time)
        dialog.destroy()
        self.refresh_events()

    def delete_event_action(self, dialog, event_id):
        self.db.delete_event(event_id)
        dialog.destroy()
        self.refresh_events()

    def open_zoho_log_window(self, parent_dialog, event):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Log Time su Zoho")
        dialog.geometry("450x450")
        dialog.grid_columnconfigure(1, weight=1)
        dialog.transient(self)
        dialog.grab_set()
        ctk.CTkLabel(dialog, text="Portal ID:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        portal_entry = ctk.CTkEntry(dialog)
        portal_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        ctk.CTkLabel(dialog, text="Progetto:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        project_menu = ctk.CTkOptionMenu(dialog, values=["Caricamento..."])
        project_menu.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        ctk.CTkLabel(dialog, text="Task:").grid(row=2, column=0, padx=10, pady=10, sticky="w")
        task_menu = ctk.CTkOptionMenu(dialog, values=["Seleziona un progetto"])
        task_menu.grid(row=2, column=1, padx=10, pady=10, sticky="ew")
        task_menu.configure(state="disabled")
        ctk.CTkLabel(dialog, text="Note:").grid(row=3, column=0, padx=10, pady=10, sticky="w")
        notes_box = ctk.CTkTextbox(dialog, height=100)
        notes_box.grid(row=3, column=1, padx=10, pady=10, sticky="ew")
        notes_box.insert("1.0", event.get('description', ''))
        projects_data = []
        tasks_data = []
        def load_projects():
            portal_id = portal_entry.get()
            if not portal_id: return
            projects, error = get_projects(portal_id)
            if error:
                project_menu.configure(values=[f"Errore: {error}"])
                return
            nonlocal projects_data
            projects_data = projects
            project_names = [p['name'] for p in projects_data]
            project_menu.configure(values=project_names if project_names else ["Nessun progetto trovato"], command=on_project_selected)
        def on_project_selected(selected_project_name):
            task_menu.configure(state="disabled", values=["Caricamento..."])
            selected_project_id = next((p['id_string'] for p in projects_data if p['name'] == selected_project_name), None)
            if not selected_project_id: return
            tasks, error = get_tasks(portal_entry.get(), selected_project_id)
            if error:
                task_menu.configure(values=[f"Errore: {error}"])
                return
            nonlocal tasks_data
            tasks_data = tasks
            task_names = [t['name'] for t in tasks_data]
            task_menu.configure(state="normal", values=task_names if task_names else ["Nessun task trovato"])
        portal_entry.bind("<KeyRelease>", lambda e: load_projects())
        def register_action():
            selected_project_name = project_menu.get()
            selected_task_name = task_menu.get()
            project_id = next((p['id_string'] for p in projects_data if p['name'] == selected_project_name), None)
            task_id = next((t['id_string'] for t in tasks_data if t['name'] == selected_task_name), None)
            notes = notes_box.get("1.0", "end-1c")
            if not all([project_id, task_id]):
                print("Errore: Progetto o Task non validi")
                return
            self.execute_zoho_log(dialog, parent_dialog, event, portal_entry.get(), project_id, task_id, notes)
        log_button = ctk.CTkButton(dialog, text="Registra Tempo", command=register_action)
        log_button.grid(row=4, column=0, columnspan=2, padx=10, pady=20, sticky="ew")

    def execute_zoho_log(self, log_dialog, event_dialog, event, portal_id, project_id, task_id, notes):
        start_dt = datetime.strptime(event['start_time'], '%Y-%m-%d %H:%M')
        end_dt = datetime.strptime(event['end_time'], '%Y-%m-%d %H:%M')
        duration_hours = (end_dt - start_dt).total_seconds() / 3600
        log_date = start_dt.strftime("%m-%d-%Y")
        response = log_time_to_zoho(
            portal_id=portal_id,
            project_id=project_id,
            task_id=task_id,
            event_name=event['name'],
            hours=duration_hours,
            notes=notes,
            log_date=log_date
        )
        if response["success"]:
            self.db.set_event_logged(event['id'])
            log_dialog.destroy()
            event_dialog.destroy()
            self.refresh_events()
        else:
            print(f"Errore durante il logging su Zoho: {response['message']}")
