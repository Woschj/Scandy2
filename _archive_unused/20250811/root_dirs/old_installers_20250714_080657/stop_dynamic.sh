#!/bin/bash

echo "========================================"
echo "Scandy - Stoppe alle Abteilungen"
echo "========================================"

echo
echo "Stoppe alle dynamisch erstellten Container..."
echo

python3 stop_dynamic.py

echo 