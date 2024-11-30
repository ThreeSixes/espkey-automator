# ESPKey automator

## Background and requirements

This project is designed to interface with an [ESPKey Wiegand Interception Tool](https://www.redteamtools.com/espkey) to perform actions from a CLI instead of manually through the web interface. Current work is underway to provide a basic CLI interface and support for recipes (ordered sets of actions) against one or more ESPKey is coming after the MVP CLI utility is complete.

Once the MVP is complete this readme will be updated with proper instructions.


### Requirements

Installation/development requirements:
* Python 3.12.4 either as system or pyenv installation.
* Pipenv

Operational requirements:
* [ESPKey Wiegand Interception Tool](https://www.redteamtools.com/espkey)
* To run the script the host running the script must have the ability to reach ESPKey device using HTTP requests using web interface credentials if they've been configured.

## CLI operation

Coming soon.

## Recipe operation

Coming soon with recipe feature.

## Known limitations

* The timestamps on log entries generated before a reboot of the device can't be recovered as human-readable. The algorithm required to decode the timestamps sent by the ESPKey rely on building these timestamps in reverse from the present time. If the millisecond epoch on the device is reset there's no way to recover the number of milliseconds that psased between the last log entry before a reboot and the next timestamp after. Please consider downloading logs before you reboot the device in order to preserve timestamps on any data you record before a reboot.
* Timestamps aren't as precise as would be ideal. This is because there is some difference in time between the microcontroller's milisecond timestamp being sent and the local system timestamp being set for the computations to run. The margin for error can be many seconds. See the next limitation note regarding request delays caused by mDNS resolution. Not using mDNS may be helpful in reducing the margin for error on the logs.
* Accessing the ESPKey's API with a `.local` address introduced significant delays (around 6 seconds) because mDNS resolution is slow. To avoid increased latency you can use the device's IP address or configure a static DNS name for it rather than using mDNS.