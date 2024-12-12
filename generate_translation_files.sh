#!/bin/bash
# https://lokalise.com/blog/translating-apps-with-gettext-comprehensive-tutorial/
if [ ! -d "locales" ]; then
   mkdir locales
fi
xgettext -d messages -o locales/messages.pot main.py configuration.py mqtt_client.py zone_control.py --from-code UTF-8

if [ ! -d "locales/hu/LC_MESSAGES" ]; then
    mkdir -p locales/hu/LC_MESSAGES
fi

if [ -f "locales/hu/LC_MESSAGES/messages.po" ]; then
    msgmerge -U locales/hu/LC_MESSAGES/messages.po locales/messages.pot
else
    msginit -l hu_HU.UTF8 -o locales/hu/LC_MESSAGES/messages.po -i locales/messages.pot --no-translator
fi
