# fahclient_handler

[![MIT licensed](https://img.shields.io/badge/license-MIT-blue.svg)]


Folding@Home wrapper to automatically start/stop fahclient service (using systemd) by monitoring system métrique (load and temperature).

Folding@Home currently doesn't fit well with systemd (https://github.com/FoldingAtHome/fah-issues/issues/1396), you may want to add the service file in this repo to /etc/systemd/system/fahclient.service location. Then run a systemctl daemon-reload to apply changes.

## How to use

fahclient_handler.py is a daemon which can be run as a service.

2 parameters can be use:
* Temperature in celsius degre
* Load which is a percentage of total load available. Let's say you have 8 thread, 0.5 mean that limit be reach on a 15 min average load of 4. 

When the daemon start or stop fahclient, it will wait 20 minutes before starting/stoping back fahclient (preventing quick start and stop of fahclient if your system metric are close to the limit you set). 

Example:

python3 fahclient_handler.py --load 0.6 -temp 95




