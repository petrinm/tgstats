#!/usr/bin/env python3

import argparse
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import sqlite3, json, datetime
import time, math, os, re


def chat_renames():
    """
        Returns list of topics
    """

    print("Getting topics...")

    renames = []
    for sid, timestamp, service  in c.execute("""SELECT id, timestamp, json FROM messages WHERE event="service" ORDER BY timestamp;"""):
        service = json.loads(service)
        if service["action"]["type"] == "chat_rename":
            renames.append((
                datetime.datetime.fromtimestamp(timestamp),
                service["action"]["title"],
                service["from"]["print_name"].replace("_", " ")
            ))

    return sorted(renames, key=lambda x: x[0], reverse=True)


def talker_stats(span=None, max_talkers=10):
    """"
        Return list of top talkers in decending order
    """

    print("Getting top talkers...")
    i = 0
    talkers = {}

    before = int(time.time() - span*24*60*60) if span else 0

    for sid, timestamp, message  in c.execute("""SELECT id, timestamp, json FROM messages WHERE event="message" AND timestamp >= ?;""", (before, )):
        message = json.loads(message)
        name = message["from"]["print_name"]

        if name not in talkers:
            talkers[name] = [0, 0, 0, 0]

        if "text" in message:
            talkers[name][0] += 1
            talkers[name][1] += len(re.findall('[a-zäöå]{2,}', message["text"], flags=re.IGNORECASE))

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


def bot_spammers(max_talkers=10):

    print("Getting top bot spammers...")
    cmds = {}
    bots = {}

    for sid, timestamp, message  in c.execute("""SELECT id, timestamp, json FROM messages WHERE event="message";"""):
        message = json.loads(message)
        name = message["from"]["print_name"]

        if "text" in message and message["text"].startswith("/"):

            cmd = message["text"].strip().split(" ")[0].split("@")[0]

            #print(cmd, "\t", message["text"])

            if cmd in cmds:
                if name in cmds[cmd]:
                    cmds[cmd][name] += 1
                else:
                    cmds[cmd][name] = 1
            else:
                cmds[cmd] = { name: 1 }

        elif name.lower()[-3:]== "bot":
            # Increase bot's popularity
            if name in bots:
                bots[name] += 1
            else:
                bots[name] = 1


    # Filter Top-6 commands
    cmds = sorted(cmds.items(), key=lambda x: sum(x[1].values()), reverse=True)[:6]

    # Filter Top-6 users for each command
    cmds = [(c[0], sorted(c[1].items(), key=lambda x: x[1], reverse=True)[:6]) for c in cmds]

    # Filter Top-5 Bots
    bots = sorted(bots.items(), key=lambda x: x[1], reverse=True)[:5]

    return cmds, bots


def most_commonly_used_words():
    """"
        Return list of most commonly used words
    """

    print("Getting most commonly used words...")

    words = {}
    users = {}
    for sid, timestamp, message  in c.execute("""SELECT id, timestamp, json FROM messages WHERE event="message";"""):
        message = json.loads(message)

        if "text" not in message:
            continue

        for mword in re.findall('[a-zäöå]{2,}', message["text"], flags=re.IGNORECASE):
            mword = mword.lower()
            if mword not in words:
                words[mword] = 1
            else:
                words[mword] += 1

            if mword[0] == "@":
                if mword not in users:
                    users[mword] = 1
                else:
                    users[mword] += 1

    #print(sorted(users.items(), key=lambda x: x[1], reverse=True)[:10])
    return sorted(words.items(), key=lambda x: x[1], reverse=True)


def population_graph(filepath="aski_population.png", show=False):

    print("Creating population graph...")

    population = {}
    total = 0

    prev_date = None

    for sid, timestamp, service  in c.execute("""SELECT id, timestamp, json FROM messages WHERE event="service" ORDER BY timestamp;"""):
        service = json.loads(service)

        action_type = service["action"]["type"]

        if action_type not in ["chat_add_user", "chat_add_user_link", "chat_del_user"]:
            continue

        timestamp = datetime.datetime.fromtimestamp(timestamp)
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

    # TODO: Add today to the list if doesn't exist
    #if population[-1] != today:
    #    population[today] = [total, 0, 0]

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


def hourly_rate(timespan=3600):
    """
        Calculate most messages inside the timespan
    """

    print("Calculating message rates...")

    buff = []
    top_date, top_rate = (0, 0), 0

    for sid, timestamp, message  in c.execute("""SELECT id, timestamp, json FROM messages WHERE event="message" ORDER BY timestamp;"""):
        message = json.loads(message)

        # Append new message to the buffer
        if "text" in message:
            buff.append(timestamp)

        # Filter old messages
        buff = [x for x in buff if x + timespan > timestamp]

        if len(buff) > top_rate:
            top_rate = len(buff)
            top_date = (buff[0], buff[-1])
            #print(top_date, top_rate, message["text"])

    return top_rate, datetime.datetime.fromtimestamp(top_date[0]), \
           datetime.datetime.fromtimestamp(top_date[1])


def messages_graph(filepath="messages.png", show=True):

    print("Creating messages graphs...")

    messages = {}
    prev_date = None


    for sid, timestamp, message  in c.execute("""SELECT id, timestamp, json FROM messages WHERE event="message" ORDER BY timestamp;"""):
        message = json.loads(message)

        timestamp = datetime.datetime.fromtimestamp(timestamp)
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



def popular_emojis():

    print("Searching emojis...")

    highpoints = re.compile(u'['
        u'\U0001F300-\U0001F5FF'
        u'\U0001F600-\U0001F64F'
        u'\U0001F680-\U0001F6FF'
        u'\u2600-\u26FF\u2700-\u27BF]',
        re.UNICODE)

    emojis = {}

    for mid, message in c.execute("""SELECT id, json FROM messages WHERE event="message";"""):
        message = json.loads(message)

        if "text" not in message:
            continue

        #if len(r) > 0:
        #print(r, hex(ord(r[0])))
        for ec in map(ord, highpoints.findall(message["text"])):
            emojis[ec] = emojis.get(ec, 0) + 1

    return sorted(emojis.items(), key=lambda x: x[1], reverse=True)[:20]



def activity_graph(filepath="activity.png", show=True):

    print("Creating activity graph...")

    messages = 24 * [0]
    for sid, timestamp, message  in c.execute("""SELECT id, timestamp, json FROM messages WHERE event="message" ORDER BY id;"""):
        message = json.loads(message)

        timestamp = datetime.datetime.fromtimestamp(timestamp)
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
    parser.add_argument('--no-words', action='store_true', help="Disable most commonly used words list")
    parser.add_argument('--no-bots', action='store_true', help="Disable most commonly used bots/commands list")
    parser.add_argument('--no-emojis', action='store_true', help="Disable most commonly used emojis list")
    args = parser.parse_args()

    if len(args.name) < 3:
        print("Invalid name!")

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
    <title>%s Telegram Statistics</title>
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap.min.css" crossorigin="anonymous">
    <script src="https://code.jquery.com/jquery-2.2.4.min.js" crossorigin="anonymous"></script>
    <script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/js/bootstrap.min.js" crossorigin="anonymous"></script>

    </head><body>
    <div class="container">
    """ % args.name)

    out.write("<h1>%s Telegram Statistics</h1>" % args.name)

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

        top_rate, top_start, top_end = hourly_rate()
        messages = 0
        stickers = 0
        photos = 0
        for talker, stats in talkers:
            messages += stats[0]
            stickers += stats[2]
            photos += stats[3]

        out.write("<tr><td>Messages</td><td>%d</td></tr>\n" % messages)
        out.write("<tr><td>Top speed</td><td>%d messages/hour (%s-%s)</td></tr>\n" % (top_rate, top_start.strftime("%d. %B %Y %I:%M"), top_end.strftime("%I:%M")))
        out.write("<tr><td>Stickers</td><td>%d (%.1f%% of messages)</td></tr>\n" % (stickers, (100.0 * stickers) / messages))
        out.write("<tr><td>Media</td><td>%d (%.1f%% of messages)</td></tr>\n" % (photos, (100.0 * photos) / messages))
        #out.write("<tr><td>Videos</td><td>TODO</td></tr>\n")
        #out.write("<tr><td>Audio</td><td>TODO</td></tr>\n")
        out.write("</table>\n")


    if not args.no_talkers:

        out.write("<h2>Top 15 Talkers</h2>\n")

        out.write("<ul class=\"nav nav-tabs\">" \
                  "<li class=\"active\"><a data-toggle=\"tab\" href=\"#all\">All-time</a></li>"\
                  "<li><a data-toggle=\"tab\" href=\"#week\">Last week</a></li>" \
                  "<li><a data-toggle=\"tab\" href=\"#month\">Last month</a></li>"\
                  "<li><a data-toggle=\"tab\" href=\"#year\">Last year</a></li></ul>" \
                  "<div class=\"tab-content\">\n")

        timeranges = [
            ("all", "active", 3600),
            ("week", "", 7),
            ("month", "", 31),
            ("year", "", 365)
        ]


        for trange, active, span in timeranges:

            talks = talkers if trange == "all" else talker_stats(span)
            top_talkers = sorted(talks, key=lambda x: x[1][0], reverse=True)[:15]

            out.write("<div id=\"%s\" class=\"tab-pane %s\"><table class='table tabler-striped'>\n" % (trange, active))
            out.write("\t<tr><th>#</th><th>Talker</th><th>Messages</th><th>Words</th><th>WPM</th><th>Stickers</th><th>Media</th></tr>\n")
            pos = 1
            for talker, (messages, words, stickers, photos) in top_talkers:
                out.write("\t<tr><td>%d</td><td>%s</td><td>%d</td><td>%d</td><td>%.1f</td><td>%d</td><td>%d</td></tr>\n" % \
                    (pos, talker.replace("_", " "), messages, words, words / messages, stickers, photos))
                pos += 1
            out.write("</table></div>\n")

    if not args.no_bots:

        cmds, bots = bot_spammers()

        out.write("<h2>Bot spammers</h2>\n<b>Most used bots:</b> ")
        for bot, count in bots:
            out.write("%s (%d), " % (bot, count))

        out.write("\n<table class='table'><tr>\n")

        for cmd, users in cmds:
            out.write("<td><b>%s</b><br/>" % cmd)
            for user, count in users:
                out.write("%s (%d), <br/>" % (user.replace("_", " "), count))
            out.write("</td>\n")

        out.write("</tr></table>\n")


    if not args.no_emojis:
        out.write("<h2>Most popular emojis</h2>\n")

        for emoji, count in popular_emojis():
            out.write("<img width=\"32px\" src=\"http://emojione.com/wp-content/uploads/assets/emojis/%x.svg\" title=\"%d uses\"/>" % (emoji, count))


    if not args.no_words:

        out.write("<h2>100 most commonly used words</h2>\n<p>\n")
        out.write(", ".join([ "%s (%d)" % c for c in most_commonly_used_words()[:100]]))
        out.write("</p>\n")


    if not args.no_topics:
        out.write("<h2>Latest topics</h2>\n<table class='table tabler-striped'>\n")
        for timestamp, title, changer in chat_renames()[:10]:
            out.write("\t<tr><td>%s</td><td>Changed by %s (%s)</td></tr>\n" % (title, changer, timestamp.strftime("%d. %B %Y %I:%M")))
            # TODO: Add deltatime
        out.write("</table>\n")


    out.write("<p>Generated %s with <a href='https://github.com/petrinm/tgstats'>tgstats</a></p>\n" % datetime.datetime.now().strftime("%d. %B %Y %H:%M"))
    out.write("\n</div>\n</body></html>")
