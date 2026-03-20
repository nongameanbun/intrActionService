from gateway import *
from interruption.build.Adele import *

handle_dead_function = {
    "Adele_SungMoon_4" : Adele_SungMoon_4,
}

def handle_dead() :
    Rdelay_2(5000)
    cur_build, cur_build_sys = get_running_build()['resp'], get_running_build()['system']
    press_key_with_delay(cur_build_sys['npc_key'], 1500)
    Rdelay_2(5000)
    return "wait"
    # Rdelay_2(5000)
    # cur_build, cur_build_sys = get_running_build()['resp'], get_running_build()['system']
    # press_key_with_delay(cur_build_sys['npc_key'], 1500)
    # Rdelay_2(5000)
    # press_key_with_delay(cur_build_sys['dead_potion_key'], 100)
    # Rdelay_2(1000)

    # if not cur_build or cur_build not in handle_dead_function :
    #     send_message("Dead with no handle")
    #     return "wait"

    # if find_in_screen("notice_dead") != None :
    #     send_message("Dead with no handle")
    #     return "wait"

    # prev = check_pos()
    # print(prev)

    # press_key_with_delay('right', 200)

    # cur = check_pos()
    # print(cur)

    # if prev == cur :
    #     send_message("handled failed")
    #     return "wait"
    
    # if handle_dead_function[cur_build]() :
    #     send_message("handled successfully")
    #     return "continue"
    
    # send_message("handled failed")
    # return "wait"