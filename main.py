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
    await update.message.reply_text("This bot can be used to travel around Switzerland with public transport.\n• type \"/travel <departure> <destination>\" to use it\n• type /about to acess some documentation\nLet's do it !")

# define about command
async def about_command(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Version : 1.0\nSource : https://transport.opendata.ch/")

# define help command
async def help_command(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('You can use \"/start\" to begin.')

# define unknown command
async def unknown_command(update: Update, context: CallbackContext) -> None:
    chat = update.effective_chat
    if chat:
        await context.bot.send_message(chat_id = chat.id, text = "Try \"/travel <departure> <destination>\" !")

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

    # title
    message = f"<b>Options to travel between {from_input} and {to_input}</b>\n\n"

    # options
    nbOption = 0
    for connection in json_resp['connections']:

        # subtitle
        nbOption += 1
        message += f"<u>Option {nbOption}</u>\n"

        # departure
        departure_time = datetime.strptime(connection.get('from').get('departure'), '%Y-%m-%dT%H:%M:%S%z')
        departure_time_casted = departure_time.strftime("%X")
        now = datetime.now(departure_time.tzinfo)
        time_diff = round((departure_time - now).total_seconds() / 60)
        message += f"Departure in about {time_diff} minutes ({departure_time_casted})\n"

        # duration
        duration = "Duration"
        duration_time = connection.get('duration')
        message += await addToMessage(duration, duration_time)

        # step
        transport = "With"
        step = "\n"
        for section in connection.get('sections', []):
            journey = section.get('journey')
            if journey:

                # construction category + number
                category = journey['category']
                number = journey['number']
                step += f"  • {category}{number} :\n"

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
                step += f"  • walk :\n"
                time = "time"
                time_elasped = section.get('walk').get('duration')
                time_elasped_content = f"{time_elasped} meters"
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
    await update.message.reply_text(message, parse_mode='HTML')

# define travel from home to epfl command
async def to_epfl_command(update: Update, context: CallbackContext):
    from_input = "Bottens, croisée"
    to_input = "Ecublens VD, EPFL"
    message = await api_call(from_input, to_input)
    await update.message.reply_text(message, parse_mode='HTML')

# define travel from epfl to home command
async def from_epfl_command(update: Update, context: CallbackContext):
    from_input = "Ecublens VD, EPFL"
    to_input = "Bottens, croisée"
    message = await api_call(from_input, to_input)
    await update.message.reply_text(message, parse_mode='HTML')

# define travel from home to heig command
async def to_heig_command(update: Update, context: CallbackContext):
    from_input = "Bottens, croisée"
    to_input = "Yverdon-les-Bains, HEIG-VD"
    message = await api_call(from_input, to_input)
    await update.message.reply_text(message, parse_mode='HTML')

# define travel from heig to home command
async def from_heig_command(update: Update, context: CallbackContext):
    from_input = "Yverdon-les-Bains, HEIG-VD"
    to_input = "Bottens, croisée"
    message = await api_call(from_input, to_input)
    await update.message.reply_text(message, parse_mode='HTML')

def main():
    token = BOT_TOKEN
    app = ApplicationBuilder().token(token).concurrent_updates(True).read_timeout(30).write_timeout(30).build()

    # commands handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("about",about_command))

    app.add_handler(CommandHandler("travel", travel_command))
    app.add_handler(CommandHandler("bottens_epfl", to_epfl_command))
    app.add_handler(CommandHandler("epfl_bottens", from_epfl_command))
    app.add_handler(CommandHandler("bottens_heig", to_heig_command))
    app.add_handler(CommandHandler("heig_bottens", from_heig_command))

    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    app.add_handler(MessageHandler(filters.TEXT, unknown_command))
    
    print("Telegram Bot started !", flush=True)

    app.run_polling()

if __name__ == '__main__':
    main()
