from app.DBHandler import Handler

import geopy
import telebot

locator = geopy.Nominatim(user_agent="A")
#bot = telebot.TeleBot(open('config_file').read())
bot = telebot.TeleBot('1844480969:AAGiJFJnqAIA1jQBLQSlpBYJDno6qH27t9E')
handler = Handler()
