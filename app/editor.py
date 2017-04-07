# Copyright 2016 The ci_edit Authors. All rights reserved.
# Use of this source code is governed by an Apache-style license that can be
# found in the LICENSE file.

"""Key bindings for the ciEditor."""

from app.curses_util import *
import app.buffer_manager
import app.controller
import curses
import curses.ascii
import os
import re
import subprocess
import text_buffer


# Break up a command line into separate piped processes.
kRePipeChain = re.compile(
    r'''\s*([^|]*"(?:\\"|[^"])*"|[^|]*'(?:\\'|[^'])*'|[^|]*|\|\|)'''
    r'''\s*\|?''')
def functionTest(a, b):
  assert a == b, "%r != %r"%(a, b)
functionTest(kRePipeChain.findall('date'),
    ['date', ''])
functionTest(kRePipeChain.findall('date|wc'),
    ['date', 'wc', ''])
functionTest(kRePipeChain.findall('  date | wc  '),
    ['date ', 'wc  ', ''])
functionTest(kRePipeChain.findall('date|wc|sort'),
    ['date', 'wc', 'sort', ''])
functionTest(kRePipeChain.findall('date || wc | sort'),
    ['date ', '', 'wc ', 'sort', ''])
functionTest(kRePipeChain.findall('date "foo" || wc | sort'),
    ['date "foo"', '', 'wc ', 'sort', ''])
functionTest(kRePipeChain.findall('date "foo" "bar" || wc | sort'),
    ['date "foo" "bar"', '', 'wc ', 'sort', ''])


def parseInt(str):
  i = 0
  k = 0
  if len(str) > i and str[i] in ('+', '-'):
    i += 1
  k = i
  while len(str) > k and str[k].isdigit():
    k += 1
  if k > i:
    return int(str[:k])
  return 0

def test_parseInt():
  assert parseInt('0') == 0
  assert parseInt('0e') == 0
  assert parseInt('qwee') == 0
  assert parseInt('10') == 10
  assert parseInt('+10') == 10
  assert parseInt('-10') == -10
  assert parseInt('--10') == 0
  assert parseInt('--10') == 0


class InteractiveOpener(app.controller.Controller):
  """Open a file to edit."""
  def __init__(self, host, textBuffer):
    app.controller.Controller.__init__(self, host, 'opener')
    self.textBuffer = textBuffer
    self.textBuffer.lines = [""]

  def focus(self):
    app.log.info('InteractiveOpener.focus')
    self.priorPath = self.host.textBuffer.fullPath
    self.commandDefault = self.textBuffer.insertPrintable
    # Create a new text buffer to display dir listing.
    self.host.setTextBuffer(text_buffer.TextBuffer())

  def info(self):
    app.log.info('InteractiveOpener command set')

  def createOrOpen(self):
    if 0:
      expandedPath = os.path.abspath(os.path.expanduser(self.textBuffer.lines[0]))
      app.log.info('createOrOpen\n\n', expandedPath)
      if not os.path.isdir(expandedPath):
        self.host.setTextBuffer(
            app.buffer_manager.buffers.loadTextBuffer(expandedPath))
    self.changeToHostWindow()

  def maybeSlash(self, expandedPath):
    if (self.textBuffer.lines[0] and self.textBuffer.lines[0][-1] != '/' and
        os.path.isdir(expandedPath)):
      self.textBuffer.insert('/')

  def tabCompleteFirst(self):
    """Find the first file that starts with the pattern."""
    dirPath, fileName = os.path.split(self.lines[0])
    foundOnce = ''
    app.log.debug('tabComplete\n', dirPath, '\n', fileName)
    for i in os.listdir(os.path.expandvars(os.path.expanduser(dirPath)) or '.'):
      if i.startswith(fileName):
        if foundOnce:
          # Found more than one match.
          return
        fileName = os.path.join(dirPath, i)
        if os.path.isdir(fileName):
          fileName += '/'
        self.lines[0] = fileName
        self.onChange()
        return

  def tabCompleteExtend(self):
    """Extend the selection to match characters in common."""
    dirPath, fileName = os.path.split(self.textBuffer.lines[0])
    expandedDir = os.path.expandvars(os.path.expanduser(dirPath)) or '.'
    matches = []
    if not os.path.isdir(expandedDir):
      return
    for i in os.listdir(expandedDir):
      if i.startswith(fileName):
        matches.append(i)
      else:
        pass
        #app.log.info('not', i)
    if len(matches) <= 0:
      self.maybeSlash(expandedDir)
      self.onChange()
      return
    if len(matches) == 1:
      self.textBuffer.insert(matches[0][len(fileName):])
      self.maybeSlash(os.path.join(expandedDir, matches[0]))
      self.onChange()
      return
    def findCommonPrefixLength(prefixLen):
      count = 0
      ch = None
      for match in matches:
        if len(match) <= prefixLen:
          return prefixLen
        if not ch:
          ch = match[prefixLen]
        if match[prefixLen] == ch:
          count += 1
      if count and count == len(matches):
        return findCommonPrefixLength(prefixLen + 1)
      return prefixLen
    prefixLen = findCommonPrefixLength(len(fileName))
    self.textBuffer.insert(matches[0][len(fileName):prefixLen])
    self.onChange()

  def setFileName(self, path):
    self.textBuffer.lines = [path]
    self.textBuffer.cursorCol = len(path)
    self.textBuffer.goalCol = self.textBuffer.cursorCol

  def oldAutoOpenOnChange(self):
    path = os.path.expanduser(os.path.expandvars(self.textBuffer.lines[0]))
    dirPath, fileName = os.path.split(path)
    dirPath = dirPath or '.'
    app.log.info('O.onChange', dirPath, fileName)
    if os.path.isdir(dirPath):
      lines = []
      for i in os.listdir(dirPath):
        if i.startswith(fileName):
          lines.append(i)
      if len(lines) == 1 and os.path.isfile(os.path.join(dirPath, fileName)):
        self.host.setTextBuffer(app.buffer_manager.buffers.loadTextBuffer(
            os.path.join(dirPath, fileName)))
      else:
        self.host.textBuffer.lines = [
            os.path.abspath(os.path.expanduser(dirPath))+":"] + lines
    else:
      self.host.textBuffer.lines = [
          os.path.abspath(os.path.expanduser(dirPath))+": not found"]

  def onChange(self):
    return
    path = os.path.abspath(os.path.expanduser(os.path.expandvars(
        self.textBuffer.lines[0])))
    dirPath = path or '.'
    fileName = ''
    if not os.path.isdir(path):
      dirPath, fileName = os.path.split(path)
    app.log.info('O.onChange\n', path, '\n', dirPath, fileName)
    if os.path.isdir(dirPath):
      lines = []
      for i in os.listdir(dirPath):
        if os.path.isdir(i):
          i += '/'
        lines.append(i)
      clip = tuple([dirPath+":"] + lines)
    else:
      clip = tuple([dirPath+": not found"])
    app.log.info(clip)
    self.host.textBuffer.selectionAll()
    self.host.textBuffer.redoAddChange(('v', clip))
    self.host.textBuffer.redo()
    self.host.textBuffer.selectionNone()

  def unfocus(self):
    expandedPath = os.path.abspath(os.path.expanduser(self.textBuffer.lines[0]))
    if os.path.isdir(expandedPath):
      app.log.info('dir\n\n', expandedPath)
      self.host.setTextBuffer(
          app.buffer_manager.buffers.loadTextBuffer(self.priorPath))
    else:
      app.log.info('non-dir\n\n', expandedPath)
      app.log.info('non-dir\n\n',
          app.buffer_manager.buffers.loadTextBuffer(expandedPath).lines[0])
      self.host.setTextBuffer(
          app.buffer_manager.buffers.loadTextBuffer(expandedPath))


class InteractiveFind(app.controller.Controller):
  """Find text within the current document."""
  def __init__(self, host, textBuffer):
    app.controller.Controller.__init__(self, host, 'find')
    self.textBuffer = textBuffer
    self.textBuffer.lines = [""]

  def findNext(self):
    self.findCmd = self.document.textBuffer.findNext

  def findPrior(self):
    self.findCmd = self.document.textBuffer.findPrior

  def findReplace(self):
    self.findCmd = self.document.textBuffer.findReplace

  def focus(self):
    app.log.info('InteractiveFind')
    self.findCmd = self.document.textBuffer.find
    selection = self.document.textBuffer.getSelectedText()
    if selection:
      self.textBuffer.selectionAll()
      # Make a single regex line.
      selection = "\\n".join(selection)
      app.log.info(selection)
      self.textBuffer.insert(selection)
    self.textBuffer.selectionAll()

  def info(self):
    app.log.info('InteractiveFind command set')

  def onChange(self):
    app.log.info('InteractiveFind')
    searchFor = self.textBuffer.lines[0]
    try:
      self.findCmd(searchFor)
    except re.error, e:
      self.error = e.message
    self.findCmd = self.document.textBuffer.find


class InteractiveGoto(app.controller.Controller):
  """Jump to a particular line number."""
  def __init__(self, host, textBuffer):
    app.controller.Controller.__init__(self, host, 'goto')
    self.textBuffer = textBuffer
    self.textBuffer.lines = [""]

  def focus(self):
    app.log.info('InteractiveGoto.focus')
    self.textBuffer.selectionAll()
    self.textBuffer.insert(str(self.document.textBuffer.cursorRow+1))
    self.textBuffer.selectionAll()

  def info(self):
    app.log.info('InteractiveGoto command set')

  def gotoBottom(self):
    app.log.info()
    self.textBuffer.selectionAll()
    self.textBuffer.insert(str(len(self.document.textBuffer.lines)))
    self.changeToHostWindow()

  def gotoHalfway(self):
    self.textBuffer.selectionAll()
    self.textBuffer.insert(str(len(self.document.textBuffer.lines)/2+1))
    self.changeToHostWindow()

  def gotoTop(self):
    app.log.info(self.document)
    self.textBuffer.selectionAll()
    self.textBuffer.insert("0")
    self.changeToHostWindow()

  def cursorMoveTo(self, row, col):
    textBuffer = self.document.textBuffer
    cursorRow = min(max(row - 1, 0), len(textBuffer.lines)-1)
    #app.log.info('cursorMoveTo row', row, cursorRow)
    textBuffer.cursorMove(cursorRow-textBuffer.cursorRow,
        col-textBuffer.cursorCol,
        col-textBuffer.goalCol)
    textBuffer.redo()
    textBuffer.cursorScrollToMiddle()
    textBuffer.redo()

  def onChange(self):
    app.log.info()
    line = ''
    try: line = self.textBuffer.lines[0]
    except: pass
    gotoLine, gotoCol = (line.split(',') + ['0', '0'])[:2]
    self.cursorMoveTo(parseInt(gotoLine), parseInt(gotoCol))


class InteractivePrompt(app.controller.Controller):
  """Extended commands prompt."""
  def __init__(self, host, textBuffer):
    app.controller.Controller.__init__(self, host, 'prompt')
    self.textBuffer = textBuffer
    self.textBuffer.lines = [""]
    self.commands = {
      'build': self.buildCommand,
      'format': self.formatCommand,
      'make': self.makeCommand,
    }
    self.filters = {
      'lower': self.lowerSelectedLines,
      'sort': self.sortSelectedLines,
      'upper': self.upperSelectedLines,
    }

  def buildCommand(self):
    return 'building things'

  def formatCommand(self):
    return 'formatting text'

  def makeCommand(self):
    return 'making stuff'

  def execute(self):
    line = ''
    try: line = self.textBuffer.lines[0]
    except: pass
    if not len(line):
      return
    tb = self.host.textBuffer
    command = self.commands.get(line)
    if command:
      command()
    elif line[0] == '!':
      output = self.shellExecute(line[1:])
      output = tb.doDataToLines(output)
      if tb.selectionMode == app.selectable.kSelectionLine:
        output.append('')
      tb.editPasteLines(tuple(output))
    else:
      lines = list(tb.getSelectedText())
      if not len(lines):
        tb.setMessage('The %s command needs a selection.'%(line,))
        return
      lines = self.filters.get(line, self.unknownCommand)(lines)
      tb.setMessage('Changed %d lines'%(len(lines),))
      if tb.selectionMode == app.selectable.kSelectionLine:
        lines.append('')
      tb.editPasteLines(tuple(lines))
    self.changeToHostWindow()

  def shellExecute(self, commands):
    tb = self.host.textBuffer
    lines = list(tb.getSelectedText())
    #chain = re.split(r'\s*\|\s*', commands.strip())
    chain = kRePipeChain.findall(commands.strip())[:-1]
    app.log.info('chain', chain)
    try:
      process = subprocess.Popen(chain[-1].split(),
          stdin=subprocess.PIPE, stdout=subprocess.PIPE,
          stderr=subprocess.STDOUT);
      if len(chain) == 1:
        output = process.communicate('\n'.join(lines))[0]
      else:
        chain.reverse()
        prior = process
        for i in chain[1:]:
          prior = subprocess.Popen(i.split(),
              stdin=subprocess.PIPE, stdout=prior.stdin,
              stderr=subprocess.STDOUT);
        prior.communicate('\n'.join(lines))
        output = process.communicate()[0]
    except Exception, e:
      tb.setMessage('Error running shell command\n', e)
      return ''
    return output

  def info(self):
    app.log.info('InteractivePrompt command set')

  def lowerSelectedLines(self, lines):
    return [line.lower() for line in lines]

  def sortSelectedLines(self, lines):
    lines.sort()
    return lines

  def upperSelectedLines(self, lines):
    return [line.upper() for line in lines]

  def unknownCommand(self, lines):
    self.host.textBuffer.setMessage('Unknown command')
    return lines
