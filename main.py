import requests
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext
from datetime import datetime, timezone

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')

# define start command
async def start_command(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("This bot can be used to travel around Switzerland with public transport. To use it, type \"/travel <departure> <destination>\". Let's do it !")

# define help command
async def help_command(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('You can use \"/start\" to begin.')

# define unknown command
async def unknown_command(update: Update, context: CallbackContext) -> None:
    chat = update.effective_chat
    if chat:
        await context.bot.send_message(chat_id = chat.id, text = "Try \"/travel <departure> <destination>\" or \"/travel <aller_epfl/retour_epfl/aller_heig/retour_heig>\" !")

# define api call
async def api_call(from_input, to_input):
    # contact with api
    query = f"https://transport.opendata.ch/v1/connections?from={from_input}&to={to_input}"
    response = requests.get(query)
    json_resp = response.json()

    # check valid travel
    if (len(json_resp['connections']) == 0):
        return "INVALID TRAVEL"

    # message construction
    # departure
    time = datetime.strptime(json_resp['connections'][0].get('from').get('departure'), '%Y-%m-%dT%H:%M:%S%z')
    message = f"\nDeparture : {time.strftime("%X")}\n"
    # duration
    duration = json_resp['connections'][0].get('duration')
    message += f"Duration : {duration}\n"
    # step
    message += "With :\n"
    step = ""
    for section in json_resp['connections'][0].get('sections', []):
        journey = section.get('journey')
        if journey:
            # construction category + number
            category = journey['category']
            number = journey['number']
            step += f"  - {category}{number}:\n"
            # construction from + to
            tmp_from = section.get('departure')['station'].get('name')
            tmp_from_time = datetime.strptime(section.get('departure').get('departure'), '%Y-%m-%dT%H:%M:%S%z').strftime("%X")
            step += f"      from : {tmp_from} - {tmp_from_time}\n"
            tmp_to = section.get('arrival').get('station').get('name')
            tmp_to_time = datetime.strptime(section.get('arrival').get('arrival'), '%Y-%m-%dT%H:%M:%S%z').strftime("%X")
            step += f"      to : {tmp_to} - {tmp_to_time}\n"
            # construction time
            tmp_time_elasped = datetime.fromtimestamp(section.get('arrival').get('arrivalTimestamp') - section.get('departure').get('departureTimestamp'), tz=timezone.utc).strftime("%X")
            step += f"      time : {tmp_time_elasped}\n"
    message += step

    return message

# define general travel command
async def travel_command(update: Update, context: CallbackContext):
    input = " ".join(context.args).split(" ")

    # check arguments
    if (len(input) != 2):
        await update.message.reply_text("INVALID PARAMETERS (\"/travel <departure> <destination>\")")
        return
    else:
        from_input = input[0]
        to_input = input[1]

    message = await api_call(from_input, to_input)
    await update.message.reply_text(message)

# define travel from home to epfl command
async def to_epfl_command(update: Update, context: CallbackContext):
    from_input = "Bottens, croisée"
    to_input = "Ecublens VD, EPFL"
    message = await api_call(from_input, to_input)
    await update.message.reply_text(message)

# define travel from epfl to home command
async def from_epfl_command(update: Update, context: CallbackContext):
    from_input = "Ecublens VD, EPFL"
    to_input = "Bottens, croisée"
    message = await api_call(from_input, to_input)
    await update.message.reply_text(message)

# define travel from home to heig command
async def to_heig_command(update: Update, context: CallbackContext):
    from_input = "Bottens, croisée"
    to_input = "Yverdon-les-Bains, HEIG-VD"
    message = await api_call(from_input, to_input)
    await update.message.reply_text(message)

# define travel from heig to home command
async def from_heig_command(update: Update, context: CallbackContext):
    from_input = "Yverdon-les-Bains, HEIG-VD"
    to_input = "Bottens, croisée"
    message = await api_call(from_input, to_input)
    await update.message.reply_text(message)

def main():
    token = BOT_TOKEN
    app = ApplicationBuilder().token(token).concurrent_updates(True).read_timeout(30).write_timeout(30).build()

    # commands handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))

    app.add_handler(CommandHandler("travel", travel_command))
    app.add_handler(CommandHandler("aller_epfl", to_epfl_command))
    app.add_handler(CommandHandler("retour_epfl", from_epfl_command))
    app.add_handler(CommandHandler("aller_heig", to_heig_command))
    app.add_handler(CommandHandler("retour_heig", from_heig_command))

    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    app.add_handler(MessageHandler(filters.TEXT, unknown_command))
    
    print("Telegram Bot started !", flush=True)

    app.run_polling()

if __name__ == '__main__':
    main()
