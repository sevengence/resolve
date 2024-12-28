from pymongo import MongoClient
from datetime import datetime


class MongoController:
    def __init__(self, uri, db_name="data"):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        self.invoices = self.db["invoices"]

    def add_invoice(self, chat_id, message_id, client_name, user_id, full_name):
        """Добавление накладной в базу данных."""
        self.invoices.insert_one({
            "chat_id": chat_id,
            "message_id": message_id,
            "client_name": client_name,
            "added_by": {"user_id": user_id, "full_name": full_name},
            "status": "не решена",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        })

    def get_all_invoices(self):
        """Получение всех активных накладных."""
        return list(self.invoices.find({"status": "не решена"}))

    def find_invoice_by_message_id(self, message_id):
        """Поиск накладной по message_id."""
        return self.invoices.find_one({"message_id": message_id, "status": "не решена"})

    def delete_invoice(self, message_id):
        """Обновление статуса накладной на 'удалена'."""
        self.invoices.update_one(
            {"message_id": message_id},
            {"$set": {"status": "удалена", "updated_at": datetime.now()}}
        )

    def resolve_invoice(self, message_id):
        """Обновление статуса накладной на 'решена'."""
        self.invoices.update_one(
            {"message_id": message_id},
            {"$set": {"status": "решена", "updated_at": datetime.now()}}
        )

    def get_today_invoices(self):
        """Получение всех накладных за текущий день."""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return list(self.invoices.find({"created_at": {"$gte": today}}))

    def get_today_resolved_invoices(self):
        """Получение решённых накладных за текущий день."""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return list(self.invoices.find({"status": "решена", "updated_at": {"$gte": today}}))

    def get_today_deleted_invoices(self):
        """Получение удалённых накладных за текущий день."""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return list(self.invoices.find({"status": "удалена", "updated_at": {"$gte": today}}))
