# Natalie group manager bot
Originally a simple group management bot with multiple admin features, it has evolved, becoming extremely modular and 
simple to use.

Can be found on telegram as [Natalie](https://t.me/Maver_ckBot).

For support please use [NatalieSupport](https://t.me/NatalieSupport)!

## Credits
A huge thanks to [Paul](https://github.com/PaulSonOfLars) for creating [Marie](https://github.com/PaulSonOfLars/tgbot)!
Without his work we wouldn't have started off and evolved to where we are now!

We'd also like to thank everyone involved in helping Paul create Marie!

## Starting the bot.

Once you've setup your database and your configuration (see below) is complete, simply run:

`python3 -m natalie_bot`


## Setting up the bot (Read this before trying to use!):
Please make sure to use python3.7.4, as I cannot guarantee everything will work as expected on older python versions!

Make sure to use python-telegram-bot version 12.4.2 as older version will not work anymore.

### SpamWatch Configuration

Inside the sample_config.py you will find a SPAMWATCH_TOKEN variable. If you want your chats protected by [SpamWatch](docs.spamwat.ch) request a key
from that site and add it in.

 - `SPAMWATCH_TOKEN`: Enables SpamWatch protection in your group chats.

### Python dependencies

Install the necessary python dependencies by moving to the project directory and running:

`pip3 install -r requirements.txt`.

This will install all necessary python packages.

### Database

If you wish to use a database-dependent module (eg: locks, notes, userinfo, users, filters, welcomes),
you'll need to have a database installed on your system. I use postgres, so I recommend using it for optimal compatibility.

In the case of postgres, this is how you would set up a the database on a debian/ubuntu system. Other distributions may vary.

- install postgresql:

`sudo apt-get update && sudo apt-get install postgresql`

- change to the postgres user:

`sudo su - postgres`

- create a new database user (change YOUR_USER appropriately):

`createuser -P -s -e YOUR_USER`

This will be followed by you needing to input your password.

- create a new database table:

`createdb -O YOUR_USER YOUR_DB_NAME`

Change YOUR_USER and YOUR_DB_NAME appropriately.

- finally:

`psql YOUR_DB_NAME -h YOUR_HOST YOUR_USER`

This will allow you to connect to your database via your terminal.
By default, YOUR_HOST should be 0.0.0.0:5432.

You should now be able to build your database URI. This will be:

`sqldbtype://username:pw@hostname:port/db_name`

Replace sqldbtype with whichever db youre using (eg postgres, mysql, sqllite, etc)
repeat for your username, password, hostname (localhost?), port (5432?), and db name.
