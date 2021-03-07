# errbot-czechia-covid
An errbot plugin for Czechia covid statistics.
Based on implementation from [this repo](https://github.com/MatyasKriz/situace).
It does not look that fancy and some data are omitted, but it works well enough.

Example of an output:

(Note: I use `:nothing:` emoji for separators as errbot can only return strings.)
![Czechia-Covid plugin output](/res/screenshot.jpg)

## Installation
As this is a plugin for Errbot, you'll need an errbot instance up and running first.
Please refer to the [documentation](https://errbot.readthedocs.io/en/latest/user_guide/setup.html#installation)
on how to set up Errbot and [install plugins](https://errbot.readthedocs.io/en/latest/user_guide/administration.html#installing-plugins).

To use this plugin, you'll also need to have a Redis database set up.
You can download it [here](https://redis.io/download).
When you have Redis up and running, export env variables `REDIS_HOST` and `REDIS_PORT` 
with IP address of the redis instance and its port.
If you are running everything locally with default settings, then these variables should be
`REDIS_HOST=localhost` and `REDIS_PORT=6379`. If you have Errbot already running, you should restart it.

## Message customization
The only way to customize the report message is to fork this repository 
and update the message in the `czechia_covid.py` file.
