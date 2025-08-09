import telebot

# ضع التوكن الخاص بك هنا
TOKEN = "8217632244:AAH30Ytf-7koU93ni32WoNAKiy3h08lQXw0"
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً! البوت شغال ✅")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, message.text)

print("البوت يعمل الآن...")
bot.polling()
