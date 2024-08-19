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

ping_fails = 0
ping_fails_str = ''
last_newline_inverted = ''

# Get the handle of the current console window
console_window_handle = ctypes.windll.kernel32.GetConsoleWindow()

def get_active_window_handle():
    # Get the handle of the currently active window
    return ctypes.windll.user32.GetForegroundWindow()

def set_console_title(s):
    win32api.SetConsoleTitle('pingport: ' + s)

def test_youtube_speed(video_url, resolution='360p'):
    ydl_opts = {
        'format': f'bestvideo[height<={resolution}]',
        'noplaylist': True,
        'outtmpl': 'temp_video.%(ext)s',
    }
    
    org_stdout = sys.stdout
    org_stderr = sys.stderr

    try:
        # Redirect stdout and stderr
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')

        start_time = time.time()
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=True)
            video_title = info_dict.get('title', None)
            file_size = info_dict.get('filesize', None)
        
        end_time = time.time()
        download_time = end_time - start_time
        speed_mbps = (file_size * 8) / (download_time * 1_000_000) if file_size else None
        speed_mbps = round(speed_mbps, 1)
        
        return {
            'video_title': video_title,
            'resolution': resolution,
            'file_size_MB': file_size / 1_000_000 if file_size else None,
            'download_time_sec': download_time,
            'speed_Mbps': speed_mbps
        }

    except Exception as e:
        return f"An error occurred: {str(e)}"

    finally:
        # Restore stdout and stderr
        sys.stdout = org_stdout
        sys.stderr = org_stderr

        temp_file = 'temp_video.webm'
        if os.path.exists(temp_file):
            os.remove(temp_file)
        temp_file = 'temp_video.mp4'
        if os.path.exists(temp_file):
            os.remove(temp_file)

def test_download_speed(url):
    anti_cache_stamp = random.randint(0, 0xFFFFFFFF)
    url = url + '?x=%s' % anti_cache_stamp

    start_time = time.time()
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

    end_time = time.time()
    elapsed_time = end_time - start_time

    down_speed_byte = round(len(data) / elapsed_time, 2)  # Calculate speed based on the data length

    # Explicitly discard the accumulated data
    del data

    return down_speed_byte * 8

def show_download_speed(show_timestamp = True):
    timedate_stamp = time.strftime('%Y-%m-%d %H:%M:%S')
    if show_timestamp:
        print(f'[{timedate_stamp}] testing download speed... ', end='')
    else:
        print('testing download speed... ', end='')
    
    ping = ping_host(sys.argv[1])
    if ping < 0:
        time.sleep(5)
        ping = ping_host(host)
    if ping < 0:
        print('ping error')
        return

    print(f'ping ' + Style.BRIGHT + Fore.YELLOW + f'{ping}' + Style.RESET_ALL + ' ms, ', end='')

    url1, url2, url3, url4 = sys.argv[2:]

    set_console_title('testing speed1')
    spd1 = test_download_speed(url1)
    set_console_title('speed1 is %d' % round(spd1 / 1_000_000))
    spd2 = test_download_speed(url2)
    # resulting speed is best of two
    down_speed_1_mbit = round(max([spd1, spd2]) / 1_000_000, 1)
    print('down1 ' + Style.BRIGHT + Fore.YELLOW + f'{down_speed_1_mbit}' + Style.RESET_ALL + f' mbit, ', end='')

    # {'video_title': 'Rick Astley - Never Gonna Give You Up (Official Music Video)', 'resolution': '360', 'file_size_MB': 6.625667, 'download_time_sec': 5.190907955169678, 'speed_Mbps': 10.211187803322817}
    video_url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
    result = test_youtube_speed(video_url)
    # second try to measure yt speed
    if not type(result) == dict:
        print('\ntest_youtube_speed() second try [%s]' % result)
        custom_sleep(5)
        result = test_youtube_speed(video_url)
        if not type(result) == dict:
            print('\ntest_youtube_speed() failed [%s]' % result)
            return
        
    down_speed_2_mbit = result['speed_Mbps']
    print('down2 ' + Style.BRIGHT + Fore.YELLOW + f'{down_speed_2_mbit}' + Style.RESET_ALL + f' mbit, ', end='')

    spd3 = test_download_speed(url3)
    set_console_title('speed3 is %d' % round(spd3 / 1_000_000))
    spd4 = test_download_speed(url4)
    # resulting speed is best of two
    down_speed_3_mbit = round(max([spd3, spd4]) / 1_000_000, 1)
    print('down3 ' + Style.BRIGHT + Fore.YELLOW + f'{down_speed_3_mbit}' + Style.RESET_ALL + f' mbit')

    speed_file = 'speed.csv'
    # if speed file not exist create header in it
    if not os.path.exists(speed_file):
        with open(speed_file, 'a') as myfile:
            myfile.write('"DATETIME","PING","DOWN1","DOWN2","DOWN3"\n')
    with open(speed_file, 'a') as myfile:
        myfile.write(f'"{timedate_stamp}","{ping}","{down_speed_1_mbit}","{down_speed_2_mbit}","{down_speed_3_mbit}"\n')

def get_win_uptime(): 
    # getting the library in which GetTickCount64() resides
    lib = ctypes.windll.kernel32
     
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
    return f"{days} days, {hour:02}:{mins:02}:{sec:02}"

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
            if get_active_window_handle() == console_window_handle and keyboard.is_pressed('f1'):
                # manual ping
                print('m', end='')
                i = 0
                j = 0

def ping_host(host):
    try:
        output = subprocess.check_output(["ping", "-n", "1", host], stderr=subprocess.STDOUT, universal_newlines=True)
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
    timedate_stamp = time.strftime('%Y-%m-%d %H:%M:%S')
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

def main():
    global ping_fails

    logfilename = time.strftime('pingport_%Y%m%d_%H%M%S.log')
    dupe_console_to_file(logfilename)
    timedate_stamp = time.strftime('[%Y-%m-%d %H:%M:%S]')
    init(convert=True, autoreset=True)

    # Check if exactly 5 arguments (plus the script name) are passed
    if len(sys.argv) < 6:
        print("Error: Please provide exactly 1 host and 4 URLs.")
        print("Usage: python pingport.py <host> <url1> <url2> <url3> <url4>")
        sys.exit(1)
    host_to_ping = sys.argv[1]

    print(Style.BRIGHT + Fore.CYAN + time.strftime(timedate_stamp + ' pingport started'))
    print('python version: "%s"' % sys.version)
    print('python path: "%s"' % sys.executable)
    print('log: "%s"' % logfilename)
    print('windows uptime: "%s"' % get_win_uptime())
    print('host to ping: "%s"' % host_to_ping)
    try:
        host_to_ping_ip = socket.gethostbyname(host_to_ping)
        print('host to ping ip: "%s"' % host_to_ping_ip)
        print('host to ping ip reverse: "%s"' % reverse_ip(host_to_ping_ip))
    except Exception as e:
        print(f"host to ping ip: failed - {str(e)}")
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
        print(f"wan ip: failed - {str(e)}")
    if '--show-download-speed' in sys.argv:
        show_download_speed(show_timestamp = False)
    print('Press F1 for a manual ping\n')

    last_60min_mark = time.time()
    last_24hours_mark = time.time()
    ping_day_attempts = 0
    ping_day_ok = 0
    hour_count = 0
    day_count = 0


    while True:
        time_stamp = time.strftime('%H:%M:%S')
        timedate_stamp = time.strftime('[%Y-%m-%d %H:%M:%S]')
        current_time = time.time()

        # Check if 60 minutes have passed
        hours_passed = (current_time - last_60min_mark) / 3600
        if hours_passed >= 1:
            last_60min_mark = current_time
            hour_count += 1
            if hours_passed >= 2:
                print(last_newline_inverted + Style.BRIGHT + timedate_stamp + ' +%d hours slept' % hours_passed)
            print(last_newline_inverted + timedate_stamp + ' hour%d' % hour_count)
            if '--show-download-speed' in sys.argv:
                show_download_speed()

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
            print(last_newline_inverted + Style.BRIGHT + timedate_stamp + ' day%d%s uptime %s%%, %d outof %d %s' % (day_count, partial, perc, ping_day_ok, ping_day_attempts, ping_fails_str))
            print('windows uptime: "%s"' % get_win_uptime())
            # empty string between days
            print('')
            # reset day counters
            ping_day_attempts = 0
            ping_day_ok = 0

        ping_day_attempts += 1

        result = show_ping(host_to_ping)
        if result:
            ping_day_ok += 1
        else:
            ping_fails += 1
            # don't wait long time for next try
            custom_sleep(10)
            continue

        custom_sleep(60)

if __name__ == "__main__":
    main()
