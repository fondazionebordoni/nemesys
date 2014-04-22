#!/bin/sh

# REMINDER: YOU NEED TO RUN THIS SCRIPT VIA SUDO
if [ $UID -ne 0 ]; then
  echo 'Per disinstallare Ne.Me.Sys. occorre essere superutente. Eseguire:\n  sudo ./unistall.sh'
  exit 1
fi

# Kill all processes
/bin/ps -axcopid,command | /usr/bin/grep "executer*" | /usr/bin/awk '{ system("kill -9 "$1) }'

# Remove service script
/bin/rm -rf /Library/LaunchDaemons/it.fub.nemesys.*

# Remove Applications
/bin/rm -rf /Applications/Nemesys

echo 'Disinstallazione avvenuta con successo.'
exit 0

