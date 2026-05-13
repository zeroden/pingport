PINGPORT_VERSION = "v0.4"

import socket
import time
import sys
import platform
if platform.system() == "Windows":
    import win32api
    import keyboard
    from colorama import init, Fore, Style
    init(convert=True, autoreset=True)
else:
    # linux
    class Style:
        BRIGHT = ""
        RESET_ALL = ""
    class Fore:
        YELLOW = ""  # yellow
        GREEN  = ""  # green
        RED    = ""  # red
        CYAN   = ""  # cyan
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
import datetime
import psutil
import shutil

PING_FAILS = 0
PING_FAILS_STR = ""
LAST_NEWLINE_INVERTED = ""
ARGS = None
SEND_TELEGRAM_FAILS = 0

STATS = {
    # total ping time for a day
    "day_ping_sum" : 0,
    # total ping counts for a day
    "day_ping_count" : 0,
    # max day ping
    "day_ping_max" : 0,
    # max day ping time
    "day_ping_max_time" : 0,
    # min day ping
    "day_ping_min" : 0,
    # min day ping time
    "day_ping_min_time" : 0,

    # total local speed for a day
    "day_speed_loc_sum" : 0,
    # total local speed counts for a day
    "day_speed_loc_count" : 0,
    # day max local speed
    "day_speed_loc_max" : 0,
    # day max local speed time
    "day_speed_loc_max_time" : 0,
    # day min local speed
    "day_speed_loc_min" : 0,
    # day min local speed time
    "day_speed_loc_min_time" : 0,

    # total global speed for a day
    "day_speed_glo_sum" : 0,
    # total global speed counts for a day
    "day_speed_glo_count" : 0,
    # day max global speed
    "day_speed_glo_max" : 0,
    # day max global speed time
    "day_speed_glo_max_time" : 0,
    # day min global speed
    "day_speed_glo_min" : 0,
    # day min global speed time
    "day_speed_glo_min_time" : 0
}

if platform.system() == "Windows":
    # Get the handle of the current console window
    console_window_handle = ctypes.windll.kernel32.GetConsoleWindow()


def get_active_window_handle():
    # Get the handle of the currently active window
    return ctypes.windll.user32.GetForegroundWindow()


def set_console_title(s):
    if platform.system() == "Windows":
        win32api.SetConsoleTitle("pingport: " + s)


def test_youtube_speed(video_url):
    temp_filename = "temp_video.mp4"
    speed_pattern = re.compile(r"at (\d+\.\d+)MiB/s")

    ydl_opts = {
        "format": "135", # 135 mp4   854x480     25    │    8.28MiB  328k https │ avc1.4D401E    328k video only          480p, mp4_dash
        "noplaylist": True,
        "quiet": False,  # Set to False to capture log messages
        "outtmpl": temp_filename,
        "force_generic_extractor": True,
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
                print("ydl.download() failed [%s]" % e)
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
    url = url + "?x=%s" % anti_cache_stamp

    start_time = time.time()
    try:
        response = requests.get(url, stream=True)
        total_length = response.headers.get("content-length")
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
        print("test_download_speed.requests.get(%s) failed [%s]" % (url, e))
        return 0

    end_time = time.time()
    elapsed_time = end_time - start_time

    down_speed_byte = round(len(data) / elapsed_time, 2)  # Calculate speed based on the data length

    # Explicitly discard the accumulated data
    del data

    return down_speed_byte * 8


def get_nice_timestamp(fmt="%Y-%m-%d %H:%M:%S", t=None):
    t = time.localtime(t)  # use current local time to convert float timestamp to struct_time
    return time.strftime(fmt, t)


def send_telegram_worker(text, parse_mode=None):
    if not ARGS.telegram_update:
        return True

    try:
        # truncated if too long
        max_length = 4096
        if len(text) > max_length:
            text = text[:max_length - 3] + "..."  # Add ellipsis to indicate truncation

        bot_token, bot_chat_id = ARGS.telegram_update.split(";")
        api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {"chat_id": bot_chat_id, "text": text, "disable_web_page_preview": True}
        if parse_mode:
            data["parse_mode"] = parse_mode
        response = requests.post(api_url, data=data)
        if not response.ok:
            print(f"[{get_nice_timestamp()}] ," + f"Telegram error: {response.status_code} - {response.text}")
            return False
        return True
    except Exception as e:
        msg = f"[{get_nice_timestamp()}] ," + f"Error sending Telegram message: {e}"
        print(msg)
        return False


def send_telegram(text, parse_mode=None):
    global SEND_TELEGRAM_FAILS

    if SEND_TELEGRAM_FAILS:
        text += f"\n(tg fails {SEND_TELEGRAM_FAILS})"

    ret = send_telegram_worker(text, parse_mode)
    if not ret:
        print("tg try 2")
        custom_sleep(10)
        ret = send_telegram_worker(text, parse_mode)
        if not ret:
            print("tg try 3")
            custom_sleep(60)
            ret = send_telegram_worker(text, parse_mode)

    if ret:
        SEND_TELEGRAM_FAILS = 0
    else:
        SEND_TELEGRAM_FAILS += 1


def get_hostname():
    return socket.getfqdn()


def show_download_speed(msg = ""):
    global STATS

    if msg:
        msg = "%s, speed: " % msg
    else:
        msg = "speed: "
    print(msg, end="")
    
    ping = ping_host(ARGS.host_to_ping)
    if ping < 0:
        print("ping error")
        return

    print("ping " + Style.BRIGHT + Fore.YELLOW + f"{ping}" + Style.RESET_ALL + "ms", end="")

    url_1 = ARGS.local_url1
    url_2 = ARGS.local_url2
    url_3 = ARGS.global_url1
    url_4 = ARGS.global_url2

    down_speed_1 = test_download_speed(url_1)
    if not down_speed_1:
        print(LAST_NEWLINE_INVERTED + "test_download_speed(url_1) failed")
    down_speed_1 = round(down_speed_1 / 1_000_000, 1)
    down_speed_2 = 0
    if url_2:
        down_speed_2 = test_download_speed(url_2)
        if not down_speed_2:
            print(LAST_NEWLINE_INVERTED + "test_download_speed(url_2) failed")
        down_speed_2 = round(down_speed_2 / 1_000_000, 1)
    down_speed_1_2 = max(down_speed_1, down_speed_2)
    if down_speed_1_2:
        print(", loc " + Style.BRIGHT + Fore.YELLOW + f"{down_speed_1_2}" + Style.RESET_ALL + "mbit", end="")

    down_speed_3 = test_download_speed(url_3)
    if not down_speed_3:
        print(LAST_NEWLINE_INVERTED + "test_download_speed(url_3) failed")
    down_speed_3 = round(down_speed_3 / 1_000_000, 1)
    down_speed_4 = 0
    if url_4:
        down_speed_4 = test_download_speed(url_4)
        if not down_speed_4:
            print(LAST_NEWLINE_INVERTED + "test_download_speed(url_4) failed")
        down_speed_4 = round(down_speed_4 / 1_000_000, 1)
    down_speed_3_4 = max(down_speed_3, down_speed_4)
    if down_speed_3_4:
        print(", glo " + Style.BRIGHT + Fore.YELLOW + f"{down_speed_3_4}" + Style.RESET_ALL + "mbit", end="")

    timedate_stamp = get_nice_timestamp()
    tg_msg = f"{get_hostname()} ▒ ping {ping:>3} ▒ speed {down_speed_1_2:>4} - {down_speed_3_4:>4}"

    # gather speed stats

    STATS["day_speed_loc_sum"] += down_speed_1_2
    STATS["day_speed_loc_count"] += 1
    if down_speed_1_2 > STATS["day_speed_loc_max"]:
        STATS["day_speed_loc_max"] = down_speed_1_2
        STATS["day_speed_loc_max_time"] = datetime.datetime.now()
    if down_speed_1_2 < STATS["day_speed_loc_min"] or not STATS["day_speed_loc_min"]:
        STATS["day_speed_loc_min"] = down_speed_1_2
        STATS["day_speed_loc_min_time"] = datetime.datetime.now()

    STATS["day_speed_glo_sum"] += down_speed_3_4
    STATS["day_speed_glo_count"] += 1
    if down_speed_3_4 > STATS["day_speed_glo_max"]:
        STATS["day_speed_glo_max"] = down_speed_3_4
        STATS["day_speed_glo_max_time"] = datetime.datetime.now()
    if down_speed_3_4 < STATS["day_speed_glo_min"] or not STATS["day_speed_glo_min"]:
        STATS["day_speed_glo_min"] = down_speed_3_4
        STATS["day_speed_glo_min_time"] = datetime.datetime.now()

    down_speed_5 = 0
    if ARGS.enable_yt_speed:
        # {"video_title": "Rick Astley - Never Gonna Give You Up (Official Music Video)"}
        video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        result = test_youtube_speed(video_url)
        down_speed_5 = round(result, 1)
        if not down_speed_5:
            print(LAST_NEWLINE_INVERTED + "test_youtube_speed() failed")
        else:
            print(", yt " + Style.BRIGHT + Fore.YELLOW + f"{down_speed_5}" + Style.RESET_ALL + f"mbit", end="")
            tg_msg += f", yt {down_speed_5}"

    # print newline to done with speed output
    print("")

    # send monospace
    send_telegram("`" + tg_msg + "`", parse_mode="MarkdownV2")

    speed_file = "speed.csv"
    # if speed file not exist create header in it
    if not os.path.exists(speed_file):
        with open(speed_file, "a") as myfile:
            myfile.write("DATETIME,PING,GLOB,LOC,YT\n")
    with open(speed_file, "a") as myfile:
        myfile.write(f"{timedate_stamp},{ping},{down_speed_1_2},{down_speed_3_4},{down_speed_5}\n")

ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
def remove_ansi(text):
    return ansi_escape.sub('', text)
    
def dupe_console_to_file(filepath):
    class Logger(object):
        def __init__(self):
            self.logfile = open(filepath, "ab", 0)
            self.prevstdout = sys.stdout

        def write(self, message):
            self.prevstdout.write(message)
            self.prevstdout.flush()
            message = remove_ansi(message)
            self.logfile.write(message.encode())
            self.logfile.flush()
            global LAST_NEWLINE_INVERTED
            if message and message[-1] == "\n":
                LAST_NEWLINE_INVERTED = ""
            else:
                LAST_NEWLINE_INVERTED = "\n"

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
    return str(round(perc, 2))


def custom_sleep(i):
    while i:
        if PING_FAILS:
            PING_FAILS_STR = " (fails %d)" % PING_FAILS
            set_console_title("%d%s" % (i, PING_FAILS_STR))
        else:
            set_console_title("%d" % i)
        i = i - 1
        j = 10
        while j:
            j = j - 1
            time.sleep(0.1)
            if platform.system() == "Windows":
                if get_active_window_handle() == console_window_handle:
                    # manual ping
                    if keyboard.is_pressed("f1"):
                        print("m", end="")
                        i = 0
                        j = 0
                    # manual speed test
                    elif keyboard.is_pressed("f2"):
                        timedate_stamp = get_nice_timestamp()
                        msg = LAST_NEWLINE_INVERTED + f"[{timedate_stamp}] manual"
                        show_download_speed(msg)


def ping_host(host):
    try:
        if platform.system() == "Windows":
            cmd = ["ping", "-n", "1", host]
        else:
            cmd = ["ping", "-c", "1", host]
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True)
        # Extract the time in ms using regular expressions
        time_match = re.search(r"time[=<](\d+)", output)
        if time_match:
            time_ms = int(time_match.group(1))
            return time_ms
        else:
            return -1  # General failure
    except (subprocess.CalledProcessError, PermissionError, Exception):
        return -1  # General failure


def show_ping(host):
    global STATS

    timedate_stamp = get_nice_timestamp()
    # ping using classical ping
    ret_ping = ping_host(host)
    if ret_ping >= 0:
        STATS["day_ping_sum"] += ret_ping
        STATS["day_ping_count"] += 1
        if ret_ping > STATS["day_ping_max"]:
            STATS["day_ping_max"] = ret_ping
            STATS["day_ping_max_time"] = datetime.datetime.now()
        if ret_ping < STATS["day_ping_min"] or not STATS["day_ping_min"]:
            STATS["day_ping_min"] = ret_ping
            STATS["day_ping_min_time"] = datetime.datetime.now()
        print(Style.BRIGHT + Fore.GREEN + "%d" % ret_ping, end="")
    else:
        print(LAST_NEWLINE_INVERTED + Style.BRIGHT + Fore.RED + "%s ping down %d" % (timedate_stamp, PING_FAILS + 1))

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
        print(Style.BRIGHT + Fore.GREEN + ".", end="");
    else:
        print(LAST_NEWLINE_INVERTED + Style.BRIGHT + Fore.RED + "%s conn down %d" % (timedate_stamp, PING_FAILS + 1))

    # successful only if both type of pings are ok
    return ret_ping >= 0 and ret_sock == 0


def reverse_ip(ip):
    # try reverse lookup
    try:
        hostname = socket.gethostbyaddr(ip)[0]
    except socket.herror:
        # fallback: get fqdn of local ip
        hostname = get_hostname()
    return hostname


def nice_duration(time):
    return str(datetime.timedelta(seconds=int(time)))


def GetCommandLine():
    if platform.system() == "Windows":
        try:
            import win32api
            cmdline = win32api.GetCommandLine()
        except ImportError:
            # fallback if win32api not installed
            cmdline = " ".join(sys.argv)
    else:
        # Linux
        cmdline = " ".join(sys.argv)

    return cmdline


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # use a public IP, Google DNS for example, port doesn't matter
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def get_uptime():
    if platform.system() == "Windows":
        # use Windows API
        # getting the library in which GetTickCount64() resides
        lib = ctypes.windll.kernel32
        # Set the return type to match the expected unsigned 64-bit integer (no negatives values)
        lib.GetTickCount64.restype = ctypes.c_ulonglong
        # calling the function and storing the return value
        t = lib.GetTickCount64()  # milliseconds
        # since the time is in milliseconds i.e. 1000 * seconds
        # therefore truncating the value
        t = int(str(t)[:-3])
    else:
        # Linux: read /proc/uptime
        try:
            with open("/proc/uptime", "r") as f:
                t = float(f.readline().split()[0])  # seconds
                t = int(t)
        except Exception:
            return "uptime unavailable"

    # convert seconds to days, hours, minutes, seconds
    # extracting hours, minutes, seconds & days from t
    # variable (which stores total time in seconds)
    mins, sec = divmod(t, 60)
    hour, mins = divmod(mins, 60)
    days, hour = divmod(hour, 24)

    # formatting the time in readable form
    # (format = x days, HH:MM:SS)
    return f"{days} days, {hour:02}:{mins:02}:{sec:02}"


def human_bytes(num: int) -> str:
    step = 1024.0
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num < step:
            return f"{num:.2f} {unit}"
        num /= step
    return f"{num:.2f} PB"


def get_all_storage_info():
    disks = []

    for part in psutil.disk_partitions(all=False):
        try:
            usage = shutil.disk_usage(part.mountpoint)

            disks.append({
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "total": usage.total,
                "free": usage.free,
                "used": usage.used,
                "total_h": human_bytes(usage.total),
                "free_h": human_bytes(usage.free),
                "used_h": human_bytes(usage.used),
            })

        except PermissionError:
            # some system partitions are not accessible
            continue

    return disks


def get_memory_info():
    mem = psutil.virtual_memory()
    return {
        "total_h": human_bytes(mem.total),
        "free_h": human_bytes(mem.available),
    }


def get_cpu_load_percent():
    return psutil.cpu_percent(interval=1)


def get_platform():
    system = platform.system()

    if system == "Windows":
        try:
            return subprocess.check_output(
                ["powershell", "-Command", "Get-CimInstance Win32_Processor | Select-Object -ExpandProperty Name"],
                text=True
            ).strip()
        except:
            return os.popen("wmic cpu get name").read().split("\n")[1].strip()

    if system == "Linux":
        try:
            with open("/proc/device-tree/model") as f:
                return f.read().strip("\x00")
        except:
            pass
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if "model name" in line:
                        return line.split(":", 1)[1].strip()
        except:
            pass

        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if "model name" in line:
                        return line.split(":", 1)[1].strip()
        except:
            pass

    return platform.processor() or "Unknown CPU"


def get_linux_os():
    os_name = "Unknown"
    debian_ver = ""

    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("PRETTY_NAME"):
                    os_name = line.split("=", 1)[1].strip().strip('"')
    except:
        pass

    try:
        with open("/etc/debian_version") as f:
            debian_ver = f.read().strip()
    except:
        pass

    extra = f" | Debian {debian_ver}" if debian_ver else ""
    return f"{os_name}{extra} | Kernel {platform.release()} | Arch {platform.machine()}"


def get_windows_os():
    # More detailed Windows version string
    ver = platform.version()
    rel = platform.release()
    win = platform.system()

    # Optional: more precise build info
    try:
        build = platform.win32_ver()[1]
        return f"{win} {rel} (build {build})"
    except:
        return f"{win} {rel} | Version {ver}"

def get_os():
    if os.name == "posix":
        osinfo = get_linux_os()
    elif os.name == "nt":
        osinfo = get_windows_os()
    else:
        osinfo = "Unknown OS"

    return osinfo


def get_system_info(extended = True):

    s = f"{get_hostname()} uptime: {get_uptime()}\n"
    if extended:
        s += f"platform: {get_platform()}\n"
        s += f"os: {get_os()}\n"
    s += "storage:\n"
    disks = get_all_storage_info()
    for d in disks:
        s += f"{d['device']} ({d['mountpoint']}) [{d['fstype']}] - total {d['total_h']}, free {d['free_h']}\n"

    mem = get_memory_info()
    s += f"memory: total {mem['total_h']}, free {mem['free_h']}\n"

    cpu = get_cpu_load_percent()
    s += f"cpu: {cpu:.0f}%"

    return s


def main():
    global PING_FAILS, ARGS, STATS

    parser = argparse.ArgumentParser()
    parser.add_argument("--host-to-ping", help="Host for ping", required=True)
    parser.add_argument("--local-url1", help="Local speed test URL", required=True)
    parser.add_argument("--local-url2", help="Local speed test URL 2 (optional)")
    parser.add_argument("--global-url1", help="Global speed test URL", required=True)
    parser.add_argument("--global-url2", help="Global speed test URL 2 (optional)")
    parser.add_argument("--enable-yt-speed", action="store_true", help="Enable youtube speed test (optional)")
    parser.add_argument("--telegram-update", help="Send data to telegram bot (optional)")
    parser.add_argument("--offline-short-cmd", help="Run command on short offline time (optional)")
    parser.add_argument("--offline-long-cmd", help="Run command on long offline time (optional)")
    parser.add_argument("--offline-short-timeout", help="Short offline command timeout in seconds (optional)", type=int, default=300)
    parser.add_argument("--offline-long-timeout", help="Long offline command timeout in seconds (optional)", type=int, default=3600)
    ARGS = parser.parse_args()

    logfilename = get_nice_timestamp("pingport_%Y%m%d_%H%M%S.log")
    dupe_console_to_file(logfilename)
    timedate_stamp = get_nice_timestamp("[%Y-%m-%d %H:%M:%S]")
    hostname = get_hostname()

    tg_msg = (s := f"pingport {PINGPORT_VERSION} started @ {hostname}") + "\n"
    print(Style.BRIGHT + Fore.CYAN + timedate_stamp + " " + s)

    tg_msg += (s := f"python version: \"{sys.version}\"") + "\n"
    print(s)
    tg_msg += (s := f"python path: \"{sys.executable}\"") + "\n"
    print(s)
    print(f"cmdl: <{GetCommandLine()}>")
    tg_msg += (s := f"log: \"{logfilename}\"") + "\n"
    print(s)
    tg_msg += (s := f"hostname: {hostname}") + "\n"
    print(s)
    tg_msg += (s := f"host to ping: \"{ARGS.host_to_ping}\"") + "\n"
    print(s)
    try:
        host_to_ping_ip = socket.gethostbyname(ARGS.host_to_ping)
        tg_msg += (s := f"host to ping ip: \"{host_to_ping_ip}\"") + "\n"
        print(s)
        tg_msg += (s := f"host to ping ip reverse: \"{reverse_ip(host_to_ping_ip)}\"") + "\n"
        print(s)
    except Exception as e:
        tg_msg += (s := f"host to ping ip: failed - {str(e)}") + "\n"
        print(s)
    loc_ip = get_local_ip()
    tg_msg += (s := f"local ip: \"{loc_ip}\"") + "\n"
    print(s)
    tg_msg += (s := f"local ip reverse: \"{reverse_ip(loc_ip)}\"") + "\n"
    print(s)
    try:
        wan_ip = get("https://api.ipify.org").content.decode("utf8")
        tg_msg += (s := f"wan ip: \"{wan_ip}\"") + "\n"
        print(s)
        tg_msg += (s := f"wan ip reverse: \"{reverse_ip(wan_ip)}\"") + "\n"
        print(s)
        ip2isp_fn = "dbip-asn-lite-2024-07.mmdb"
        if os.path.exists(ip2isp_fn):
            with maxminddb.open_database(ip2isp_fn) as reader:
                rec = reader.get(wan_ip)
                tg_msg += (s := f"isp: \"{rec['autonomous_system_organization']}\"") + "\n"
                print(s)
    except Exception as e:
        tg_msg += (s := f"wan ip: failed - {str(e)}") + "\n"
        print(s)

    # Insert in url a character that is invisible to humans, but breaks Telegram’s link detection
    # The most useful one is: zero width space → \u200b
    tg_msg = tg_msg.replace(".", ".\u200b")
    send_telegram(timedate_stamp + " " + tg_msg)

    if ARGS.offline_short_cmd:
        print(f"offline short command: [{ARGS.offline_short_cmd}]")
        print(f"offline short timeout: {ARGS.offline_short_timeout}")
    if ARGS.offline_long_cmd:
        print(f"offline long command: [{ARGS.offline_long_cmd}]")
        print(f"offline long timeout: {ARGS.offline_long_timeout}")

    sys_info = get_system_info()
    print(sys_info)
    timedate_stamp = get_nice_timestamp("[%Y-%m-%d %H:%M:%S]")
    send_telegram(timedate_stamp + " " + sys_info)
    if platform.system() == "Windows":
        print("Press F1 for a manual ping, F2 for manual speed test\n")
    show_download_speed()

    last_60min_mark = time.time()
    last_24hours_mark = time.time()
    offline_short_cmd_executed = False
    offline_long_cmd_executed = False
    first_offline_time = 0
    hour_count = 0
    day_count = 0
    day_ping_attempts = 0
    day_ping_ok = 0

    while True:
        timedate_stamp = get_nice_timestamp("[%Y-%m-%d %H:%M:%S]")
        current_time = time.time()

        # Check if 60 minutes have passed
        hours_passed = (current_time - last_60min_mark) / 3600
        if hours_passed >= 1:
            last_60min_mark = current_time
            hour_count += 1
            if hours_passed >= 2:
                hours_msg = "+%d hours slept" % hours_passed
                print(LAST_NEWLINE_INVERTED + Style.BRIGHT + hours_msg)
                print("\n\n\n")
                hours_msg += " (%s)" % hostname
                send_telegram(hours_msg)
                # wait some time after unsleep to allow network up
                custom_sleep(10)
            msg = LAST_NEWLINE_INVERTED + timedate_stamp + " hour%d" % hour_count
            show_download_speed(msg)

        # Check if 24 hours have passed
        # print day stat
        #if current_time - last_24hours_mark >= 24 * 60 * 60:
        if current_time - last_24hours_mark >= 1 * 60 * 60:
            # reset day marker
            last_24hours_mark = current_time
            day_count += 1
            perc = get_percentage(day_ping_attempts, day_ping_ok)
            partial = ""
            if day_ping_attempts != day_ping_ok:
                partial = "partial "
            day_msg_pre = f"{timedate_stamp} {get_hostname()} day{day_count}\n"
            print(LAST_NEWLINE_INVERTED + Style.BRIGHT + "\n" + day_msg_pre, end = "")
            day_msg = f"up: {partial}{perc}%, {day_ping_ok}/{day_ping_attempts} {PING_FAILS_STR}\n"
            day_avg_ping = round(STATS["day_ping_sum"] / STATS["day_ping_count"])
            day_avg_speed_loc = round(STATS["day_speed_loc_sum"] / STATS["day_speed_loc_count"], 1)
            day_avg_speed_glo = round(STATS["day_speed_glo_sum"] / STATS["day_speed_glo_count"], 1)
            day_msg += f"avg ping: {day_avg_ping}\n"
            if STATS['day_ping_max']:
                day_msg += f"max ping: {STATS['day_ping_max']} @ {STATS['day_ping_max_time'].strftime('%H:%M')}\n"
            if STATS['day_ping_min']:
                day_msg += f"min ping: {STATS['day_ping_min']} @ {STATS['day_ping_min_time'].strftime('%H:%M')}\n"
            day_msg += f"avg speed: {day_avg_speed_loc} / {day_avg_speed_glo}\n"
            if STATS['day_speed_loc_max']:
                day_msg += f"max loc speed: {STATS['day_speed_loc_max']} @ {STATS['day_speed_loc_max_time'].strftime('%H:%M')}\n"
            if STATS['day_speed_loc_min']:
                day_msg += f"min loc speed: {STATS['day_speed_loc_min']} @ {STATS['day_speed_loc_min_time'].strftime('%H:%M')}\n"
            if STATS['day_speed_glo_max']:
                day_msg += f"max glo speed: {STATS['day_speed_glo_max']} @ {STATS['day_speed_glo_max_time'].strftime('%H:%M')}\n"
            if STATS['day_speed_glo_min']:
                day_msg += f"min glo speed: {STATS['day_speed_glo_min']} @ {STATS['day_speed_glo_min_time'].strftime('%H:%M')}\n"
            day_msg += get_system_info(extended = False)
            print(day_msg + "\n")
            send_telegram(day_msg_pre + day_msg)

            # reset day counters
            day_ping_attempts = 0
            day_ping_ok = 0
            STATS["day_ping_sum"] = 0
            STATS["day_ping_count"] = 0
            STATS["day_speed_loc_sum"] = 0
            STATS["day_speed_loc_count"] = 0
            STATS["day_speed_glo_sum"] = 0
            STATS["day_speed_glo_count"] = 0
            STATS['day_ping_max'] = 0
            STATS['day_ping_min'] = 0
            STATS['day_speed_loc_max'] = 0
            STATS['day_speed_glo_max'] = 0
            STATS['day_speed_loc_min'] = 0
            STATS['day_speed_glo_min'] = 0

        day_ping_attempts += 1

        result = show_ping(ARGS.host_to_ping)
        # ping ok
        if result:
            day_ping_ok += 1
            if first_offline_time:
                offline_msg = f"[{get_nice_timestamp(t=first_offline_time)}] {hostname} offline\n"
                offline_time_dur_raw = current_time - first_offline_time
                # reset offline period
                first_offline_time = 0
                # reset offline commands
                offline_short_cmd_executed = False
                offline_long_cmd_executed = False
                offline_time_dur_nice = nice_duration(offline_time_dur_raw)
                offline_msg += f"{timedate_stamp} online, downtime {offline_time_dur_nice}"
                print("\n" + offline_msg)
                send_telegram(offline_msg)
        # in case of ping fail check if offline command needed
        else:
            PING_FAILS += 1

            # we now offline so init first offline time
            if not first_offline_time:
                first_offline_time = current_time

            # after some offline time exec cmds
            if ARGS.offline_short_cmd and not offline_short_cmd_executed and current_time - first_offline_time >= ARGS.offline_short_timeout:
                print(f"short offline command activated [{ARGS.offline_short_cmd}]")
                # exec cmd only once for each offline period
                offline_short_cmd_executed = True
                # exec cmd
                subprocess.Popen(ARGS.offline_short_cmd, shell=True)
            if ARGS.offline_long_cmd and not offline_long_cmd_executed and current_time - first_offline_time >= ARGS.offline_long_timeout:
                print(f"long offline command activated [{ARGS.offline_long_cmd}]")
                # exec cmd only once for each offline period
                offline_long_cmd_executed = True
                # exec cmd
                subprocess.Popen(ARGS.offline_long_cmd, shell=True)

            # if ping failed don't wait long time for next try
            custom_sleep(30)
            continue

        # next good ping timeout
        custom_sleep(120)


if __name__ == "__main__":
    main()
