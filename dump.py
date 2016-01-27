#!/usr/bin/env python3

import argparse, sys
import sqlite3, time, json
from datetime import datetime
from pytg.exceptions import *
from pytg.sender import Sender
from pytg.receiver import Receiver



if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--name', action="store", default="", help="Will be used as database name")
    parser.add_argument('--id', action="store", default="", help="Channel ID")
    parser.add_argument('--step', action="store", default=100, help="Channel ID")
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

    # Check ID
    if len(args.id) != 32:
        print("Invalid dialog ID!", args.id)
        sys.exit(1)
    else:
        args.id = "$" + args.id


    # Open the database
    conn = sqlite3.connect('%s.db' % args.name)
    c = conn.cursor()

    # Init database
    if args.initdb:
        print("Creating tables..")
        c.execute('''CREATE TABLE messages (id INTEGER, timestamp INTEGER, json TEXT, event CHAR(16))''')
        c.execute('''CREATE UNIQUE INDEX messages_id ON messages (id);''')


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
            res = sender.history(args.id, args.step, offset)
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
