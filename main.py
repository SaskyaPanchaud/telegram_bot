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

# define message construction
async def addToMessage(title, content):
    return f"\n{title} : {content}\n"

# define step construction
async def addToStep(title, content):
    return f"      {title} : {content}\n"

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
    message = ""

    # departure
    departure = "Departure"
    departure_time = datetime.strptime(json_resp['connections'][0].get('from').get('departure'), '%Y-%m-%dT%H:%M:%S%z').strftime("%X")
    message += await addToMessage(departure, departure_time)

    # duration
    duration = "Duration"
    duration_time = json_resp['connections'][0].get('duration')
    message += await addToMessage(duration, duration_time)

    # step
    transport = "With"
    step = "\n"
    for section in json_resp['connections'][0].get('sections', []):
        journey = section.get('journey')
        if journey:

            # construction category + number
            category = journey['category']
            number = journey['number']
            step += f"  - {category}{number} :\n"

            # construction from
            from_title = "from"
            from_name = section.get('departure')['station'].get('name')
            from_time = datetime.strptime(section.get('departure').get('departure'), '%Y-%m-%dT%H:%M:%S%z').strftime("%X")
            from_platform = section.get('departure').get('platform')
            from_platform_content = f" / {from_platform}" if from_platform else ""
            from_content = f"{from_name}{from_platform_content} - {from_time}"
            step += await addToStep(from_title, from_content)
            
            # construction to
            to_title = "to"
            to_name = section.get('arrival')['station'].get('name')
            to_time = datetime.strptime(section.get('arrival').get('arrival'), '%Y-%m-%dT%H:%M:%S%z').strftime("%X")
            to_platform = section.get('arrival').get('platform')
            to_platform_content = f" / {to_platform}" if to_platform else ""
            to_content = f"{to_name}{to_platform_content} - {to_time}"
            step += await addToStep(to_title, to_content)

            # construction time
            time = "time"
            time_elasped = datetime.fromtimestamp(section.get('arrival').get('arrivalTimestamp') - section.get('departure').get('departureTimestamp'), tz=timezone.utc).strftime("%X")
            step += await addToStep(time, time_elasped)
        else:
            # construction walk
            step += f"  - walk :\n"
            time = "time"
            time_elasped = section.get('walk').get('duration') / 60
            time_elasped_content = f"{time_elasped} minutes"
            step += await addToStep(time, time_elasped_content)

    message += await addToMessage(transport, step)

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
