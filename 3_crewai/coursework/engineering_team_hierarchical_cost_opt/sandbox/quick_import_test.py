"""Quick import test - just imports app and prints success."""
import sys
sys.stdout.write("importing app...\n")
sys.stdout.flush()
from app import app
sys.stdout.write("app imported successfully\n")
sys.stdout.flush()
