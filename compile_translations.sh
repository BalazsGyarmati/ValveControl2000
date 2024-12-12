#!/bin/bash
# https://lokalise.com/blog/translating-apps-with-gettext-comprehensive-tutorial/
for lang in $(ls -d locales/*/); do
    msgfmt -o ${lang}LC_MESSAGES/messages.mo ${lang}LC_MESSAGES/messages.po
done