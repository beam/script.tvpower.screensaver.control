import os,sys
import xbmc, xbmcaddon
import time
import subprocess

def log(message):
    xbmc.log("### TV power controller: " + str(message), level=xbmc.LOGNOTICE)

class TVPowerContorl(object):

    target_time_for_execution = 0
    at_least_ones_player_launched = False

    def __init__(self, addon, monitor, external_run = False):
        self.addon = addon
        self.monitor = monitor
        self.external_run = external_run
        self.load_settings()

    def load_settings(self):
        log("loading settings")
        self.turn_off_activated = self.addon.getSetting("turn_off_activated") == 'true'
        self.turn_off_after = int(self.addon.getSetting("turn_off_wait_time"))
        self.stop_player_on_turn_off = self.addon.getSetting("turn_off_stop") == 'true'
        self.stop_player_on_turn_off_last_at = 0

        self.turn_off_action = self.addon.getSetting("turn_off_action")
        self.turn_off_player_ones_launched = self.addon.getSetting("turn_off_player_ones_launched") == 'true'

        self.turn_on_deactivated = self.addon.getSetting("turn_on_deactivated") == 'true'
        self.turn_on_player_start = self.addon.getSetting("turn_on_player") == 'true'

        self.cec_method = self.addon.getSetting("cec_method")
        self.cec_client_command = self.addon.getSetting("cec_client_path")

        self.suppress_wake_up = int(self.addon.getSetting("suppress_wake_up"))

    def hook_stop_player(self):
        log(["stop player",self.stop_player_on_turn_off])
        if self.stop_player_on_turn_off == False: return False
        if xbmc.Player().isPlaying() == True:
            xbmc.Player().stop()
            self.stop_player_on_turn_off_last_at = time.time()
        return True

    def hook_turn_off_action(self):
        log(["turn off post action", self.turn_off_action])
        if self.turn_off_action == "none": return False

        while self.scan_running():
            log(["scan running","waiting"])
            time.sleep(10)

        if self.turn_off_action == "restart":
            xbmc.executebuiltin('XBMC.RestartApp()')
        elif self.turn_off_action == "quit":
            xbmc.executebuiltin('XBMC.Quit()')
        elif self.turn_off_action == "reboot":
            xbmc.restart()
        elif self.turn_off_action == "shutdown":
            xbmc.shutdown()

        return True

    def turn_off_tv(self):
        log(["turn_off_tv", self.turn_off_activated])
        if self.external_run == False:
            if self.turn_off_activated == False: return False
            if self.turn_off_player_ones_launched == True and self.at_least_ones_player_launched == False:
                log(["skipping", "player wasn't launched"])
                return False

        # do action
        if self.cec_method == "kodi":
            xbmc.executebuiltin('XBMC.CECStandby()')
        elif self.cec_method == "cec-client":
            subprocess.call("echo 'standby 0' | " + self.cec_client_command + " -s", shell=True)

        self.hook_stop_player()
        self.hook_turn_off_action()
        return True

    def turn_on_tv(self):
        log(["turn_on_tv", self.turn_on_deactivated])
        if self.external_run == False:
            if self.turn_on_deactivated == False: return False
            
        # do action
        if self.cec_method == "kodi":
            xbmc.executebuiltin('XBMC.CECActivateSource()')
        elif self.cec_method == "cec-client":
            subprocess.call("echo 'on 0' | " + self.cec_client_command + " -s", shell=True)

        return True

    def execute_command(self, event):
        log(["Execute", event])
        if event == "screen_saver_activated_target_time_ago":
            self.turn_off_tv()
        elif event == "screen_saver_deactivated":
            if self.suppress_wake_up != 0 and (self.stop_player_on_turn_off_last_at + self.suppress_wake_up) > time.time():
                log("suppressing wake up actions")
                self.stop_player_on_turn_off_last_at = 0
                xbmc.executebuiltin("XBMC.ActivateScreensaver()")
                log("screensaver activated again")
            else:
                self.turn_on_tv()
        elif event == "player_stared":
            self.at_least_ones_player_launched = True
            if self.turn_on_player_start == True: self.turn_on_tv()

        # screen_saver_activated
        # screen_saver_deactivated
        # screen_saver_activated_target_time_ago
        # player_stared

    def check_monitor(self, event = None):
        if self.monitor == None: return False
        if event != None: self.execute_command(event)
        if event == "screen_saver_activated": self.target_time_for_execution = time.time() + (self.turn_off_after * 60)

        if self.monitor.screensaver_running == True and self.target_time_for_execution > 0 and self.target_time_for_execution <= time.time():
            self.target_time_for_execution = 0
            self.execute_command("screen_saver_activated_target_time_ago")

    def scan_running(self):
        #check if any type of scan is currently running
        if(xbmc.getCondVisibility('Library.IsScanningVideo') or xbmc.getCondVisibility('Library.IsScanningMusic')):
            return True
        else:
            return False
