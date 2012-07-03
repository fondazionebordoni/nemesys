from string import ascii_letters, digits, punctuation
from logger import logging

logger = logging.getLogger()

def printData(data):

  index = 0
  size = 16
  bytesRead = len(data)

  logger.debug("================================================================================")
  while index < bytesRead:
      
    output = ''
    output += ('| %04d |  ' % index)
    
    for item in range(size):
      output += data[index + item].encode('hex') + ' '
      if item == 7:
        output += ' '
    
    if size < 8:
      output += ' '
    
    if size < 16:
      for i in range(16-size):
        output += '   '
    
    output += ' | '
      
    for item in range(size):
      char = data[index + item]
      if char in ascii_letters  \
      or char in digits         \
      or char in punctuation    \
      or char == ' ':
          output += char
      else:
          output += '.'
    
    if size < 16:
      for i in range(16-size):
        output += '.'
    
    output += ' | '
    
    logger.debug(output)
    
    index += size
    if bytesRead - index < size:
        size = bytesRead - index
