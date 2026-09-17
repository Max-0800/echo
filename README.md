# Reibot Project
A script that uses an Ollama LLM to run discord bot for a polished and free user experience.

Use this as a reference or inspiration for your future AI hosting needs!

note:
The LLM will shutdown when you have not spoken with it for 5 minutes,
you can keep it alive forever by adding '-1' keepalive in the ollama.chat() funciton in your code.

# REQUIREMENTS & SETUP.
Host machine:
  Install ollama.
  Run an LLM using ollama.
Python:
  Required libs:
  ollama, discord, asyncio, io, psutil, pytz, subprocess, and pynvml
