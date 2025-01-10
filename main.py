import requests
import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext,
    CallbackQueryHandler,
)
from datetime import datetime, timezone

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("bot.log")]
)
logger = logging.getLogger(__name__)


def log_user_activity(update: Update):
    user = update.effective_user
    chat = update.effective_chat
    message = update.message.text if update.message else None
    callback_data = update.callback_query.data if update.callback_query else None
    if message:
        logger.info(f"Message from user {user.id} in chat {chat.id}: {message}")
    elif callback_data:
        logger.info(f"Callback from user {user.id} in chat {chat.id}: {callback_data}")


async def start_command(update: Update, _: CallbackContext):
    log_user_activity(update)
    await update.message.reply_text(
        'This bot can be used to travel around Switzerland with public transport.\n• type "/travel <departure> <destination>" to use it\n• type /about to acess some documentation\nLet\'s do it !'
    )


async def about_command(update: Update, _: CallbackContext):
    log_user_activity(update)
    await update.message.reply_text(
        "Version : 2.0\nData source : https://transport.opendata.ch/\nCode source : https://github.com/SaskyaPanchaud/telegram_bot\n"
    )


async def help_command(update: Update, _: CallbackContext):
    log_user_activity(update)
    await update.message.reply_text('You can use "/start" to begin.')


async def unknown_command(update: Update, context: CallbackContext):
    log_user_activity(update)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Try "/travel <departure> <destination>" !',
    )


async def addToMessage(title, content):
    return f"\n{title} : {content}\n"


async def addToStep(title, content):
    return f"      {title} : {content}\n"


async def api_call_general(from_input, to_input):
    # contact with api
    query = (
        f"https://transport.opendata.ch/v1/connections?from={from_input}&to={to_input}"
    )
    response = requests.get(query)
    json_resp = response.json()

    # check valid travel
    if len(json_resp["connections"]) == 0:
        return "INVALID TRAVEL"

    # message construction
    message = f"<b>Options to travel between {from_input} and {to_input}</b>\n\n"
    for nbOp, connection in enumerate(json_resp["connections"], start=1):

        # subtitle
        message += f"<u>Option {nbOp}</u>\n\n"
        # departure
        departure_time = datetime.strptime(
            connection.get("from").get("departure"), "%Y-%m-%dT%H:%M:%S%z"
        )
        departure_time_casted = departure_time.strftime("%X")
        now = datetime.now(departure_time.tzinfo)
        time_diff = round((departure_time - now).total_seconds() / 60)
        hour = 0 if time_diff < 60 else (int) (time_diff / 60)
        hour_plural = "s" if hour > 1 else ""
        minute = time_diff % 60
        minute_plural = "s" if minute > 1 else ""
        time_print = f"{hour} hour{hour_plural} and " if hour != 0 else ""
        time_print += f"{minute} minute{minute_plural}"
        message += (
            f"Departure in about {time_print} ({departure_time_casted})\n"
        )
        # duration
        duration_time = connection.get("duration")
        if duration_time.startswith("00d"):
            duration_time = duration_time[3:]
            if duration_time.startswith("00:"):
                duration_time = duration_time[3:]
        message += await addToMessage("Duration", duration_time)
        # step
        transport = "With"
        step = "\n"
        for section in connection.get("sections", []):
            journey = section.get("journey")
            if journey:
                # construction category + number
                category = journey["category"]
                number = journey["number"]
                step += f"  • {category}{number} :\n"
                # construction from
                from_name = section.get("departure")["station"].get("name")
                from_time = datetime.strptime(
                    section.get("departure").get("departure"), "%Y-%m-%dT%H:%M:%S%z"
                ).strftime("%X")
                from_platform = section.get("departure").get("platform")
                from_platform_content = f" / {from_platform}" if from_platform else ""
                from_content = f"{from_name}{from_platform_content} - {from_time}"
                step += await addToStep("From", from_content)
                # construction to
                to_name = section.get("arrival")["station"].get("name")
                to_time = datetime.strptime(
                    section.get("arrival").get("arrival"), "%Y-%m-%dT%H:%M:%S%z"
                ).strftime("%X")
                to_platform = section.get("arrival").get("platform")
                to_platform_content = f" / {to_platform}" if to_platform else ""
                to_content = f"{to_name}{to_platform_content} - {to_time}"
                step += await addToStep("To", to_content)
                # construction time
                time_elasped = datetime.fromtimestamp(
                    section.get("arrival").get("arrivalTimestamp")
                    - section.get("departure").get("departureTimestamp"),
                    tz=timezone.utc,
                ).strftime("%X")
                step += await addToStep("Time", time_elasped)
            else:
                # construction walk
                step += f"  • walk :\n"
                distance = section.get("walk").get("duration")
                distance_content = f"{distance} meters"
                step += await addToStep("distance", distance_content)
        message += await addToMessage(transport, step)
    return message


async def travel_command(update: Update, context: CallbackContext):
    log_user_activity(update)
    input = " ".join(context.args).split(" ")
    # check arguments
    if len(input) != 2:
        await update.message.reply_text(
            'INVALID PARAMETERS ("/travel <departure> <destination>")'
        )
        return
    else:
        from_input = input[0]
        to_input = input[1]
    message = await api_call_general(from_input, to_input)
    await update.message.reply_text(message, parse_mode="HTML")


# define travel from home to epfl command
async def to_epfl_command(update: Update, _: CallbackContext):
    log_user_activity(update)
    from_input = "Bottens, croisée"
    to_input = "Ecublens VD, EPFL"
    message = await api_call_general(from_input, to_input)
    await update.message.reply_text(message, parse_mode="HTML")


# define travel from epfl to home command
async def from_epfl_command(update: Update, _: CallbackContext):
    log_user_activity(update)
    from_input = "Ecublens VD, EPFL"
    to_input = "Bottens, croisée"
    message = await api_call_general(from_input, to_input)
    await update.message.reply_text(message, parse_mode="HTML")


# define travel from home to heig command
async def to_heig_command(update: Update, _: CallbackContext):
    log_user_activity(update)
    from_input = "Bottens, croisée"
    to_input = "Yverdon-les-Bains, HEIG-VD"
    message = await api_call_general(from_input, to_input)
    await update.message.reply_text(message, parse_mode="HTML")


# define travel from heig to home command
async def from_heig_command(update: Update, _: CallbackContext):
    log_user_activity(update)
    from_input = "Yverdon-les-Bains, HEIG-VD"
    to_input = "Bottens, croisée"
    message = await api_call_general(from_input, to_input)
    await update.message.reply_text(message, parse_mode="HTML")


# define api call for leaving epfl
async def api_call_from_epfl(to_input):
    from_input = "Ecublens VD, EPFL"
    # contact with api
    query = (
        f"https://transport.opendata.ch/v1/connections?from={from_input}&to={to_input}"
    )
    response = requests.get(query)
    json_resp = response.json()
    # check valid travel
    if len(json_resp["connections"]) == 0:
        return "INVALID TRAVEL"
    # message construction
    message = f"M1 direction {to_input} :\n"
    for i, connection in enumerate(json_resp["connections"], start=0):
        # departure
        departure_time = datetime.strptime(
            connection.get("from").get("departure"), "%Y-%m-%dT%H:%M:%S%z"
        )
        now = datetime.now(departure_time.tzinfo)
        time_diff = round((departure_time - now).total_seconds() / 60)
        if time_diff < 0:
            continue
        if i == 0:
            message += f"Dans {time_diff}'"
        elif i == len(json_resp["connections"]) - 1:
            message += f" et {time_diff}'\n"
        else:
            message += f", {time_diff}'"
    return message


async def leave_epfl_command(update: Update, _: CallbackContext):
    log_user_activity(update)
    # define buttons
    keyboard = [
        [InlineKeyboardButton(text="Renens", callback_data="renens")],
        [InlineKeyboardButton(text="Lausanne", callback_data="lausanne")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Which direction ?", reply_markup=reply_markup)


async def button(update: Update, _: CallbackContext):
    log_user_activity(update)
    query = update.callback_query
    await query.answer()
    if query.data == "renens":
        message = await api_call_from_epfl("Renens VD")
        await query.edit_message_text(message, parse_mode="HTML")
    elif query.data == "lausanne":
        message = await api_call_from_epfl("Lausanne-Flon, Gare")
        await query.edit_message_text(message, parse_mode="HTML")


def main():
    token = BOT_TOKEN
    app = (
        ApplicationBuilder()
        .token(token)
        .concurrent_updates(True)
        .read_timeout(30)
        .write_timeout(30)
        .build()
    )

    # commands handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("about", about_command))

    app.add_handler(CommandHandler("travel", travel_command))
    app.add_handler(CommandHandler("bottens_epfl", to_epfl_command))
    app.add_handler(CommandHandler("epfl_bottens", from_epfl_command))
    app.add_handler(CommandHandler("bottens_heig", to_heig_command))
    app.add_handler(CommandHandler("heig_bottens", from_heig_command))
    app.add_handler(CommandHandler("leave_EPFL", leave_epfl_command))

    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    app.add_handler(MessageHandler(filters.TEXT, unknown_command))

    app.add_handler(CallbackQueryHandler(button))

    print("Telegram Bot started !", flush=True)

    app.run_polling()


if __name__ == "__main__":
    main()
