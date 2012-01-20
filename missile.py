#!/usr/bin/env python
#
#  Written by: Scott Weston <scott@weston.id.au>
#
# - Version --------------------------------------------------------------
#
#  $Id: missile.py,v 1.13 2006/07/25 17:01:24 scott Exp $
#
# - License --------------------------------------------------------------
#
# Copyright (c) 2006, Scott Weston
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
# 
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
# * The name of the contributors may not be used to endorse or promote
#   products derived from this software without specific prior written
#   permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER
# OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# - Change Log -----------------------------------------------------------
#
#  $Log: missile.py,v $
#  Revision 1.13  2006/07/25 17:01:24  scott
#  Bug fix (no default execution, missing usage text)
#  as reported by: Petter Reinholdtsen
#
#  Revision 1.12  2006/07/07 18:23:20  scott
#  comment out the noisey bits and leave it to users to enable if they so fit
#
#  Revision 1.11  2006/07/07 18:19:22  scott
#  fix rcs history
#
#  Revision 1.10  2006/07/07 18:17:48  scott
#  some fixes for better network control
#
#  Revision 1.9  2006/06/07 17:19:15  scott
#  oops, forgot the -n in the usage
#
#  Revision 1.8  2006/06/07 17:17:36  scott
#  added support for a -n network mode
#  allows for control by simple udp packets
#
#  Revision 1.7  2006/05/29 13:27:54  scott
#  added support for multiple missiles
#
#  Revision 1.6  2006/04/17 18:25:02  scott
#  changed warning message for more comedic value
#
#  Revision 1.5  2006/03/17 15:39:21  scott
#  added bsd license
#
#  Revision 1.4  2006/01/26 16:28:09  scott
#  better exception handling
#
#  Revision 1.3  2006/01/26 15:03:01  scott
#  added command line arguments (ready for more)
#  cleaned up display class
#
#  Revision 1.2  2006/01/26 14:27:55  scott
#  added more useful RCS tags
#
#
import usb
import exceptions
import urwid
import urwid.curses_display
import sys
import getopt
import random
import re
import os
from time import sleep, time
from socket import *

class MissileDevice:
  INITA     = (85, 83, 66, 67,  0,  0,  4,  0)
  INITB     = (85, 83, 66, 67,  0, 64,  2,  0)
  CMDFILL   = ( 8,  8,
                0,  0,  0,  0,  0,  0,  0,  0,
                0,  0,  0,  0,  0,  0,  0,  0,
                0,  0,  0,  0,  0,  0,  0,  0,
                0,  0,  0,  0,  0,  0,  0,  0,
                0,  0,  0,  0,  0,  0,  0,  0,
                0,  0,  0,  0,  0,  0,  0,  0,
                0,  0,  0,  0,  0,  0,  0,  0)
  STOP      = ( 0,  0,  0,  0,  0,  0)
  LEFT      = ( 0,  1,  0,  0,  0,  0)
  RIGHT     = ( 0,  0,  1,  0,  0,  0)
  UP        = ( 0,  0,  0,  1,  0,  0)
  DOWN      = ( 0,  0,  0,  0,  1,  0)
  LEFTUP    = ( 0,  1,  0,  1,  0,  0)
  RIGHTUP   = ( 0,  0,  1,  1,  0,  0)
  LEFTDOWN  = ( 0,  1,  0,  0,  1,  0)
  RIGHTDOWN = ( 0,  0,  1,  0,  1,  0)
  FIRE      = ( 0,  0,  0,  0,  0,  1)

  def __init__(self, battery):
    try:
      self.dev=UsbDevice(0x1130, 0x0202, battery)
      self.dev.open()
      self.dev.handle.reset()
    except NoMissilesError, e:
      raise NoMissilesError()

  def move(self, direction):
    self.dev.handle.controlMsg(0x21, 0x09, self.INITA, 0x02, 0x01)
    self.dev.handle.controlMsg(0x21, 0x09, self.INITB, 0x02, 0x01)
    self.dev.handle.controlMsg(0x21, 0x09, direction+self.CMDFILL, 0x02, 0x01)

class NoMissilesError(Exception): pass

class UsbDevice:
  def __init__(self, vendor_id, product_id, skip):
    busses = usb.busses()
    self.handle = None
    count = 0
    for bus in busses:
      devices = bus.devices
      for dev in devices:
        if dev.idVendor==vendor_id and dev.idProduct==product_id:
          if count==skip:
            self.dev = dev
            self.conf = self.dev.configurations[0]
            self.intf = self.conf.interfaces[0][0]
            self.endpoints = []
            for endpoint in self.intf.endpoints:
              self.endpoints.append(endpoint)
            return
          else:
            count=count+1
    raise NoMissilesError()

  def open(self):
    if self.handle:
      self.handle = None
    self.handle = self.dev.open()
    self.handle.detachKernelDriver(0)
    self.handle.detachKernelDriver(1)
    self.handle.setConfiguration(self.conf)
    self.handle.claimInterface(self.intf)
    self.handle.setAltInterface(self.intf)

class MissileDisplay:
  palette = [ ('body', 'black', 'dark cyan', 'standout'),
              ('footer','light gray', 'dark blue'),
              ('header', 'white', 'dark blue', 'underline'),
              ('important','white', 'dark red', 'bold'),
              ('key', 'light cyan', 'black', 'underline'),
              ('title', 'white', 'black',), ]

  BLANK   = urwid.Text("")
  WARNING = urwid.Text([('important',"CAUTION: AIM AWAY FROM FACE")],
                       align='center')
  HEADER  = urwid.AttrWrap(urwid.Text("MISSILE COMMAND!", align='center'),
                           'header')
  FOOTER  = urwid.AttrWrap(urwid.Text("scott@weston.id.au", align='center'),
                           'footer')
  CONTENT = [ BLANK,
              urwid.Text(["Use the following\n"
                          "keys  to move\n\n"
                          "Q   W   E \n"
                          "  \ | /   \n"
                          "A -(S)- D \n"
                          "  / | \   \n"
                          "Z   X   C \n\n"
                          "F to fire all guns once\n"
                          "R for rapid sequentual fire of all missiles\n"
                          "S to Stop\n"
                          "ESC to Exit\n\n",], align='center'),
              WARNING,
              BLANK, ]

  def __init__(self):
    self.listbox = urwid.ListBox(self.CONTENT)
    view = urwid.AttrWrap(self.listbox, 'body')
    self.view = urwid.Frame(view, header=self.HEADER, footer=self.FOOTER)

  def main(self):
    self.ui = urwid.curses_display.Screen()
    self.ui.register_palette(self.palette)
    self.ui.run_wrapper(self.run)

  def run(self):
    md = []
    for missiles in range(10):
      try:
        md.append(MissileDevice(missiles))
      except NoMissilesError, e:
        break
    if missiles==0:
      raise NoMissilesError
    size = self.ui.get_cols_rows()
    while 1:
      canvas = self.view.render(size, focus=1)
      self.ui.draw_screen(size, canvas)
      keys = None
      while not keys:
        keys = self.ui.get_input()
      for k in keys:
        if k == 'window resize':
          size = self.ui.get_cols_rows()
        elif k in ('w', 'up'):
          for m in md:
            m.move(MissileDevice.UP)
        elif k in ('x', 'down'):
          for m in md:
            m.move(MissileDevice.DOWN)
        elif k in ('a', 'left'):
          for m in md:
            m.move(MissileDevice.LEFT)
        elif k in ('d', 'right'):
          for m in md:
            m.move(MissileDevice.RIGHT)
        elif k in ('f', 'space'):
          for m in md:
            m.move(MissileDevice.FIRE)
        elif k in ('s'):
          for m in md:
            m.move(MissileDevice.STOP)
        elif k in ('q'):
          for m in md:
            m.move(MissileDevice.LEFTUP)
        elif k in ('e'):
          for m in md:
            m.move(MissileDevice.RIGHTUP)
        elif k in ('z'):
          for m in md:
            m.move(MissileDevice.LEFTDOWN)
        elif k in ('c'):
          for m in md:
            m.move(MissileDevice.RIGHTDOWN)
        elif k in ('r'):
          for n in range(3):
            for m in md:
              m.move(MissileDevice.FIRE)
              sleep(0.5)
        elif k in ('v'):
          for m in md:
            if  random.random() > 0.8:
              m.move(MissileDevice.FIRE)
        elif k in ('esc'):
          return
        self.view.keypress(size, k)

class MissileNetwork:

  def main(self):
    host = "localhost"
    port = 20000
    buf  = 1024
    addr = (host,port)

    md = []
    lt = 0
    mc = 0
    af = 0
    lpid = 1

    for missiles in range(10):
      try:
        md.append(MissileDevice(missiles))
      except NoMissilesError, e:
        break
    if missiles==0:
      raise NoMissilesError

    UDPSock = socket(AF_INET,SOCK_DGRAM)
    UDPSock.bind(addr)

    while 1:
      cmd,addr = UDPSock.recvfrom(buf)
      cmd = cmd.strip()

      spa = re.split(r':', cmd)
      k = spa[0]
      ppid = spa[1]

      if not k:
        continue
      else:
        if k == "s":
          if ppid != lpid:
            print "Received a STOP for order %s but last order was %s, ignored" % (ppid, lpid)
            continue

        if abs(time()-lt) < 60:
          mc = mc + 1
        else:
          mc = 0
          af = 0
# you can make it noisey here if you wanted to
#         os.system("aplay sounds/firstwarning.wav &")

        if mc > 60 and af == 0:
          k = "v"
# you can make it noisey here if you wanted to
#         os.system("aplay sounds/secondwarning.wav &")

        print "Received via network at %2.2f command %s/%s (move count: %d, %d)" % (time(), k, ppid, mc, af)

        lt = time()
        lpid = ppid

        if k in ('w', 'up'):
          for m in md:
            m.move(MissileDevice.UP)
        elif k in ('x', 'down'):
          for m in md:
            m.move(MissileDevice.DOWN)
        elif k in ('a', 'left'):
          for m in md:
            m.move(MissileDevice.LEFT)
        elif k in ('d', 'right'):
          for m in md:
            m.move(MissileDevice.RIGHT)
        elif k in ('f', 'space'):
          for m in md:
            m.move(MissileDevice.FIRE)
        elif k in ('s', 'S'):
          for m in md:
            m.move(MissileDevice.STOP)
        elif k in ('q'):
          for m in md:
            m.move(MissileDevice.LEFTUP)
        elif k in ('e'):
          for m in md:
            m.move(MissileDevice.RIGHTUP)
        elif k in ('z'):
          for m in md:
            m.move(MissileDevice.LEFTDOWN)
        elif k in ('c'):
          for m in md:
            m.move(MissileDevice.RIGHTDOWN)
        elif k in ('r'):
          for n in range(3):
            for m in md:
              m.move(MissileDevice.FIRE)
              sleep(0.5)
        elif k in ('v'):
          for m in md:
            if random.random() > 0.9:
              m.move(MissileDevice.FIRE)
              af = 1
        elif k in ('esc'):
          UDPSock.close()
          return

def usage():
  print "Usage:"
  print "  -h | --help : this help"
  print "  -n | --network: simple network listener mode (Read the source Luke!)"
  print "  -v | --version: version"
  sys.exit(2)

def version():
  print "$Id: missile.py,v 1.13 2006/07/25 17:01:24 scott Exp $"
  sys.exit(0)

def main(argv):
  try:
    opts, args = getopt.getopt(argv, "hvn", ["help", "version", "network"])
  except getopt.GetoptError:
    print "Sorry, bad option."
    usage()

  if opts:
    for o, a in opts:
      if o in ("-h", "--help"):
        usage()
      elif o in ("-v", "--version"):
        version()
      elif o in ("-n", "--network"):
        try:
          MissileNetwork().main()
        except NoMissilesError, e:
          print "No WMDs found."
          return
      else:
        try:
          MissileDisplay().main()
        except NoMissilesError, e:
          print "No WMDs found."
          return
  else:
    try:
      MissileDisplay().main()
    except NoMissilesError, e:
      print "No WMDs found."
      return

if __name__=="__main__":
  main(sys.argv[1:])

