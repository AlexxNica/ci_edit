# Copyright 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""A fake curses api intended for making tests. By creating a fake version of
the curses API the ci_edit code can be tested for various inputs and outputs.

The values of constants and function calls are bogus. This was created based on
what ci_edit uses, without regard or reference to the internals of the curses
library."""


from .constants import *
import ascii
import app.curses_util
import inspect
import os
import sys
import time
import traceback
import types


class FakeInput:
  def __init__(self, display):
    self.fakeDisplay = display
    self.setInputs([])

  def setInputs(self, cmdList):
    self.inputs = cmdList
    self.inputsIndex = -1
    self.inBracketedPaste = False
    self.tupleIndex = -1
    self.waitingForRefresh = True

  def next(self):
    if not self.waitingForRefresh:
      while self.inputsIndex + 1 < len(self.inputs):
        self.inputsIndex += 1
        cmd = self.inputs[self.inputsIndex]
        if type(cmd) == types.FunctionType:
          cmd(self.fakeDisplay, self.inputsIndex)
        elif type(cmd) == types.StringType and len(cmd) == 1:
          if (not self.inBracketedPaste) and cmd != ascii.ESC:
            self.waitingForRefresh = True
          return ord(cmd)
        elif (type(cmd) == types.TupleType and len(cmd) > 1 and
            type(cmd[0]) == types.IntType):
          if cmd == app.curses_util.BRACKETED_PASTE_BEGIN:
            self.inBracketedPaste = True
          self.tupleIndex += 1
          if self.tupleIndex >= len(cmd):
            self.tupleIndex = -1
            if cmd == app.curses_util.BRACKETED_PASTE_END:
              self.inBracketedPaste = False
              self.waitingForRefresh = True
            return ERR
          self.inputsIndex -= 1
          return cmd[self.tupleIndex]
        else:
          if (not self.inBracketedPaste) and cmd != ascii.ESC:
            self.waitingForRefresh = True
          return cmd
    return ERR


def testLog(*msg):
  # Remove return to get function call trace.
  return
  functionLine = inspect.stack()[1][2]
  function = inspect.stack()[1][3]
  frame = inspect.stack()[2]
  callingFile = os.path.split(frame[1])[1]
  callingLine = frame[2]
  callingFunction = frame[3]
  caller = "%20s %5s %20s %3s %s " % (callingFile,
        callingLine, callingFunction, functionLine, function)
  print caller + " ".join([repr(i) for i in msg])


getchCallback = None
def setGetchCallback(callback):
  global getchCallback
  getchCallback = callback


# Test output. Use |display| to check the screen output.
class FakeDisplay:
  def __init__(self):
    self.rows = 15
    self.cols = 40
    self.cursorRow = 0
    self.cursorCol = 0
    self.display = None
    self.reset()

  def check(self, row, col, lines):
    for i in range(len(lines)):
      line = lines[i]
      for k in range(len(line)):
        d = self.display[row + i][col + k]
        c = line[k]
        if d != c:
          self.show()
          return "row %s, col %s mismatch '%s' != '%s'" % (
              row + i, col + k, d, c)
    return None

  def get(self):
    return [''.join(self.display[i]) for i in range(self.rows)]

  def show(self):
    print '+' + '-' * self.cols + '+'
    for line in self.get():
      print '|' + line + '|'
      #print [ord(i) for i in line]
    print '+' + '-' * self.cols + '+'

  def reset(self):
    self.display = [
        [u'x' for k in range(self.cols)] for i in range(self.rows)]

fakeDisplay = None
fakeInput = None
mouseEvents = []

def getFakeDisplay():
  return fakeDisplay

def printFakeDisplay():
  fakeDisplay.show()


#####################################


class FakeCursesWindow:
  def __init__(self, rows, cols):
    self.rows = rows
    self.cols = cols
    self.cursorRow = 0
    self.cursorCol = 0

  def addstr(self, *args):
    global fakeDisplay
    try:
      testLog(*args)
      cursorRow = args[0]
      cursorCol = args[1]
      text = args[2].decode('utf-8')
      color = args[3]
      for i in range(len(text)):
        fakeDisplay.display[cursorRow][cursorCol + i] = text[i]
      self.cursorRow = cursorRow + len(text)
      self.cursorCol = cursorCol + len(text[-1])
      if len(text) > 1:
        self.cursorCol = len(text[-1])
      return (1, 1)
    except:
      sys.exit(1)

  def getch(self):
    testLog()
    if 1:
      global getchCallback
      if getchCallback:
        val = getchCallback()
        return val
    val = fakeInput.next()
    if 0 and val != ERR:
      print 'val', val
    return val

  def getyx(self):
    testLog()
    return (self.cursorRow, self.cursorCol)

  def getmaxyx(self):
    testLog()
    return (fakeDisplay.rows, fakeDisplay.cols)

  def keypad(self, a):
    testLog(a)

  def leaveok(self, a):
    testLog(a)

  def move(self, a, b):
    testLog(a, b)
    self.cursorRow = a
    self.cursorCol = b

  def noutrefresh(self):
    pass

  def refresh(self):
    testLog()

  def resize(self, a, b):
    testLog(a, b)

  def scrollok(self, a):
    testLog(a)

  def timeout(self, a):
    testLog(a)


class StandardScreen(FakeCursesWindow):
  def __init__(self):
    global fakeDisplay, fakeInput
    testLog()
    FakeCursesWindow.__init__(self, 0, 0)
    fakeDisplay = FakeDisplay()
    fakeInput = FakeInput(fakeDisplay)
    self.fakeInput = fakeInput

  def setFakeInputs(self, cmdList):
    self.fakeInput.setInputs(cmdList)

  def getmaxyx(self):
    testLog()
    global fakeDisplay
    return (fakeDisplay.rows, fakeDisplay.cols)

  def refresh(self):
    fakeInput.waitingForRefresh = False
    testLog()


def can_change_color():
  testLog()

def color_content():
  testLog()

def color_pair(a):
  testLog(a)
  return 1

def curs_set(a):
  testLog(a)

def error():
  testLog()

def errorpass():
  testLog()

def getch():
  testLog()
  return ERR

def addMouseEvent(mouseEvent):
  testLog()
  return mouseEvents.append(mouseEvent)

def getmouse():
  testLog()
  return mouseEvents.pop()

def has_colors():
  testLog()

def init_color():
  testLog()

def init_pair(*args):
  testLog(*args)

def keyname():
  testLog()

def meta(*args):
  testLog(*args)

def mouseinterval(*args):
  testLog(*args)

def mousemask(*args):
  testLog(*args)

def newwin(*args):
  testLog(*args)
  return FakeCursesWindow(args[0], args[1])

def raw(*args):
  testLog(*args)

def resizeterm():
  pass

def start_color():
  pass

def ungetch(*args):
  testLog(*args)

def use_default_colors():
  pass

def get_pair(*args):
  testLog(*args)

def wrapper(fun, *args, **kw):
  standardScreen = StandardScreen()
  fun(standardScreen, *args, **kw)

