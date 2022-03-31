from app.DBHandler import Handler

import geopy
import telebot

locator = geopy.Nominatim(user_agent="A")
bot = telebot.TeleBot(open('config_file').read())
handler = Handler()