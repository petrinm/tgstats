

Telegram Channel Statistic Generator
===

Simple Python script to dump Telegram logs and generate html/png statistics.

Dependencies
---
* Python3
* Telegram-cli https://github.com/vysheng/tg/
* Matplotlib http://matplotlib.org/
* pytg https://github.com/luckydonald/pytg/



Getting started
---

0) Dependencies libevent-dev, libssl-dev... (TODO)

1) Download and compile telegram-cli. Use the test branch!
```
git clone --recursive -b test https://github.com/vysheng/tg.git tg-test && cd tg-test
./configure --disable-liblua
make
```

1½) Install python stuff
```
pip3 install pytg
```

2) Start the client with JSON support (Do the registration!)
```
./bin/telegram-cli --json -P 4458
```

3) Dump dialogs to find correct id for the channel. Copy the id!
```
$ ./dump.py --dialogs
```

4) Start dumping messages.

If the dump script is terminated it stores it's current offset to "name_offset"
file and the script tries always to continue from the last position.
Remove the offset file when you need to start from the beginning or use

Note: When executed the first time initdb is required.

```
$ ./dump.py test --initdb --id <your id>
```

5) To update or continue dumping without reseting request index
```
$ ./dump.py test [--continue]
```

6) Generate stats
```
$ ./generate.py test
```

7) View stats at "test" folder
