#!/bin/bash

sudo rm -f /etc/systemd/system/wonderbot.service
sudo cp ../service/wonderbot.service /etc/systemd/system/
sudo systemctl daemon-reload

