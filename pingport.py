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

timestamp = time.strftime('%Y%m%d_%H%M%S_pingport.log')
origstdout = sys.stdout
DupeConsoleToFile(timestamp)
print(sys.version)
print(sys.executable)
timestamp = time.strftime('[%Y-%m-%d %H:%M:%S pingport started]')
print(timestamp)
print("press f1 for next ping")

def sleep(i):
	while i:
		win32api.SetConsoleTitle('pingport %d' %i)
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
	perc = 100 * float(part) / float(whole)
	return str(round(perc))

sock = None
timemark_prev = time.time()
ping_hour_attempts = 0
ping_hour_ok = 0
while True:
	timestamp = time.strftime('%H:%M:%S')
	timemark_now = time.time()
	timediff = (timemark_now - timemark_prev) / 3600
	if (timediff >= 1):
		timemark_prev = timemark_now
		perc = percentage(ping_hour_attempts, ping_hour_ok)
		ping_hour_attempts = 0
		ping_hour_ok = 0
		if (timediff >= 2):
			print('%s +%d hours' % (time.strftime('[%Y-%m-%d %H:%M:%S]'), timediff))
		else:
			print(time.strftime('[%Y-%m-%d %H:%M:%S]') + ' hour uptime %s%%' % perc)

	if sock:
		sock.close()
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	
	ping_hour_attempts += 1
	
	# 87.250.250.242 ya.ru
	# 5.255.255.242 ya.ru
	result = sock.connect_ex(('5.255.255.242', 80))
	if result == 0:
		print('%s up' % timestamp)
		ping_hour_ok += 1
	else:
		# 91.198.174.192 wikipedia.org
		# 185.15.59.224 wikipedia.org
		result = sock.connect_ex(('185.15.59.224', 80))
		if result == 0:
			print('%s up2' % timestamp)
			ping_hour_ok += 1
			sleep(5)
			continue
		else:
			print('%s down' % timestamp)
			sleep(5)
			continue

	sleep(60) # 60 slow, 30 fast
