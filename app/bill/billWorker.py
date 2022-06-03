from app.bill import Bill
from app import bot


def delete_bill(call, user_id, bill_id):
    Bill.get_bill(bill_id).delete()
    bot.delete_message(call.message.chat.id, call.message.id)


def renew_bill(call, user_id, bill_id):
    """Обновить просроченный счет"""
    Bill.get_bill(bill_id).renew()
    bot.delete_message(call.message.chat.id, call.message.id)