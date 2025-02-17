import logging
import os
from time import strftime, gmtime

from pymobiledevice.lockdown import LockdownClient

from pprint import *

SB_PORTRAIT = 1
SB_PORTRAIT_UPSIDE_DOWN = 2
SB_LANDSCAPE = 3
SB_LANDSCAPE_HOME_TO_LEFT = 4


class SBServiceClient(object):

    service = None
    def __init__(self, lockdown = None, udid=None, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.lockdown = lockdown if lockdown else LockdownClient(udid=udid)
        if not self.lockdown:
            raise Exception("Unable to start lockdown")
        self.start()

    def start(self):
        self.service = self.lockdown.startService("com.apple.springboardservices")
        if not self.service:
            raise Exception("SBService init error : Could not start com.apple.springboardservices")


    def get_icon_state(self, format_version="2"):
        cmd = { "command": "getIconState" }
        if format_version:
            cmd["formatVersion"] = format_version

        self.service.sendPlist(cmd)
        res = self.service.recvPlist()
        return res


    def set_icon_state(self, newstate={}):
        cmd = { "command": "setIconState",
                "iconState": newstate }

        self.service.sendPlist(cmd)


    def get_icon_pngdata(self, bid):
        cmd = { "command": "getIconPNGData",
                "bundleId": bid }

        self.service.sendPlist(cmd)
        res = self.service.recvPlist()
        pngdata = res.get("pngData")
        if res:
            return pngdata
        return None

    def get_interface_orientation(self):
        cmd = { "command": "getInterfaceOrientation" }
        self.service.sendPlist(cmd)
        res = self.service.recvPlist()
        return res.get('interfaceOrientation')


    def get_wallpaper_pngdata(self):
        cmd = { "command": "getHomeScreenWallpaperPNGData" }
        self.service.sendPlist(cmd)
        res = self.service.recvPlist()
        if res:
            return res.get("pngData")
        return None



def mySave(image_data):
    if image_data:
        image_dir = os.path.expanduser("~/Downloads/Screenshots")
        if not os.path.exists(image_dir):
            os.makedirs(image_dir)
        filename = strftime('image-%Y-%m-%d-%H-%M-%S.png', gmtime())
        outPath = os.path.join(image_dir, filename)

        print('Saving image at %s' % outPath)
        with open(outPath, 'wb') as o:
            o.write(image_data)


if __name__ == "__main__":
    s = SBServiceClient()

    # icon_data = s.get_icon_pngdata("com.apple.weather")
    # wallpaper_data = s.get_wallpaper_pngdata()
    # mySave(icon_data)
    # mySave(wallpaper_data)

    icon_state = s.get_icon_state()
    pprint(icon_state)

    interface_orientation = s.get_interface_orientation()
    pprint(interface_orientation)
