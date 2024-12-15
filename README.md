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

Documentation coming soon. Use the `--help` for CLI options.

## Configuration

Order of precedence:
  * Environment variables
  * Configuration JSON document. The default filename the application looks for is `config.json` in the current working directory.

### JSON-based configuration

To specify a single device to target use the `default` top-level key and define a `base_url` and optional `web_user` and `web_pass`. If only `web_user` or `web_pass` are specified the credentials are ignored. Both are required to use HTTP basic auth against the ESP key.
Exmaple from `config.json.basic-example`:

```json
{
    "default": {
        "base_url": "http://192.168.4.1",
        "web_user": "myuser",
        "web_pass": "somegreatpass"
    }
}
```

To specify multiple devices and a default use a structure that contains a `default` key and one more additional named entries that have a `base_url` and optional `web_user` and `web_pass`. This example defines one `default` entry that is identical to `espkey1`, and another device called `espkey2` that doesn't have any credentials associated with it. If at least one non-default entry is created defaults aren't required.
Example from `confg.json.exmaple`:

```json
{
    "default": {
        "base_url": "http://192.168.4.1",
        "web_user": "myuser",
        "web_pass": "somegreatpass"
    },
    "espkey1": {
        "base_url": "http://192.168.4.1",
        "web_user": "myuser",
        "web_pass": "somegreatpass"
    },
    "espkey2": {
        "base_url": "http://192.168.4.2"
    }
}
```

### Environment variables

Thie application can also be configured with environment variables.

Global env vars:
 - `EKA_CONFIG_FILE` (optional): When set this changes the default JSON configuration file from `config.json` to whatever the user specifies.
 - `EKA_RECIPE_FILE` (optional): When set this changes the default JSON recipe file from `recipe.json` to whatever the user specifies.

Target specification:
 - `EKA_BASE_URL` (required if targeting specific ESPKey with env vars): Specifies the base URL for the target ESPKey.
 - `EKA_WEB_USER`: (optional if targeting specific ESPKey with env vars): Specifies the HTTP basic user use with the request. This option is ignored without `EKA_WEB_PASS`.
 - `EKA_WEB_PASS`: (optional if targeting specific ESPKey with env vars): Specifies the HTTP basic password use with the request. This option is ignored without `EKA_WEB_USER`.

Examples:

`EKA_CONFIG_FILE=otherconfig.json ./src/espkey_automator.py --delete-log`
`EKA_BASE_URL="http://192.168.4.3" ./src/espkey_automator.py --get-log`
`EKA_BASE_URL="http://192.168.4.3" EKA_WEB_USER="bob"` `EKA_WEB_PASS="bobspass" ./src/espkey_automator.py --get-version`


## Recipe operation

Using a recipe allows users to automate operations against one or more ESPKeys. The main concepts here are ESPKey definitions that specify the target device that tasks are run against. Recipes are specified and executed using the `--recpie` command line switch. Use `--recipe <recipe filename>` where `<file name>` a JSON-formatted recpie document. See `recipe.json.example` for an example. Tasks are a list of actions that are run against the ESPKeys defined in the afformentioned section. Tasks are scoped to a single ESPKey, and contain one or more actions. Individual actions contain an operation and any required or optional arguments for that operation. After each task is run a JSON-formatted log file is created in the format `<YYYY><MM><DD>-<HH><mm><ss>_<target>_<task>.json` Where `<YYYY><MM><DD>-<HH><mm><ss>` is the host running the task's UTC timestamp specifying the year, month, day, hour, minutes, and seconds. `<target>` is the target ESPKey the task was run against and the `<task>` is the named task.


### Recipe operations and properties

The recpie supports a number of potential operations that can be run in sequence. Each action contains an `operation` and any mandatory or optional argument that the operation supports. Below are supported `operations` and their arguments. See the examples in the next section.

* `get_log` gets the log data from an ESPKey.
* `delete_log` gets the log data on an ESPKey.
  *  `with_post` is an optional boolean argument that uses an HTTP post instead of GET endpoint to delete logs on some firmware versions.
* `get_diagnostics` retrieves diagnostic data from the ESPKey.
* `get_config` retrieves the JSON configuration data from the ESPKey.
* `get_version` gets firmware and hardware version data from the ESPKey.
* `restart` restarts the ESPKey.
* `send_weigand` sends Weigand data from the ESPKey.
  * `data` is a mandatory argument that contains a hex string representing the weigand data to be sent and a bit length separated by a colon. The bit length is the number of bits from that string to send. It's useful because some data one may want to send don't align on byte lengths. 26-bit HID data is one example that lands between 3 and 4 bytes thus a bit length of 26 should be used.
* `delay` pauses execution of the script for a specified number of seconds.
  * `sec` is mandatory and defines the number of seconds to delay for as an int or float.

### Example recpipe and log

This recipe defines two `espkeys`: `ek1` and `ek2`. Each has the required `base_url` and an optional `web_user` and `web_pass` argument. There are two `tasks` - one called `one` and one called `two`. Both contain the required `target` which should match one of the named ESPKeys in the `espkeys` section. Task `one` runs with a `target` of `ek1`, and task `two` runs with a target of `ek2`. Both contain a list of actions. More on that later. Task `two` has an argument that disables pretty printing JSON: `"pretty_json": false`. This can be used to make the returned JSON more compact, and without the argument the JSON is automatically pretty printed.

Each task under the `tasks` key contains a number of actions, each with the required `operation` key, but there can be one or many actions per task. I'll break down the actions in each task:

 * Task `one` which targets `ek1`:
   * Gets the version of ESPKey softare, hardware, etc.
   * Gets the diagnostic data from the ESPKey.
   * Sends the weigand the all `8` bits of the Weigand `data` `0x42`.
   * Gets the logs from the ESPKey.
   * Deletes the log using an HTTP POST.
 * Task `two` which targets `ek2` is more simple. It:
   * Sends the last `26` bits of the Weigand `data` `0x025369d0`.
   * Gets the logs from the ESPKey.

Exmple recipe file:faq

```json
{
    "espkeys": {
        "ek1": {
            "base_url": "http://192.168.4.1",
            "web_user": "key_user",
            "web_pass": "greatpass"
        },
        "ek2": {
            "base_url": "http://192.168.4.2",
            "web_user": "key_user",
            "web_pass": "evenbetterpass"
        }
    },
    "tasks": {
        "one": {
            "target": "ek1",
            "pretty_json": true,
            "actions": [
                {
                    "operation": "get_version"
                },
                {
                    "operation": "get_diagnostics"
                },
                {
                    "operation": "send_weigand",
                    "data": "42:8"
                },
                {
                    "operation": "get_log"
                },
                {
                    "operation": "delete_log",
                    "with_post": true
                }
            ]
        },
        "two": {
            "target": "ek2",
            "pretty_json": false,
            "actions": [
                {
                    "operation": "send_weigand",
                    "data": "42:8"
                },
                {
                    "operation": "get_log"
                }
            ]
        }
    }
}
```

The log for `ek2` task `two` has been omitted since it just perofrms a `get_log` action and there's an example of that below.

Example log file named `20241213-160204_ek1_one.json` for `ek1` task `one`:

```json
{
    "actions": [
        {
            "action": "get_version",
            "run": "2024-12-13T16:02:04.267399",
            "result": {
                "version": "131",
                "log_name": "ESPKey",
                "ChipID": "112233"
            }
        },
        {
            "action": "get_diagnostics",
            "run": "2024-12-13T16:02:04.340589",
            "result": {
                "heap": 35288,
                "analog": 146,
                "gpio": 24581,
                "parsed": {
                    "green": true,
                    "white": true,
                    "aux": false
                }
            }
        },
        {
            "action": "get_log",
            "run": "2024-12-13T16:02:04.553133",
            "result": [
                {
                    "time_raw": 508,
                    "log_msg": "Starting up!"
                },
                {
                    "time_raw": 21319,
                    "data_hex": "29b0bfc",
                    "data_len": 26,
                    "possible_hid_26": {
                        "fc": 77,
                        "cn": 34302
                    },
                    "dts": "2024-12-13T15:58:04.420187"
                },
                {
                    "time_raw": 24005,
                    "data_hex": "2c8636e",
                    "data_len": 26,
                    "possible_hid_26": {
                        "fc": 100,
                        "cn": 12727
                    },
                    "dts": "2024-12-13T15:58:07.106187"
                },
                {
                    "time_raw": 26990,
                    "data_hex": "0ec31bc",
                    "data_len": 26,
                    "possible_hid_26": {
                        "fc": 118,
                        "cn": 6366
                    },
                    "dts": "2024-12-13T16:00:07.322187"
                }
            ]
        },
        {
            "action": "send_weigand",
            "run": "2024-12-13T16:02:05.042829",
            "result": true
        },
        {
            "action": "delay",
            "run": "2024-12-13T16:02:05.273198",
            "delay": 2
        },
        {
            "action": "delete_log",
            "run": "2024-12-13T16:02:07.278558",
            "result": true
        }
    ],
    "metadata": {
        "espkey": "ek1",
        "run_start": "2024-12-13T16:02:04.267237"
    }
}
```


## Known limitations

 * The timestamps on log entries generated before a reboot of the device can't be recovered as human-readable. The algorithm required to decode the timestamps sent by the ESPKey rely on building these timestamps in reverse from the present time. If the millisecond epoch on the device is reset there's no way to recover the number of milliseconds that psased between the last log entry before a reboot and the next timestamp after. Please consider downloading logs before you reboot the device in order to preserve timestamps on any data you record before a reboot.
 * Timestamps aren't as precise as would be ideal. This is because there is some difference in time between the microcontroller's milisecond timestamp being sent and the local system timestamp being set for the computations to run. The margin for error can be many seconds. See the next limitation note regarding request delays caused by mDNS resolution. Not using mDNS may be helpful in reducing the margin for error on the logs.
 * Accessing the ESPKey's API with a `.local` address introduced significant delays (around 6 seconds) because mDNS resolution is slow. To avoid increased latency you can use the device's IP address or configure a static DNS name for it rather than using mDNS.
 * Firmware and web UI upgrades aren't supported. 
 * Setting the configuration isn't supported.
