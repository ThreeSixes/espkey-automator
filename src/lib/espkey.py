import datetime
import json
from pprint import pprint
import re

from .http_requests import HTTPRequests


class ESPKey:
    def __init__(self, config):
        self.__config = config
        self.__http = HTTPRequests(config)

        self.__aux_entry_re = re.compile("^([0-9]+) (Aux changed to ([01]))$")
        self.__data_entry_re = re.compile("^([0-9]+) ([0-9a-f]+):([0-9]+)$")
        self.__log_entry_re = re.compile("^([0-9]+) (.+)$")


    def __parse_log(self, log_request):
        """Parse log_text as ESPKey logs.

        Args:
            log_text (str): Log text.

        Returns:
            list: List of dictionaries containing parsed log entries.
        """

        parsed = []

        # Crop carriage returns, split by linefeeds.
        log_text = log_request["text"].replace("\r", "")
        log_split = log_text.split("\n")

        # Go through each line in our log data.
        for line in log_split:
            this_entry = {}
            line_stripped = line.strip()

            # Look for data or logs.
            data_match = re.match(self.__data_entry_re, line_stripped)
            aux_entry_match = re.match(self.__aux_entry_re, line_stripped)
            log_match = re.match(self.__log_entry_re, line_stripped)

            # Look for data.
            if data_match:
                data_groups = data_match.groups()

                this_entry = {
                    "time_raw": int(data_groups[0]),
                    "data_hex": data_groups[1],
                    "data_len": int(data_groups[2])
                }

                # HID data is 26 bits so make a guess.
                if this_entry['data_len'] == 26:
                    hid_data = self.__parse_hid_26(data_groups[1])

                    # Did we get a possible HID hit?
                    if len(hid_data) > 0:
                        this_entry.update({
                            "possible_hid_26": hid_data
                        })

                # Detect potential 4, 7, or 10 byte UID.
                if this_entry['data_len'] in [32, 56, 80]:
                    possible_uid = self.__parse_possible_uid(data_groups[1])

                    if possible_uid:
                        this_entry.update({
                            "possible_uid": possible_uid
                        })

                # Detect potential HID keypad
                if int(this_entry['data_len'] % 2) == 0:
                    possible_keypad = self.__parse_hid_keypad(data_groups[1])

                    if possible_keypad:
                            this_entry.update({
                                "possible_hid_keypad": possible_keypad
                            })

                # Add entry.
                parsed.append(this_entry)

            # Look for aux line toggles.
            elif aux_entry_match:
                log_groups = aux_entry_match.groups()

                this_entry = {
                    "aux_status": bool(int(log_groups[2])),
                    "log_msg": log_groups[1],
                    "time_raw": int(log_groups[0])
                }

                parsed.append(this_entry)

            # Look for textual logs.
            elif log_match:
                log_groups = log_match.groups()

                this_entry = {
                    "time_raw": int(log_groups[0]),
                    "log_msg": log_groups[1]
                }

                parsed.append(this_entry)

        # Set timestamp data for time reconstruction.
        now_ts = int(log_request['now_header'])
        timestamps = self.__process_time_stamps(parsed, now_ts, log_request['req_dts'])

        # Add reconstructed times to parsed entries.
        for idx in timestamps:
            parsed[idx].update({"dts": timestamps[idx]})

        return parsed


    def __parse_diagnostics(self, diagnostic_bin):
        """Parse diagnostic data as int.

        Args:
            diagnostic_bin (int): Registers as integer. 

        Returns:
            dict: Dictinoary conaining a pin name and logic level.
        """

        parsed = {
            "green": bool((diagnostic_bin >> 13) & 0x01),
            "white": bool((diagnostic_bin >> 14) & 0x01),
            "aux": bool((diagnostic_bin >> 5) & 0x01)
        }

        return parsed


    def __parse_possible_uid(self, hex_raw):
        """Parse possible 4, 7, or 10 byte UID.

        Args:
            hex_raw (str): Hex data as string.

        Returns:
            dict, None: Dict containg possible decoded data or None if no match.
        """

        uid = ""
        metadata = []
        data = {}

        raw_len = len(hex_raw)

        for cursor in range(0, raw_len, 2):
            this_byte = f"{hex_raw[cursor + 1]}{hex_raw[cursor]}"

            # Byte order is reversed.
            uid = f"{this_byte}{uid}"

        data.update({"uid": uid})

        # Check for possible 4-byte random UID.
        if raw_len == 8 and uid[0:2] == "08":
                metadata.append("Possible random 4-byte UID used in Mifare DESFire EV2 or EV3.")

        if len(metadata) > 0:
            data.update({"metadata": metadata})

        return data


    def __parse_hid_keypad(self, hex_raw):
        """Look for possible HID keypad data.

        Args:
            hex_raw (str): String representing one or more nibbles in hex.

        Returns:
            str, None: Str for possible keypad entries or None for a failed decode.
        """

        hid_data = None
        possible = True

        # HID characters - 1st nibble is the logical NOT of the second.
        char_table = {
            "e1": "1", "d2": "2", "c3": "3",
            "b4": "4", "a5": "5", "96": "6",
            "87": "7", "78": "8", "69": "9",
            "5a": "*", "f0": "0", "4b": "#"
        }

        nibbles_ct = len(hex_raw)

        # Do we have an even number of nibbles up to 5 bytes?
        if (nibbles_ct % 2) == 0 and nibbles_ct <= 10:
            decoded = []

            # Iterate over bytes looking for hits on the character table.
            for start_nbl in range(0, nibbles_ct, 2):
                end_nbl = start_nbl + 1
                this_byte = f"{hex_raw[start_nbl]}{hex_raw[end_nbl]}"

                if this_byte in char_table:
                    decoded.append(char_table[this_byte])

                else:
                    possible = False
                    break

        else:
            possible = False

        if possible:
            hid_data = decoded

        return hid_data


    def __parse_hid_26(self, hex_raw):
        """Parse data as 26-bit HID

        Args:
            hex_raw (str): 26-bit hex string

        Returns:
            dict: Dictionary containing a facility code and card #.
        """

        # Type convert the hex string to an int.
        hex_int = int(hex_raw, base=16)

        # 26-bit Weigand data structure for HID
        # x = ignore, f=facility code bit, c = card number bit
        #           xffffffffccccccccccccccccx

        fc_shift = 17
        fc_mask = 0b01111111100000000000000000
        cn_shift = 1
        cn_mask = 0b00000000011111111111111110

        # Mask and shift FC and CN
        hid_data = {
            "fc": int((fc_mask & hex_int) >> fc_shift),
            "cn": int((cn_mask & hex_int) >> cn_shift)
        }

        return hid_data


    @staticmethod
    def __process_time_stamps(entries, now_ts, req_dts):
        """Reconstruct approximate timestamp fr

        Args:
            entries (list): List of parsed log entries as dicts.
            now_ts (int): Timestamp from microncontroller Now header.
            req_dts (datetime.datetime): Approximate time request to microcontroller was sent.

        Returns:
            dict: A dictionary containing the entry index as a key and approximate datetime of
                the log entry.
        """

        entries_parsed = {}

        past_latest_entry = False
        last_dts = None
        last_raw_ts = None
        range_start_adj = len(entries) - 1

        # Iterate in reverse.
        for i in range(range_start_adj, 0, -1):
            this_entry = entries[i]

            # Construct past point in time.
            if past_latest_entry:
                # Detect the unit rebooting and stop computing timestamps since the timing
                # data is unrecoverable after a reboot.
                if this_entry['time_raw'] > last_raw_ts:
                    break

                # Compute delta T and datetime.
                delta_t_ms = this_entry['time_raw'] - last_raw_ts
                delta_t = datetime.timedelta(milliseconds=delta_t_ms)
                this_dts = last_dts + delta_t

                # Prep data for next iteration, set current timestamp.
                last_dts = this_dts
                last_raw_ts = this_entry['time_raw']
                entries_parsed.update({i: this_dts.isoformat()})

            # Build starting point using the timing of the request made and the reported
            # microcontroller timestamp header.
            else:
                past_latest_entry = True

                # Compute delta T and datetime.
                delta_t_ms = this_entry['time_raw'] - now_ts
                delta_t = datetime.timedelta(milliseconds=delta_t_ms)
                this_dts = req_dts + delta_t

                # Prep data for next iteration, set current timestamp.
                last_dts = this_dts
                last_raw_ts = now_ts
                entries_parsed.update({i: this_dts.isoformat()})

                # This is a very odd hack to prevent a bug that decodes the first three entries -
                # two of them being incorrect. Typically the startup time ovseserved has been
                # between 510 and 525 ms. I'm adding padding.
                if this_entry['time_raw'] < 540:
                    break

                # Compute delta T and datetime.
                delta_t_ms = this_entry['time_raw'] - last_raw_ts
                delta_t = datetime.timedelta(milliseconds=delta_t_ms)
                this_dts = last_dts + delta_t



        return entries_parsed


    def dos_start(self):
        """Not implemented.
        """
        pass


    def dos_stop(self):
        """Not implemented.
        """
        pass


    def delete_log(self, post_method=False):
        """Delete logs from the ESPKey.

        Args:
            post_method (bool, optional): _description_. Defaults to False.

        Returns:
            bool: True if there was an HTTP 200 response.
        """

        worked = False

        if post_method:
            log_file = ""

            url = f"{self.__config['base_url']}/edit"
            request = self.__http.http_form_post(url, "/log.txt", log_file)

        else:
            url = f"{self.__config['base_url']}/delete"
            request = self.__http.http_get(url)

        if request["status"] == 200:
            worked = True

        return worked


    def get_config(self):

        content = {}

        url = f"{self.__config['base_url']}/config.json"

        request = self.__http.http_get(url)

        if request["status"] != 200:
            raise RuntimeError(f"HTTP status: {request['status']}")

        content = json.loads(request['text'])

        return content

 
    def get_diagnostics(self):
        diagnostic_data = {}

        url = f"{self.__config['base_url']}/all"

        request = self.__http.http_get(url)

        if request["status"] != 200:
            raise RuntimeError(f"HTTP status: {request['status']}")

        diagnostic_data.update(json.loads(request['text']))

        # Parse GPIO status bytes.
        gpio = diagnostic_data['gpio']
        diagnostic_data.update({"parsed": self.__parse_diagnostics(gpio)})

        return diagnostic_data


    def get_log(self, file_name=None):
        """Get log data from ESPKey via HTTP or from a log file if file_name is specified.
           NOTE: Parsing files does not decode raw timestamps. An HTTP header from the request

                 and the Unix timestamp of that rququest are required to convert the relative
                 raw_timestamp to a usable date object.:w

        Args:
            file_name (str, optional): Optional text log file. Defaults to None.

        Raises:
            RuntimeError: The ESPKey returned a non-200 HTTP status code in HTTP mode.

        Returns:
            list: A list of log entries as dcits.
        """

        content = []

        # If we want to load from file...
        if file_name:
            with open(file_name, "r") as f:
                content = self.__parse_log(f.read(-1))

        # Else make an HTTP request.
        else:
            url = f"{self.__config['base_url']}/log.txt"

            request = self.__http.http_get(url)

            if request["status"] != 200:
                raise RuntimeError(f"HTTP status: {request['status']}")

            content = self.__parse_log(request)

        return content


    def get_version(self):
        """Get ESPKey firmware version.

        Raises:
            RuntimeError: The ESPKey returned a non-200 HTTP status code.

        Returns:
            dict: ESPKey version
        """

        content = {}

        url = f"{self.__config['base_url']}/version"

        request = self.__http.http_get(url)

        if request["status"] != 200:
            raise RuntimeError(f"HTTP status: {request['status']}")

        content = json.loads(request['text'])

        return content


    def restart(self):
        """Restart target ESPKey.

        Returns:
            bool: Command successful.
        """

        worked = False

        url = f"{self.__config['base_url']}/restart"

        request = self.__http.http_get(url)

        if request["status"] == 200:
            worked = True

        return worked


    def send_weigand(self, weigand_hex, bit_len):
        """Send weigand data given hex data and binary length.

        Args:
            weigand_hex (str): Weigand data as hex string.
            bit_len (int): Bit length of data to send in string.

        Returns:
            bool: Was the message sent?
        """

        worked = False

        url = f"{self.__config['base_url']}/txid?v={weigand_hex}:{bit_len}"

        request = self.__http.http_get(url)

        if request["status"] == 200:
            worked = True

        return worked
