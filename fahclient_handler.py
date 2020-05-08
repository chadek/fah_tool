import os
import time
import multiprocessing
import argparse
import syslog
import glob

class FahClient:
    def __init__(self):
        self.delai = 1200
        self.timer = time.time()-self.delai

    def IsRunning(self):
    #useless in our case but this is a nice way to list all runnig processes
#        running_processes = []
        pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]
        for pid in pids:
            try:
                cmdline = open(os.path.join('/proc', pid, 'cmdline'), 'rb').read()
            except IOError: # proc has already terminated
                continue

            for cmd_element in cmdline.split(b'\00'):
                if cmd_element != b'':
                    for item in cmd_element.split(b' '):
                        if item.startswith(b'/usr/bin/FAHClient'):
                            return True
                            #useless in our case but this is a nice way to list all runnig processes
#                            running_processes.append(item)
        return False

    def Start(self):
        if self.timer+self.delai > time.time():
            syslog.syslog(syslog.LOG_INFO,"won't start until we aren't off at least for {} sec".format(self.delai))
            return False
        if self.IsRunning():
            if os.system("systemctl is-active --quiet fahclient") != 0:
                syslog.syslog(syslog.LOG_WARNING, "fahclient is runnig, but systemd think it is not")
            else:
                syslog.syslog(syslog.LOG_INFO, "Fahclient already runnig, ignoring start request")
            return True

        if os.system("systemctl start fahclient") != 0:
            if not self.IsRunning():
                syslog.syslog(syslog.LOG_ERR, "Systemd think it wasn't able to start fahclient but a fahclient process is currently running")
            else:
                syslog.syslog(syslog.LOG_ERR, "Failed to start fahclient")
            return False
        self.timer = time.time()
        return True

    def Stop(self):
        if self.timer+self.delai > time.time():
            syslog.syslog(syslog.LOG_INFO,"won't stop until we aren't off at least for {} sec".format(self.delai))
            return False
        if not self.IsRunning():
            if os.system("systemctl is-active --quiet fahclient") == 0:
                syslog.syslog(syslog.LOG_WARNING, "fahclient is not runnig, but systemd think it is")
            else:
                syslog.syslog(syslog.LOG_INFO, "Fahclient is already stopped, ignoring stop request")
            return True

        if os.system("systemctl stop fahclient") != 0:
            if self.IsRunning():
                syslog.syslog(syslog.LOG_ERR, "Systemd thinks it wasn't able to stop fahclient but not fahclient process is currently running")
            else:
                syslog.syslog(syslog.LOG_ERR, "Failed to stop fahclient")
            return False
        self.timer = time.time()
        return True

class LoadMonitor:
    cpu_count = -1
    def __init__(self):
        try:
            self.file = open("/proc/loadavg")
        except Exception as e:
            syslog.syslog(syslog.LOG_ERR, "failed to open /proc/loadavg: {}".format(e))
            raise e

        try:
            self.cpu_count = multiprocessing.cpu_count()
        except Exception as e:
            syslog.syslog(syslog.LOG_ERR, "failed to get cpu count: {}".format(e))
            raise e

    def Average(self):
        # seek to the beginning of the file
        self.file.seek(0)
        contents = self.file.read()
        # split on whitespace
        fields = contents.split(' ', 3)

        return (float(fields[0]) / self.cpu_count,
                float(fields[1]) / self.cpu_count,
                float(fields[2]) / self.cpu_count)

class TempMonitor:
    # def __init__(self):
    #     self.temperature=0

    def GetTemp(self):
        temp_files = glob.glob("/sys/class/thermal/thermal_zone*/temp")
        current_temp = 0
        for file in temp_files:
            try:
                tmp = int(open(file).read())
            except Exception as e:
                syslog.syslog(syslog.LOG_ERR, "failed to open {}: {}".format(file,e))
                raise e
            if tmp > current_temp:
                 current_temp = tmp
        return int(current_temp/1000)


class FahclientHandler:
    def __init__(self, load, temperature):
        syslog.openlog(ident="fahclient_handler",
                        logoption=syslog.LOG_PID,
                        facility=syslog.LOG_LOCAL0)

        if isinstance(load, float):
            raise Exception("Load argument is not a float: percentage of available cpu load usually between 0 and 1")

        if isinstance(temperature, int):
            raise Exception("Temperature argument is not an int, representing a celsius temperature")

        self.load = float(load)
        self.temperature = int(temperature)

        # create monitor
        self.load_monitor = LoadMonitor()
        self.temp_monitor = TempMonitor()
        self.fahclient = FahClient()

    def Run(self):
        syslog.syslog(syslog.LOG_INFO, "fahclient_handler started")

        time.sleep(5)

        while True:
            _,_,load = self.load_monitor.Average()
            temperature = self.temp_monitor.GetTemp()
            if load > self.load:
                self.fahclient.Stop()
            elif temperature > self.temperature:
                self.fahclient.Stop()
            else:
                if not self.fahclient.IsRunning():
                    self.fahclient.Start()
            time.sleep(60)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--load', default=0.7, help='15min load limit before stopping fahclient')
    parser.add_argument('-t', '--temp', default=95, help='cpu temperature limit (celcius) before stopping fahclient')
    args = parser.parse_args()

    handler = FahclientHandler(args.load, args.temp)

    handler.Run()
