from gateway import *
import random


def handle_go_myster(stack = 0) :
    if stack > 3 :
        send_message("Go Myster Failed.")
        return False

    Rdelay_2(500)
    press_key_with_delay("v", 100)
    Rdelay_2(500)

    detected_result = find_in_screen("mystervil")
    print(f"[handle_go_myster] detected_result: {detected_result}")
    if detected_result is None :
        handle_go_myster(stack + 1)
        return

    x, y = detected_result['center']
    mouse_click('left', 50, x+random.randint(-5, 5), y+random.randint(-2, 2))

    Rdelay_2(500)
    press_key_with_delay("enter", 100)

    Rdelay_2(500)

    press_key_with_delay("v", 100)
    Rdelay_2(500)

    return "wait"


def handle_exitmyster() :
    press_key_with_delay("up", 100)
    Rdelay_2(500)
    return "wait"