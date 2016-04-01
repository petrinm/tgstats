#!/usr/bin/env python3

import argparse, sys
import sqlite3, time, json
from datetime import datetime
from pytg.exceptions import *
from pytg.sender import Sender
from pytg.receiver import Receiver




if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('name', type=str, help="Will be used as database name")
    parser.add_argument('--id', action="store", default="", help="Channel ID (needed only with initdb!)")
    parser.add_argument('--step', action="store", default=100, help="Number of messages loaded per query")
    parser.add_argument('--dialogs', action='store_true', help="List all dialogs")
    parser.add_argument('--initdb', action='store_true', help="Initalise database")
    parser.add_argument('--continue', dest='continue_dump', action='store_true', help="Continue dumping after interrup")

    args = parser.parse_args()

    sender = Sender(host="localhost", port=4458)


    # Dialog listing
    if args.dialogs:
        for dialog in sender.dialog_list():
            print(dialog.id[1:], "\t", dialog.print_name)
        sys.exit(0)

    # Check name
    if len(args.name) < 2:
        print("Invalid name!")




    # Open the database
    conn = sqlite3.connect('%s.db' % args.name)
    c = conn.cursor()

    # Init database
    if args.initdb:
        print("Creating tables..")
        # ID on 48 merkkiäpitkä hexa
        c.execute('''CREATE TABLE messages (id CHAR(48), timestamp INTEGER, json TEXT, event CHAR(16))''')
        c.execute('''CREATE TABLE users (id CHAR(), full_name CHAR(32), json TEXT)''')
        c.execute('''CREATE UNIQUE INDEX messages_id ON messages (id);''')

        # Check ID
        if len(args.id) != 32:
            print("Invalid dialog ID!", args.id)
            sys.exit(1)
        else:
            channel_id = "$" + args.id

    else:

        if args.id != "":
            print("Given ID is ignored!")

        # Get the ID from the database!
        c.execute("SELECT json FROM messages LIMIT 1;")
        ret = json.loads(c.fetchone()[0])
        channel_id = ret["to"]["id"]

        print("ID:", channel_id)


    if args.continue_dump:
        try:
            with open("%s_offset" % args.name, "r") as f:
                offset = int(f.read()) or 0
        except FileNotFoundError:
            offset = 0
    else:
        offset = 0

    print("Offset:", offset)


    while True:
        try:
            res = sender.history(channel_id, args.step, offset)
            if "error" in res:
                print(res)
                break
        except (IllegalResponseException, NoResponse):
            print("Empty response")
            time.sleep(2)
            continue

        for msg in res:
            try:
                c.execute("INSERT INTO messages VALUES (?, ?, ?, ?)", (msg.id, msg.date, json.dumps(msg), msg.event))
                conn.commit()
                print("Added", msg.id)
            except sqlite3.IntegrityError:
                print("Collision", msg.id)

        offset += len(res)
        with open("%s_offset" % args.name, "w") as f:
            f.write("%d" % offset)
        print("Offset", offset)
