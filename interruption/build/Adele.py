from gateway import *

def Adele_SungMoon_4() :
    sys = get_running_build()['system']
    if not sys :
        return False
    
    goto_point(138, 84)
    Rdelay_2(500)
    press_key_with_delay(sys['rope_key'], 100)
    Rdelay_2(2000)

    press_key_with_delay('up', 100)
    Rdelay_2(1000)
    goto_point(190, 130)
    Rdelay_2(500)

    press_key_with_delay('up', 100)
    Rdelay_2(2000)

    for _ in range(3) :
        press_key_with_delay('left_alt', 100)
        Rdelay_2(100)


    return True
