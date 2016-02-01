#!/usr/bin/env python3

import argparse
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import sqlite3, json, datetime
from pytz import timezone
import math, os


def chat_renames():
    """
        Returns list of topics
    """

    print("Getting topics...")

    renames = []
    for sid, timestamp, service  in c.execute("""SELECT id, timestamp, json FROM messages WHERE event="service" ORDER BY id DESC;"""):
        service = json.loads(service)
        if service["action"]["type"] == "chat_rename":
            renames.append((
                datetime.datetime.fromtimestamp(timestamp, localtz),
                service["action"]["title"],
                service["from"]["print_name"].replace("_", " ")
            ))

    return renames


def talker_stats(max_talkers=10):
    """"
        Return list of top talkers in decending order
    """

    print("Getting top talkers...")
    i = 0
    talkers = {}
    for sid, timestamp, message  in c.execute("""SELECT id, timestamp, json FROM messages WHERE event="message" ORDER BY id;"""):
        message = json.loads(message)
        name = message["from"]["print_name"]

        if name not in talkers:
            talkers[name] = [0, 0, 0, 0]

        if "text" in message:
            talkers[name][0] += 1
            talkers[name][1] += len(message["text"].split())

        elif "media" in message:
            media_type = message["media"]["type"]

            if media_type == "photo":
                talkers[name][3] += 1
            elif media_type == "document":
                talkers[name][2] += 1
            elif media_type == "geo":
                pass
            elif media_type == "contact":
                pass

    return talkers.items()

def top_tsalkers(max_talkers=10):
    """"
        Return list of top talkers in decending order
    """

    print("Getting top talkers...")

    messages = 0
    for sid, timestamp, message  in c.execute("""SELECT id, timestamp, json FROM messages WHERE event="message" ORDER BY timestamp;"""):
        message = json.loads(message)

        if name not in talkers:
            talkers[name] = 0

        talkers[name] += 1

    return messages, stickers, pictures




def population_graph(filepath="aski_population.png", show=False):

    print("Creating population graph...")

    population = {}
    total = 4 # TODO: This is random constant!

    prev_date = None

    for sid, timestamp, service  in c.execute("""SELECT id, timestamp, json FROM messages WHERE event="service" ORDER BY timestamp;"""):
        service = json.loads(service)

        action_type = service["action"]["type"]

        if action_type not in ["chat_add_user", "chat_add_user_link", "chat_del_user"]:
            continue

        timestamp = datetime.datetime.fromtimestamp(timestamp, localtz)
        date = datetime.date(timestamp.year, timestamp.month, timestamp.day)

        #  Init table for the date
        if date != prev_date:
            population[date] = [total, 0, 0]
        prev_date = date

        if action_type == "chat_add_user" or action_type == "chat_add_user_link":
            total += 1
            population[date][0] = total
            population[date][1] += 1

        elif action_type == "chat_del_user":
            total -= 1
            population[date][0] = total
            population[date][2] -= 1


    dates = []
    members = []
    income = []
    outcome = []
    for date, vals in sorted(population.items(), key=lambda x: x[0]):
        dates.append(date)
        members.append(vals[0])
        income.append(vals[1])
        outcome.append(vals[2])

    fig, ax = plt.subplots()
    fig.set_size_inches(14, 6)

    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%y'))

    ax.set_xlim(datetime.date(dates[0].year, dates[0].month, 1), datetime.date(dates[-1].year, dates[-1].month, dates[-1].day))
    ax.set_ylim(10 * math.floor(min(outcome) / 10.), 20 * math.ceil((1 + total) / 20.))

    ax.plot(dates, members)

    ax.bar(dates, income, color="green", edgecolor = "none")
    ax.bar(dates, outcome, color="red", edgecolor = "none")

    plt.xlabel('Date')
    plt.ylabel('Members')
    plt.title('Population')
    plt.grid(True)
    plt.savefig(filepath, dpi=250)
    if show:
        plt.show()



def messages_graph(filepath="messages.png", show=True):

    print("Creating messages graphs...")

    messages = {}

    prev_date = None

    for sid, timestamp, message  in c.execute("""SELECT id, timestamp, json FROM messages WHERE event="message" ORDER BY timestamp;"""):
        message = json.loads(message)


        timestamp = datetime.datetime.fromtimestamp(timestamp, localtz)
        date = datetime.date(timestamp.year, timestamp.month, timestamp.day)

        #  Init table for the date
        if date != prev_date:
            messages[date] = 0
        prev_date = date

        messages[date] += 1


    dates = []
    mgs = []
    for date, vals in sorted(messages.items(), key=lambda x: x[0]):
        dates.append(date)
        mgs.append(vals)

    fig, ax = plt.subplots()
    fig.set_size_inches(14, 6)

    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%y'))

    ax.set_xlim(datetime.date(dates[0].year, dates[0].month, 1), datetime.date(dates[-1].year, dates[-1].month, dates[-1].day))
    #ax.set_ylim(10 * math.floor(min(outcome) / 10.), 20 * math.ceil((1 + total) / 20.))

    ax.plot(dates, mgs)

    plt.xlabel('Date')
    plt.ylabel('Messages')
    plt.title('Messages per day')
    plt.grid(True)
    plt.savefig(filepath, dpi=250)
    if show:
        plt.show()



def activity_graph(filepath="activity.png", show=True):

    print("Creating activity graph...")

    messages = 24 * [0]
    for sid, timestamp, message  in c.execute("""SELECT id, timestamp, json FROM messages WHERE event="message" ORDER BY id;"""):
        message = json.loads(message)

        timestamp = datetime.datetime.fromtimestamp(timestamp, localtz)
        messages[timestamp.hour] += 1

    fig, ax = plt.subplots()
    fig.set_size_inches(14, 4)

    ax.set_xlim(0, 23)

    ax.bar(list(range(0, 24)), messages)

    plt.xlabel('Hours')
    plt.ylabel('Messages')
    plt.title('Activity')
    plt.grid(True)
    plt.savefig(filepath, dpi=250)

    if show:
        plt.show()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('name', type=str, help="Will be used as database name")
    parser.add_argument('--no-population', action='store_true', help="Disable population graph")
    parser.add_argument('--no-messages', action='store_true', help="Disable messages graph")
    parser.add_argument('--no-activity', action='store_true', help="Disable activity graph")
    parser.add_argument('--no-general', action='store_true', help="Disable general stats")
    parser.add_argument('--no-talkers', action='store_true', help="Disable top talkers")
    parser.add_argument('--no-topics', action='store_true', help="Disable topic list")
    args = parser.parse_args()

    if len(args.name) < 3:
        print("Invalid name!")


    localtz = timezone('Europe/Helsinki')

    conn = sqlite3.connect("%s.db" % args.name)
    c = conn.cursor()


    # Try to create a folder
    try:
        os.mkdir(args.name)
    except OSError:
        pass

    if not args.no_population:
        population_graph("%s/population.png" % args.name, show=False)
    if not args.no_messages:
        messages_graph("%s/messages.png" % args.name, show=False)
    if not args.no_activity:
        activity_graph("%s/activity.png" % args.name, show=False)

    out = open("%s/index.html" % args.name, "w")

    out.write("""<!DOCTYPE html><html lang="en"><head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>%s</title>
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap.min.css" crossorigin="anonymous">
    </head><body>
    <div class="container">
    """ % "ASki Telegram Statistics")

    out.write("<h1>%s</h1>" % "ASki Telegram Statistics")

    if not args.no_general or not args.no_talkers:
        talkers = talker_stats()

    if not args.no_population:
        out.write("<h2>Members</h2>\n")
        out.write("<img src='population.png' class='img-responsive' alt='Population over time'/>\n")

    if not args.no_messages:
        out.write("<h2>Messages per day</h2>\n")
        out.write("<img src='messages.png' class='img-responsive' alt='Messages per day'/>\n")

    if not args.no_activity:
        out.write("<h2>Activity</h2>\n")
        out.write("<img src='activity.png' class='img-responsive' alt=''/>\n")

    if not args.no_general:
        out.write("<h2>General numbers</h2>\n<table class='table tabler-striped'>\n")

        messages = 0
        stickers = 0
        photos = 0
        for talker, stats in talkers:
            messages += stats[0]
            stickers += stats[2]
            photos += stats[3]

        out.write("<tr><td>Messages</td><td>%d</td></tr>\n" % messages)
        out.write("<tr><td>Stickers</td><td>%d</td></tr>\n" % stickers)
        out.write("<tr><td>Media</td><td>%d</td></tr>\n" % photos)
        #out.write("<tr><td>Videos</td><td>TODO</td></tr>\n")
        #out.write("<tr><td>Audio</td><td>TODO</td></tr>\n")
        out.write("</table>\n")


    if not args.no_talkers:

        top_talkers = sorted(talkers, key=lambda x: x[1][0], reverse=True)[:15]

        out.write("<h2>Top 15 Talkers</h2>\n<table class='table tabler-striped'>\n")
        out.write("\t<tr><th>#</th><th>Talker</th><th>Messages</th><th>Words</th><th>Stickers</th><th>Media</th></tr>\n")
        pos = 1
        for talker, (messages, words, stickers, photos) in top_talkers:
            out.write("\t<tr><td>%d</td><td>%s</td><td>%d</td><td>%d</td><td>%d</td><td>%d</td></tr>\n" % (pos, talker.replace("_", " "), messages, words, stickers, photos))
            pos += 1
        out.write("</table>\n")


    if not args.no_topics:
        out.write("<h2>Latest topics</h2>\n<table class='table tabler-striped'>\n")
        for timestamp, title, changer in chat_renames()[:10]:
            out.write("\t<tr><td>%s</td><td>Changed by %s (%s)</td></tr>\n" % (title, changer, timestamp.strftime("%d. %B %Y %I:%M")))
            # TODO: Add deltatime
        out.write("</table>\n")


    out.write("<p>Generated %s with <a href='https://github.com/petrinm/tgstats'>tgstats</a></p>\n" % datetime.datetime.now(localtz).strftime("%d. %B %Y %H:%M"))
    out.write("\n</div>\n</body></html>")
