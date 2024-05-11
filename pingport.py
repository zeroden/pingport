import socket
import time
import sys
import win32api
import keyboard

def DupeConsoleToFile(filepath):
	class Logger(object):
		def __init__(self):
			self.logfile = open(filepath, 'ab', 0)
			self.prevstdout = sys.stdout

		def write(self, message):
			self.prevstdout.write(message)
			self.prevstdout.flush()
			self.logfile.write(message.encode())
			self.logfile.flush()

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

logfilename = time.strftime('%Y%m%d_%H%M%S_pingport.log')
DupeConsoleToFile(logfilename)
timedate_stamp = time.strftime('[%Y-%m-%d %H:%M:%S]')
print(time.strftime(timedate_stamp + ' pingport started'))
print('python version: "%s"' % sys.version)
print('python path: "%s"' % sys.executable)
print("Press F1 for a manual ping")

ping_series_ok = 0
ping_fails = 0
ping_fails_str = ''

def sleep(i):
	while i:
		if ping_fails:
			ping_fails_str = ' (fails %d)' % ping_fails
			win32api.SetConsoleTitle('pingport %d%s' % (i, ping_fails_str))
		else:
			win32api.SetConsoleTitle('pingport %d' % i)
		i = i - 1
		j = 10
		while j:
			j = j - 1
			time.sleep(0.1)
			if (keyboard.is_pressed('f1')):
				print('next ping')
				i = 0
				j = 0

def percentage(whole, part):
	if whole:
		perc = 100 * float(part) / float(whole)
	else:
		perc = 0
	return str(round(perc))

sock = None
timemark_prev_hour = time.time()
timemark_prev_day = time.time()
ping_hour_attempts = 0
ping_day_attempts = 0
ping_hour_ok = 0
ping_day_ok = 0
while True:
	time_stamp = time.strftime('%H:%M:%S')
	timedate_stamp = time.strftime('[%Y-%m-%d %H:%M:%S]')
	timemark_now = time.time()

	# print hour stat
	timediff = (timemark_now - timemark_prev_hour) / 3600
	if (timediff >= 1):
		# reset hour marker
		timemark_prev_hour = timemark_now
		perc = percentage(ping_hour_attempts, ping_hour_ok)
		if (timediff >= 2):
			print(timedate_stamp + ' +%d hours' % timediff)
		else:
			partial = ''
			if ping_hour_attempts != ping_hour_ok:
				partial = ' partial'
			print(timedate_stamp + ' hour%s uptime %s%%, %d outof %d %s' % (partial, perc, ping_hour_ok, ping_hour_attempts, ping_fails_str))
		# reset hour counters
		ping_hour_attempts = 0
		ping_hour_ok = 0

	# print day stat
	timediff = (timemark_now - timemark_prev_day) / 3600
	if (timediff >= 24):
		# reset day marker
		timemark_prev_day = timemark_now
		perc = percentage(ping_day_attempts, ping_day_ok)
		partial = ''
		if ping_day_attempts != ping_day_ok:
			partial = ' partial'
		print(timedate_stamp + ' day%s uptime %s%%, %d outof %d %s' % (partial, perc, ping_day_ok, ping_day_attempts, ping_fails_str))
		# reset day counters
		ping_day_attempts = 0
		ping_day_ok = 0

	if sock:
		sock.close()
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	
	ping_hour_attempts += 1
	ping_day_attempts += 1
	
	# 5.255.255.242 ya.ru
	result = sock.connect_ex(('5.255.255.242', 80))
	if result == 0:
		ping_hour_ok += 1
		ping_day_ok += 1
		ping_series_ok += 1
		print('%s up %d' % (time_stamp, ping_series_ok))
	else:
		# 185.15.59.224 wikipedia.org
		result = sock.connect_ex(('185.15.59.224', 80))
		if result == 0:
			ping_hour_ok += 1
			ping_day_ok += 1
			ping_series_ok += 1
			print('%s up2 %d' % (time_stamp, ping_series_ok))
			sleep(10)
			continue
		else:
			ping_fails += 1
			ping_series_ok = 0
			print('%s down %d' % (timedate_stamp, ping_fails))
			sleep(10)
			continue

	sleep(60)
