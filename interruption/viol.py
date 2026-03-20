from gateway import *
import random
import winsound


def handle_viol(event=None):
        
    mouse_move(500 + random.randint(-10, 10), 500 + random.randint(-10, 10))
    if event is not None:
        while not event.is_set():
            time.sleep(0.1)
        return "continue"
    return "wait"