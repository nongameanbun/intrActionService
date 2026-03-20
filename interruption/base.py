from gateway import *

def handle_exception(event=None):
    send_message("An exception has occurred.")
    if event is not None:
        while not event.is_set():
            time.sleep(0.1)
        return "continue"
    return "wait"

def handle_user_pause(event=None):
    if event is not None:
        while not event.is_set():
            time.sleep(0.1)
        return "continue"
    return "wait"

def handle_exit(event=None):
    return "exit"