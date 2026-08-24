#!/usr/bin/env python3
import os
import sys
import json
import redis
import subprocess
import threading
import base64
import io
import wave
import ssl
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

print("All imports successful!")
print(f"Flask version: {Flask.__version__}")
print(f"Python: {sys.version}")