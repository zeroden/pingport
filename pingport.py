import socket
import time
import sys
import win32api
import keyboard
from colorama import init, Fore, Style
import ctypes
import subprocess
import re
from requests import get
import maxminddb
import random
import requests
import os
import yt_dlp
import contextlib
from io import StringIO
import argparse
import subprocess
import datetime

ping_fails = 0
ping_fails_str = ''
last_newline_inverted = ''
args = None

# Get the handle of the current console window
console_window_handle = ctypes.windll.kernel32.GetConsoleWindow()

def get_active_window_handle():
    # Get the handle of the currently active window
    return ctypes.windll.user32.GetForegroundWindow()

def set_console_title(s):
    win32api.SetConsoleTitle('pingport: ' + s)

def test_youtube_speed(video_url):
    temp_filename = 'temp_video.mp4'
    speed_pattern = re.compile(r'at (\d+\.\d+)MiB/s')

    ydl_opts = {
        'format': '135', # 135 mp4   854x480     25    │    8.28MiB  328k https │ avc1.4D401E    328k video only          480p, mp4_dash
        'noplaylist': True,
        'quiet': False,  # Set to False to capture log messages
        'outtmpl': temp_filename,
        'force_generic_extractor': True,
    }

    # Remove the temp file if it exists
    if os.path.exists(temp_filename):
        os.remove(temp_filename)

    # Capture the log output
    log_output = StringIO()
    with contextlib.redirect_stdout(log_output), contextlib.redirect_stderr(log_output):
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                ydl.download([video_url])
            except Exception as e:
                print('ydl.download() failed [%s]' % e)
                return 0

    # Parse and extract speed from the log output
    log_contents = log_output.getvalue()
    match = speed_pattern.search(log_contents)
    if match:
        speed_mibps = float(match.group(1))
        yt_speed_mbps = speed_mibps * 8 * (1024 / 1000)  # Convert MiB/s to Mbps
    else:
        yt_speed_mbps = 0

    # Clean up the temporary file after downloading
    if os.path.exists(temp_filename):
        os.remove(temp_filename)

    return yt_speed_mbps

def test_download_speed(url):
    anti_cache_stamp = random.randint(0, 0xFFFFFFFF)
    url = url + '?x=%s' % anti_cache_stamp

    start_time = time.time()
    try:
        response = requests.get(url, stream=True)
        total_length = response.headers.get('content-length')
        if total_length is None:
            data = response.content
        else:
            dl = 0
            data = bytearray()
            total_length = int(total_length)
            for chunk in response.iter_content(chunk_size=4096):
                dl += len(chunk)
                data.extend(chunk)
    except Exception as e:
        print('test_download_speed.requests.get() failed [%s]' % e)
        return 0

    end_time = time.time()
    elapsed_time = end_time - start_time

    down_speed_byte = round(len(data) / elapsed_time, 2)  # Calculate speed based on the data length

    # Explicitly discard the accumulated data
    del data

    return down_speed_byte * 8

def get_timestamp(fmt = '%Y-%m-%d %H:%M:%S'):
    return time.strftime(fmt)

def send_telegram(text):
    global args

    if not args.telegram_update:
        return

    try:
        max_length = 4096
        if len(text) > max_length:
            text = text[:max_length - 3] + '...'  # Add ellipsis to indicate truncation
        bot_token, bot_chat_id = args.telegram_update.split(';')
        api_url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
        data = {'chat_id': bot_chat_id, 'text': text, 'disable_web_page_preview': True, 'parse_mode': 'HTML'}
        response = requests.post(api_url, data=data)
        if not response.ok:
            print(get_timestamp('[%Y-%m-%d %H:%M:%S], ') + f'Telegram error: {response.status_code} - {response.text}')
    except Exception as e:
        msg = get_timestamp('[%Y-%m-%d %H:%M:%S], ') + f'Error sending Telegram message: {e}'
        print(msg)

def show_download_speed(msg = ''):
    global args

    if msg:
        msg = '%s, speed: ' % msg
    else:
        msg = 'speed: '
    print(msg, end='')
    
    ping = ping_host(args.host_to_ping)
    if ping < 0:
        print('ping error')
        return

    print('ping ' + Style.BRIGHT + Fore.YELLOW + f'{ping}' + Style.RESET_ALL + 'ms', end='')

    url_1 = args.global_url1
    url_2 = args.global_url2
    url_3 = args.local_url1
    url_4 = args.local_url2

    down_speed_1 = test_download_speed(url_1)
    if not down_speed_1:
        print(last_newline_inverted + 'test_download_speed(url_1) failed')
    down_speed_1 = round(down_speed_1 / 1_000_000, 1)
    down_speed_2 = test_download_speed(url_2)
    if not down_speed_2:
        print(last_newline_inverted + 'test_download_speed(url_2) failed')
    down_speed_2 = round(down_speed_2 / 1_000_000, 1)
    down_speed_1_2 = max(down_speed_1, down_speed_2)
    if down_speed_1_2:
        print(', glob ' + Style.BRIGHT + Fore.YELLOW + f'{down_speed_1_2}' + Style.RESET_ALL + 'mbit', end='')

    down_speed_3 = test_download_speed(url_3)
    if not down_speed_3:
        print(last_newline_inverted + 'test_download_speed(url_3) failed')
    down_speed_3 = round(down_speed_3 / 1_000_000, 1)
    down_speed_4 = test_download_speed(url_4)
    if not down_speed_4:
        print(last_newline_inverted + 'test_download_speed(url_4) failed')
    down_speed_4 = round(down_speed_4 / 1_000_000, 1)
    down_speed_3_4 = max(down_speed_3, down_speed_4)
    if down_speed_3_4:
        print(', loc ' + Style.BRIGHT + Fore.YELLOW + f'{down_speed_3_4}' + Style.RESET_ALL + 'mbit', end='')

    timedate_stamp = get_timestamp()
    tg_msg = f'ping <b>{ping}</b>ms ▒ glob <b>{down_speed_1_2}</b>mbit ▒ loc <b>{down_speed_3_4}</b>mbit'

    down_speed_5 = 0
    if args.enable_yt_speed:
        # {'video_title': 'Rick Astley - Never Gonna Give You Up (Official Music Video)'}
        video_url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        result = test_youtube_speed(video_url)
        down_speed_5 = round(result, 1)
        if not down_speed_5:
            print(last_newline_inverted + 'test_youtube_speed() failed')
        else:
            print(', yt ' + Style.BRIGHT + Fore.YELLOW + f'{down_speed_5}' + Style.RESET_ALL + f'mbit', end='')
            tg_msg += f', yt {down_speed_5}'

    # print newline to done with speed output
    print('')

    send_telegram(tg_msg)

    speed_file = 'speed.csv'
    # if speed file not exist create header in it
    if not os.path.exists(speed_file):
        with open(speed_file, 'a') as myfile:
            myfile.write('DATETIME,PING,GLOB,LOC,YT\n')
    with open(speed_file, 'a') as myfile:
        myfile.write(f'{timedate_stamp},{ping},{down_speed_1_2},{down_speed_3_4},{down_speed_5}\n')

def get_win_uptime(): 
    # getting the library in which GetTickCount64() resides
    lib = ctypes.windll.kernel32

    # Set the return type to match the expected unsigned 64-bit integer (no negatives values)
    lib.GetTickCount64.restype = ctypes.c_ulonglong

    # calling the function and storing the return value
    t = lib.GetTickCount64()
     
    # since the time is in milliseconds i.e. 1000 * seconds
    # therefore truncating the value
    t = int(str(t)[:-3])
     
    # extracting hours, minutes, seconds & days from t
    # variable (which stores total time in seconds)
    mins, sec = divmod(t, 60)
    hour, mins = divmod(mins, 60)
    days, hour = divmod(hour, 24)
     
    # formatting the time in readable form
    # (format = x days, HH:MM:SS)
    return f'{days} days, {hour:02}:{mins:02}:{sec:02}'

def dupe_console_to_file(filepath):
    class Logger(object):
        def __init__(self):
            self.logfile = open(filepath, 'ab', 0)
            self.prevstdout = sys.stdout

        def write(self, message):
            self.prevstdout.write(message)
            self.prevstdout.flush()
            self.logfile.write(message.encode())
            self.logfile.flush()
            global last_newline_inverted
            if message[-1] == '\n':
                last_newline_inverted = ''
            else:
                last_newline_inverted = '\n'

        def __del__(self):
            self.logfile.close()

        def flush(self):
        #this flush method is needed for python 3 compatibility.
        #this handles the flush command by doing nothing.
        #you might want to specify some extra behavior here.
            pass

    sys.stdout = Logger()
    # no necessary, but redirect errors too
    sys.stderr = sys.stdout

def get_percentage(whole, part):
    if whole:
        perc = 100 * float(part) / float(whole)
    else:
        perc = 0
    return str(round(perc))

def custom_sleep(i):
    while i:
        if ping_fails:
            ping_fails_str = ' (fails %d)' % ping_fails
            set_console_title('%d%s' % (i, ping_fails_str))
        else:
            set_console_title('%d' % i)
        i = i - 1
        j = 10
        while j:
            j = j - 1
            time.sleep(0.1)
            if get_active_window_handle() == console_window_handle:
                # manual ping
                if keyboard.is_pressed('f1'):
                    print('m', end='')
                    i = 0
                    j = 0
                # manual speed test
                elif keyboard.is_pressed('f2'):
                    timedate_stamp = get_timestamp()
                    msg = last_newline_inverted + f'[{timedate_stamp}] manual'
                    show_download_speed(msg)

def ping_host(host):
    try:
        output = subprocess.check_output(['ping', '-n', '1', host], stderr=subprocess.STDOUT, universal_newlines=True)
        # Extract the time in ms using regular expressions
        time_match = re.search(r'time[=<](\d+)', output)
        if time_match:
            time_ms = int(time_match.group(1))
            return time_ms
        else:
            return -1  # General failure
    except (subprocess.CalledProcessError, PermissionError, Exception):
        return -1  # General failure

def show_ping(host):
    timedate_stamp = get_timestamp()
    # ping using classical ping
    ret_ping = ping_host(host)
    # make second ping try
    if ret_ping < 0:
        custom_sleep(5)
        ret_ping = ping_host(host)
    if ret_ping >= 0:
        print(Style.BRIGHT + Fore.GREEN + '%d' % ret_ping, end='')
    else:
        print(last_newline_inverted + Style.BRIGHT + Fore.RED + '%s ping down %d' % (timedate_stamp, ping_fails + 1))

    sock = 0
    ret_sock = -1
    try:
        # ping using connect ping
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ret_sock = sock.connect_ex((host, 80))
    except socket.error as e:
        pass

    if sock:
        sock.close()

    if ret_sock == 0:
        print(Style.BRIGHT + Fore.GREEN + '.', end='');
    else:
        print(last_newline_inverted + Style.BRIGHT + Fore.RED + '%s conn down %d' % (timedate_stamp, ping_fails + 1))

    # successful only if both type of pings are ok
    return ret_ping >= 0 and ret_sock == 0

def reverse_ip(ip):
    try:
        host_rev = socket.gethostbyaddr(ip)[0]
    except (socket.herror) as err:
        host_rev = err
    return host_rev

def nice_time(time):
    return str(datetime.timedelta(seconds=int(time)))

def main():
    global ping_fails, args

    parser = argparse.ArgumentParser()
    parser.add_argument('--host-to-ping', help='Host for ping', required=True)
    parser.add_argument('--local-url1', help='Local url 1', required=True)
    parser.add_argument('--local-url2', help='Local url 2', required=True)
    parser.add_argument('--global-url1', help='Global url 1', required=True)
    parser.add_argument('--global-url2', help='Global url 2', required=True)
    parser.add_argument('--enable-yt-speed', action='store_true', help='Enable youtube speed test (optional)')
    parser.add_argument('--enable-hibernate', type=int, metavar='MINUTES', help='Enable hibernation after the specified number of offline minutes (optional)')
    parser.add_argument('--telegram-update', help='Send data to telegram bot (optional)')
    args = parser.parse_args()

    logfilename = get_timestamp('pingport_%Y%m%d_%H%M%S.log')
    dupe_console_to_file(logfilename)
    timedate_stamp = get_timestamp('[%Y-%m-%d %H:%M:%S]')
    init(convert=True, autoreset=True)

    start_msg = timedate_stamp + ' pingport started'
    print(Style.BRIGHT + Fore.CYAN + start_msg)
    send_telegram(start_msg)

    print('python version: "%s"' % sys.version)
    print('python path: "%s"' % sys.executable)
    print('cmdl: <%s>' % win32api.GetCommandLine())
    print('log: "%s"' % logfilename)
    print('windows uptime: "%s"' % get_win_uptime())
    print('host to ping: "%s"' % args.host_to_ping)
    try:
        host_to_ping_ip = socket.gethostbyname(args.host_to_ping)
        print('host to ping ip: "%s"' % host_to_ping_ip)
        print('host to ping ip reverse: "%s"' % reverse_ip(host_to_ping_ip))
    except Exception as e:
        print(f'host to ping ip: failed - {str(e)}')
    loc_ip = socket.gethostbyname(socket.getfqdn())
    print('local ip: "%s"' % loc_ip)
    print('local ip reverse: "{}"'.format(reverse_ip(loc_ip)))
    print('local name: "%s"' % socket.getfqdn())
    try:
        wan_ip = get('https://api.ipify.org').content.decode('utf8')
        print('wan ip: "{}"'.format(wan_ip))
        print('wan ip reverse: "{}"'.format(reverse_ip(wan_ip)))
        ip2isp_fn = 'dbip-asn-lite-2024-07.mmdb'
        if os.path.exists(ip2isp_fn):
            with maxminddb.open_database(ip2isp_fn) as reader:
                rec = reader.get(wan_ip)
                print('isp: "%s"' % rec['autonomous_system_organization'])
    except Exception as e:
        print(f'wan ip: failed - {str(e)}')
    show_download_speed()
    print('Press F1 for a manual ping, F2 for manual speed test\n')

    last_60min_mark = time.time()
    last_24hours_mark = time.time()
    first_offline_mark = 0
    first_offline_time = 0
    ping_day_attempts = 0
    ping_day_ok = 0
    hour_count = 0
    day_count = 0
    telegram_message = ''

    while True:
        timedate_stamp = get_timestamp('[%Y-%m-%d %H:%M:%S]')
        current_time = time.time()

        # Check if 60 minutes have passed
        hours_passed = (current_time - last_60min_mark) / 3600
        if hours_passed >= 1:
            last_60min_mark = current_time
            hour_count += 1
            if hours_passed >= 2:
                hours_msg = '+%d hours slept' % hours_passed
                print(last_newline_inverted + Style.BRIGHT + hours_msg)
                send_telegram(hours_msg)
                # wait some time after unsleep to allow network up
                custom_sleep(10)
            msg = last_newline_inverted + timedate_stamp + ' hour%d' % hour_count
            show_download_speed(msg)

        # Check if 24 hours have passed
        # print day stat
        if current_time - last_24hours_mark >= 24 * 60 * 60:
            # reset day marker
            last_24hours_mark = current_time
            day_count += 1
            perc = get_percentage(ping_day_attempts, ping_day_ok)
            partial = ''
            if ping_day_attempts != ping_day_ok:
                partial = ' partial'
            day_msg = timedate_stamp + ' day%d%s uptime %s%%, %d outof %d %s' % (day_count, partial, perc, ping_day_ok, ping_day_attempts, ping_fails_str)
            print(last_newline_inverted + Style.BRIGHT + day_msg)
            send_telegram(day_msg)
            day_msg = 'windows uptime: "%s"' % get_win_uptime()
            print(day_msg)
            send_telegram(day_msg)

            # empty string between days
            print('')
            # reset day counters
            ping_day_attempts = 0
            ping_day_ok = 0

        ping_day_attempts += 1

        result = show_ping(args.host_to_ping)
        # ping ok
        if result:
            ping_day_ok += 1
            first_offline_mark = 0
            offline_msg = ''
            if first_offline_time:
                offline_time_raw = current_time - first_offline_time
                offline_time_nice = nice_time(offline_time_raw)
                offline_msg = f'{timedate_stamp} back online, downtime lasted {offline_time_nice}'
                print(offline_msg)
                first_offline_time = 0
            if telegram_message:
                if offline_msg:
                    telegram_message += '\n' + offline_msg
                send_telegram(telegram_message)
                telegram_message = ''
        # in case of ping fail check if hiberanation needed
        else:
            telegram_message += f'{timedate_stamp} ping fail\n'
            ping_fails += 1
            if not first_offline_mark:
                first_offline_mark = current_time
            if not first_offline_time:
                first_offline_time = current_time
            # after some offline time go hibernate
            if args.enable_hibernate and current_time - first_offline_mark >= 60 * args.enable_hibernate:
                print('hibernation activated')
                # reset hibernation timer
                first_offline_mark = current_time
                # Command to open a new cmd window, wait, then hibernate
                cmd = f'start cmd /k "echo delayed hibernation & timeout /t 300 && shutdown /h"'
                subprocess.Popen(cmd, shell=True)

            # if ping failed don't wait long time for next try
            custom_sleep(10)
            continue

        # next good ping timeout
        custom_sleep(60)

if __name__ == '__main__':
    main()
