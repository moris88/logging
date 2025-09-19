from calendar_logger.app import App
from calendar_logger.database import Database

if __name__ == "__main__":
    # Inizializza il database e crea la tabella se non esiste
    db = Database()
    db.create_table()

    # Crea e avvia l'applicazione
    app = App(db=db)
    app.mainloop()