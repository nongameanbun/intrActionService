from gateway import *
import random

def handle_shape(event=None):
    mouse_move(500 + random.randint(-10, 10), 500 + random.randint(-10, 10))
    if event is not None:
        while not event.is_set():
            time.sleep(0.1)
        return "continue"
    return "wait"