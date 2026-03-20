from interruption.base import handle_exception, handle_user_pause, handle_exit
from interruption.viol import handle_viol
from interruption.liecheck import handle_liecheck
from interruption.shape import handle_shape
from interruption.booster import handle_booster
from interruption.myster import handle_go_myster
from interruption.dead import handle_dead

intr_functions = {
    "user pause": handle_user_pause,
    "viol":       handle_viol,
    "liecheck":   handle_liecheck,
    "shape":      handle_shape,
    "exception":  handle_exception,
    "booster":    handle_booster,
    "exit" :      handle_exit,
    "gomyster" :  handle_go_myster,
    "dead":       handle_dead,
    "continue":   lambda event=None: "continue",
}
