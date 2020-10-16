.. _installation_setup:

======================
Installation and setup
======================

.. toctree::

Environment setup
-----------------

Prerequisites
~~~~~~~~~~~~~

This bot was developed under and tested with Debian GNU/Linux. It might
work with other operating systems of the Linux family as well as other
UNIX systems, as long as those support the required libraries. We do not
support Windows and Mac OS and have no plans to do so.

We encourage you to use another user to run the bot for security purposes,
e.g. ``matebot`` or ``matebot_user`` (just anything but ``root`` of course).
Choose a name and stick to it during this setup.

You need to have at least `Python 3.7 <https://www.python.org/downloads>`_
with ``pip`` and ``venv`` installed on your system. You will also need a
MariaDB or MySQL server (other database backends are currently not supported).

On Debian GNU/Linux and its derivatives, the following snippet should do the
steps for you (you need to be ``root`` or prefix the commands with ``sudo``):

.. code-block::

    apt-get update
    apt-get upgrade -y
    apt-get install mariadb-server python3 python3-pip python3-venv git -y
    mysql_secure_installation

Code setup
~~~~~~~~~~

Clone our repository to your server:

.. code-block::

    git clone https://github.com/CrsiX/matebot
    cd matebot

Create and enable a virtual environment for the Python packages:

.. code-block::

    python3 -m venv venv
    source venv/bin/activate

Install the minimally required Python packages:

.. code-block::

    pip3 install -r requirements.txt

.. note::

    You may want `mysqlclient <https://pypi.org/project/mysqlclient/>`_
    instead of ``pymysql``. In case it's available, we prefer it over
    `pymysql <https://pypi.org/project/PyMySQL/>`_, which is installed
    because it's listed in the ``requirements.txt`` file. However, it
    requires the installation of OS-specific libraries which the pure-Python
    implementation does not. Therefore, there's the requirement for the
    pure-Python library, while the other one could be used by doing:

    .. code-block::

        apt install default-libmysqlclient-dev
        pip3 install mysqlclient

Telegram Bot Setup
------------------

To deploy your own instance of the MateBot, you have to create a Telegram bot.
Talk to `@BotFather <https://t.me/botfather>`_ to create your own bot
and gather a bot token. To do so follow the instructions on the official
`Telegram website <https://core.telegram.org/bots#6-botfather>`_.

The token may look something like this:
``1153242342:AA3ofnI2ABvleFEmPq9naIfeY9Y2afeof2v``.
Store it in the config option ``token`` as shown below.

In order to use all features of the bot (including the
inline search features), you need to perform the following
two commands in the chat with ``@BotFather``:

.. code-block::

    /setinline
    /setinlinefeedback

.. note::

    You need to set the quota for the inline feedback to 100%,
    otherwise the inline search features will not work properly.

MateBot Configuration
---------------------

The configuration of the MateBot is stored in a JSON file called
``config.json``. You need to adjust this file according to your needs.
Read :ref:`config` for further information.