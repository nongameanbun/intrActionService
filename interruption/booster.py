from gateway import *

def handle_booster() :
    press_key_with_delay("f9", 100)
    Rdelay_2(500)
    press_key_with_delay("f10", 100)
    Rdelay_2(1000)

    detected_result = find_in_screen("booster")

    if detected_result is not None :
        for _ in range(2) :
            press_key_with_delay("left", 100)
            Rdelay_2(500)
        press_key_with_delay("enter", 100)
    return "go"