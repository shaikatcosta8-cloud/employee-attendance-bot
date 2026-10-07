import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import logging
from datetime import datetime, time
from collections import defaultdict

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ============================================================
# TELEGRAM BOT TOKEN
# ============================================================


TOKEN = os.environ.get("8777801514:AAGlw8BQwQqkwvmtZ0EGMCy-kDyCdlOmkGY")

# ============================================================
# SETTINGS
# ============================================================

WORK_START_HOUR = 10
WORK_START_MINUTE = 30

WORK_END_HOUR = 23
WORK_END_MINUTE = 0

SMOKING_LIMIT = 8 * 60       # 8 minutes
EATING_LIMIT = 45 * 60       # 45 minutes
TOILET_LIMIT = 10 * 60       # 10 minutes


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)


# ============================================================
# EMPLOYEE DATA
# ============================================================

employees = {}

# Structure:
#
# employees[user_id] = {
#     "name": "",
#     "status": "OFF",
#     "activity": None,
#     "activity_start": None,
#     "work_start": None,
#     "off_work": None,
#     "warnings": [],
#     "activities": {
#         "SMOKING": [],
#         "EATING": [],
#         "TOILET": [],
#         "MEETING": []
#     }
# }


# ============================================================
# BUTTONS
# ============================================================

keyboard = [
    ["🟢 START WORK"],
    ["🚬 SMOKING", "🍽️ EATING"],
    ["🚻 TOILET", "🤝 MEETING"],
    ["🪑 BACK TO SEAT"],
    ["🔴 OFF WORK"],
]

reply_keyboard = ReplyKeyboardMarkup(
    keyboard,
    resize_keyboard=True
)


# ============================================================
# TIME FUNCTIONS
# ============================================================

def now():
    return datetime.now()


def format_time(dt):
    if not dt:
        return "-"

    return dt.strftime("%I:%M:%S %p")


def format_duration(seconds):
    seconds = int(seconds)

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"

    if minutes > 0:
        return f"{minutes}m {secs}s"

    return f"{secs}s"


def today_work_start():
    n = now()

    return n.replace(
        hour=WORK_START_HOUR,
        minute=WORK_START_MINUTE,
        second=0,
        microsecond=0
    )


# ============================================================
# EMPLOYEE CREATION
# ============================================================

def get_employee(user):
    user_id = user.id

    if user_id not in employees:

        employees[user_id] = {
            "name": user.full_name,
            "status": "OFF",
            "activity": None,
            "activity_start": None,
            "work_start": None,
            "off_work": None,
            "warnings": [],
            "activities": {
                "SMOKING": [],
                "EATING": [],
                "TOILET": [],
                "MEETING": []
            }
        }

    else:
        employees[user_id]["name"] = user.full_name

    return employees[user_id]


# ============================================================
# START COMMAND
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    get_employee(user)

    await update.message.reply_text(
        "👋 Welcome to Employee Work Attendance Bot\n\n"
        "আপনার কাজের status নির্বাচন করুন:",
        reply_markup=reply_keyboard
    )


# ============================================================
# START WORK
# ============================================================

async def start_work(update: Update):

    user = update.effective_user

    employee = get_employee(user)

    if employee["status"] == "WORKING":

        await update.message.reply_text(
            "⚠️ আপনি ইতিমধ্যে WORKING অবস্থায় আছেন।"
        )

        return

    if employee["status"] in ["SMOKING", "EATING", "TOILET", "MEETING"]:

        await update.message.reply_text(
            "⚠️ আপনি বর্তমানে একটি activity-তে আছেন।\n"
            "আগে 🪑 BACK TO SEAT চাপুন।"
        )

        return

    current = now()

    employee["work_start"] = current
    employee["status"] = "WORKING"
    employee["activity"] = None
    employee["activity_start"] = None

    expected = today_work_start()

    late_seconds = (current - expected).total_seconds()

    if late_seconds > 0:

        late_text = format_duration(late_seconds)

        employee["warnings"].append(
            f"Late Start: {late_text}"
        )

        message = (
            "🚨 **LATE START WARNING**\n\n"
            f"👤 Employee: {employee['name']}\n"
            f"🕐 Expected Start: {format_time(expected)}\n"
            f"🕐 Actual Start: {format_time(current)}\n"
            f"⏱️ Late: {late_text}"
        )

    else:

        message = (
            "🟢 **START WORK**\n\n"
            f"👤 Employee: {employee['name']}\n"
            f"🕐 Start Time: {format_time(current)}\n"
            "✅ On Time"
        )

    await update.message.reply_text(message)


# ============================================================
# START ACTIVITY
# ============================================================

async def start_activity(update: Update, activity):

    user = update.effective_user

    employee = get_employee(user)

    if employee["status"] == "OFF":

        await update.message.reply_text(
            "⚠️ আগে 🟢 START WORK চাপুন।"
        )

        return

    if employee["status"] == activity:

        await update.message.reply_text(
            f"⚠️ আপনি ইতিমধ্যে {activity} অবস্থায় আছেন।"
        )

        return

    if employee["status"] in ["SMOKING", "EATING", "TOILET", "MEETING"]:

        await update.message.reply_text(
            "⚠️ আপনি বর্তমানে "
            f"{employee['status']} অবস্থায় আছেন।\n\n"
            "আগে 🪑 BACK TO SEAT চাপুন।"
        )

        return

    if employee["status"] != "WORKING":

        await update.message.reply_text(
            "⚠️ এই activity শুরু করা যাচ্ছে না।"
        )

        return

    current = now()

    employee["status"] = activity
    employee["activity"] = activity
    employee["activity_start"] = current

    icons = {
        "SMOKING": "🚬",
        "EATING": "🍽️",
        "TOILET": "🚻",
        "MEETING": "🤝"
    }

    names = {
        "SMOKING": "Smoking",
        "EATING": "Eating",
        "TOILET": "Toilet",
        "MEETING": "Meeting"
    }

    icon = icons[activity]
    name = names[activity]

    await update.message.reply_text(
        f"{icon} **{name} STARTED**\n\n"
        f"👤 Employee: {employee['name']}\n"
        f"🕐 Start Time: {format_time(current)}"
    )


# ============================================================
# BACK TO SEAT
# ============================================================

async def back_to_seat(update: Update):

    user = update.effective_user

    employee = get_employee(user)

    current = now()

    if employee["status"] == "OFF":

        await update.message.reply_text(
            "⚠️ আপনি বর্তমানে OFF WORK অবস্থায় আছেন।"
        )

        return

    if employee["status"] == "WORKING":

        await update.message.reply_text(
            "🪑 আপনি already WORKING অবস্থায় আছেন।"
        )

        return

    activity = employee["activity"]

    start_time = employee["activity_start"]

    if not activity or not start_time:

        employee["status"] = "WORKING"

        await update.message.reply_text(
            "🪑 **BACK TO SEAT**\n\n"
            f"👤 Employee: {employee['name']}\n"
            "Status: WORKING"
        )

        return

    duration = (current - start_time).total_seconds()

    employee["activities"][activity].append({
        "start": start_time,
        "end": current,
        "duration": duration
    })

    # Limits
    limit = None

    if activity == "SMOKING":
        limit = SMOKING_LIMIT

    elif activity == "EATING":
        limit = EATING_LIMIT

    elif activity == "TOILET":
        limit = TOILET_LIMIT

    exceeded = False

    if limit is not None and duration > limit:

        exceeded = True

        extra = duration - limit

        warning = (
            f"{activity}: exceeded by "
            f"{format_duration(extra)}"
        )

        employee["warnings"].append(warning)

    employee["status"] = "WORKING"
    employee["activity"] = None
    employee["activity_start"] = None

    icons = {
        "SMOKING": "🚬",
        "EATING": "🍽️",
        "TOILET": "🚻",
        "MEETING": "🤝"
    }

    names = {
        "SMOKING": "Smoking",
        "EATING": "Eating",
        "TOILET": "Toilet",
        "MEETING": "Meeting"
    }

    icon = icons[activity]
    name = names[activity]

    if exceeded:

        limit_text = {
            "SMOKING": "8 minutes",
            "EATING": "45 minutes",
            "TOILET": "10 minutes"
        }.get(activity, "No limit")

        extra = duration - limit

        message = (
            "🚨 **TIME LIMIT WARNING**\n\n"
            f"👤 Employee: {employee['name']}\n"
            f"{icon} Activity: {name}\n"
            f"🕐 Started: {format_time(start_time)}\n"
            f"🕐 Back to Seat: {format_time(current)}\n"
            f"⏱️ Duration: {format_duration(duration)}\n"
            f"⚠️ Allowed: {limit_text}\n"
            f"❌ Exceeded By: {format_duration(extra)}"
        )

    else:

        message = (
            "🪑 **BACK TO SEAT**\n\n"
            f"👤 Employee: {employee['name']}\n"
            f"{icon} Activity: {name}\n"
            f"🕐 Started: {format_time(start_time)}\n"
            f"🕐 Back to Seat: {format_time(current)}\n"
            f"⏱️ Duration: {format_duration(duration)}\n"
            "✅ Within Limit"
        )

    await update.message.reply_text(message)


# ============================================================
# OFF WORK
# ============================================================

async def off_work(update: Update):

    user = update.effective_user

    employee = get_employee(user)

    current = now()

    if employee["status"] == "OFF":

        await update.message.reply_text(
            "⚠️ আপনি ইতিমধ্যে OFF WORK অবস্থায় আছেন।"
        )

        return

    if employee["status"] in ["SMOKING", "EATING", "TOILET", "MEETING"]:

        await update.message.reply_text(
            "⚠️ আপনি এখন "
            f"{employee['status']} অবস্থায় আছেন।\n\n"
            "আগে 🪑 BACK TO SEAT চাপুন, "
            "তারপর OFF WORK করুন।"
        )

        return

    employee["off_work"] = current

    work_start = employee["work_start"]

    work_duration = 0

    if work_start:
        work_duration = (
            current - work_start
        ).total_seconds()

    smoking = employee["activities"]["SMOKING"]
    eating = employee["activities"]["EATING"]
    toilet = employee["activities"]["TOILET"]
    meeting = employee["activities"]["MEETING"]

    smoking_total = sum(
        x["duration"] for x in smoking
    )

    eating_total = sum(
        x["duration"] for x in eating
    )

    toilet_total = sum(
        x["duration"] for x in toilet
    )

    meeting_total = sum(
        x["duration"] for x in meeting
    )

    warning_count = len(employee["warnings"])

    warning_text = "\n".join(
        f"• {w}" for w in employee["warnings"]
    )

    if not warning_text:
        warning_text = "None"

    message = (
        "🔴 **OFF WORK - DAILY REPORT**\n\n"

        f"👤 Employee: {employee['name']}\n\n"

        f"🟢 Start Work: {format_time(work_start)}\n"
        f"🔴 Off Work: {format_time(current)}\n"
        f"⏱️ Work Period: {format_duration(work_duration)}\n\n"

        "📊 **ACTIVITY SUMMARY**\n\n"

        f"🚬 Smoking: {len(smoking)} times\n"
        f"   Total: {format_duration(smoking_total)}\n\n"

        f"🍽️ Eating: {len(eating)} times\n"
        f"   Total: {format_duration(eating_total)}\n\n"

        f"🚻 Toilet: {len(toilet)} times\n"
        f"   Total: {format_duration(toilet_total)}\n\n"

        f"🤝 Meeting: {len(meeting)} times\n"
        f"   Total: {format_duration(meeting_total)}\n\n"

        f"⚠️ Total Warnings: {warning_count}\n"
        f"{warning_text}"
    )

    employee["status"] = "OFF"
    employee["activity"] = None
    employee["activity_start"] = None

    await update.message.reply_text(message)


# ============================================================
# REPORT COMMAND
# ============================================================

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not employees:

        await update.message.reply_text(
            "আজ এখনো কোনো employee record নেই।"
        )

        return

    message = "📊 **TODAY'S EMPLOYEE STATUS**\n\n"

    for employee in employees.values():

        status = employee["status"]

        icons = {
            "WORKING": "🟢",
            "SMOKING": "🚬",
            "EATING": "🍽️",
            "TOILET": "🚻",
            "MEETING": "🤝",
            "OFF": "🔴"
        }

        icon = icons.get(status, "⚪")

        message += (
            f"{icon} **{employee['name']}**\n"
            f"Status: {status}\n"
        )

        if employee["activity_start"]:

            duration = (
                now() - employee["activity_start"]
            ).total_seconds()

            message += (
                f"Current Duration: "
                f"{format_duration(duration)}\n"
            )

        message += "\n"

    await update.message.reply_text(message)


# ============================================================
# WARNINGS COMMAND
# ============================================================

async def warnings(update: Update, context: ContextTypes.DEFAULT_TYPE):

    message = "⚠️ **TODAY'S WARNINGS**\n\n"

    found = False

    for employee in employees.values():

        if employee["warnings"]:

            found = True

            message += (
                f"👤 **{employee['name']}**\n"
            )

            for warning in employee["warnings"]:

                message += (
                    f"• {warning}\n"
                )

            message += "\n"

    if not found:

        message += "✅ আজ কোনো warning নেই।"

    await update.message.reply_text(message)


# ============================================================
# MESSAGE HANDLER
# ============================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    if text == "🟢 START WORK":

        await start_work(update)

    elif text == "🚬 SMOKING":

        await start_activity(
            update,
            "SMOKING"
        )

    elif text == "🍽️ EATING":

        await start_activity(
            update,
            "EATING"
        )

    elif text == "🚻 TOILET":

        await start_activity(
            update,
            "TOILET"
        )

    elif text == "🤝 MEETING":

        await start_activity(
            update,
            "MEETING"
        )

    elif text == "🪑 BACK TO SEAT":

        await back_to_seat(update)

    elif text == "🔴 OFF WORK":

        await off_work(update)

    else:

        await update.message.reply_text(
            "⚠️ অনুগ্রহ করে নিচের button ব্যবহার করুন।",
            reply_markup=reply_keyboard
        )

# ============================================================
# MAIN
# ============================================================

# ============================================================
# RENDER HEALTH SERVER
# ============================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Employee Attendance Bot is running!")

    def log_message(self, format, *args):
        pass


def start_health_server():

    port = int(os.getenv("PORT", "10000"))

    server = HTTPServer(
        ("0.0.0.0", port),
        HealthHandler
    )

    server.serve_forever()


def main():

    print("=" * 45)
    print("Employee Attendance Telegram Bot")
    print("Bot is running...")
    print("=" * 45)

    application = (
        Application.builder()
        .token(TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("report", report)
    )

    application.add_handler(
        CommandHandler("warnings", warnings)
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    application.run_polling()


if __name__ == "__main__":
    main()
